package org.visionmachine.agriclinic

import android.content.Context
import android.graphics.BitmapFactory
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.util.UUID

data class ServerRgbResult(val normal: Float, val abnormal: Float, val millis: Long, val sha256: String,
    val model: String, val inspectionId: String, val sensor: SensorRecord?)

class ServerRgbClient(private val context: Context, private val config: ServerConfig) {
    fun analyze(uri: Uri, reference: CaptureRecord): ServerRgbResult {
        val bytes = context.contentResolver.openInputStream(uri)?.use { input ->
            val output = ByteArrayOutputStream(); val buffer = ByteArray(65536)
            while (true) {
                val count = input.read(buffer); if (count < 0) break
                require(output.size().toLong() + count <= 24L * 1024 * 1024) { "사진은 24MiB 이하여야 합니다." }
                output.write(buffer, 0, count)
            }
            output.toByteArray()
        } ?: error("사진을 읽지 못했습니다.")
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
        require(bounds.outMimeType in setOf("image/jpeg", "image/png")) { "JPEG/PNG 사진을 선택해 주세요." }
        val sha = LocalRgbEngine.sha(bytes)
        val sensor = SensorStore(context).all().firstOrNull {
            it.sourceCaptureId == reference.inspectionId && it.cropCode == reference.cropCode && it.photoSha256 == sha
        }?.let { stored ->
            val assessment = stored.assessmentJson ?: SensorScoring.assess(JSONObject(stored.packetJson),
                SensorProfileStore(context).get(reference.cropCode)).put("sensor_received_at", stored.receivedAt).toString()
            stored.copy(assessmentJson = assessment)
        }
        val meta = JSONObject().put("source_photo_id", reference.inspectionId).put("crop_code", reference.cropCode)
            .put("subject_id", reference.subjectId).put("batch_id", reference.batchId)
            .put("image_sha256", sha).put("image_media_type", bounds.outMimeType)
            .put("captured_at", reference.capturedAt.takeIf { it.isNotBlank() } ?: JSONObject.NULL)
            .put("sensor", sensor?.let { s -> JSONObject().put("sensor_record_id", s.inspectionId)
                .put("source_photo_id", reference.inspectionId).put("crop_code", s.cropCode).put("photo_sha256", sha)
                .put("received_at", s.receivedAt).put("packet", JSONObject(s.packetJson))
                .put("assessment_json", s.assessmentJson ?: JSONObject.NULL) } ?: JSONObject.NULL)
        // Stable content-derived request ID survives manual retries and process restarts.
        val id = UUID.nameUUIDFromBytes(meta.toString().toByteArray(Charsets.UTF_8)).toString()
        val payload = JSONObject().put("schema_version", "0.1.0").put("client_inspection_id", id).put("photos", JSONArray().put(meta))
        val boundary = "VisionMachine-${UUID.randomUUID()}"
        val start = ("--$boundary\r\nContent-Disposition: form-data; name=\"payload\"\r\n\r\n$payload\r\n" +
            "--$boundary\r\nContent-Disposition: form-data; name=\"photos\"; filename=\"photo\"\r\nContent-Type: ${bounds.outMimeType}\r\n\r\n").toByteArray(Charsets.UTF_8)
        val end = "\r\n--$boundary--\r\n".toByteArray(Charsets.UTF_8)
        val connection = URL(checkedServerUrl(config.baseUrl) + "/api/v1/inspections").openConnection() as HttpURLConnection
        try {
            connection.instanceFollowRedirects = false
            connection.requestMethod = "POST"; connection.connectTimeout = 10_000; connection.readTimeout = 180_000
            connection.doOutput = true; connection.setFixedLengthStreamingMode(start.size.toLong() + bytes.size + end.size)
            connection.setRequestProperty("X-API-Key", config.apiKey)
            connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            connection.outputStream.use { it.write(start); it.write(bytes); it.write(end) }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val body = stream?.use { input ->
                val output = ByteArrayOutputStream(); val buffer = ByteArray(8192)
                while (true) { val n = input.read(buffer); if (n < 0) break
                    require(output.size() + n <= 1024 * 1024) { "서버 응답이 너무 큽니다." }; output.write(buffer, 0, n) }
                output.toString("UTF-8")
            }.orEmpty()
            if (status !in 200..299) {
                val code = runCatching { JSONObject(body).getJSONObject("detail").getString("code") }.getOrDefault("HTTP_$status")
                error(when (code) { "MODEL_NOT_READY" -> "서버 모델이 준비되지 않았습니다. ONNX 파일과 GPU 준비 상태를 확인해 주세요."
                    "UNAUTHORIZED" -> "서버 인증키를 확인해 주세요."
                    "ID_CONFLICT" -> "같은 검사 ID의 내용이 다릅니다. 서버 기록을 확인해 주세요."
                    else -> "서버 요청 실패: $code" })
            }
            val card = JSONObject(context.assets.open("vision_rgb_model.json").bufferedReader().use { it.readText() })
            val result = parseServerRgbResponse(body, id, reference.inspectionId, reference.cropCode, sha, card)
            return result.copy(sensor = sensor)
        } finally { connection.disconnect() }
    }
}

internal fun parseServerRgbResponse(body: String, id: String, photoId: String, crop: String, sha: String, card: JSONObject): ServerRgbResult {
    val root = JSONObject(body)
    require(root.getString("inspection_id") == id && root.getString("client_inspection_id") == id)
    require((0 until root.getJSONArray("providers").length()).any { root.getJSONArray("providers").getString(it) == "CUDAExecutionProvider" })
    val photos = root.getJSONArray("photos"); require(photos.length() == 1)
    val result = photos.getJSONObject(0)
    require(result.getString("source_photo_id") == photoId && result.getString("image_sha256") == sha && result.getString("crop_code") == crop)
    check(result.getString("status") == "completed") { "사진 분석 실패: ${result.optString("error_code")}" }
    require(result.getString("model_version") == card.getString("model_version") && result.getString("model_sha256") == card.getString("model_sha256"))
    val normal = result.getDouble("normal"); val abnormal = result.getDouble("abnormal")
    require(normal.isFinite() && abnormal.isFinite() && normal in 0.0..1.0 && abnormal in 0.0..1.0 && kotlin.math.abs(normal + abnormal - 1) < 1e-4)
    val millis = result.getLong("elapsed_ms"); require(millis >= 0)
    return ServerRgbResult(normal.toFloat(), abnormal.toFloat(), millis, sha, card.getString("model_version"), id, null)
}
