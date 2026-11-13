package org.visionmachine.agriclinic.usb

import android.os.SystemClock
import org.visionmachine.agriclinic.SensorFrame
import org.visionmachine.agriclinic.SensorPacketFramer
import java.io.Closeable
import java.io.IOException
import java.util.UUID

internal interface SensorWire : Closeable {
    fun write(bytes: ByteArray)
    fun read(buffer: ByteArray, timeoutMs: Int): Int
}

class UsbSensorFailure(val code: String) : IOException(code)

internal class SensorExchange(
    private val wire: SensorWire,
    private val now: () -> Long = SystemClock::elapsedRealtime,
) {
    fun measure(requestId: UUID, isCurrent: () -> Boolean, timeoutMs: Long = 12_000): SensorFrame.Measurement {
        val framer = SensorPacketFramer(requestId)
        if (!isCurrent()) throw UsbSensorFailure("CANCELLED")
        val deadline = now() + timeoutMs
        wire.write(framer.measureRequest())
        val buffer = ByteArray(1024)
        while (now() < deadline) {
            if (!isCurrent()) throw UsbSensorFailure("CANCELLED")
            val count = wire.read(buffer, minOf(250L, deadline - now()).coerceAtLeast(1L).toInt())
            if (count < 0) throw UsbSensorFailure("DISCONNECTED")
            if (count == 0) continue
            for (frame in framer.feed(buffer.copyOf(count))) {
                when (frame) {
                    is SensorFrame.Measurement -> {
                        if (!isCurrent()) throw UsbSensorFailure("CANCELLED")
                        return frame
                    }
                    is SensorFrame.Rejected -> if (frame.code != "STALE_REQUEST_ID") {
                        throw UsbSensorFailure(frame.code)
                    }
                }
            }
        }
        val incomplete = framer.endOfStream()
        throw UsbSensorFailure(if (incomplete != null) "INCOMPLETE_RESPONSE" else "MEASUREMENT_TIMEOUT")
    }
}
