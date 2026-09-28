package org.visionmachine.agriclinic

import android.content.Context
import android.net.Uri
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.UUID

data class UploadResult(val analysisStatus: String, val outcome: String?)

class UploadFailure(val code: String) : IOException(code)

/** Development endpoint only: adb reverse tcp:8000 tcp:8000 reaches the loopback server. */
class InspectionUploadClient(
    private val context: Context,
    private val endpoint: URL = URL("http://127.0.0.1:8000/v1/inspections"),
) {
    fun upload(record: CaptureRecord): UploadResult {
        require(endpoint.protocol == "http" && endpoint.host == "127.0.0.1" && endpoint.port in 1..65535 && endpoint.path == "/v1/inspections") {
            "Only the local development server is supported"
        }
        val uri = Uri.parse(record.photoUri)
        val digest = MessageDigest.getInstance("SHA-256")
        var size = 0L
        context.contentResolver.openInputStream(uri)?.use { input ->
            val buffer = ByteArray(8192)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                size += count
                if (size > 12L * 1024 * 1024) throw UploadFailure("IMAGE_TOO_LARGE")
                digest.update(buffer, 0, count)
            }
        } ?: throw UploadFailure("PHOTO_UNAVAILABLE")
        if (size == 0L) throw UploadFailure("PHOTO_UNAVAILABLE")
        val hash = digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
        val metadata = JSONObject()
            .put("schema_version", "0.1.0")
            .put("inspection_id", record.inspectionId)
            .put("subject_id", record.subjectId)
            .put("subject_type", "plant")
            .put("parent_plant_id", JSONObject.NULL)
            .put("batch_id", record.batchId)
            .put("crop_code", record.cropCode)
            .put("captured_at", record.capturedAt)
            .put("capture_source", "real")
            .put("image_sha256", hash)
            .put("image_media_type", "image/jpeg")
            .put("sensor_packet", JSONObject.NULL)
            .put("sensor_received_at", JSONObject.NULL)
            .put("sensor_absence_reason", "not_acquired")
        val boundary = "VisionMachine-${UUID.randomUUID()}"
        val connection = endpoint.openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = 10_000
            connection.readTimeout = 30_000
            connection.doOutput = true
            connection.setChunkedStreamingMode(8192)
            connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            connection.outputStream.use { output ->
                fun write(value: String) = output.write(value.toByteArray(Charsets.UTF_8))
                write("--$boundary\r\nContent-Disposition: form-data; name=\"metadata\"\r\n\r\n")
                write(metadata.toString())
                write("\r\n--$boundary\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"capture.jpg\"\r\n")
                write("Content-Type: image/jpeg\r\n\r\n")
                context.contentResolver.openInputStream(uri)?.use { it.copyTo(output) }
                    ?: throw UploadFailure("PHOTO_UNAVAILABLE")
                write("\r\n--$boundary--\r\n")
            }
            val status = connection.responseCode
            val response = (if (status in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader(Charsets.UTF_8)?.use { it.readText().take(65_536) } ?: ""
            if (status !in 200..299) {
                val code = runCatching { JSONObject(response).getJSONObject("detail").getString("code") }
                    .getOrDefault("HTTP_$status")
                throw UploadFailure(code)
            }
            val body = try { JSONObject(response) } catch (_: Exception) { throw UploadFailure("INVALID_RESPONSE") }
            if (body.optString("inspection_id") != record.inspectionId) throw UploadFailure("ID_MISMATCH")
            val analysis = body.optJSONObject("analysis") ?: throw UploadFailure("INVALID_RESPONSE")
            val analysisStatus = analysis.optString("status")
            if (analysisStatus !in setOf("pending_model", "completed", "failed")) {
                throw UploadFailure("INVALID_RESPONSE")
            }
            val outcome = if (analysis.isNull("outcome")) null else analysis.optString("outcome")
            return UploadResult(analysisStatus, outcome)
        } finally {
            connection.disconnect()
        }
    }
}
