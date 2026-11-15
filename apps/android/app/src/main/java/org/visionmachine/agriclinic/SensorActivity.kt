package org.visionmachine.agriclinic

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.core.view.WindowCompat
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelProvider
import org.json.JSONObject
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

class SensorActivity : ComponentActivity() {
    private lateinit var vm: SensorViewModel
    private val export = registerForActivityResult(ActivityResultContracts.CreateDocument("text/csv")) { uri ->
        if (uri != null) vm.export(uri)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars = true
        vm = ViewModelProvider(this)[SensorViewModel::class.java]
        if (savedInstanceState == null) vm.selectId(intent.getStringExtra("source_capture_id"))
        setContent {
            VisionTheme {
                Surface(color = VisionColors.Cream) {
                SensorScreen(vm, { export.launch("VisionMachine_sensor_records.csv") },
                    { startActivity(Intent(this, MainActivity::class.java)) }, ::openPhoto, ::finish)
                }
            }
        }
    }

    override fun onResume() { super.onResume(); if (::vm.isInitialized) vm.refresh() }
    override fun onStop() {
        if (::vm.isInitialized && !isChangingConfigurations && vm.usb.connected) vm.disconnect()
        super.onStop()
    }

    private fun openPhoto(record: SensorRecord) {
        val uri = record.photoUri ?: return
        try {
            startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(Uri.parse(uri), "image/jpeg")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
        } catch (_: Exception) { vm.reportPhotoError() }
    }
}

