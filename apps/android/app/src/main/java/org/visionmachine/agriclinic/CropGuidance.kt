package org.visionmachine.agriclinic

import org.json.JSONObject
import java.util.Locale

/** Conditional field checks. A photo classification alone cannot identify these symptoms. */
internal data class FieldCheck(
    val symptom: String,
    val cause: String,
    val verify: String,
    val action: String,
    val source: String,
)

private const val maryland = "https://extension.umd.edu/resource/"
private const val minnesota = "https://extension.umn.edu/"

private val blossomEnd = FieldCheck(
    "열매의 꽃이 붙었던 끝이 검고 움푹 들어갔어요", "배꼽썩음과 불규칙한 수분 공급",
    "꼭지 반대편부터 변했는지, 최근 흙이 바짝 말랐다가 한꺼번에 젖은 적이 있는지 확인하세요.",
    "뿌리 주변 흙의 수분을 확인해 물 주는 간격을 조절하세요. 이후 새로 자라는 열매에 같은 자국이 생기는지 보세요.",
    minnesota + "agriculture/specialty-crops/vegetable-farming/irrigation-strategies-for-vegetables",
)
private val aphids = FieldCheck(
    "새잎이 말리고 작은 벌레가 모여 있어요", "진딧물의 흡즙 피해",
    "말린 잎을 펼쳐 뒷면과 새순에 작은 벌레 무리나 끈적한 분비물이 있는지 살펴보세요.",
    "벌레가 확인된 잎은 줄기를 받치고 물로 씻어 내세요. 다음 점검 때 새순에 다시 모이는지 확인하세요.",
    maryland + "aphids-home-gardens",
)
private val leafHoles = FieldCheck(
    "어린잎에 작은 구멍이 여러 개 생겼어요", "벼룩잎벌레류의 잎 피해",
    "잎에 난 구멍의 크기를 살피고, 잎을 건드릴 때 작은 딱정벌레가 튀는지 확인하세요.",
    "주변 어린 포기도 살펴보세요. 벌레가 없는 새 모종은 심은 직후 방충망으로 덮고 가장자리를 고정하세요.",
    minnesota + "garden-and-home/yard-and-garden/yard-and-garden-insects/flea-beetles",
)
private val bolting = FieldCheck(
    "잎 사이로 긴 꽃대가 올라왔어요", "기온과 생육 단계에 따른 추대",
    "가운데 줄기가 길어지고 끝에 꽃봉오리가 보이는지, 최근 더운 날이 이어졌는지 확인하세요.",
    "남은 포기는 흙이 마르지 않게 관리하고, 다음 파종은 서늘한 시기에 나누어 하세요.",
    minnesota + "garden-and-home/yard-and-garden/gardening-in-minnesota/yard-and-garden-problems/non-pest-issues-in-cool-season-crops",
)
private val cucumberFruit = FieldCheck(
    "열매 한쪽 끝만 가늘게 자라요", "수분이 필요한 오이 품종에서의 꽃가루받이 부족",
    "품종 설명에서 단위결과성 여부와 꽃이 핀 시기의 벌 방문·방충망 사용 여부를 확인하세요.",
    "꽃가루받이가 필요한 품종이라면 개화기에 망을 열어 벌이 접근하게 하세요. 이후 맺히는 열매의 모양을 비교하세요.",
    maryland + "key-common-problems-cucumbers",
)
private val basilLeaf = FieldCheck(
    "잎 윗면은 노랗고 뒷면에는 회색 솜털이 보여요", "바질 노균병 가능성",
    "노랗게 변한 곳의 바로 뒷면과 이웃 포기에 같은 흔적이 있는지 확인하세요.",
    "포기 사이를 띄워 통풍을 확보하세요. 증상이 번지면 잎 앞뒷면 사진을 찍어 농업기술센터에 확인을 요청하세요.",
    maryland + "downy-mildew-basil-home-garden",
)
private val wetRoots = FieldCheck(
    "흙이 오래 젖어 있고 포기가 시들어요", "배수 불량에 따른 뿌리 스트레스",
    "흙 속의 습기와 화분 받침에 고인 물, 막힌 배수구를 확인하세요.",
    "고인 물을 비우고 물 빠짐을 확보하세요. 흙의 습기를 다시 확인한 뒤 다음 물 주기를 결정하세요.",
    maryland + "care-herbs-and-starting-herbs-seed",
)

