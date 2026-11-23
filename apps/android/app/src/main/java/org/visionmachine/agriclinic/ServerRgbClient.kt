package org.visionmachine.agriclinic

import android.content.Context
import android.net.Uri
import android.os.SystemClock
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

data class ServerRgbResult(val normal: Float, val abnormal: Float, val millis: Long, val sha256: String,
    val model: String, val inspectionId: String, val sensor: SensorRecord?)

internal class UnconfirmedRgbUpload(val inspectionId: String, cause: IOException) :
    IOException("서버 응답을 받지 못했습니다. 다시 분석하면 저장된 결과부터 확인합니다.", cause)

class ServerRgbClient(
    private val context: Context,
    private val config: ServerConfig,
    private val knownServerIds: Set<String> = emptySet(),
) {
    fun analyze(uri: Uri, reference: CaptureRecord, refreshCredentials: (() -> ServerConfig)? = null): ServerRgbResult {
        val stagingStartedAt = SystemClock.elapsedRealtime()
        var activeConfig = config
        var refresh = refreshCredentials
        return withRgbUploadPhoto(context, uri) { photo ->
            val request = prepareRequest(photo, reference, stagingStartedAt)
            try {
                request(activeConfig)
            } catch (error: ServerRequestException) {
                if (error.code != "UNAUTHORIZED") throw error
                val renew = refresh ?: throw error
                refresh = null
                activeConfig = renew()
                request(activeConfig)
            }
        }
    }

    private fun prepareRequest(
        photo: RgbUploadPhoto,
        reference: CaptureRecord,
        stagingStartedAt: Long,
    ): (ServerConfig) -> ServerRgbResult {
        val stagedAt = SystemClock.elapsedRealtime()
        val sha = photo.sha256
        val mediaType = photo.mediaType
        val sensor = SensorStore(context).all().firstOrNull {
            it.sourceCaptureId == reference.inspectionId && it.cropCode == reference.cropCode && it.photoSha256 == sha
        }?.let { stored ->
            val assessment = stored.assessmentJson ?: SensorScoring.assess(JSONObject(stored.packetJson),
                SensorProfileStore(context).get(reference.cropCode)).put("sensor_received_at", stored.receivedAt).toString()
            stored.copy(assessmentJson = assessment)
        }
        val meta = JSONObject().put("source_photo_id", reference.inspectionId).put("crop_code", reference.cropCode)
            .put("subject_id", reference.subjectId).put("batch_id", reference.batchId)
            .put("image_sha256", sha).put("image_media_type", mediaType)
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
            "--$boundary\r\nContent-Disposition: form-data; name=\"photos\"; filename=\"photo\"\r\nContent-Type: $mediaType\r\n\r\n").toByteArray(Charsets.UTF_8)
        val end = "\r\n--$boundary--\r\n".toByteArray(Charsets.UTF_8)
        val preparedAt = SystemClock.elapsedRealtime()
        fun checkedResult(body: String): ServerRgbResult {
            val card = JSONObject(context.assets.open("vision_rgb_model.json").bufferedReader().use { it.readText() })
            return parseServerRgbResponse(body, id, reference.inspectionId, reference.cropCode, sha, card)
                .copy(sensor = sensor)
        }
        fun request(activeConfig: ServerConfig): ServerRgbResult {
            if (id in knownServerIds) {
                val prior = lookupServerRgbResponse(activeConfig, id)
                if (prior != null) {
                    val result = checkedResult(prior)
                    Log.i("VisionRgbTiming", "status=200 method=GET photo_bytes_sent=0 " +
                        "client_total_ms=${SystemClock.elapsedRealtime() - stagingStartedAt} server_inference_ms=unavailable")
                    return result
                }
            }
            val connection = URL(checkedServerUrl(activeConfig.baseUrl) + "/api/v1/inspections").openConnection() as HttpURLConnection
            var submitted = false
            try {
                connection.instanceFollowRedirects = false
                connection.requestMethod = "POST"; connection.connectTimeout = 10_000; connection.readTimeout = 180_000
                connection.doOutput = true; connection.setFixedLengthStreamingMode(start.size.toLong() + photo.size + end.size)
                connection.setRequestProperty("X-API-Key", activeConfig.apiKey)
                connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
                val requestOpenStartedAt = SystemClock.elapsedRealtime()
                val requestBody = connection.outputStream
                val requestOpenedAt = SystemClock.elapsedRealtime()
                requestBody.use { output ->
                    output.write(start)
                    photo.writeTo(output)
                    output.write(end)
                    submitted = true
                }
                val requestWrittenAt = SystemClock.elapsedRealtime()
                val status = connection.responseCode
                if (status < 0) throw IOException("Invalid HTTP response")
                val responseHeadersAt = SystemClock.elapsedRealtime()
                val body = connection.readRgbResponse(status)
                val responseReadAt = SystemClock.elapsedRealtime()
                if (status !in 200..299) throw rgbRequestError(status, body)
                val result = checkedResult(body)
                val serverQueueMs = connection.headerFields.entries
                    .firstOrNull { it.key?.equals("Server-Timing", ignoreCase = true) == true }
                    ?.value?.firstNotNullOfOrNull(::parseServerQueueMillis)
                val serverInferenceMs = result.millis.takeIf { status == HttpURLConnection.HTTP_CREATED }
                Log.i("VisionRgbTiming",
                    "status=$status client_total_ms=${SystemClock.elapsedRealtime() - stagingStartedAt} " +
                        "staging_ms=${stagedAt - stagingStartedAt} " +
                        "request_prepare_ms=${preparedAt - stagedAt} " +
                        "request_open_ms=${requestOpenedAt - requestOpenStartedAt} " +
                        "request_write_ms=${requestWrittenAt - requestOpenedAt} " +
                        "response_headers_wait_ms=${responseHeadersAt - requestWrittenAt} " +
                        "response_body_ms=${responseReadAt - responseHeadersAt} " +
                        "server_queue_ms=${serverQueueMs ?: "unavailable"} " +
                        "server_inference_ms=${serverInferenceMs ?: "unavailable"}")
                return result
            } catch (error: IOException) {
                if (submitted && error !is ServerRequestException) throw UnconfirmedRgbUpload(id, error)
                throw error
            } finally { connection.disconnect() }
        }
        return ::request
    }
}

internal fun parseServerQueueMillis(header: String): Double? = header.split(',').firstNotNullOfOrNull { value ->
    val metric = value.split(';')
    if (metric.first().trim() != "vm_queue") return@firstNotNullOfOrNull null
    metric.drop(1).firstOrNull { it.substringBefore('=').trim() == "dur" }
        ?.substringAfter('=', "")?.trim()?.removeSurrounding("\"")?.toDoubleOrNull()
        ?.takeIf { it.isFinite() && it >= 0 }
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
