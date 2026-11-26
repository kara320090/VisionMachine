package org.visionmachine.agriclinic

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withLink
import androidx.compose.ui.unit.dp

@Composable
internal fun CropGuidanceCard(record: RgbRecord) {
    val checks = remember(record.cropCode) { fieldChecks(record.cropCode) }
    val findings = remember(record) { sensorFindings(record) }
    val abnormal = record.abnormal >= .5f
    var expanded by rememberSaveable(record.sha256, record.timestamp, record.cropCode) { mutableStateOf(abnormal) }
    var symptom by rememberSaveable(record.sha256, record.timestamp, record.cropCode) { mutableStateOf<String?>(null) }
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = VisionColors.Mint)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("원인 분석과 대처", style = MaterialTheme.typography.titleMedium)
            for (finding in findings) {
                Text("센서 실측 · ${finding.evidence}", style = MaterialTheme.typography.titleSmall)
                Text(finding.action, style = MaterialTheme.typography.bodyMedium)
            }
            if (findings.isNotEmpty()) Text("측정한 환경이 설정 범위를 벗어났습니다. 잎의 증상과 함께 살펴보세요.")
            if (checks.isEmpty()) {
                Text("이 기록에는 작물별 안내가 없습니다. 작물을 선택해 새로 분석하거나, 증상 부위와 포기 전체를 촬영해 상담에 활용하세요.")
                return@Column
            }
            Text(if (abnormal) "사진에서 이상이 의심됩니다. 아래는 ${cropLabel(record.cropCode)}에서 확인할 원인 후보입니다. 실제 증상과 맞는 항목을 눌러 확인 방법을 보세요."
                else "사진은 정상 쪽입니다. 눈에 띄는 변화가 있다면 직접 확인한 증상으로 대처법을 찾아보세요.")
            if (!abnormal || !expanded) {
                TextButton(onClick = { expanded = !expanded }) { Text(if (expanded) "증상 목록 접기" else "증상으로 원인 살펴보기") }
            }
            if (expanded) {
                for (check in checks) {
                    HorizontalDivider(color = VisionColors.Line)
                    Text(check.cause, style = MaterialTheme.typography.titleSmall)
                    FilterChip(selected = symptom == check.symptom, onClick = {
                        symptom = if (symptom == check.symptom) null else check.symptom
                    }, label = { Text(check.symptom) })
                    if (symptom == check.symptom) {
                        Text(check.verify)
                    }
                    Text("이 증상이 맞을 때", style = MaterialTheme.typography.labelLarge)
                    Text(check.action)
                    if (symptom == check.symptom) {
                        Text(buildAnnotatedString { withLink(LinkAnnotation.Url(check.source)) { append("재배 안내 원문 보기") } },
                            style = MaterialTheme.typography.labelLarge, color = VisionColors.Forest)
                    }
                }
                Text("맞는 증상이 없으면 같은 포기의 잎 앞뒷면과 전체 모습을 다시 촬영하세요. 증상이 번지면 사진과 측정 기록을 가지고 지역 농업기술센터에 문의하세요.",
                    style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
