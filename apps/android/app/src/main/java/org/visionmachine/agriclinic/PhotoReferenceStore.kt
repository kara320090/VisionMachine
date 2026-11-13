package org.visionmachine.agriclinic

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID
import java.security.MessageDigest

/** Photo references only. An imported image's exposure time and plant identity are unknown. */
class PhotoReferenceStore(context: Context) {
    private val prefs = context.getSharedPreferences("analysis_photo_references_v1", Context.MODE_PRIVATE)
    fun all(): List<CaptureRecord> = synchronized(lock) {
        val rows = JSONArray(prefs.getString("rows", "[]"))
        (0 until rows.length()).map { index ->
            val row = rows.getJSONObject(index)
            CaptureRecord(row.getString("id"), row.getString("subject"), row.getString("batch"),
                row.getString("crop"), row.getString("uri"), row.getString("captured_at"))
        }
    }
    fun put(uri: Uri, crop: String, capture: CaptureRecord? = null): CaptureRecord = synchronized(lock) {
        require(CropChoices.any { it.first == crop })
        val rows = all()
        val previous = rows.find { it.photoUri == uri.toString() }
        val source = capture ?: previous ?: CaptureRecord(UUID.randomUUID().toString(), "unassigned", "unassigned", crop, uri.toString(), "")
        val updated = source.copy(cropCode = crop)
        val result = JSONArray()
        (rows.filter { it.inspectionId != updated.inspectionId }.takeLast(499) + updated).forEach { row ->
            result.put(JSONObject().put("id", row.inspectionId).put("subject", row.subjectId).put("batch", row.batchId)
                .put("crop", row.cropCode).put("uri", row.photoUri).put("captured_at", row.capturedAt))
        }
        check(prefs.edit().putString("rows", result.toString()).commit())
        updated
    }
    companion object {
        private val lock = Any()
        fun hash(context: Context, uri: Uri): String {
            val digest=MessageDigest.getInstance("SHA-256")
            context.contentResolver.openInputStream(uri)!!.use { input ->
                val bytes=ByteArray(65536);var total=0L
                while(true) {val count=input.read(bytes);if(count<0) break;total+=count;require(total<=24L*1024*1024);digest.update(bytes,0,count)}
                require(total>0)
            }
            return digest.digest().joinToString("") {"%02x".format(it)}
        }
    }
}

// Union of the RGB model card and the existing recording catalogue; no crop recognition is claimed.
internal val CropChoices = listOf("tomato" to "토마토", "cherry_tomato" to "방울토마토(토마토 자료 참고)", "pepper" to "고추", "cucumber" to "오이",
    "lettuce" to "상추", "bok_choy" to "청경채", "basil" to "바질", "rosemary" to "로즈마리", "kale" to "케일", "eggplant" to "가지(센서 기록)")
internal fun cropLabel(code: String?) = CropChoices.find { it.first == code }?.second ?: "작물 미지정"
