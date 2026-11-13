package org.visionmachine.agriclinic

import android.app.Application
import android.graphics.Bitmap
import android.graphics.ImageDecoder
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.os.Build
import androidx.exifinterface.media.ExifInterface
import android.net.Uri
import android.provider.OpenableColumns
import android.os.Handler
import android.os.Looper
import androidx.lifecycle.AndroidViewModel
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.time.Instant
import java.util.concurrent.Executors
import org.json.JSONObject

data class AnalysisPhotoItem(val uri: Uri, val reference: CaptureRecord, val status: String = "대기",
    val result: RgbRecord? = null, val error: String? = null)

class RgbAnalysisViewModel(app:Application):AndroidViewModel(app) {
    private val worker=Executors.newSingleThreadExecutor()
    private val main=Handler(Looper.getMainLooper())
    private val store=RgbHistory(app)
    private var engine:LocalRgbEngine?=null
    @Volatile private var cleared=false
    var ready by mutableStateOf(false);private set
    var busy by mutableStateOf(false);private set
    var message by mutableStateOf("사진 분석 모델을 준비하고 있습니다.");private set
    var items by mutableStateOf<List<AnalysisPhotoItem>>(emptyList());private set
    val selected get()=items.map {it.uri}
    var focusIndex by mutableStateOf(0);private set
    var defaultCrop by mutableStateOf("tomato");private set
    var cameraPending by mutableStateOf(false);private set
    private val settings=app.getSharedPreferences("analysis_settings_v1",Application.MODE_PRIVATE)
    var sensorWeight by mutableStateOf(settings.getFloat("sensor_weight",0.5f).coerceIn(0f,1f));private set
    fun changeSensorWeight(value:Float) {if(!busy&&value.isFinite()) sensorWeight=value.coerceIn(0f,1f)}
    fun saveSensorWeight() {settings.edit().putFloat("sensor_weight",sensorWeight).apply();message="가중치를 저장했습니다. 다음 분석부터 적용됩니다."}
    private var revision=0L
    var preview by mutableStateOf<Bitmap?>(null);private set
    var filename by mutableStateOf("");private set
    var current by mutableStateOf<RgbRecord?>(null);private set
    var records by mutableStateOf<List<RgbRecord>>(emptyList());private set
    private fun ui(block:()->Unit) {main.post {if(!cleared) block()}}
    init { worker.execute {
        try {val saved=store.read();val pending=CaptureStore(app).pending()!=null;ui {records=saved;cameraPending=pending}}
        catch(_:Exception) {ui {message="이전 기록을 읽지 못했습니다. 기존 파일을 보존했습니다."};return@execute}
        try {engine=LocalRgbEngine(app);ui {ready=true;message="준비 완료 · 촬영하거나 사진을 추가해 주세요."}}
        catch(_:Exception) {ui {message="모델을 불러오지 못했습니다. 앱을 다시 실행해 주세요."}}
    }}
    private fun name(uri:Uri):String=runCatching {getApplication<Application>().contentResolver.query(uri,arrayOf(OpenableColumns.DISPLAY_NAME),null,null,null)?.use {c->if(c.moveToFirst()) c.getString(0) else null}?.take(180)}.getOrNull()?:"선택한 사진"
    fun chooseDefaultCrop(code:String) {if(!busy&&!cameraPending&&CropChoices.any {it.first==code}) defaultCrop=code}
    fun select(uris:List<Uri>)=setInputs(uris,false)
    fun append(uris:List<Uri>)=setInputs(uris,true)
    private fun setInputs(uris:List<Uri>,append:Boolean,capture:CaptureRecord?=null) {
        if(busy||uris.isEmpty()) return
        val previous=if(append) items else emptyList()
        val combined=(previous.map {it.uri}+uris).distinct()
        val accepted=combined.take(8)
        val crop=defaultCrop
        val ticket=++revision
        current=null;filename="사진 불러오는 중";preview=null;busy=true
        worker.execute {
            try {
                val references=PhotoReferenceStore(getApplication())
                val next=accepted.map {uri -> previous.find {it.uri==uri} ?: AnalysisPhotoItem(uri,references.put(uri,capture?.cropCode?:crop,capture?.takeIf {it.photoUri==uri.toString()}))}
                val index=if(capture!=null) next.indexOfFirst {it.uri.toString()==capture.photoUri}.coerceAtLeast(0) else 0
                val image=runCatching {preview(next[index].uri)}.getOrNull()
                val n=name(next[index].uri)
                ui {if(ticket==revision) {items=next;focusIndex=index;preview=image;filename=n;current=next[index].result;busy=false
                    message=if(combined.size>8) "최대 8장입니다. ${combined.size-8}장은 추가하지 않았습니다." else "사진 ${next.size}/8장 · 사진별 작물을 확인하고 모두 분석을 누르세요."}}
            } catch(_:Exception) {ui {busy=false;message="사진 목록을 저장하지 못했습니다. 기존 기록은 보존됩니다."}}
        }
    }
    fun clearSelection() {if(!busy&&!cameraPending) {revision++;items=emptyList();preview=null;filename="";current=null;focusIndex=0;message="사진을 촬영하거나 추가해 주세요."}}
    fun focus(index:Int) {
        if(busy||index !in items.indices) return
        focusIndex=index;current=items[index].result;preview=null;busy=true
        val ticket=++revision;val uri=items[index].uri
        worker.execute {val image=runCatching {preview(uri)}.getOrNull();val n=name(uri)
            ui {if(ticket==revision) {preview=image;filename=n;busy=false}}}
    }
    fun changeCrop(index:Int,code:String) {
        if(busy||index !in items.indices||CropChoices.none {it.first==code}) return
        val item=items[index];busy=true
        worker.execute {
            try {val reference=PhotoReferenceStore(getApplication()).put(item.uri,code,item.reference)
                ui {items=items.mapIndexed {i,value -> if(i==index) value.copy(reference=reference,result=null,status="대기",error=null) else value};if(index==focusIndex) current=null;busy=false}}
            catch(_:Exception) {ui {busy=false;message="작물 정보를 저장하지 못했습니다."}}
        }
    }
    fun prepareCamera(subject:String,batch:String):Uri? {
        if(busy||cameraPending||items.size>=8) {message="최대 8장입니다. 선택을 비우거나 기존 사진을 분석해 주세요.";return null}
        return runCatching {
            val subjectId=subject.trim().ifBlank {"unassigned"};val batchId=batch.trim().ifBlank {"unassigned"}
            require(Regex("[A-Za-z0-9_-]{1,80}").matches(subjectId)&&Regex("[A-Za-z0-9_-]{1,80}").matches(batchId))
            val pending=CaptureStore(getApplication()).prepare(subjectId,batchId,defaultCrop)
            cameraPending=true;Uri.parse(pending.photoUri)
        }.getOrElse {message="촬영 준비 실패 · ID 형식과 미완료 촬영을 확인해 주세요.";null}
    }
    fun completeCamera(success:Boolean) {
        val captureStore=CaptureStore(getApplication())
        try {
            val id=captureStore.pending()?.inspectionId
            val saved=captureStore.finish(success);cameraPending=captureStore.pending()!=null
            if(saved) {
                val record=captureStore.all().first {it.inspectionId==id}
                setInputs(listOf(Uri.parse(record.photoUri)),true,record)
            } else message="촬영이 취소되었거나 저장된 사진이 없습니다. 기존 선택 사진은 유지됩니다."
        } catch(_:Exception) {cameraPending=runCatching {captureStore.pending()!=null}.getOrDefault(true);message="촬영 저장을 완료하지 못했습니다. 촬영 복구를 눌러 주세요."}
    }
    private fun preview(uri:Uri):Bitmap {
        val resolver=getApplication<Application>().contentResolver
        if(Build.VERSION.SDK_INT>=28) return ImageDecoder.decodeBitmap(ImageDecoder.createSource(resolver,uri)) { decoder,info,_ ->
            val ratio=minOf(1.0,900.0/maxOf(info.size.width,info.size.height))
            decoder.setTargetSize(maxOf(1,(info.size.width*ratio).toInt()),maxOf(1,(info.size.height*ratio).toInt()))
            decoder.allocator=ImageDecoder.ALLOCATOR_SOFTWARE
        }
        val bounds=BitmapFactory.Options().apply {inJustDecodeBounds=true}
        resolver.openInputStream(uri)!!.use {BitmapFactory.decodeStream(it,null,bounds)}
        require(bounds.outWidth>0&&bounds.outHeight>0)
        val options=BitmapFactory.Options().apply {inSampleSize=1;while(maxOf(bounds.outWidth,bounds.outHeight)/inSampleSize>1200) inSampleSize*=2}
        val bitmap=resolver.openInputStream(uri)!!.use {BitmapFactory.decodeStream(it,null,options)}?:error("사진 읽기 실패")
        val o=resolver.openInputStream(uri)!!.use {runCatching {ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION,1)}.getOrDefault(1)}
        val matrix=Matrix()
        when(o) {2->matrix.setScale(-1f,1f);3->matrix.setRotate(180f);4->matrix.setScale(1f,-1f)
            5->{matrix.setRotate(90f);matrix.postScale(-1f,1f)};6->matrix.setRotate(90f)
            7->{matrix.setRotate(-90f);matrix.postScale(-1f,1f)};8->matrix.setRotate(-90f)}
        val oriented=Bitmap.createBitmap(bitmap,0,0,bitmap.width,bitmap.height,matrix,true)
        if(oriented!==bitmap) bitmap.recycle()
        return oriented
    }
    fun analyze(all:Boolean) {
        if(busy||!ready||selected.isEmpty()||cameraPending) return
        busy=true;current=null
        val inputs=if(all) items.indices.toList() else listOf(focusIndex)
        val snapshot=items.toList()
        val weight=sensorWeight
        worker.execute {
            var done=0;var failed=0
            for((position,index) in inputs.withIndex()) {
                if(cleared) break
                val input=snapshot[index]
                ui {message="기기에서 사진 분석 중 · ${position+1}/${inputs.size}";items=items.mapIndexed {i,item -> if(i==index) item.copy(status="분석 중",result=null,error=null) else item}}
                try {
                    require(input.reference.cropCode!="eggplant") {"가지는 현재 RGB 모델 적용 범위 밖입니다. 센서 기록만 가능합니다."}
                    val n=name(input.uri);val r=engine!!.analyze(input.uri)
                    val record=attachSensor(RgbRecord(n,r.normal,r.abnormal,r.elapsedMs,r.sha256,Instant.now().toString(),engine!!.modelCard.getString("model_version"),input.reference.cropCode,input.reference.inspectionId),weight)
                    val updated=(store.read()+record).takeLast(200)
                    store.write(updated);done++
                    ui {records=updated;items=items.mapIndexed {i,item -> if(i==index) item.copy(status="완료",result=record,error=null) else item};if(index==focusIndex) current=record}
                } catch(error:Exception) {failed++;ui {items=items.mapIndexed {i,item -> if(i==index) item.copy(status="실패",result=null,error=error.message?.take(100)?:"사진을 읽지 못했습니다.") else item}}}
                catch(_:OutOfMemoryError) {failed++;ui {items=items.mapIndexed {i,item -> if(i==index) item.copy(status="실패",result=null,error="사진 메모리 부족 · 더 작은 사진을 선택해 주세요.") else item}}}
            }
            ui {busy=false;message="분석 완료 · 성공 ${done}장 / 실패 ${failed}장 · 사진별 결과를 확인하세요."}
        }
    }
    private fun attachSensor(record:RgbRecord,weight:Float):RgbRecord {
        val sensor=runCatching {SensorStore(getApplication()).all().firstOrNull {it.sourceCaptureId==record.sourceCaptureId&&record.sourceCaptureId!=null&&it.cropCode==record.cropCode&&it.photoSha256==record.sha256}}.getOrNull()?:return record
        if(record.sensorRecordId==sensor.inspectionId&&record.sensorAssessmentJson!=null) return record
        val assessment=(sensor.assessmentJson?.let {JSONObject(it)}?:SensorScoring.assess(JSONObject(sensor.packetJson),SensorProfileStore(getApplication()).get(record.cropCode!!)))
            .put("sensor_received_at",sensor.receivedAt).toString()
        return CompositeIndex.attach(record.copy(sensorRecordId=sensor.inspectionId,sensorAssessmentJson=assessment),weight)
    }
    fun refreshSensors() {
        val weight=sensorWeight
        worker.execute {
            try {
                val saved=store.read();val seen=mutableSetOf<String>()
                val updated=saved.asReversed().map {record ->
                    if(record.sourceCaptureId!=null&&seen.add(record.sourceCaptureId)) attachSensor(record,weight) else record
                }.asReversed()
                if(updated!=saved) store.write(updated)
                ui {
                    records=updated
                    items=items.map {item -> item.copy(result=item.result?.let {old -> updated.find {it.timestamp==old.timestamp&&it.sha256==old.sha256}?:old})}
                    current=items.getOrNull(focusIndex)?.result
                }
            } catch(_:Exception) {ui {message="센서 연결 기록을 읽지 못했습니다. 사진 분석 기록은 보존됩니다."}}
        }
    }
    fun saved(success:Boolean) {message=if(success) "CSV 저장 완료 · ${records.size}건" else "CSV 저장에 실패했습니다. 다시 시도해 주세요."}
    override fun onCleared() {cleared=true;worker.execute {engine?.close()};worker.shutdown();super.onCleared()}
}