internal fun fieldChecks(crop: String?): List<FieldCheck> = when (crop) {
    "tomato", "cherry_tomato", "pepper" -> listOf(blossomEnd, aphids)
    "cucumber" -> listOf(cucumberFruit, aphids)
    "bok_choy", "kale" -> listOf(leafHoles, aphids)
    "lettuce" -> listOf(bolting, leafHoles)
    "basil" -> listOf(basilLeaf, wetRoots)
    "rosemary" -> listOf(wetRoots, aphids)
    else -> emptyList()
}

internal data class SensorFinding(val evidence: String, val action: String)

internal fun sensorFindings(record: RgbRecord): List<SensorFinding> {
    val raw = record.sensorAssessmentJson ?: return emptyList()
    if (record.sourceCaptureId.isNullOrBlank() || record.sensorRecordId.isNullOrBlank()) return emptyList()
    val assessment = runCatching { JSONObject(raw) }.getOrNull() ?: return emptyList()
    val profile = assessment.optJSONObject("profile") ?: return emptyList()
    if (!profile.optBoolean("applied") || profile.optString("crop") != record.cropCode) return emptyList()
    val bands = profile.optJSONObject("bands") ?: return emptyList()
    val details = assessment.optJSONArray("details") ?: return emptyList()
    return buildList {
        for (index in 0 until details.length()) {
            val item = details.optJSONObject(index) ?: continue
            if (item.optString("status") != "SCORED") continue
            val metric = item.optString("metric")
            val band = bands.optJSONObject(metric) ?: continue
            val low = band.optDouble("low")
            val high = band.optDouble("high")
            val tolerance = band.optDouble("tolerance", 0.0)
            val value = item.optDouble("value")
            if (!low.isFinite() || !high.isFinite() || low >= high || !value.isFinite() ||
                !tolerance.isFinite() || tolerance < 0 || value in (low - tolerance)..(high + tolerance)) continue
            val above = value > high
            val action = when (metric) {
                "air_temp_c" -> if (above) "온도계가 직사광선을 받는지 확인하고 그늘에서 다시 재세요. 계속 높으면 온실 환기 상태를 점검하세요."
                    else "같은 시간대에 작물 높이에서 다시 재세요. 계속 낮으면 야간 보온 상태와 찬바람이 들어오는 곳을 점검하세요."
                "air_rh_pct" -> if (above) "잎이 오래 젖어 있는지 살피고 포기 사이의 통풍을 확인하세요."
                    else "같은 위치에서 습도를 다시 재고 뿌리 주변 흙의 습기도 확인한 뒤 물 주기를 결정하세요."
                "soil_raw" -> "같은 흙과 삽입 깊이에서 다시 재고 실제 흙의 습기를 확인하세요. 원시값만으로 물 주는 양을 결정하기 어렵습니다."
                "optical_sum" -> "광원과 센서 거리·각도를 기준 측정 때와 맞춰 다시 재세요."
                "surface_air_delta_c" -> "같은 잎을 같은 거리와 각도에서 다시 재고 직사광선과 바람의 영향을 확인하세요."
                else -> continue
            }
            val label = SensorMetrics.first { it.first == metric }.second
            val direction = if (above) "높음" else "낮음"
            add(SensorFinding(String.format(Locale.KOREA, "%s · %.2f (기준 %.2f~%.2f보다 %s)", label, value, low, high, direction), action))
        }
    }
}
