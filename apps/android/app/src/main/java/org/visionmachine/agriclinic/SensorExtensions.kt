package org.visionmachine.agriclinic

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.abs
import kotlin.math.min

internal const val OPTICAL_CHANNEL_ORDER = "F1,F2,F3,F4,CLEAR_1,NIR_1,F5,F6,F7,F8,CLEAR_2,NIR_2"

internal fun validSensorExtensions(extension: JSONObject?, errors: JSONArray): Boolean {
    if (extension == null || extension.fields() != setOf("schema_version", "optical", "surface_temperature") ||
        extension.optString("schema_version") != "0.1.0") return false
    val optical = extension.opt("optical")
    val surface = extension.opt("surface_temperature")
    if ((optical == JSONObject.NULL || surface == JSONObject.NULL) && errors.length() == 0) return false
    if (optical != JSONObject.NULL) {
        if (optical !is JSONObject || !validOptical(optical)) return false
        if (optical.optBoolean("saturated") && (0 until errors.length()).none { errors.optString(it) == "as7341_saturated" }) return false
    }
    return surface == JSONObject.NULL || surface is JSONObject && validSurface(surface)
}

private fun validOptical(value: JSONObject): Boolean {
    if (value.fields() != setOf("sensor", "i2c_address", "raw_counts", "channel_order", "gain_x", "atime", "astep",
            "integration_time_ms", "illumination", "led_enabled", "status2", "saturated", "started_uptime_ms", "finished_uptime_ms")) return false
    if (value.optString("sensor") != "AS7341" || !value.opt("i2c_address").integer(57, 57) ||
        value.optString("channel_order") != OPTICAL_CHANNEL_ORDER || value.optString("illumination") != "ambient" ||
        value.opt("led_enabled") != false || value.opt("saturated") !is Boolean ||
        !value.opt("gain_x").number(Double.MIN_VALUE, 512.0) || !value.opt("atime").integer(0, 255) ||
        !value.opt("astep").integer(0, 65535) || !value.opt("started_uptime_ms").integer() ||
        !value.opt("finished_uptime_ms").integer()) return false
    val counts = value.optJSONArray("raw_counts") ?: return false
    val status = value.optJSONArray("status2") ?: return false
    if (counts.length() != 12 || (0 until 12).any { !counts.opt(it).integer(0, 65535) } ||
        status.length() != 2 || (0 until 2).any { !status.opt(it).integer(0, 255) }) return false
    val cycles = (value.getInt("atime") + 1L) * (value.getInt("astep") + 1L)
    if (!value.opt("integration_time_ms").number(0.00001, 50000.0) ||
        abs(value.getDouble("integration_time_ms") - cycles * 0.00278) > 0.005) return false
    val clipped = (0 until 12).any { counts.getLong(it) >= min(cycles, 65535) } ||
        (0 until 2).any { status.getInt(it) and 0x18 != 0 }
    return !clipped || value.getBoolean("saturated")
}

private fun validSurface(value: JSONObject): Boolean {
    if (value.fields() != setOf("sensor", "i2c_address", "object_raw", "ambient_raw", "object_temp_c", "ambient_temp_c",
            "emissivity_raw", "emissivity", "pec_checked", "read_uptime_ms")) return false
    if (value.optString("sensor") != "MLX90614" || !value.opt("i2c_address").integer(90, 90) ||
        !value.opt("object_raw").integer(1, 32767) || !value.opt("ambient_raw").integer(1, 32767) ||
        !value.opt("object_temp_c").number(-70.0, 380.0) || !value.opt("ambient_temp_c").number(-40.0, 125.0) ||
        !value.opt("emissivity_raw").integer(1, 65535) || !value.opt("emissivity").number(0.000001, 1.0) ||
        value.opt("pec_checked") != true || !value.opt("read_uptime_ms").integer()) return false
    return abs(value.getDouble("object_temp_c") - (value.getInt("object_raw") * 0.02 - 273.15)) <= 0.011 &&
        abs(value.getDouble("ambient_temp_c") - (value.getInt("ambient_raw") * 0.02 - 273.15)) <= 0.011 &&
        abs(value.getDouble("emissivity") - value.getInt("emissivity_raw") / 65535.0) <= 0.000011
}

private fun JSONObject.fields(): Set<String> = keys().asSequence().toSet()
private fun Any?.integer(min: Long = 0, max: Long = Long.MAX_VALUE): Boolean =
    (this is Int || this is Long) && (this as Number).toLong() in min..max
private fun Any?.number(min: Double, max: Double): Boolean =
    this is Number && toDouble().isFinite() && toDouble() in min..max
