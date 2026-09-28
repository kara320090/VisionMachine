package org.visionmachine.agriclinic

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.core.content.FileProvider
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.Instant
import java.util.UUID

data class CaptureRecord(
    val inspectionId: String,
    val subjectId: String,
    val batchId: String,
    val cropCode: String,
    val photoUri: String,
    val capturedAt: String,
)

data class PendingCapture(
    val inspectionId: String,
    val subjectId: String,
    val batchId: String,
    val cropCode: String,
    val photoUri: String,
)

// The pending camera URI must be durable before launching another app.
@SuppressLint("ApplySharedPref")
class CaptureStore(private val context: Context) {
    private val prefs = context.getSharedPreferences("captures_v1", Context.MODE_PRIVATE)
    private val photos = File(context.filesDir, "photos")

    fun all(): List<CaptureRecord> {
        val array = JSONArray(prefs.getString("records", "[]"))
        return (0 until array.length()).map { index ->
            val item = array.getJSONObject(index)
            CaptureRecord(
                item.getString("inspectionId"), item.getString("subjectId"),
                item.getString("batchId"), item.getString("cropCode"),
                item.getString("photoUri"), item.getString("capturedAt"),
            )
        }.reversed()
    }

    fun pending(): PendingCapture? {
        val raw = prefs.getString("pending", null) ?: return null
        val item = JSONObject(raw)
        return PendingCapture(
            item.getString("inspectionId"), item.getString("subjectId"),
            item.getString("batchId"), item.getString("cropCode"), item.getString("photoUri"),
        )
    }

    fun prepare(subjectId: String, batchId: String, cropCode: String): PendingCapture {
        check(pending() == null) { "A camera capture is already pending" }
        photos.mkdirs()
        val id = UUID.randomUUID().toString()
        val file = File(photos, "$id.jpg")
        check(file.createNewFile()) { "Could not prepare the photo" }
        val uri = try {
            FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
        } catch (error: Exception) {
            file.delete()
            throw error
        }
        val capture = PendingCapture(id, subjectId, batchId, cropCode, uri.toString())
        val item = JSONObject()
            .put("inspectionId", id)
            .put("subjectId", subjectId)
            .put("batchId", batchId)
            .put("cropCode", cropCode)
            .put("photoUri", capture.photoUri)
        if (!prefs.edit().putString("pending", item.toString()).commit()) {
            file.delete()
            error("Could not save capture state")
        }
        return capture
    }

    fun finish(success: Boolean): Boolean {
        val capture = pending() ?: return false
        val file = File(photos, "${capture.inspectionId}.jpg")
        val image = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        if (success && file.isFile && file.length() > 0L) {
            BitmapFactory.decodeFile(file.absolutePath, image)
        }
        if (!success || image.outMimeType != "image/jpeg" || image.outWidth <= 0 || image.outHeight <= 0) {
            file.delete()
            prefs.edit().remove("pending").commit()
            return false
        }
        val record = JSONObject()
            .put("inspectionId", capture.inspectionId)
            .put("subjectId", capture.subjectId)
            .put("batchId", capture.batchId)
            .put("cropCode", capture.cropCode)
            .put("photoUri", capture.photoUri)
            .put("capturedAt", Instant.now().toString())
        val records = JSONArray(prefs.getString("records", "[]"))
        records.put(record)
        check(prefs.edit().putString("records", records.toString()).remove("pending").commit()) {
            "Could not save captured photo record"
        }
        return true
    }

    fun fileFor(record: CaptureRecord): Uri = Uri.parse(record.photoUri)
}
