package org.visionmachine.agriclinic

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.ViewModelProvider
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale

private val Forest=Color(0xFF1F4D3A)
private val Cream=Color(0xFFF7F1E2)
private val Mint=Color(0xFFCFE8D8)
private val Terra=Color(0xFFC0562E)

class AnalysisActivity:ComponentActivity() {
    private lateinit var vm:RgbAnalysisViewModel
    private val photos=registerForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->vm.select(uris) }
    private val export=registerForActivityResult(ActivityResultContracts.CreateDocument("text/csv")) { uri ->
        if(uri!=null) vm.saved(runCatching {contentResolver.openOutputStream(uri,"wt")!!.bufferedWriter(Charsets.UTF_8).use {it.write(RgbHistory.csv(vm.records))}}.isSuccess)
    }
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        vm=ViewModelProvider(this)[RgbAnalysisViewModel::class.java]
        setContent {
            MaterialTheme(colorScheme=lightColorScheme(primary=Forest,secondary=Terra,background=Cream,surface=Color.White)) {
                Surface(Modifier.fillMaxSize(),color=Cream) {
                    AnalysisScreen(vm,{photos.launch(arrayOf("image/jpeg","image/png"))},{export.launch("VisionMachine_results.csv")},
                        {startActivity(Intent(this,MainActivity::class.java))},{startActivity(Intent(this,SensorActivity::class.java))})
                }
            }
        }
    }
}

@Composable private fun AnalysisScreen(vm:RgbAnalysisViewModel,open:()->Unit,save:()->Unit,camera:()->Unit,sensors:()->Unit) {
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
            OutlinedButton(sensors,modifier=Modifier.fillMaxWidth()) {Text("USB 센서 연결 · 측정")}
        }
        item {
            Button(open,enabled=!vm.busy,modifier=Modifier.fillMaxWidth()) {Text("1  사진 선택 · 최대 8장")}
            Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                Button({vm.analyze(false)},enabled=vm.ready&&!vm.busy&&vm.selected.isNotEmpty(),modifier=Modifier.weight(1f),colors=ButtonDefaults.buttonColors(containerColor=Terra)) {Text("2  사진 분석")}
                OutlinedButton({vm.analyze(true)},enabled=vm.ready&&!vm.busy&&vm.selected.size>1,modifier=Modifier.weight(1f)) {Text("선택 사진 일괄 분석")}
            }
            if(vm.busy) LinearProgressIndicator(Modifier.fillMaxWidth().padding(top=10.dp))
            Text(vm.message,color=Forest,fontSize=13.sp,modifier=Modifier.padding(top=10.dp))
        }
        item {
            Card(colors=CardDefaults.cardColors(containerColor=Color.White),shape=RoundedCornerShape(20.dp)) {
                Column(Modifier.fillMaxWidth().padding(16.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
                    Text(if(vm.filename.isEmpty()) "고른 사진" else "고른 사진 · ${vm.filename}",fontWeight=FontWeight.Bold,color=Forest)
                    vm.preview?.let {Image(it.asImageBitmap(),"선택한 작물 사진",Modifier.fillMaxWidth().height(230.dp),contentScale=ContentScale.Fit)}
                        ?:Box(Modifier.fillMaxWidth().height(120.dp).background(Cream),contentAlignment=Alignment.Center) {Text("사진을 선택해 주세요",color=Forest)}
                    val r=vm.current
                    Text(r?.label?:"분석 대기",fontSize=26.sp,fontWeight=FontWeight.Bold,color=if(r!=null&&r.abnormal>=.5f) Terra else Forest)
                    if(r!=null) {
                        Score("정상",r.normal,Forest);Score("이상",r.abnormal,Terra)
                        Text("모델 출력값이며 보정된 진단 확률이 아닙니다.\n${r.millis}ms · ${r.name}",fontSize=11.sp)
                    } else Text("사진을 바꾸면 결과가 초기화됩니다. 분석을 실행해 주세요.",fontSize=12.sp)
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
            Text("이 사진 점검은 RGB 모델만 사용합니다. USB 센서·서버 통합 진단과 별개의 시험 경로이며 센서 측정값을 만들지 않습니다.",fontSize=11.sp,modifier=Modifier.padding(bottom=20.dp))
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
