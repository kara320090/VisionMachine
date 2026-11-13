package org.visionmachine.agriclinic

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import kotlin.math.max

data class ReferenceBand(val low: Double, val high: Double, val tolerance: Double = 0.0) {
    init { require(low.isFinite() && high.isFinite() && low < high && tolerance.isFinite() && tolerance >= 0) }
    fun deviation(value: Double): Double {
        require(value.isFinite())
        return max(0.0, max(low - value, value - high) - tolerance)
    }
    fun score(value: Double): Double = (100.0 * deviation(value) / (high - low)).coerceIn(0.0, 100.0)
    fun json() = JSONObject().put("low", low).put("high", high).put("tolerance", tolerance)
}

internal val SensorMetrics = listOf("air_temp_c" to "외기 온도 °C", "air_rh_pct" to "상대습도 %",
    "soil_raw" to "토양 원시 ADC", "optical_sum" to "광학 F1~F8 원시 합", "surface_air_delta_c" to "표면−외기 온도차 °C")

data class SensorProfile(val crop: String, val bands: Map<String, ReferenceBand> = emptyMap(), val context: String = "사용자 재배 기준",
    val source: String = "", val applied: Boolean = false, val version: String = "unapplied",
    val opticalConditions: String? = null, val soilAdcBits: Int? = null) {
    fun json(): JSONObject {
        val ranges = JSONObject(); bands.forEach { (key, value) -> ranges.put(key, value.json()) }
        return JSONObject().put("crop", crop).put("bands", ranges).put("context", context).put("source", source)
            .put("applied", applied).put("version", version).put("optical_conditions", opticalConditions ?: JSONObject.NULL)
            .put("soil_adc_bits", soilAdcBits ?: JSONObject.NULL)
    }
}

class SensorProfileStore(context: Context) {
    private val prefs = context.getSharedPreferences("sensor_reference_profiles_v1", Context.MODE_PRIVATE)
    fun get(crop: String): SensorProfile {
        val raw = prefs.getString(crop, null) ?: return template(crop)
        val value = JSONObject(raw); val ranges = value.getJSONObject("bands")
        return SensorProfile(crop, ranges.keys().asSequence().associateWith { key ->
            val band = ranges.getJSONObject(key); ReferenceBand(band.getDouble("low"), band.getDouble("high"), band.getDouble("tolerance"))
        }, value.getString("context"), value.getString("source"), value.getBoolean("applied"), value.getString("version"),
            value.optString("optical_conditions").takeUnless { value.isNull("optical_conditions") || it.isBlank() },
            if (value.isNull("soil_adc_bits")) null else value.getInt("soil_adc_bits"))
    }
    fun save(profile: SensorProfile): SensorProfile {
        require(profile.context.isNotBlank() && profile.source.isNotBlank() && profile.bands.isNotEmpty())
        require(profile.bands.keys.all { key -> SensorMetrics.any { it.first == key } })
        profile.bands.forEach { (key, band) ->
            when (key) {
                "air_rh_pct" -> require(band.low >= 0 && band.high <= 100)
                "air_temp_c" -> require(band.low >= -40 && band.high <= 125)
                "soil_raw" -> require(profile.soilAdcBits != null && band.low >= 0 && band.high < (1 shl profile.soilAdcBits))
                "optical_sum" -> require(profile.opticalConditions != null && band.low >= 0 && band.high <= 8 * 65535)
                "surface_air_delta_c" -> require(band.low >= -150 && band.high <= 450)
            }
        }
        val saved = profile.copy(applied = true, version = Instant.now().toString())
        check(prefs.edit().putString(profile.crop, saved.json().toString()).commit())
        return saved
    }
    companion object {
        fun template(crop: String): SensorProfile {
            fun f(value: Double) = (value - 32) * 5 / 9
            val nmsu = "https://pubs.nmsu.edu/_circulars/CR556/index.html"
            val herbs = "https://ipm.cahnr.uconn.edu/herbs-greenhouse/"
            return when (crop) {
                "tomato", "cherry_tomato" -> SensorProfile(crop, mapOf("air_temp_c" to ReferenceBand(f(70.0), f(75.0))), "토마토 육묘: 초기 저온처리 뒤 주간 참고", nmsu)
                "cucumber" -> SensorProfile(crop, mapOf("air_temp_c" to ReferenceBand(f(80.0), f(85.0))), "온실 오이 주간 참고", nmsu)
                "lettuce" -> SensorProfile(crop, mapOf("air_temp_c" to ReferenceBand(f(60.0), f(65.0))), "온실 상추 주간 참고", nmsu)
                "basil", "rosemary" -> SensorProfile(crop, mapOf("air_temp_c" to ReferenceBand(f(70.0), f(75.0))), "온실 허브 모종 공통 주간 참고", herbs)
                else -> SensorProfile(crop)
            }
        }
    }
}

