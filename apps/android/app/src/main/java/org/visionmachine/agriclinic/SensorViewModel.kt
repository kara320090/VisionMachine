package org.visionmachine.agriclinic

import android.app.Application
import android.os.Handler
import android.os.Looper
import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import org.visionmachine.agriclinic.usb.UsbSensorClient
import org.visionmachine.agriclinic.usb.UsbSensorState
import java.time.Instant
import java.util.UUID
import java.util.concurrent.Executors

class SensorViewModel(application: Application) : AndroidViewModel(application) {
    private val store = SensorStore(application)
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var closed = false
    private var activeId: UUID? = null
    var usb by mutableStateOf(UsbSensorState()); private set
    var saving by mutableStateOf(false); private set
    val busy get() = usb.busy || saving
    var message by mutableStateOf("측정 장치를 USB-C로 연결한 뒤 연결 버튼을 눌러 주세요."); private set
    var current by mutableStateOf<SensorRecord?>(null); private set
    var records by mutableStateOf<List<SensorRecord>>(emptyList()); private set
    var photos by mutableStateOf<List<CaptureRecord>>(emptyList()); private set
    var selectedPhoto by mutableStateOf<CaptureRecord?>(null); private set
    private val client = UsbSensorClient(application) { next ->
        usb = next
        if (!next.connected) current = null
        message = sensorStatusText(next.code)
    }

    init { refresh() }

    fun refresh() {
        io.execute {
            try {
                val saved = store.all()
                val captures = CaptureStore(getApplication()).all()
                main.post { if (!closed) { records = saved; photos = captures } }
            } catch (_: Exception) { main.post { if (!closed) message = "저장된 기록을 읽지 못했습니다. 기존 기록은 보존됩니다." } }
        }
    }

    fun select(photo: CaptureRecord?) { if (!busy) { selectedPhoto = photo; current = null } }
    fun selectId(id: String?) {
        if (id == null) return
        io.execute {
            val selected = runCatching { CaptureStore(getApplication()).all().find { it.inspectionId == id } }.getOrNull()
            main.post { if (!closed && !busy) selectedPhoto = selected }
        }
    }
    fun connect() { if (!busy) client.connect() }
    fun disconnect() { activeId = null; client.disconnect(); current = null }

    fun measure() {
        if (busy || !usb.connected) return
        val id = UUID.randomUUID()
        activeId = id
        current = null
        val source = selectedPhoto
        client.measure(id) callback@{ frame, error ->
            if (error != null || frame == null) { message = sensorStatusText(error ?: "USB_IO_ERROR"); return@callback }
            val receivedAt = Instant.now().toString()
            saving = true
            io.execute {
                try {
                    val row = store.save(id, frame, source, receivedAt)
                    val saved = store.all()
                    main.post {
                        if (!closed) {
                            records = saved
                            saving = false
                            if (activeId == id && usb.connected) {
                                current = row
                                message = if (frame.isMock) "모의 시험자료를 저장했습니다." else "실측값을 기기에 저장했습니다."
                            }
                        }
                    }
                } catch (_: Exception) {
                    main.post { if (!closed) { saving = false; current = null; message = "측정은 수신했지만 기록 저장에 실패했습니다. 다시 측정해 주세요." } }
                }
            }
        }
    }

    fun reportExport(success: Boolean) { message = if (success) "측정 기록 CSV를 저장했습니다." else "CSV를 저장하지 못했습니다." }
    fun export(uri: Uri) {
        val snapshot = records
        io.execute {
            val success = runCatching {
                getApplication<Application>().contentResolver.openOutputStream(uri, "wt")!!.bufferedWriter(Charsets.UTF_8).use {
                    it.write("\uFEFF")
                    it.write(SensorStore.csv(snapshot))
                }
            }.isSuccess
            main.post { if (!closed) reportExport(success) }
        }
    }
    fun reportPhotoError() { message = "사진 파일을 열지 못했습니다." }

    override fun onCleared() {
        closed = true
        client.close()
        io.shutdownNow()
        super.onCleared()
    }
}

internal fun sensorStatusText(code: String): String = when (code) {
    "CONNECTED" -> "측정 장치가 연결됐습니다."
    "CONNECTING" -> "측정 장치를 연결하고 있습니다."
    "WAITING_PERMISSION" -> "USB 사용 권한 창에서 허용해 주세요."
    "MEASURING" -> "네 센서의 값을 측정하고 있습니다."
    "DEVICE_NOT_FOUND" -> "UNO R4 Minima를 찾지 못했습니다. USB-C 데이터 연결을 확인해 주세요."
    "MULTIPLE_DEVICES" -> "측정 장치를 한 대만 연결해 주세요."
    "PERMISSION_DENIED" -> "USB 권한이 허용되지 않았습니다. 연결 버튼을 눌러 다시 허용할 수 있습니다."
    "DISCONNECTED", "CANCELLED" -> "장치 연결이 해제됐습니다. 이전 값은 이력에서 볼 수 있습니다."
    "MEASUREMENT_TIMEOUT", "INCOMPLETE_RESPONSE" -> "측정 응답을 받지 못했습니다. 장치를 다시 연결한 뒤 측정해 주세요."
    "INVALID_EXTENSIONS", "INVALID_PACKET", "INVALID_JSON", "INVALID_UTF8", "LINE_TOO_LONG" -> "측정 데이터 형식이 올바르지 않아 저장하지 않았습니다. 다시 연결해 주세요."
    else -> "장치와 통신하지 못했습니다. USB 연결과 보드 전원을 확인한 뒤 다시 연결해 주세요."
}
