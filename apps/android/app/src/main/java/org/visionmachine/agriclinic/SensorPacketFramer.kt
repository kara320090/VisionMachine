package org.visionmachine.agriclinic

import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.util.UUID

sealed interface SensorFrame {
    data class Measurement(val json: String, val isMock: Boolean) : SensorFrame
    data class Rejected(val code: String) : SensorFrame
}

/** Frames USB CDC JSONL bytes. This does not open or authorize a USB device. */
class SensorPacketFramer(private val expectedRequestId: UUID) {
    private val line = ByteArrayOutputStream()
    private var droppingOversizedLine = false

    fun measureRequest(): ByteArray = (
        JSONObject()
            .put("schema_version", "0.1.0")
            .put("message_type", "measure")
            .put("request_id", expectedRequestId.toString())
            .toString() + "\n"
        ).toByteArray(Charsets.UTF_8)

    fun feed(bytes: ByteArray): List<SensorFrame> {
        val frames = mutableListOf<SensorFrame>()
        for (byte in bytes) {
            if (byte == '\n'.code.toByte()) {
                if (droppingOversizedLine) {
                    frames.add(SensorFrame.Rejected("LINE_TOO_LONG"))
                } else {
                    val raw = line.toByteArray()
                    val length = if (raw.isNotEmpty() && raw.last() == '\r'.code.toByte()) raw.size - 1 else raw.size
                    frames.add(parse(raw.copyOf(length)))
                }
                line.reset()
                droppingOversizedLine = false
            } else if (!droppingOversizedLine) {
                if (line.size() == MAX_LINE_BYTES) {
                    line.reset()
                    droppingOversizedLine = true
                } else {
                    line.write(byte.toInt())
                }
            }
        }
        return frames
    }

    fun endOfStream(): SensorFrame? {
        val incomplete = droppingOversizedLine || line.size() > 0
        line.reset()
        droppingOversizedLine = false
        return if (incomplete) SensorFrame.Rejected("INCOMPLETE_LINE") else null
    }

    private fun parse(bytes: ByteArray): SensorFrame {
        val text = try {
            Charsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(bytes)).toString()
        } catch (_: Exception) {
            return SensorFrame.Rejected("INVALID_UTF8")
        }
        val packet = try { JSONObject(text) } catch (_: Exception) {
            return SensorFrame.Rejected("INVALID_JSON")
        }
        if (!packet.hasExactly(TOP_FIELDS) || packet.optString("schema_version") != "0.1.0" ||
            packet.optString("message_type") != "measurement"
        ) return SensorFrame.Rejected("INVALID_PACKET")
        val requestId = packet.optString("request_id")
        val parsedId = runCatching { UUID.fromString(requestId) }.getOrNull()
        if (parsedId == null || parsedId.toString() != requestId) return SensorFrame.Rejected("INVALID_PACKET")
        if (parsedId != expectedRequestId) return SensorFrame.Rejected("STALE_REQUEST_ID")
        if (!(packet.opt("device_id") is String && packet.optString("device_id").isIdentifier()) ||
            !(packet.opt("boot_id") is String && packet.optString("boot_id").isIdentifier()) ||
            !(packet.opt("firmware_version") is String && packet.optString("firmware_version").length in 1..40) ||
            !packet.opt("sequence").isNonNegativeInteger() || !packet.opt("uptime_ms").isNonNegativeInteger()
        ) return SensorFrame.Rejected("INVALID_PACKET")
        val mode = packet.optString("mode")
        if (mode !in setOf("real", "mock")) return SensorFrame.Rejected("INVALID_PACKET")
        val calibration = packet.opt("calibration_id")
        if (calibration != JSONObject.NULL && (calibration !is String || !calibration.isIdentifier())) {
            return SensorFrame.Rejected("INVALID_PACKET")
        }
        val readings = packet.optJSONObject("readings") ?: return SensorFrame.Rejected("INVALID_PACKET")
        if (!readings.hasExactly(READING_FIELDS)) return SensorFrame.Rejected("INVALID_PACKET")
        val bits = readings.opt("soil_adc_bits")
        if (!bits.isNonNegativeInteger() || (bits as Number).toInt() !in setOf(10, 12, 14)) {
            return SensorFrame.Rejected("INVALID_PACKET")
        }
        val raw = readings.opt("soil_raw")
        if (raw != JSONObject.NULL && (!raw.isNonNegativeInteger() || (raw as Number).toLong() >= (1 shl bits.toInt()))) {
            return SensorFrame.Rejected("INVALID_PACKET")
        }
        val index = readings.opt("soil_index")
        if (index != JSONObject.NULL && (!index.isFiniteNumber(0.0, 1.0) || calibration == JSONObject.NULL)) {
            return SensorFrame.Rejected("INVALID_PACKET")
        }
        val temperature = readings.opt("air_temp_c")
        val humidity = readings.opt("air_rh_pct")
        if (temperature != JSONObject.NULL && !temperature.isFiniteNumber(-273.15, Double.MAX_VALUE)) {
            return SensorFrame.Rejected("INVALID_PACKET")
        }
        if (humidity != JSONObject.NULL && !humidity.isFiniteNumber(0.0, 100.0)) {
            return SensorFrame.Rejected("INVALID_PACKET")
        }
        val errors = packet.optJSONArray("errors") ?: return SensorFrame.Rejected("INVALID_PACKET")
        if (!errors.validErrors() || (listOf(raw, temperature, humidity).any { it == JSONObject.NULL } && errors.length() == 0)) {
            return SensorFrame.Rejected("INVALID_PACKET")
        }
        return SensorFrame.Measurement(text, mode == "mock")
    }

    private fun JSONObject.hasExactly(expected: Set<String>): Boolean = keys().asSequence().toSet() == expected
    private fun String.isIdentifier(): Boolean = IDENTIFIER.matches(this)
    private fun Any?.isNonNegativeInteger(): Boolean = when (this) {
        is Int -> this >= 0
        is Long -> this >= 0
        else -> false
    }
    private fun Any?.isFiniteNumber(min: Double, max: Double): Boolean =
        this is Number && this.toDouble().isFinite() && this.toDouble() in min..max
    private fun JSONArray.validErrors(): Boolean = (0 until length()).all { index ->
        val value = opt(index)
        value is String && value.length in 1..80
    }

    companion object {
        const val MAX_LINE_BYTES = 4096
        private val IDENTIFIER = Regex("[A-Za-z0-9_-]{1,80}")
        private val TOP_FIELDS = setOf(
            "schema_version", "message_type", "request_id", "device_id", "boot_id",
            "firmware_version", "sequence", "uptime_ms", "mode", "calibration_id", "readings", "errors",
        )
        private val READING_FIELDS = setOf("soil_adc_bits", "soil_raw", "soil_index", "air_temp_c", "air_rh_pct")
    }
}
