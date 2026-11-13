package org.visionmachine.agriclinic

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.PickVisualMediaRequest
import androidx.core.view.WindowCompat
import androidx.lifecycle.ViewModelProvider
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale
import kotlin.math.roundToInt

private val Forest=Color(0xFF1F4D3A)
private val Cream=Color(0xFFF7F1E2)
private val Mint=Color(0xFFCFE8D8)
private val Terra=Color(0xFFC0562E)

class AnalysisActivity:ComponentActivity() {
    private lateinit var vm:RgbAnalysisViewModel
    private val photos=registerForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(8)) { uris ->
        uris.forEach { uri -> runCatching {contentResolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION)} }
        vm.append(uris)
    }
    private val filePhotos=registerForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) {uris ->
        uris.forEach {uri ->runCatching {contentResolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION)}}
        vm.append(uris)
    }
    private val camera=registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->vm.completeCamera(success) }
    private val export=registerForActivityResult(ActivityResultContracts.CreateDocument("text/csv")) { uri ->
        if(uri!=null) vm.saved(runCatching {contentResolver.openOutputStream(uri,"wt")!!.bufferedWriter(Charsets.UTF_8).use {it.write(RgbHistory.csv(vm.records))}}.isSuccess)
    }
    override fun onResume() {super.onResume();if(::vm.isInitialized) vm.refreshSensors()}
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.getInsetsController(window,window.decorView).isAppearanceLightStatusBars=true
        vm=ViewModelProvider(this)[RgbAnalysisViewModel::class.java]
        setContent {
            MaterialTheme(colorScheme=lightColorScheme(primary=Forest,secondary=Terra,background=Cream,surface=Color.White)) {
                Surface(Modifier.fillMaxSize(),color=Cream) {
                    AnalysisScreen(vm,{photos.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))},{export.launch("VisionMachine_results.csv")},
                        {startActivity(Intent(this,MainActivity::class.java))},
                        {id ->startActivity(Intent(this,SensorActivity::class.java).apply {if(id!=null) putExtra("source_capture_id",id)})},
                        {subject,batch ->vm.prepareCamera(subject,batch)?.let {uri ->try {camera.launch(uri)} catch(_:Exception) {vm.completeCamera(false)}}},
                        {filePhotos.launch(arrayOf("image/jpeg","image/png"))})
                }
            }
        }
    }
}

