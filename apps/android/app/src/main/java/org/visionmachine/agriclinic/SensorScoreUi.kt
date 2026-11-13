package org.visionmachine.agriclinic

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONObject
import java.util.Locale

@Composable internal fun CropChooser(code: String, enabled: Boolean = true, choose: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        OutlinedButton({ expanded = true }, enabled = enabled) { Text("작물: ${cropLabel(code)} ▾") }
        DropdownMenu(expanded, { expanded = false }) {
            CropChoices.forEach { (key, label) -> DropdownMenuItem(text = { Text(label) }, onClick = { expanded = false; choose(key) }) }
        }
    }
}

@Composable internal fun SensorProfileDialog(profile: SensorProfile, packet: JSONObject?, dismiss: () -> Unit, save: (SensorProfile) -> Boolean) {
    var context by remember { mutableStateOf(profile.context) }
    var source by remember { mutableStateOf(profile.source) }
    val initial = SensorMetrics.associate { (key, _) -> key to listOf(profile.bands[key]?.low?.toString().orEmpty(),
        profile.bands[key]?.high?.toString().orEmpty(), profile.bands[key]?.tolerance?.toString() ?: "0") }
    var fields by remember { mutableStateOf(initial) }
    var error by remember { mutableStateOf("") }
    AlertDialog(onDismissRequest = dismiss, title = { Text("${cropLabel(profile.crop)} 센서 기준") }, text = {
        LazyColumn(Modifier.heightIn(max = 480.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            item {
                Text("현재 작물·생육단계·주야간에 맞는 기준만 적용하세요. 빈 항목은 점수에서 제외됩니다. 참고 문헌의 모든 조건이 현장에 적용되는 것은 아닙니다.")
                OutlinedTextField(context, { context = it }, label = { Text("재배·측정 조건") })
                OutlinedTextField(source, { source = it }, label = { Text("출처 또는 기준 측정 기록") })
            }
            SensorMetrics.forEach { (key, label) -> item {
                Text(label, fontWeight = FontWeight.Bold)
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    listOf("하한", "상한", "허용편차").forEachIndexed { index, title ->
                        OutlinedTextField(fields.getValue(key)[index], { text ->
                            fields = fields + (key to fields.getValue(key).toMutableList().also { it[index] = text })
                        }, label = { Text(title) }, singleLine = true, modifier = Modifier.weight(1f))
                    }
                }
            } }
            item {
                Text("토양 원시값은 같은 흙·삽입 조건에서 정한 기준을 사용합니다. 수분 %가 아닙니다. 광학은 현재 실측의 게인·노출·채널 조건을 기준과 함께 저장합니다. 토양·광학 기준을 새로 입력하려면 먼저 실측하세요.", style = MaterialTheme.typography.bodySmall)
                Text("허용편차는 사용자가 정하는 여유 범위입니다. 센서 교정 오차를 자동 측정한 값이 아닙니다.", style = MaterialTheme.typography.bodySmall)
                if (error.isNotEmpty()) Text(error, color = MaterialTheme.colorScheme.error)
            }
        }
    }, confirmButton = { TextButton({
        try {
            val bands = fields.mapNotNull { (key, values) ->
                if (values[0].isBlank() && values[1].isBlank()) null
                else key to ReferenceBand(values[0].toDouble(), values[1].toDouble(), values[2].ifBlank { "0" }.toDouble())
            }.toMap()
            val needsRaw = bands.keys.any { it == "soil_raw" || it == "optical_sum" }
            require(!needsRaw || packet?.optString("mode") == "real")
            val conditions = if ("optical_sum" in bands) packet?.let { SensorScoring.opticalConditions(it) } else null
            require("optical_sum" !in bands || packet!!.getJSONObject("extensions").getJSONObject("optical").getBoolean("saturated").not())
            val edited = profile.copy(bands = bands, context = context, source = source,
                opticalConditions = conditions, soilAdcBits = if ("soil_raw" in bands) packet!!.getJSONObject("readings").getInt("soil_adc_bits") else null)
            if (save(edited)) dismiss() else error = "기준을 저장하지 못했습니다. 범위·출처·측정 조건을 확인해 주세요."
        } catch (_: Exception) { error = "하한 < 상한, 허용편차 ≥ 0이어야 합니다. 토양·광학 기준은 유효한 실측 후 저장할 수 있습니다." }
    }) { Text("이 조건으로 기준 적용") } }, dismissButton = { TextButton(dismiss) { Text("닫기") } })
}

