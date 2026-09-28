package org.visionmachine.agriclinic

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class SensorPacketFramerTest {
    private val requestId = UUID.fromString("11111111-1111-4111-8111-111111111111")

    @Test
    fun requestCarriesInspectionIdAndEndsWithNewline() {
        val request = SensorPacketFramer(requestId).measureRequest().toString(Charsets.UTF_8)
        assertTrue(request.endsWith("\n"))
        assertEquals("measure", JSONObject(request.trim()).getString("message_type"))
        assertEquals(requestId.toString(), JSONObject(request.trim()).getString("request_id"))
    }

    @Test
    fun splitAndMultipleLinesKeepTheirPacketBoundariesAndMockBadge() {
        val framer = SensorPacketFramer(requestId)
        val first = packet(requestId, "mock").toString() + "\n"
        val second = packet(requestId, "real").toString() + "\n"
        val bytes = (first + second).toByteArray(Charsets.UTF_8)
        assertTrue(framer.feed(bytes.copyOfRange(0, 17)).isEmpty())
        val frames = framer.feed(bytes.copyOfRange(17, bytes.size))
        assertEquals(2, frames.size)
        assertTrue((frames[0] as SensorFrame.Measurement).isMock)
        assertFalse((frames[1] as SensorFrame.Measurement).isMock)
        assertEquals(requestId.toString(), JSONObject((frames[0] as SensorFrame.Measurement).json).getString("request_id"))
    }

    @Test
    fun staleRequestIdIsRejectedWithoutUsingOldMeasurement() {
        val framer = SensorPacketFramer(requestId)
        val oldId = UUID.fromString("22222222-2222-4222-8222-222222222222")
        val frames = framer.feed((packet(oldId, "real").toString() + "\n").toByteArray())
        assertEquals(SensorFrame.Rejected("STALE_REQUEST_ID"), frames.single())
    }

    @Test
    fun oversizedLineIsDiscardedAndNextLineStillParses() {
        val framer = SensorPacketFramer(requestId)
        val oversized = "x".repeat(SensorPacketFramer.MAX_LINE_BYTES + 1) + "\n"
        val valid = packet(requestId, "real").toString() + "\n"
        val frames = framer.feed((oversized + valid).toByteArray())
        assertEquals(SensorFrame.Rejected("LINE_TOO_LONG"), frames.first())
        assertEquals(2, frames.size)
        assertTrue(frames.last() is SensorFrame.Measurement)
    }

    @Test
    fun malformedUtf8AndMissingReadingErrorAreRejected() {
        val framer = SensorPacketFramer(requestId)
        assertEquals(SensorFrame.Rejected("INVALID_UTF8"), framer.feed(byteArrayOf(0xc3.toByte(), 0x28, 0x0a)).single())
        val missing = packet(requestId, "real")
        missing.getJSONObject("readings").put("soil_raw", JSONObject.NULL)
        assertEquals(
            SensorFrame.Rejected("INVALID_PACKET"),
            framer.feed((missing.toString() + "\n").toByteArray()).single(),
        )
    }

    @Test
    fun partialLineAtDisconnectIsNotAUsableMeasurement() {
        val framer = SensorPacketFramer(requestId)
        assertTrue(framer.feed(packet(requestId, "real").toString().toByteArray()).isEmpty())
        assertEquals(SensorFrame.Rejected("INCOMPLETE_LINE"), framer.endOfStream())
    }

    private fun packet(id: UUID, mode: String): JSONObject = JSONObject()
        .put("schema_version", "0.1.0")
        .put("message_type", "measurement")
        .put("request_id", id.toString())
        .put("device_id", "fixture-uno")
        .put("boot_id", "fixture-boot")
        .put("firmware_version", "mock-0.1.0")
        .put("sequence", 1)
        .put("uptime_ms", 1000)
        .put("mode", mode)
        .put("calibration_id", JSONObject.NULL)
        .put("readings", JSONObject()
            .put("soil_adc_bits", 12)
            .put("soil_raw", 1500)
            .put("soil_index", JSONObject.NULL)
            .put("air_temp_c", 24.0)
            .put("air_rh_pct", 55.0))
        .put("errors", JSONArray())
}