@Composable private fun AnalysisScreen(vm:RgbAnalysisViewModel,open:()->Unit,save:()->Unit,camera:()->Unit,sensors:(String?)->Unit,takePicture:(String,String)->Unit,files:()->Unit) {
    var showIds by rememberSaveable {mutableStateOf(false)}
    var subject by rememberSaveable {mutableStateOf("")}
    var batch by rememberSaveable {mutableStateOf("")}
    LazyColumn(Modifier.fillMaxSize().systemBarsPadding(),verticalArrangement=Arrangement.spacedBy(14.dp),contentPadding=PaddingValues(18.dp)) {
        item {
            Column(Modifier.fillMaxWidth().background(Forest,RoundedCornerShape(24.dp)).padding(22.dp)) {
                Text("비전머신",color=Color.White,fontSize=29.sp,fontWeight=FontWeight.Bold)
                Text("작물 사진으로 상태를 한 번 더 살펴보세요",color=Mint,fontSize=15.sp,modifier=Modifier.padding(top=8.dp))
                Text("사진은 이 기기에서 처리됩니다",color=Color.White,fontSize=12.sp,modifier=Modifier.padding(top=12.dp))
            }
        }
        item {
            Text("사진 점검",color=Forest,fontSize=21.sp,fontWeight=FontWeight.Bold)
            Text("바질 · 청경채 · 오이 · 케일 · 상추 · 고추 · 로즈마리 · 토마토",fontSize=12.sp,color=Forest,modifier=Modifier.padding(top=6.dp))
            Text("사진 분석은 상태 점검을 돕는 시험 기능입니다. 재배 문제의 원인이나 현장 정확도를 보장하지 않습니다.",fontSize=12.sp,modifier=Modifier.padding(top=6.dp))
        }
        item {
            OutlinedButton({sensors(null)},modifier=Modifier.fillMaxWidth()) {Text("USB 센서 연결 · 측정")}
        }
        item {
            CropChooser(vm.defaultCrop,enabled=!vm.busy&&!vm.cameraPending,choose=vm::chooseDefaultCrop)
            Text("새 사진의 작물입니다. 추가한 뒤 사진별로 바꿀 수 있습니다.",fontSize=11.sp)
            Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                Button({takePicture(subject,batch)},enabled=!vm.busy&&!vm.cameraPending&&vm.selected.size<8,modifier=Modifier.weight(1f)) {Text("바로 촬영")}
                OutlinedButton(open,enabled=!vm.busy&&!vm.cameraPending&&vm.selected.size<8,modifier=Modifier.weight(1f)) {Text("사진 추가 ${vm.selected.size}/8")}
            }
            TextButton(files,enabled=!vm.busy&&!vm.cameraPending&&vm.selected.size<8) {Text("파일에서 여러 장 추가")}
            TextButton({showIds=!showIds},enabled=!vm.busy&&!vm.cameraPending) {Text("개체·묶음 ID 입력(선택)")}
            if(showIds) {
                OutlinedTextField(subject,{subject=it},label={Text("개체 ID · 영문/숫자/_/-")},enabled=!vm.busy&&!vm.cameraPending)
                OutlinedTextField(batch,{batch=it},label={Text("묶음 ID · 영문/숫자/_/-")},enabled=!vm.busy&&!vm.cameraPending)
                Text("비워 두면 미지정(unassigned)으로 기록합니다.",fontSize=11.sp)
            }
            if(vm.cameraPending) OutlinedButton({vm.completeCamera(true)},enabled=!vm.busy) {Text("촬영 복구·정리")}
            Button({vm.analyze(true)},enabled=vm.ready&&!vm.busy&&!vm.cameraPending&&vm.selected.isNotEmpty(),modifier=Modifier.fillMaxWidth(),colors=ButtonDefaults.buttonColors(containerColor=Terra)) {Text("선택 ${vm.selected.size}장 모두 분석")}
            Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                OutlinedButton({vm.analyze(false)},enabled=vm.ready&&!vm.busy&&!vm.cameraPending&&vm.selected.isNotEmpty(),modifier=Modifier.weight(1f)) {Text("미리보기 사진만 분석")}
                TextButton(vm::clearSelection,enabled=!vm.busy&&!vm.cameraPending,modifier=Modifier.weight(1f)) {Text("선택 비우기")}
            }
            if(vm.busy) LinearProgressIndicator(Modifier.fillMaxWidth().padding(top=10.dp))
            Text(vm.message,color=Forest,fontSize=13.sp,modifier=Modifier.padding(top=10.dp))
            Text("종합 지수 가중치 · 사진 ${100-(vm.sensorWeight*100).roundToInt()}% / 센서 ${(vm.sensorWeight*100).roundToInt()}%",fontSize=12.sp)
            Slider(vm.sensorWeight,vm::changeSensorWeight,enabled=!vm.busy,onValueChangeFinished=vm::saveSensorWeight,steps=9)
            Text("두 점수의 가중평균을 표시하는 참고 지수입니다. 가중치는 학습한 값이 아니며, 변경값은 다음 분석에 적용됩니다.",fontSize=11.sp)
        }
        item {
            Card(colors=CardDefaults.cardColors(containerColor=Color.White),shape=RoundedCornerShape(20.dp)) {
                Column(Modifier.fillMaxWidth().padding(16.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
                    Text(if(vm.filename.isEmpty()) "고른 사진" else "고른 사진 · ${vm.filename}",fontWeight=FontWeight.Bold,color=Forest)
                    vm.preview?.let {Image(it.asImageBitmap(),"선택한 작물 사진",Modifier.fillMaxWidth().height(230.dp),contentScale=ContentScale.Fit)}
                        ?:Box(Modifier.fillMaxWidth().height(120.dp).background(Cream),contentAlignment=Alignment.Center) {Text("사진을 선택해 주세요",color=Forest)}
                    val r=vm.current
                    Text(r?.label?:if(vm.items.getOrNull(vm.focusIndex)?.error!=null) "분석 실패" else "분석 대기",fontSize=26.sp,fontWeight=FontWeight.Bold,color=if(r!=null&&r.abnormal>=.5f) Terra else Forest)
                    if(r!=null) {
                        Score("정상",r.normal,Forest);Score("이상",r.abnormal,Terra)
                        Text("모델 출력값이며 보정된 진단 확률이 아닙니다.\n${r.millis}ms · ${r.name}",fontSize=11.sp)
                        SensorAssessmentCard(r.sensorAssessmentJson)
                        CompositeIndexCard(r.compositeJson)
                    } else Text("사진을 바꾸면 결과가 초기화됩니다. 분석을 실행해 주세요.",fontSize=12.sp)
                }
            }
        }
        itemsIndexed(vm.items,key={_,item ->item.reference.inspectionId}) {index,item ->
            Card(colors=CardDefaults.cardColors(containerColor=Color.White)) {
                Column(Modifier.fillMaxWidth().padding(14.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
                    Text("사진 ${index+1} · ${item.status}${if(index==vm.focusIndex) " · 미리보기 중" else ""}",fontWeight=FontWeight.Bold)
                    CropChooser(item.reference.cropCode,enabled=!vm.busy&&!vm.cameraPending) {vm.changeCrop(index,it)}
                    item.result?.let {r ->Text("${r.label} · 이상 출력 ${"%.6f".format(Locale.US,r.abnormal)}",color=Forest)}
                    item.result?.compositeJson?.let {raw ->Text("종합 지수 ${"%.1f".format(Locale.US,org.json.JSONObject(raw).getDouble("index"))} / 100",fontWeight=FontWeight.Bold)}
                    item.error?.let {Text(it,color=Terra)}
                    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        TextButton({vm.focus(index)},enabled=!vm.busy&&!vm.cameraPending) {Text("사진·결과 보기")}
                        OutlinedButton({sensors(item.reference.inspectionId)},enabled=!vm.busy&&!vm.cameraPending) {Text("이 사진에 센서 측정")}
                    }
                    if(item.result?.sensorAssessmentJson!=null) Text("센서 점수 연결됨 · 사진·결과 보기에서 확인",fontSize=11.sp)
                }
            }
        }
        item {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceBetween) {
                Text("누적 기록 ${vm.records.size}건",fontWeight=FontWeight.Bold,fontSize=19.sp,color=Forest)
                OutlinedButton(save,enabled=vm.records.isNotEmpty()&&!vm.busy) {Text("3  CSV 저장")}
            }
            Text("최근 200건을 기기에 보관합니다. 입력 파일 해시·결과·모델 버전을 함께 저장합니다.",fontSize=11.sp)
        }
        items(vm.records.asReversed()) {r ->
            Card(colors=CardDefaults.cardColors(containerColor=Color.White)) {
                Column(Modifier.fillMaxWidth().padding(14.dp)) {
                    Text(r.name,fontWeight=FontWeight.Bold,maxLines=2)
                    Text("${r.label} · 정상 ${"%.6f".format(Locale.US,r.normal)} / 이상 ${"%.6f".format(Locale.US,r.abnormal)}",fontSize=12.sp,color=Forest)
                    Text(r.timestamp,fontSize=10.sp)
                }
            }
        }
        item {
            HorizontalDivider()
            TextButton(camera,enabled=!vm.busy) {Text("기존 촬영·기록 화면 열기")}
            Text("사진 AI 출력과 센서 기준 이탈 점수를 구분합니다. 센서는 사진마다 직접 연결하며 다른 대상의 최근 측정값을 자동으로 붙이지 않습니다.",fontSize=11.sp,modifier=Modifier.padding(bottom=20.dp))
        }
    }
}
@Composable private fun Score(label:String,value:Float,color:Color) {
    Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(10.dp)) {
        Text(label,Modifier.width(35.dp),fontSize=13.sp)
        LinearProgressIndicator(progress={value},modifier=Modifier.weight(1f),color=color,trackColor=Cream)
        Text("%.6f".format(Locale.US,value),fontSize=12.sp)
    }
}