@Composable internal fun SensorAssessmentCard(raw: String?, measuredAt: String? = null) {
    if (raw == null) { Text("연결된 센서 점수 없음 · 사진별 USB 실측과 기준 적용 후 표시됩니다."); return }
    val assessment = remember(raw) { runCatching { JSONObject(raw) }.getOrNull() }
    if (assessment == null) { Text("센서 평가 기록을 읽을 수 없습니다."); return }
    val profile = assessment.getJSONObject("profile")
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("센서 기반 · 기준 이탈 점수", fontWeight = FontWeight.Bold)
            Text(if (assessment.isNull("deviation_score")) "전체 점수 산정 조건 부족"
                else String.format(Locale.US, "%.1f / 100점 · 높을수록 기준에서 멀어짐", assessment.getDouble("deviation_score")))
            Text("${cropLabel(profile.getString("crop"))} · 점수 산정 ${assessment.getInt("scored_count")} / 설정 ${assessment.getInt("configured_count")} / 전체 5항목")
            Text(profile.getString("context"), style = MaterialTheme.typography.bodySmall)
            if (measuredAt != null) Text("측정 수신: $measuredAt", style = MaterialTheme.typography.bodySmall)
            else if (assessment.has("sensor_received_at")) Text("측정 수신: ${assessment.getString("sensor_received_at")}",style=MaterialTheme.typography.bodySmall)
            val details = assessment.getJSONArray("details")
            for (index in 0 until details.length()) {
                val detail = details.getJSONObject(index); val key = detail.getString("metric")
                val label = SensorMetrics.find { it.first == key }!!.second
                val status = when (detail.getString("status")) {
                    "SCORED" -> String.format(Locale.US, "값 %.2f · 기준 밖 편차 %.2f · %.1f점", detail.getDouble("value"), detail.getDouble("deviation"), detail.getDouble("score"))
                    "NO_REFERENCE" -> "기준 미설정"
                    "REFERENCE_NOT_APPLIED" -> "기준 적용 필요"
                    "MISSING" -> "미측정"
                    "MOCK" -> "모의 자료 · 실측 점수 제외"
                    else -> "측정 오류·포화 또는 기준 측정조건 불일치"
                }
                Text("$label: $status", style = MaterialTheme.typography.bodySmall)
                profile.getJSONObject("bands").optJSONObject(key)?.let { band ->
                    Text(String.format(Locale.US,"기준 %.2f~%.2f · 허용편차 %.2f",band.getDouble("low"),band.getDouble("high"),band.getDouble("tolerance")),style=MaterialTheme.typography.bodySmall)
                }
            }
            Text("설정된 기준까지의 거리를 계산한 참고 지표입니다. 학습된 센서 AI나 병해 확률이 아닙니다.", style = MaterialTheme.typography.bodySmall)
            Text("근거: ${profile.getString("source")}", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable internal fun CompositeIndexCard(raw: String?) {
    if (raw == null) {Text("종합 지수 없음 · 동일 사진에 연결된 유효 센서 점수가 필요합니다.");return}
    val value=remember(raw) {JSONObject(raw)}
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
            Text("사진 AI + 센서 · 종합 점검 지수(참고)",fontWeight=FontWeight.Bold)
            Text(String.format(Locale.US,"%.1f / 100 · 높을수록 추가 점검 필요",value.getDouble("index")),style=MaterialTheme.typography.titleLarge)
            Text(String.format(Locale.US,"사진 출력 %.1f × %.0f%% + 센서 이탈 %.1f × %.0f%%",value.getDouble("photo_output")*100,
                value.getDouble("photo_weight")*100,value.getDouble("sensor_deviation"),value.getDouble("sensor_weight")*100))
            Text("센서 기준 적용 ${value.getInt("sensor_metrics_used")}/${value.getInt("sensor_metrics_available")}항목",style=MaterialTheme.typography.bodySmall)
            Text("사용자 가중평균 지수이며 병해 확률·학습된 융합 AI 결과가 아닙니다. 사진 결과와 센서 기준·편차를 함께 확인하세요.",style=MaterialTheme.typography.bodySmall)
        }
    }
}
