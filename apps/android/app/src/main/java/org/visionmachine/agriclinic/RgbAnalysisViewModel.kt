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

class RgbAnalysisViewModel(app:Application):AndroidViewModel(app) {
    private val worker=Executors.newSingleThreadExecutor()
    private val main=Handler(Looper.getMainLooper())
    private val store=RgbHistory(app)
    private var engine:LocalRgbEngine?=null
    @Volatile private var cleared=false
    var ready by mutableStateOf(false);private set
    var busy by mutableStateOf(false);private set
    var message by mutableStateOf("사진 분석 모델을 준비하고 있습니다.");private set
    var selected by mutableStateOf<List<Uri>>(emptyList());private set
    var preview by mutableStateOf<Bitmap?>(null);private set
    var filename by mutableStateOf("");private set
    var current by mutableStateOf<RgbRecord?>(null);private set
    var records by mutableStateOf<List<RgbRecord>>(emptyList());private set
    private fun ui(block:()->Unit) {main.post {if(!cleared) block()}}
    init { worker.execute {
        try {val saved=store.read();ui {records=saved}}
        catch(_:Exception) {ui {message="이전 기록을 읽지 못했습니다. 기존 파일을 보존했습니다."};return@execute}
        try {engine=LocalRgbEngine(app);ui {ready=true;message="준비 완료 · 사진을 골라 주세요."}}
        catch(_:Exception) {ui {message="모델을 불러오지 못했습니다. 앱을 다시 실행해 주세요."}}
    }}
    private fun name(uri:Uri):String=getApplication<Application>().contentResolver.query(uri,arrayOf(OpenableColumns.DISPLAY_NAME),null,null,null)?.use {c->if(c.moveToFirst()) c.getString(0) else null}?.take(180)?:"선택한 사진"
    fun select(uris:List<Uri>) {
        if(busy||uris.isEmpty()) return
        selected=uris.distinct().take(8);current=null;filename="사진 불러오는 중";preview=null;busy=true
        val first=selected.first()
        worker.execute {
            try {
                val n=name(first)
                val image=preview(first)
                ui {preview=image;filename=n;busy=false;message=if(uris.size>8) "최대 8장까지 선택됩니다. 이번 사진의 분석 결과는 아직 없습니다." else "사진 ${selected.size}장 선택 · 분석 대기"}
            } catch(_:Exception) {ui {selected=emptyList();filename="";busy=false;message="사진을 읽을 수 없습니다. 다른 JPEG·PNG 사진을 골라 주세요."}}
        }
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
        if(busy||!ready||selected.isEmpty()) return
        busy=true;current=null
        val inputs=if(all) selected.toList() else selected.take(1)
        worker.execute {
            var done=0
            try {
                for((i,uri) in inputs.withIndex()) {
                    if(cleared) break
                    ui {message="기기에서 사진 분석 중 · ${i+1}/${inputs.size}"}
                    val n=name(uri);val r=engine!!.analyze(uri)
                    val record=RgbRecord(n,r.normal,r.abnormal,r.elapsedMs,r.sha256,Instant.now().toString(),engine!!.modelCard.getString("model_version"))
                    val updated=(store.read()+record).takeLast(200)
                    store.write(updated);done++
                    ui {records=updated;if(i==0) current=record}
                }
                ui {busy=false;message="분석 완료 · ${done}장 기록 · CSV로 저장할 수 있습니다."}
            } catch(e:Exception) {ui {busy=false;message="분석 실패 · ${done}장 기록됨. ${e.message?.take(100)?:"다른 사진으로 다시 시도해 주세요."}"}}
            catch(_:OutOfMemoryError) {ui {busy=false;message="이 사진을 처리할 메모리가 부족합니다. 더 작은 사진을 선택해 주세요."}}
        }
    }
    fun saved(success:Boolean) {message=if(success) "CSV 저장 완료 · ${records.size}건" else "CSV 저장에 실패했습니다. 다시 시도해 주세요."}
    override fun onCleared() {cleared=true;worker.execute {engine?.close()};worker.shutdown();super.onCleared()}
}
