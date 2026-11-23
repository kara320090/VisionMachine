package org.visionmachine.agriclinic

import android.graphics.Bitmap
import android.net.Uri
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.net.InetAddress
import java.net.ServerSocket
import java.util.UUID
import java.util.concurrent.FutureTask
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class ServerRgbLookupTest {
    @Test fun confirmedIdUsesAuthenticatedGetAndMissingResultUploadsAgain() {
        val app = InstrumentationRegistry.getInstrumentation().targetContext
        val photo = File.createTempFile("synthetic-lookup-", ".png", app.cacheDir)
        try {
            val bitmap = Bitmap.createBitmap(2, 2, Bitmap.Config.ARGB_8888)
            try {
                photo.outputStream().use { check(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)) }
            } finally {
                bitmap.recycle()
            }
            val uri = Uri.fromFile(photo)
            val ref = CaptureRecord(UUID.randomUUID().toString(), "synthetic", "batch", "basil", uri.toString(), "")
            val card = JSONObject(app.assets.open("vision_rgb_model.json").bufferedReader().use { it.readText() })
            val sha = LocalRgbEngine.sha(photo.readBytes())
            ServerSocket(0, 1, InetAddress.getByName("127.0.0.1")).use { server ->
                server.soTimeout = 10_000
                val config = ServerConfig("http://127.0.0.1:${server.localPort}", "synthetic-lookup-test-key")
                val responses = FutureTask {
                    var stored = ""
                    var id = ""
                    for (step in listOf("create", "reuse", "missing", "restore", "changed", "wrongResult", "lost", "recover")) {
                        server.accept().use serve@{ socket ->
                            socket.soTimeout = 10_000
                            val reader = socket.getInputStream().bufferedReader(Charsets.ISO_8859_1)
                            val request = reader.readLine()
                            val headers = generateSequence { reader.readLine()?.takeIf { it.isNotEmpty() } }
                                .associate { it.substringBefore(':').lowercase() to it.substringAfter(':').trim() }
                            assertEquals(config.apiKey, headers["x-api-key"])
                            val isPost = step in listOf("create", "restore", "changed", "lost")
                            val status: Int
                            val body: String
                            if (isPost) {
                                assertTrue(request.startsWith("POST /api/v1/inspections HTTP/"))
                                val size = headers.getValue("content-length").toInt()
                                val chars = CharArray(size)
                                var offset = 0
                                while (offset < size) {
                                    val n = reader.read(chars, offset, size - offset)
                                    check(n > 0)
                                    offset += n
                                }
                                val json = JSONObject(chars.concatToString().substringAfter("\r\n\r\n").substringBefore("\r\n--"))
                                val nextId = json.getString("client_inspection_id")
                                if (step == "restore") assertEquals(id, nextId)
                                if (step == "changed") assertNotEquals(id, nextId)
                                id = nextId
                                val row = json.getJSONArray("photos").getJSONObject(0)
                                val result = JSONObject().put("source_photo_id", ref.inspectionId).put("image_sha256", sha)
                                    .put("crop_code", row.getString("crop_code")).put("status", "completed")
                                    .put("normal", 0.25).put("abnormal", 0.75).put("elapsed_ms", 7)
                                    .put("model_version", card.getString("model_version")).put("model_sha256", card.getString("model_sha256"))
                                stored = JSONObject().put("inspection_id", id).put("client_inspection_id", id)
                                    .put("providers", JSONArray().put("CUDAExecutionProvider")).put("photos", JSONArray().put(result)).toString()
                                if (step == "lost") return@serve  // Close after accepting the complete photo.
                                status = 201
                                body = stored
                            } else {
                                assertTrue(request.startsWith("GET /api/v1/inspections/$id HTTP/"))
                                assertEquals(0, headers["content-length"]?.toInt() ?: 0)
                                assertFalse(headers.containsKey("transfer-encoding"))
                                status = if (step == "missing") 404 else 200
                                body = when (step) {
                                    "missing" -> "{}"
                                    "wrongResult" -> stored.replace(sha, "0".repeat(64))
                                    else -> stored
                                }
                            }
                            val data = body.toByteArray(Charsets.UTF_8)
                            val head = "HTTP/1.1 $status Test\r\nContent-Length: ${data.size}\r\nConnection: close\r\n\r\n"
                            socket.getOutputStream().apply { write(head.toByteArray(Charsets.US_ASCII)); write(data); flush() }
                        }
                    }
                }
                Thread(responses).start()
                val initial = ServerRgbClient(app, config).analyze(uri, ref)
                val client = ServerRgbClient(app, config, setOf(initial.inspectionId))
                assertEquals(initial, client.analyze(uri, ref))
                assertEquals(initial, client.analyze(uri, ref))
                val otherRef = ref.copy(cropCode = "pepper")
                val changed = client.analyze(uri, otherRef)
                assertNotEquals(initial.inspectionId, changed.inspectionId)
                assertThrows(IllegalArgumentException::class.java) {
                    ServerRgbClient(app, config, setOf(changed.inspectionId)).analyze(uri, otherRef)
                }
                val lastRef = ref.copy(cropCode = "tomato")
                val lost = assertThrows(UnconfirmedRgbUpload::class.java) { client.analyze(uri, lastRef) }
                val recovered = ServerRgbClient(app, config, setOf(lost.inspectionId)).analyze(uri, lastRef)
                assertEquals(lost.inspectionId, recovered.inspectionId)
                responses.get(10, TimeUnit.SECONDS)
            }
        } finally {
            photo.delete()
        }
    }
}