/** A transparent reference-distance index, never a trained model or disease probability. */
object SensorScoring {
    const val VERSION = "reference-deviation-v1"
    fun opticalConditions(packet: JSONObject): String? = packet.optJSONObject("extensions")?.optJSONObject("optical")?.let { optical ->
        listOf(optical.getDouble("gain_x"), optical.getInt("atime"), optical.getInt("astep"), optical.getString("illumination"),
            optical.getBoolean("led_enabled"), optical.getString("channel_order")).joinToString("|")
    }
    fun values(packet: JSONObject): Map<String, Double?> {
        fun JSONObject.number(key: String): Double? = if (isNull(key)) null else optDouble(key).takeIf { it.isFinite() }
        val readings = packet.getJSONObject("readings")
        val optical = packet.optJSONObject("extensions")?.optJSONObject("optical")
        val surface = packet.optJSONObject("extensions")?.optJSONObject("surface_temperature")
        val counts = optical?.optJSONArray("raw_counts")
        val air = readings.number("air_temp_c"); val target = surface?.number("object_temp_c")
        return mapOf("air_temp_c" to air, "air_rh_pct" to readings.number("air_rh_pct"), "soil_raw" to readings.number("soil_raw"),
            "optical_sum" to counts?.let { listOf(0,1,2,3,6,7,8,9).sumOf { i -> it.getDouble(i) } },
            "surface_air_delta_c" to if (air != null && target != null) target - air else null)
    }
    fun assess(packet: JSONObject, profile: SensorProfile): JSONObject {
        val values = values(packet); val details = JSONArray(); val scores = mutableListOf<Double>()
        val errors = packet.getJSONArray("errors"); val errorCodes = (0 until errors.length()).map { errors.getString(it) }
        for ((key, _) in SensorMetrics) {
            val band = profile.bands[key]; val value = values[key]
            val invalid = when (key) {
                "optical_sum" -> packet.optJSONObject("extensions")?.optJSONObject("optical")?.optBoolean("saturated") == true ||
                    profile.opticalConditions == null || profile.opticalConditions != opticalConditions(packet) || errorCodes.any { it.startsWith("as7341_") }
                "soil_raw" -> profile.soilAdcBits != packet.getJSONObject("readings").getInt("soil_adc_bits") || errorCodes.any { it.startsWith("soil_") }
                "surface_air_delta_c" -> errorCodes.any { it.startsWith("mlx90614_") || it.startsWith("sht31_") }
                else -> errorCodes.any { it.startsWith("sht31_") }
            }
            val reason = when {
                !profile.applied -> "REFERENCE_NOT_APPLIED"
                band == null -> "NO_REFERENCE"
                packet.getString("mode") != "real" -> "MOCK"
                value == null -> "MISSING"
                invalid -> "QUALITY_OR_CONDITIONS"
                else -> "SCORED"
            }
            val score = if (reason == "SCORED") band!!.score(value!!).also { scores.add(it) } else null
            details.put(JSONObject().put("metric", key).put("value", value ?: JSONObject.NULL).put("status", reason)
                .put("deviation", if (score != null) band!!.deviation(value!!) else JSONObject.NULL).put("score", score ?: JSONObject.NULL))
        }
        val aggregate = scores.takeIf { profile.applied && it.isNotEmpty() && it.size == profile.bands.size }?.average()
        return JSONObject().put("method", VERSION).put("profile", profile.json()).put("scored_count", scores.size)
            .put("configured_count", profile.bands.size).put("available_metric_count", SensorMetrics.size)
            .put("deviation_score", aggregate ?: JSONObject.NULL).put("details", details)
    }
}
