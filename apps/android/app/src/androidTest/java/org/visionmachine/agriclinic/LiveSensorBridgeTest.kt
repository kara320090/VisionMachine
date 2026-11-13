package org.visionmachine.agriclinic

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.core.app.ApplicationProvider
import android.content.Context
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.visionmachine.agriclinic.usb.SensorExchange
import org.visionmachine.agriclinic.usb.SensorWire
import java.net.Socket
import java.net.SocketTimeoutException
import java.util.UUID

/** Test-only PC serial bridge: validates Android protocol against real firmware.
 * It does not claim Android USB permission/enumeration has been tested. */
@RunWith(AndroidJUnit4::class)
class LiveSensorBridgeTest {
    @Test fun actualFirmwarePacketParsesOnAndroid() {
        val port = InstrumentationRegistry.getArguments().getString("sensor_bridge_port")?.toIntOrNull()
        assumeTrue("Requires an explicitly started local real-board bridge", port != null)
        Socket("10.0.2.2",port!!).use { socket ->
            val wire = object : SensorWire {
                override fun write(bytes: ByteArray) { socket.getOutputStream().write(bytes);socket.getOutputStream().flush() }
                override fun read(buffer: ByteArray, timeoutMs: Int): Int {
                    socket.soTimeout=timeoutMs
                    return try {socket.getInputStream().read(buffer)} catch (_: SocketTimeoutException) {0}
                }
                override fun close() {socket.close()}
            }
            val id=UUID.randomUUID()
            val frame=SensorExchange(wire).measure(id,{true})
            val packet=JSONObject(frame.json)
            assertFalse(frame.isMock)
            assertEquals(id.toString(),packet.getString("request_id"))
            assertEquals("uno-r4-0.2.0",packet.getString("firmware_version"))
            assertEquals(0,packet.getJSONArray("errors").length())
            assertNotNull(packet.getJSONObject("extensions").optJSONObject("optical"))
            assertTrue(packet.getJSONObject("extensions").getJSONObject("surface_temperature").getBoolean("pec_checked"))
            val stored=SensorStore(ApplicationProvider.getApplicationContext<Context>()).save(id,frame,null)
            assertEquals(frame.json,stored.packetJson)
        }
    }
}
