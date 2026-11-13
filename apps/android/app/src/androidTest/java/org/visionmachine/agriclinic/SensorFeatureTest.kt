package org.visionmachine.agriclinic

import android.content.Context
import android.content.ContextWrapper
import android.content.SharedPreferences
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.visionmachine.agriclinic.usb.SensorExchange
import org.visionmachine.agriclinic.usb.SensorWire
import org.visionmachine.agriclinic.usb.UsbSensorFailure
import java.util.UUID

/** Every packet in this class is explicitly synthetic/mock. */
internal fun syntheticExtendedSensorPacket(id: UUID): JSONObject = JSONObject()
    .put("schema_version", "0.1.0").put("message_type", "measurement").put("request_id", id.toString())
    .put("device_id", "synthetic-uno").put("boot_id", "synthetic-boot").put("firmware_version", "synthetic-0.2.0")
    .put("sequence", 1).put("uptime_ms", 1000).put("mode", "mock").put("calibration_id", JSONObject.NULL)
    .put("readings", JSONObject().put("soil_adc_bits", 12).put("soil_raw", 1500).put("soil_index", JSONObject.NULL)
        .put("air_temp_c", 24.0).put("air_rh_pct", 50.0))
    .put("errors", JSONArray())
    .put("extensions", JSONObject().put("schema_version", "0.1.0")
        .put("optical", JSONObject().put("sensor", "AS7341").put("i2c_address", 57)
            .put("raw_counts", JSONArray(listOf(10,20,30,40,100,50,60,70,80,90,110,55)))
            .put("channel_order", OPTICAL_CHANNEL_ORDER).put("gain_x", 16).put("atime", 29).put("astep", 599)
            .put("integration_time_ms", 50.04).put("illumination", "ambient").put("led_enabled", false)
            .put("status2", JSONArray(listOf(0,0))).put("saturated", false).put("started_uptime_ms", 1000).put("finished_uptime_ms", 1150))
        .put("surface_temperature", JSONObject().put("sensor", "MLX90614").put("i2c_address", 90)
            .put("object_raw", 15058).put("ambient_raw", 15058).put("object_temp_c", 28.01).put("ambient_temp_c", 28.01)
            .put("emissivity_raw", 65535).put("emissivity", 1.0).put("pec_checked", true).put("read_uptime_ms", 1151)))

@RunWith(AndroidJUnit4::class)
class SensorFeatureTest {
    private val id = UUID.fromString("33333333-3333-4333-8333-333333333333")
    private fun parse(packet: JSONObject): SensorFrame = SensorPacketFramer(id).feed((packet.toString()+"\n").toByteArray()).single()

    @Test fun extendedPacketAndRequestMatchFirmwareContract() {
        val request = JSONObject(SensorPacketFramer(id).measureRequest().toString(Charsets.UTF_8))
        assertEquals("extended", request.getString("sensor_profile"))
        assertTrue((parse(syntheticExtendedSensorPacket(id)) as SensorFrame.Measurement).isMock)
    }

    @Test fun corruptedExtensionFieldsAreRejected() {
        val badPec = syntheticExtendedSensorPacket(id)
        badPec.getJSONObject("extensions").getJSONObject("surface_temperature").put("pec_checked", false)
        assertEquals(SensorFrame.Rejected("INVALID_EXTENSIONS"), parse(badPec))
        val badRaw = syntheticExtendedSensorPacket(id)
        badRaw.getJSONObject("extensions").getJSONObject("optical").getJSONArray("raw_counts").put(0, true)
        assertEquals(SensorFrame.Rejected("INVALID_EXTENSIONS"), parse(badRaw))
        val badIntegration = syntheticExtendedSensorPacket(id)
        badIntegration.getJSONObject("extensions").getJSONObject("optical").put("integration_time_ms", 20)
        assertEquals(SensorFrame.Rejected("INVALID_EXTENSIONS"), parse(badIntegration))
        val trailing = SensorPacketFramer(id).feed((syntheticExtendedSensorPacket(id).toString()+"garbage\n").toByteArray())
        assertEquals(SensorFrame.Rejected("INVALID_JSON"), trailing.single())
    }

