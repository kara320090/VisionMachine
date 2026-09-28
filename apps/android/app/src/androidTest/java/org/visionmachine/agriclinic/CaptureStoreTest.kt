package org.visionmachine.agriclinic

import android.content.Context
import android.graphics.Bitmap
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class CaptureStoreTest {
    private lateinit var context: Context

    @Before
    fun resetRecords() {
        context = InstrumentationRegistry.getInstrumentation().targetContext
        context.getSharedPreferences("captures_v1", Context.MODE_PRIVATE).edit().clear().commit()
    }

    @Test
    fun successfulPhotoIsRecordedAcrossStoreInstances() {
        val store = CaptureStore(context)
        val capture = store.prepare("synthetic-plant", "synthetic-batch", "cherry_tomato")
        val file = File(context.filesDir, "photos/${capture.inspectionId}.jpg")
        file.outputStream().use { output ->
            Bitmap.createBitmap(2, 2, Bitmap.Config.ARGB_8888)
                .compress(Bitmap.CompressFormat.JPEG, 90, output)
        }
        try {
            assertTrue(store.finish(true))
            val reloaded = CaptureStore(context).all()
            assertEquals(1, reloaded.size)
            assertEquals(capture.inspectionId, reloaded.single().inspectionId)
            assertEquals("synthetic-plant", reloaded.single().subjectId)
            assertTrue(file.length() > 0)
        } finally {
            file.delete()
        }
    }

    @Test
    fun cancelledPhotoRemovesEmptyFileAndPendingRecord() {
        val store = CaptureStore(context)
        val capture = store.prepare("synthetic-plant", "synthetic-batch", "lettuce")
        val file = File(context.filesDir, "photos/${capture.inspectionId}.jpg")
        assertTrue(file.exists())
        assertFalse(store.finish(false))
        assertFalse(file.exists())
        assertEquals(null, CaptureStore(context).pending())
        assertTrue(CaptureStore(context).all().isEmpty())
    }

    @Test
    fun invalidCameraBytesAreDiscarded() {
        val store = CaptureStore(context)
        val capture = store.prepare("synthetic-plant", "synthetic-batch", "lettuce")
        val file = File(context.filesDir, "photos/${capture.inspectionId}.jpg")
        file.writeText("not a JPEG")
        assertFalse(store.finish(true))
        assertFalse(file.exists())
        assertTrue(CaptureStore(context).all().isEmpty())
    }

    @Test
    fun failedUploadKeepsTheSameInspectionIdForRetry() {
        val store = CaptureStore(context)
        val capture = store.prepare("synthetic-plant", "synthetic-batch", "lettuce")
        val file = File(context.filesDir, "photos/${capture.inspectionId}.jpg")
        file.outputStream().use { output ->
            Bitmap.createBitmap(2, 2, Bitmap.Config.ARGB_8888)
                .compress(Bitmap.CompressFormat.JPEG, 90, output)
        }
        try {
            assertTrue(store.finish(true))
            store.updateUpload(capture.inspectionId, UploadState.UPLOADING)
            store.updateUpload(capture.inspectionId, UploadState.FAILED, "NETWORK_ERROR")
            val retry = CaptureStore(context).all().single()
            assertEquals(capture.inspectionId, retry.inspectionId)
            assertEquals(UploadState.FAILED, retry.uploadState)
            assertEquals("NETWORK_ERROR", retry.uploadError)
            store.updateUpload(retry.inspectionId, UploadState.UPLOADED, analysisStatus = "pending_model", analysisIsMock = true)
            val uploaded = CaptureStore(context).all().single()
            assertEquals(UploadState.UPLOADED, uploaded.uploadState)
            assertEquals("pending_model", uploaded.analysisStatus)
            assertTrue(uploaded.analysisIsMock)
            assertEquals(null, uploaded.uploadError)
        } finally {
            file.delete()
        }
    }

    @Test
    fun interruptedUploadCanBeRetriedAfterRestart() {
        val store = CaptureStore(context)
        val capture = store.prepare("synthetic-plant", "synthetic-batch", "basil")
        val file = File(context.filesDir, "photos/${capture.inspectionId}.jpg")
        file.outputStream().use { output ->
            Bitmap.createBitmap(2, 2, Bitmap.Config.ARGB_8888)
                .compress(Bitmap.CompressFormat.JPEG, 90, output)
        }
        try {
            assertTrue(store.finish(true))
            store.updateUpload(capture.inspectionId, UploadState.UPLOADING)
            val restarted = CaptureStore(context)
            restarted.recoverInterruptedUploads()
            assertEquals(UploadState.FAILED, restarted.all().single().uploadState)
            assertEquals("INTERRUPTED", restarted.all().single().uploadError)
        } finally {
            file.delete()
        }
    }
}
