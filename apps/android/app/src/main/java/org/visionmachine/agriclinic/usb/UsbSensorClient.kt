package org.visionmachine.agriclinic.usb

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbDeviceConnection
import android.hardware.usb.UsbManager
import android.os.Handler
import android.os.Looper
import androidx.core.content.ContextCompat
import com.hoho.android.usbserial.driver.CdcAcmSerialDriver
import com.hoho.android.usbserial.driver.UsbSerialPort
import org.visionmachine.agriclinic.SensorFrame
import java.io.Closeable
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicLong

data class UsbSensorState(val connected: Boolean = false, val busy: Boolean = false, val code: String = "DISCONNECTED")

/** One explicitly supported UNO R4. No background scanning or uploads. */
class UsbSensorClient(
    context: Context,
    private val onState: (UsbSensorState) -> Unit,
) : Closeable {
    private val app = context.applicationContext
    private val manager = app.getSystemService(UsbManager::class.java)
    private val handler = Handler(Looper.getMainLooper())
    private val worker = Executors.newSingleThreadExecutor()
    private val generation = AtomicLong()
    private val portLock = Any()
    private val permissionAction = "${app.packageName}.USB_SENSOR_PERMISSION"
    private var permissionIntent: PendingIntent? = null
    private var pendingName: String? = null
    private var pendingGeneration = 0L
    @Volatile private var current: PortWire? = null
    @Volatile private var deviceName: String? = null
    @Volatile private var closed = false
    private var state = UsbSensorState()

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                permissionAction -> {
                    val name = pendingName ?: return
                    val ticket = pendingGeneration
                    pendingName = null
                    val device = manager.deviceList[name]
                    if (ticket != generation.get() || closed) return
                    if (device != null && manager.hasPermission(device)) open(device, ticket)
                    else update(ticket, UsbSensorState(code = "PERMISSION_DENIED"))
                }
                UsbManager.ACTION_USB_DEVICE_DETACHED -> {
                    if (deviceName != null && manager.deviceList[deviceName] == null ||
                        pendingName != null && manager.deviceList[pendingName] == null) disconnect("DISCONNECTED")
                }
            }
        }
    }

    init {
        val filter = IntentFilter(permissionAction).apply { addAction(UsbManager.ACTION_USB_DEVICE_DETACHED) }
        ContextCompat.registerReceiver(app, receiver, filter, ContextCompat.RECEIVER_NOT_EXPORTED)
    }

    fun connect() {
        if (closed || state.busy) return
        disconnect()
        val ticket = generation.get()
        val devices = manager.deviceList.values.filter { it.vendorId == 0x2341 && it.productId == 0x0069 }
        if (devices.size != 1) {
            update(ticket, UsbSensorState(code = if (devices.isEmpty()) "DEVICE_NOT_FOUND" else "MULTIPLE_DEVICES"))
            return
        }
        val device = devices.single()
        if (manager.hasPermission(device)) open(device, ticket)
        else {
            pendingName = device.deviceName
            pendingGeneration = ticket
            update(ticket, UsbSensorState(busy = true, code = "WAITING_PERMISSION"))
            permissionIntent?.cancel()
            permissionIntent = PendingIntent.getBroadcast(app, ticket.toInt(), Intent(permissionAction).setPackage(app.packageName),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            try { manager.requestPermission(device, permissionIntent) }
            catch (_: Exception) { pendingName = null; update(ticket, UsbSensorState(code = "PERMISSION_DENIED")) }
        }
    }

    private fun open(device: UsbDevice, ticket: Long) {
        update(ticket, UsbSensorState(busy = true, code = "CONNECTING"))
        worker.execute {
            var connection: UsbDeviceConnection? = null
            var wire: PortWire? = null
            try {
                if (!active(ticket)) return@execute
                connection = manager.openDevice(device) ?: throw UsbSensorFailure("OPEN_FAILED")
                val port = CdcAcmSerialDriver(device).ports.singleOrNull() ?: throw UsbSensorFailure("UNSUPPORTED_DEVICE")
                wire = PortWire(port, connection)
                port.open(connection)
                port.setParameters(115200, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE)
                port.dtr = true
                port.rts = false
                val published = synchronized(portLock) {
                    if (active(ticket)) { current = wire; deviceName = device.deviceName; true } else false
                }
                if (!published) { wire.close(); return@execute }
                update(ticket, UsbSensorState(connected = true, code = "CONNECTED"))
            } catch (error: Exception) {
                wire?.close() ?: connection?.close()
                update(ticket, UsbSensorState(code = (error as? UsbSensorFailure)?.code ?: "OPEN_FAILED"))
            }
        }
    }

    fun measure(id: UUID, result: (SensorFrame.Measurement?, String?) -> Unit) {
        if (!state.connected || state.busy || closed) { result(null, "NOT_CONNECTED"); return }
        val ticket = generation.get()
        val wire = current ?: run { result(null, "NOT_CONNECTED"); return }
        update(ticket, UsbSensorState(connected = true, busy = true, code = "MEASURING"))
        worker.execute {
            try {
                val frame = SensorExchange(wire).measure(id, { active(ticket) && current === wire })
                handler.post {
                    if (active(ticket) && current === wire) {
                        update(ticket, UsbSensorState(connected = true, code = "CONNECTED"))
                        result(frame, null)
                    }
                }
            } catch (error: Exception) {
                handler.post {
                    if (active(ticket)) {
                        disconnect((error as? UsbSensorFailure)?.code ?: "USB_IO_ERROR")
                        result(null, (error as? UsbSensorFailure)?.code ?: "USB_IO_ERROR")
                    }
                }
            }
        }
    }

    fun disconnect(code: String = "DISCONNECTED") {
        val released = synchronized(portLock) {
            val ticket = generation.incrementAndGet()
            val wire = current
            current = null
            deviceName = null
            ticket to wire
        }
        pendingName = null
        permissionIntent?.cancel()
        released.second?.close()
        update(released.first, UsbSensorState(code = code))
    }

    private fun active(ticket: Long) = !closed && generation.get() == ticket
    private fun update(ticket: Long, next: UsbSensorState) {
        if (Looper.myLooper() != Looper.getMainLooper()) { handler.post { update(ticket, next) }; return }
        if (active(ticket)) { state = next; onState(next) }
    }

    override fun close() {
        if (closed) return
        disconnect()
        closed = true
        runCatching { app.unregisterReceiver(receiver) }
        worker.shutdownNow()
    }

    private class PortWire(private val port: UsbSerialPort, private val connection: UsbDeviceConnection) : SensorWire {
        override fun write(bytes: ByteArray) { port.write(bytes, 3000) }
        override fun read(buffer: ByteArray, timeoutMs: Int): Int = port.read(buffer, timeoutMs)
        override fun close() {
            connection.close() // Interrupt an in-flight blocking read before closing driver state.
            runCatching { port.close() }
        }
    }
}