@Composable private fun SensorScreen(vm: SensorViewModel, export: () -> Unit, camera: () -> Unit, openPhoto: (SensorRecord) -> Unit, back: () -> Unit) {
    var choosePhoto by remember { mutableStateOf(false) }
    var editProfile by remember { mutableStateOf(false) }
    LazyColumn(Modifier.fillMaxSize().systemBarsPadding(), contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)) {
        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                IconButton(back) { Icon(VisionIcons.Back, "사진 분석으로 돌아가기") }
                Text("USB 센서", Modifier.weight(1f), style = MaterialTheme.typography.titleMedium)
                StatusPill(if (vm.usb.connected) "연결됨" else "연결 대기", warning = !vm.usb.connected)
            }
        }
        item {
            Surface(shape = RoundedCornerShape(26.dp), color = VisionColors.Forest) {
                Row(Modifier.fillMaxWidth().padding(24.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("센서로 더 자세하게", style = MaterialTheme.typography.headlineMedium, color = Color.White)
                        Text("토양 · 온습도 · 광학 · 표면온도", style = MaterialTheme.typography.bodySmall, color = VisionColors.Sage)
                    }
                    Icon(VisionIcons.Sensor, null, Modifier.size(40.dp), tint = VisionColors.Sage)
                }
            }
        }
        item {
            VisionCard {
                    Text("장치 연결·측정", style = MaterialTheme.typography.titleLarge)
                    Text(vm.message)
                    if (vm.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        OutlinedButton(vm::connect, enabled = !vm.busy && !vm.usb.connected, modifier = Modifier.weight(1f)) { Text("USB 연결") }
                        TextButton(vm::disconnect, enabled = vm.usb.connected || vm.usb.busy, modifier = Modifier.weight(1f)) { Text("연결 해제") }
                    }
                    Button(vm::measure, enabled = vm.usb.connected && !vm.busy, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) {
                        Icon(VisionIcons.Sensor, null, Modifier.size(20.dp)); Spacer(Modifier.width(8.dp))
                        Text("네 센서 측정 · 저장")
                    }
            }
        }
        item {
            VisionCard {
            Text("연결할 사진", style = MaterialTheme.typography.titleMedium)
            Text(vm.selectedPhoto?.let { "${cropLabel(it.cropCode)} · ${it.subjectId} · ${if (it.capturedAt.isBlank()) "가져온 사진 · 촬영시각 미상" else displaySensorTime(it.capturedAt)}" } ?: "사진 없이 측정")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton({ choosePhoto = true }, enabled = !vm.busy) { Text("촬영 사진 선택") }
                TextButton(camera, enabled = !vm.busy) { Text("사진 촬영·기록") }
            }
            Text("선택한 사진과 실측값을 함께 기록합니다. 사진 분석 결과는 센서 측정과 별도로 표시됩니다.", style = MaterialTheme.typography.bodySmall)
            }
        }
        item {
            VisionCard {
                Text("작물·평가 기준", style = MaterialTheme.typography.titleMedium)
                CropChooser(vm.selectedCrop, enabled = !vm.busy && vm.selectedPhoto == null, choose = vm::chooseCrop)
                Text("연결 사진이 있으면 해당 사진의 작물 기준을 사용합니다.", style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
                OutlinedButton({ editProfile = true }, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) { Text("작물별 센서 기준 설정") }
                Text(if (vm.profile.applied) "적용 기준: ${vm.profile.context}" else "재배 조건과 출처를 확인해 기준을 적용하면 센서 점수가 표시됩니다.", style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
            }
        }
        vm.current?.let { record -> item { SensorValues(record, "이번 측정") } }
        item {
            SectionHeading("측정 이력", "${vm.records.size}건 보관 중") {
                IconButton(export, enabled = vm.records.isNotEmpty() && !vm.busy) { Icon(VisionIcons.Download, "전체 이력 CSV 저장") }
            }
            Text("최근 20건을 표시하며 200건을 기기에 보관합니다. 토양 원시값은 보정된 수분율(%)이 아닙니다.", style = MaterialTheme.typography.bodySmall)
        }
        if (vm.records.isEmpty()) item {
            VisionCard {
                Text("아직 측정 기록이 없습니다", style = MaterialTheme.typography.titleMedium)
                Text("USB 장치를 연결하고 측정하면 실제 수신값이 저장됩니다.", style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
            }
        }
        items(vm.records.take(20), key = { it.inspectionId }) { record ->
            SensorValues(record, "저장된 측정")
            if (record.photoUri != null) TextButton({ openPhoto(record) }) { Text("연결 사진 보기") }
        }
    }
    if (editProfile) SensorProfileDialog(vm.profile, vm.current?.let { JSONObject(it.packetJson) }, { editProfile = false }, vm::saveProfile)
    if (choosePhoto) AlertDialog(onDismissRequest = { choosePhoto = false }, title = { Text("촬영 사진 선택") },
        text = {
            LazyColumn(Modifier.heightIn(max = 360.dp)) {
                item { TextButton({ vm.select(null); choosePhoto = false }) { Text("사진 없이 측정") } }
                items(vm.photos, key = { it.inspectionId }) { photo ->
                    TextButton({ vm.select(photo); choosePhoto = false }) {
                        Text("${cropLabel(photo.cropCode)} · ${photo.subjectId}\n${if (photo.capturedAt.isBlank()) "촬영시각 미상" else displaySensorTime(photo.capturedAt)}")
                    }
                }
                if (vm.photos.isEmpty()) item { Text("촬영·기록 화면에서 먼저 사진을 저장해 주세요.") }
            }
        }, confirmButton = { TextButton({ choosePhoto = false }) { Text("닫기") } })
}

@Composable private fun SensorValues(record: SensorRecord, title: String) {
    val packet = remember(record.packetJson) { JSONObject(record.packetJson) }
    val readings = packet.getJSONObject("readings")
    val optical = packet.optJSONObject("extensions")?.optJSONObject("optical")
    val surface = packet.optJSONObject("extensions")?.optJSONObject("surface_temperature")
    val errors = packet.getJSONArray("errors")
    VisionCard {
            Text("$title · ${displaySensorTime(record.receivedAt)}", fontWeight = FontWeight.Bold)
            if (packet.getString("mode") == "mock") Text("모의 시험자료", color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.Bold)
            Text("토양 원시값: ${readings.sensorValue("soil_raw")} / ${((1 shl readings.getInt("soil_adc_bits")) - 1)}")
            Text("외기 온도: ${readings.sensorValue("air_temp_c", " °C")} · 상대습도: ${readings.sensorValue("air_rh_pct", " %")}")
            Text("표면온도: ${surface?.sensorValue("object_temp_c", " °C") ?: "미측정"}")
            if (surface != null) Text("적외선 센서 자체 온도: ${surface.sensorValue("ambient_temp_c", " °C")}", style = MaterialTheme.typography.bodySmall)
            Text("광학 원시값", fontWeight = FontWeight.Bold)
            if (optical == null) Text("미측정") else {
                val counts = optical.getJSONArray("raw_counts")
                val labels = OPTICAL_CHANNEL_ORDER.split(',')
                Text((0 until 12).joinToString(" · ") { "${labels[it]} ${counts.getInt(it)}" })
                Text("게인 ${optical.getDouble("gain_x")}× · 노출당 ${optical.getDouble("integration_time_ms")}ms · 주변광", style = MaterialTheme.typography.bodySmall)
                if (optical.getBoolean("saturated")) Text("광학값이 포화됐습니다. 빛을 줄여 다시 측정해 주세요.", color = MaterialTheme.colorScheme.error)
            }
            if (errors.length() > 0) {
                Text("측정 확인사항", color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.Bold)
                (0 until errors.length()).forEach { index -> Text(sensorErrorText(errors.getString(index)), color = MaterialTheme.colorScheme.error) }
            }
            if (record.photoUri != null) Text("연결 사진: ${record.cropCode.orEmpty()} · ${record.subjectId.orEmpty()}", style = MaterialTheme.typography.bodySmall)
            SensorAssessmentCard(record.assessmentJson, record.receivedAt)
    }
}

private fun JSONObject.sensorValue(key: String, suffix: String = ""): String = if (isNull(key)) "미측정" else get(key).toString() + suffix
private fun displaySensorTime(value: String): String = runCatching {
    DateTimeFormatter.ofPattern("MM-dd HH:mm:ss", Locale.KOREA).withZone(ZoneId.systemDefault()).format(Instant.parse(value))
}.getOrDefault(value)
private fun sensorErrorText(code: String): String = when {
    code.startsWith("sht31_") -> "온습도 센서를 읽지 못했습니다. 센서 연결을 확인해 주세요."
    code == "as7341_saturated" -> "광학값 포화: 빛을 줄여 다시 측정해 주세요."
    code.startsWith("as7341_") -> "광학 센서를 읽지 못했습니다. 센서 연결을 확인해 주세요."
    code.startsWith("mlx90614_") -> "표면온도 센서의 통신·측정 검사를 통과하지 못했습니다. 다시 측정해 주세요."
    code.startsWith("soil_") -> "토양 원시값을 읽지 못했습니다. 프로브 연결을 확인해 주세요."
    else -> "측정 요청을 처리하지 못했습니다. 장치를 다시 연결해 주세요."
}
