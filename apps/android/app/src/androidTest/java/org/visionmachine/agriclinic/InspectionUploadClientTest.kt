package org.visionmachine.agriclinic

import android.content.Context
import android.graphics.Bitmap
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.InputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicReference

@RunWith(AndroidJUnit4::class)
class InspectionUploadClientTest {
    @Test
    fun mockCompletionRetainsVisibleMockFlag() {
        val id = "11111111-1111-4111-8111-111111111111"
        val response = """{"inspection_id":"$id","analysis":{"status":"completed","origin":"mock","is_mock_input":false,"outcome":"suspected_abnormality"}}"""
        val result = parseUploadResponse(id, response)
        assertEquals("suspected_abnormality", result.outcome)
        assertTrue(result.isMock)
    }

    @Test
    fun pendingModelCannotBePresentedAsNormalDiagnosis() {
        val id = "11111111-1111-4111-8111-111111111111"
        val response = """{"inspection_id":"$id","analysis":{"status":"pending_model","origin":"none","is_mock_input":false,"outcome":"no_visible_abnormality"}}"""
        val error = runCatching { parseUploadResponse(id, response) }.exceptionOrNull()
        assertEquals("INVALID_RESPONSE", (error as UploadFailure).code)
    }

    @Test
    fun sendsTheSavedPhotoAndContractMetadataToLoopback() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        context.getSharedPreferences("captures_v1", Context.MODE_PRIVATE).edit().clear().commit()
        val store = CaptureStore(context)
        val capture = store.prepare("synthetic-plant", "synthetic-batch", "cherry_tomato")
        val file = File(context.filesDir, "photos/${capture.inspectionId}.jpg")
        file.outputStream().use { output ->
            Bitmap.createBitmap(2, 2, Bitmap.Config.ARGB_8888)
                .compress(Bitmap.CompressFormat.JPEG, 90, output)
        }
        assertTrue(store.finish(true))
        val record = store.all().single()
        val requestBody = AtomicReference<ByteArray>()
        val serverError = AtomicReference<Throwable>()
        try {
            ServerSocket(0, 1, InetAddress.getByName("127.0.0.1")).use { server ->
                val responder = Thread {
                    try {
                        server.accept().use { socket ->
                            socket.soTimeout = 10_000
                            val input = socket.getInputStream()
                            assertTrue(input.readLineAscii().startsWith("POST /v1/inspections HTTP/1."))
                            val headers = mutableListOf<String>()
                            while (true) {
                                val line = input.readLineAscii()
                                if (line.isEmpty()) break
                                headers.add(line)
                            }
                            assertTrue(headers.any { it.lowercase().startsWith("content-type: multipart/form-data;") })
                            assertTrue(headers.any { it.lowercase() == "transfer-encoding: chunked" })
                            val bytes = ByteArrayOutputStream()
                            while (true) {
                                val length = input.readLineAscii().substringBefore(';').toInt(16)
                                if (length == 0) {
                                    assertEquals("", input.readLineAscii())
                                    break
                                }
                                var remaining = length
                                val buffer = ByteArray(8192)
                                while (remaining > 0) {
                                    val count = input.read(buffer, 0, minOf(buffer.size, remaining))
                                    check(count > 0)
                                    bytes.write(buffer, 0, count)
                                    remaining -= count
                                }
                                assertEquals("", input.readLineAscii())
                            }
                            requestBody.set(bytes.toByteArray())
                            val response = """{"inspection_id":"${record.inspectionId}","analysis":{"status":"pending_model","origin":"none","is_mock_input":false,"outcome":null}}"""
                            val payload = response.toByteArray(Charsets.UTF_8)
                            socket.getOutputStream().write(
                                "HTTP/1.1 201 Created\r\nContent-Type: application/json\r\nContent-Length: ${payload.size}\r\nConnection: close\r\n\r\n"
                                    .toByteArray(Charsets.US_ASCII),
                            )
                            socket.getOutputStream().write(payload)
                            socket.getOutputStream().flush()
                        }
                    } catch (error: Throwable) {
                        serverError.set(error)
                    }
                }
                responder.start()
                val result = InspectionUploadClient(
                    context, URL("http://127.0.0.1:${server.localPort}/v1/inspections"),
                ).upload(record)
                responder.join(10_000)
                serverError.get()?.let { throw AssertionError("Loopback server failed", it) }
                assertEquals("pending_model", result.analysisStatus)
                assertEquals(null, result.outcome)
                assertEquals(false, result.isMock)
            }
            val body = requestBody.get().toString(Charsets.ISO_8859_1)
            val sha = MessageDigest.getInstance("SHA-256").digest(file.readBytes())
                .joinToString("") { "%02x".format(it.toInt() and 0xff) }
            assertTrue(body.contains("\"inspection_id\":\"${record.inspectionId}\""))
            assertTrue(body.contains("\"sensor_absence_reason\":\"not_acquired\""))
            assertTrue(body.contains("\"image_sha256\":\"$sha\""))
            assertTrue(body.contains("filename=\"capture.jpg\""))
        } finally {
            file.delete()
        }
    }

    private fun InputStream.readLineAscii(): String {
        val bytes = ByteArrayOutputStream()
        while (true) {
            val value = read()
            check(value >= 0) { "Unexpected end of request" }
            if (value == '\n'.code) break
            if (value != '\r'.code) bytes.write(value)
            check(bytes.size() < 16_384) { "Request line is too long" }
        }
        return bytes.toString(Charsets.US_ASCII.name())
    }
}