    @Test fun missingSensorsNeedErrorAndSaturationNeedsWarning() {
        val missing = syntheticExtendedSensorPacket(id)
        missing.getJSONObject("extensions").put("optical", JSONObject.NULL)
        assertEquals(SensorFrame.Rejected("INVALID_EXTENSIONS"), parse(missing))
        missing.put("errors", JSONArray(listOf("as7341_disconnected")))
        assertTrue(parse(missing) is SensorFrame.Measurement)
        val saturated = syntheticExtendedSensorPacket(id)
        val optical = saturated.getJSONObject("extensions").getJSONObject("optical")
        optical.getJSONArray("raw_counts").put(0, 18000)
        assertTrue(parse(saturated) is SensorFrame.Rejected)
        optical.put("saturated", true)
        assertTrue(parse(saturated) is SensorFrame.Rejected)
        saturated.put("errors", JSONArray(listOf("as7341_saturated")))
        assertTrue(parse(saturated) is SensorFrame.Measurement)
    }

    @Test fun wireExchangeIgnoresStaleIdAndReassemblesSmallChunks() {
        var clock = 0L
        var queued = ByteArray(0)
        val wire = object : SensorWire {
            override fun write(bytes: ByteArray) {
                assertEquals(id.toString(), JSONObject(bytes.toString(Charsets.UTF_8)).getString("request_id"))
                queued = (syntheticExtendedSensorPacket(UUID.randomUUID()).toString()+"\n"+syntheticExtendedSensorPacket(id).toString()+"\n").toByteArray()
            }
            override fun read(buffer: ByteArray, timeoutMs: Int): Int {
                clock += 1
                val count = minOf(17, queued.size)
                queued.copyInto(buffer, endIndex=count)
                queued=queued.copyOfRange(count,queued.size)
                return count
            }
            override fun close() {}
        }
        val frame = SensorExchange(wire, {clock}).measure(id, {true}, 10000)
        assertEquals(id.toString(), JSONObject(frame.json).getString("request_id"))
        assertTrue(frame.isMock)
    }

    @Test fun timeoutAndCancellationNeverBecomeAReading() {
        var clock = 0L
        var writes = 0
        val wire = object : SensorWire {
            override fun write(bytes: ByteArray) { writes++ }
            override fun read(buffer: ByteArray, timeoutMs: Int): Int { clock += timeoutMs; return 0 }
            override fun close() {}
        }
        try { SensorExchange(wire,{clock}).measure(id,{false},10); fail("Cancelled operation wrote a request") }
        catch(error: UsbSensorFailure) { assertEquals("CANCELLED",error.code) }
        assertEquals(0,writes)
        try { SensorExchange(wire,{clock}).measure(id,{true},10); fail("No response was accepted") }
        catch(error: UsbSensorFailure) { assertEquals("MEASUREMENT_TIMEOUT",error.code) }
    }

    @Test fun historyPersistsPacketAndPhotoLinkWithoutRewritingCameraRecords() {
        val base = ApplicationProvider.getApplicationContext<Context>()
        val prefix = "synthetic_usb_${UUID.randomUUID()}_"
        val isolated = object : ContextWrapper(base) {
            override fun getApplicationContext(): Context = this
            override fun getSharedPreferences(name: String, mode: Int): SharedPreferences = super.getSharedPreferences(prefix+name,mode)
        }
        val originalId = UUID.randomUUID().toString()
        val photo = CaptureRecord(originalId,"=synthetic-plant","synthetic-batch","basil","content://synthetic/photo.jpg","2026-01-01T00:00:00Z")
        val frame = parse(syntheticExtendedSensorPacket(id)) as SensorFrame.Measurement
        val store = SensorStore(isolated)
        store.save(id,frame,photo,"2026-01-01T00:01:00Z")
        val saved = SensorStore(isolated).all().single()
        assertEquals(id.toString(),saved.inspectionId)
        assertEquals(originalId,saved.sourceCaptureId)
        assertEquals(frame.json,saved.packetJson)
        assertTrue(CaptureStore(isolated).all().isEmpty())
        try { store.save(id,frame,null); fail("Duplicate overwrote history") } catch (_: IllegalStateException) {}
        assertEquals(1,store.all().size)
        val csv = SensorStore.csv(store.all())
        assertTrue(csv.contains("source_capture_id"))
        assertTrue(csv.contains(originalId))
        assertTrue(csv.contains("mock"))
        assertTrue(csv.contains("\"'=synthetic-plant\""))
    }
}
