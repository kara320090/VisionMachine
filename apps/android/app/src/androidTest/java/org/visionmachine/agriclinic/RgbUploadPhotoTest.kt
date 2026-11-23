package org.visionmachine.agriclinic

import android.content.res.AssetFileDescriptor
import android.graphics.Bitmap
import android.os.ParcelFileDescriptor
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.IOException
import java.nio.file.Files
import java.security.MessageDigest

@RunWith(AndroidJUnit4::class)
class RgbUploadPhotoTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    private fun png(): ByteArray {
        val bitmap = Bitmap.createBitmap(3, 4, Bitmap.Config.ARGB_8888)
        return try {
            ByteArrayOutputStream().use { output ->
                check(bitmap.compress(Bitmap.CompressFormat.PNG, 100, output))
                output.toByteArray()
            }
        } finally { bitmap.recycle() }
    }

    private fun assertPhoto(bytes: ByteArray, photo: RgbUploadPhoto) {
        val hash = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
        assertEquals(bytes.size.toLong(), photo.size)
        assertEquals(hash, photo.sha256)
        assertEquals("image/png", photo.mediaType)
        val sent = ByteArrayOutputStream().also(photo.writeTo)
        assertArrayEquals(bytes, sent.toByteArray())
    }

    @Test fun changedOpenFileRetriesFromOneVerifiedSnapshotBeforeMultipartCanFinish() {
        val scratch = Files.createTempDirectory(context.cacheDir.toPath(), "synthetic-rgb-").toFile()
        try {
            val cache = File(scratch, "cache").apply { check(mkdir()) }
            val original = png() + 1.toByte()
            val changed = original.copyOf().apply { this[lastIndex] = 2 }
            val file = File(scratch, "photo.png").apply { writeBytes(original) }
            val fd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
            var attempts = 0
            AssetFileDescriptor(fd, 0, AssetFileDescriptor.UNKNOWN_LENGTH).use { asset ->
                withRgbUploadPhoto(asset, cache) { photo ->
                    if (++attempts == 1) {
                        assertTrue(cache.listFiles()!!.isEmpty())
                        assertPhoto(original, photo)
                        file.writeBytes(changed)
                        // HttpURLConnection may also throw when closing the incomplete request body.
                        object : ByteArrayOutputStream() {
                            override fun close() { throw IOException("synthetic incomplete body") }
                        }.use { output ->
                            photo.writeTo(output)
                            fail("Changed bytes must prevent the multipart closing boundary")
                        }
                    } else {
                        assertEquals(1, cache.listFiles()!!.size)
                        assertPhoto(changed, photo)
                    }
                }
            }
            assertEquals(2, attempts)
            assertTrue(cache.listFiles()!!.isEmpty())
        } finally { scratch.deleteRecursively() }
    }

    @Test fun pipeAndSliceAreStagedOnceAndCleanedOnFailure() {
        val scratch = Files.createTempDirectory(context.cacheDir.toPath(), "synthetic-rgb-").toFile()
        try {
            val cache = File(scratch, "cache").apply { check(mkdir()) }
            val original = png()
            fun checkSnapshot(asset: AssetFileDescriptor) {
                asset.use {
                    assertThrows(IOException::class.java) {
                        withRgbUploadPhoto(asset, cache) { photo ->
                            assertEquals(1, cache.listFiles()!!.size)
                            assertPhoto(original, photo)
                            assertPhoto(original, photo)
                            throw IOException("synthetic request failure")
                        }
                    }
                }
                assertTrue(cache.listFiles()!!.isEmpty())
            }
            val pipe = ParcelFileDescriptor.createPipe()
            ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]).use { it.write(original) }
            checkSnapshot(AssetFileDescriptor(pipe[0], 0, AssetFileDescriptor.UNKNOWN_LENGTH))
            val container = File(scratch, "slice").apply { writeBytes(ByteArray(17) + original + ByteArray(17)) }
            val fd = ParcelFileDescriptor.open(container, ParcelFileDescriptor.MODE_READ_ONLY)
            checkSnapshot(AssetFileDescriptor(fd, 17, original.size.toLong()))
        } finally { scratch.deleteRecursively() }
    }
}
