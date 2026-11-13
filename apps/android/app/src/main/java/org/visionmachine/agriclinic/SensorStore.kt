package org.visionmachine.agriclinic

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.util.UUID

data class SensorRecord(
    val inspectionId: String,
    val receivedAt: String,
    val packetJson: String,
    val sourceCaptureId: String? = null,
    val photoUri: String? = null,
    val photoCapturedAt: String? = null,
    val subjectId: String? = null,
    val batchId: String? = null,
    val cropCode: String? = null,
    val assessmentJson: String? = null,
    val photoSha256: String? = null,
)

/** New measurement IDs; existing camera records/photos are never rewritten. */
class SensorStore(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("sensor_records_v1", Context.MODE_PRIVATE)

    @Synchronized fun all(): List<SensorRecord> {
        val records = JSONArray(prefs.getString("records", "[]"))
        return (records.length() - 1 downTo 0).map { index ->
            val item = records.getJSONObject(index)
            SensorRecord(item.getString("inspectionId"), item.getString("receivedAt"), item.getString("packetJson"),
                item.nullableString("sourceCaptureId"), item.nullableString("photoUri"), item.nullableString("photoCapturedAt"),
                item.nullableString("subjectId"), item.nullableString("batchId"), item.nullableString("cropCode"), item.nullableString("assessmentJson"), item.nullableString("photoSha256"))
        }
    }

    fun save(id: UUID, frame: SensorFrame.Measurement, photo: CaptureRecord?, receivedAt: String = Instant.now().toString(),
        cropCode: String? = photo?.cropCode, assessmentJson: String? = null, photoSha256: String? = null): SensorRecord = synchronized(saveLock) {
        Instant.parse(receivedAt)
        val checked = SensorPacketFramer(id).feed((frame.json + "\n").toByteArray(Charsets.UTF_8)).singleOrNull()
        require(checked is SensorFrame.Measurement && checked.isMock == frame.isMock) { "Invalid sensor record" }
        require(photo == null || photo.cropCode == cropCode) { "Photo crop does not match measurement crop" }
        require(photoSha256 == null || Regex("[0-9a-f]{64}").matches(photoSha256))
        val existing = all()
        check(existing.none { it.inspectionId == id.toString() }) { "Duplicate measurement ID" }
        val record = SensorRecord(id.toString(), receivedAt, frame.json, photo?.inspectionId, photo?.photoUri,
            photo?.capturedAt?.takeIf { it.isNotBlank() }, photo?.subjectId, photo?.batchId, cropCode, assessmentJson, photoSha256)
        val rows = JSONArray()
        (existing.take(199).reversed() + record).forEach { row ->
            rows.put(JSONObject().put("inspectionId", row.inspectionId).put("receivedAt", row.receivedAt)
                .put("packetJson", row.packetJson).put("sourceCaptureId", row.sourceCaptureId ?: JSONObject.NULL)
                .put("photoUri", row.photoUri ?: JSONObject.NULL).put("photoCapturedAt", row.photoCapturedAt ?: JSONObject.NULL)
                .put("subjectId", row.subjectId ?: JSONObject.NULL).put("batchId", row.batchId ?: JSONObject.NULL)
                .put("cropCode", row.cropCode ?: JSONObject.NULL).put("assessmentJson", row.assessmentJson ?: JSONObject.NULL).put("photoSha256", row.photoSha256 ?: JSONObject.NULL))
        }
        check(prefs.edit().putString("records", rows.toString()).commit()) { "Could not persist sensor reading" }
        record
    }

    companion object {
        private val saveLock = Any()
        fun csv(records: List<SensorRecord>): String {
            val header = listOf("inspection_id", "sensor_received_at", "source_capture_id", "captured_at", "subject_id", "batch_id",
                "crop_code", "photo_uri", "mode", "soil_raw", "soil_index", "air_temp_c", "air_rh_pct", "optical_raw_counts",
                "object_temp_c", "mlx_ambient_temp_c", "errors", "sensor_packet_json", "sensor_assessment_json", "photo_sha256")
            fun quote(value: String, userText: Boolean): String {
                // Preserve user-entered identifiers as text in spreadsheet applications.
                val safe = if (userText && value.trimStart().firstOrNull() in listOf('=', '+', '-', '@')) "'$value" else value
                return "\"" + safe.replace("\"", "\"\"") + "\""
            }
            val rows = records.map { row ->
                val packet = JSONObject(row.packetJson)
                val readings = packet.getJSONObject("readings")
                val extensions = packet.optJSONObject("extensions")
                listOf(row.inspectionId, row.receivedAt, row.sourceCaptureId.orEmpty(), row.photoCapturedAt.orEmpty(),
                    row.subjectId.orEmpty(), row.batchId.orEmpty(), row.cropCode.orEmpty(), row.photoUri.orEmpty(), packet.getString("mode"),
                    readings.csvValue("soil_raw"), readings.csvValue("soil_index"), readings.csvValue("air_temp_c"), readings.csvValue("air_rh_pct"),
                    extensions?.optJSONObject("optical")?.csvValue("raw_counts").orEmpty(),
                    extensions?.optJSONObject("surface_temperature")?.csvValue("object_temp_c").orEmpty(),
                    extensions?.optJSONObject("surface_temperature")?.csvValue("ambient_temp_c").orEmpty(), packet.getJSONArray("errors").toString(), row.packetJson, row.assessmentJson.orEmpty(), row.photoSha256.orEmpty())
            }
            return (listOf(header) + rows).joinToString("\r\n", postfix = "\r\n") { row ->
                row.mapIndexed { index, value -> quote(value, index in 4..7) }.joinToString(",")
            }
        }
    }
}

private fun JSONObject.nullableString(key: String): String? = if (isNull(key)) null else getString(key)
private fun JSONObject.csvValue(key: String): String = if (isNull(key)) "" else get(key).toString()
