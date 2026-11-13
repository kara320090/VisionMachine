package org.visionmachine.agriclinic

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

/** Replays an unmodified privately archived physical-board response. Not live USB. */
@RunWith(AndroidJUnit4::class)
class RecordedFirmwarePacketTest {
    @Test fun archivedRealPacketReassemblesAndPersistsWithOriginalReceiveTime() {
        val assets=InstrumentationRegistry.getInstrumentation().context.assets
        val raw=runCatching { assets.open("private/sensor_packet_v020_real.json").bufferedReader().use {it.readText()} }.getOrNull()
        assumeTrue("Requires a private archived real-board fixture",raw!=null)
        val archive=JSONObject(raw!!)
        val packet=archive.getJSONObject("packet")
        val originalTime=archive.getString("received_at")
        val id=UUID.fromString(packet.getString("request_id"))
        val framer=SensorPacketFramer(id)
        val bytes=(packet.toString()+"\n").toByteArray(Charsets.UTF_8)
        val frames=bytes.asList().chunked(17).flatMap {framer.feed(it.toByteArray())}
        val frame=frames.single() as SensorFrame.Measurement
        assertFalse(frame.isMock)
        assertEquals("uno-r4-0.2.0",packet.getString("firmware_version"))
        assertEquals(12,packet.getJSONObject("extensions").getJSONObject("optical").getJSONArray("raw_counts").length())
        assertTrue(packet.getJSONObject("extensions").getJSONObject("surface_temperature").getBoolean("pec_checked"))
        val store=SensorStore(ApplicationProvider.getApplicationContext<Context>())
        val stored=store.all().find {it.inspectionId==id.toString()} ?: store.save(id,frame,null,originalTime)
        assertEquals(originalTime,stored.receivedAt)
        assertEquals(packet.toString(),stored.packetJson)
    }
}
