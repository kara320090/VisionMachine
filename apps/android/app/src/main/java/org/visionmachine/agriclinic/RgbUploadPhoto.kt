package org.visionmachine.agriclinic

import android.content.ContentResolver
import android.content.Context
import android.content.res.AssetFileDescriptor
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.system.ErrnoException
import android.system.Os
import android.system.OsConstants
import java.io.File
import java.io.InputStream
import java.io.OutputStream
import java.security.MessageDigest

private const val MAX_PHOTO_BYTES = 24L * 1024 * 1024
private const val BUFFER_SIZE = 64 * 1024

internal class RgbUploadPhoto(
    val size: Long,
    val sha256: String,
    val mediaType: String,
    val writeTo: (OutputStream) -> Unit,
)

private class SourceChanged : Exception()

private class PhotoDigest(val size: Long, val bytes: ByteArray) {
    fun hex() = bytes.joinToString("") { "%02x".format(it) }
}

private fun readAndHash(input: InputStream, output: OutputStream? = null, expected: Long? = null): PhotoDigest {
    val digest = MessageDigest.getInstance("SHA-256")
    val buffer = ByteArray(BUFFER_SIZE)
    var size = 0L
    while (true) {
        val count = input.read(buffer)
        if (count < 0) break
        size += count
        if (expected != null && size > expected) throw SourceChanged()
        require(size <= MAX_PHOTO_BYTES) { "사진은 24MiB 이하여야 합니다." }
        digest.update(buffer, 0, count)
        output?.write(buffer, 0, count)
    }
    if (expected != null && size != expected) throw SourceChanged()
    return PhotoDigest(size, digest.digest())
}

private fun mediaType(decodeBounds: (BitmapFactory.Options) -> Unit): String {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    decodeBounds(bounds)
    return bounds.outMimeType.also {
        require(it == "image/jpeg" || it == "image/png") { "JPEG/PNG 사진을 선택해 주세요." }
    }
}

private fun <T> withSnapshot(input: InputStream, cacheDir: File, consume: (RgbUploadPhoto) -> T): T {
    val file = File.createTempFile("rgb-upload-", ".tmp", cacheDir)
    try {
        val hash = file.outputStream().use { readAndHash(input, it) }
        val type = mediaType { BitmapFactory.decodeFile(file.absolutePath, it) }
        return consume(RgbUploadPhoto(hash.size, hash.hex(), type) { output ->
            file.inputStream().use { it.copyTo(output, BUFFER_SIZE) }
        })
    } finally {
        file.delete()
    }
}

internal fun <T> withRgbUploadPhoto(context: Context, uri: Uri, consume: (RgbUploadPhoto) -> T): T {
    val resolver = context.contentResolver
    if (uri.scheme == ContentResolver.SCHEME_ANDROID_RESOURCE) {
        // Android can stream compressed raw resources that have no asset file descriptor.
        val input = resolver.openInputStream(uri) ?: error("사진을 읽지 못했습니다.")
        return input.use { withSnapshot(it, context.cacheDir, consume) }
    }
    val asset = resolver.openAssetFileDescriptor(uri, "r") ?: error("사진을 읽지 못했습니다.")
    return asset.use { withRgbUploadPhoto(it, context.cacheDir, consume) }
}

/** The caller owns [asset]. Its bytes can be sent more than once while [consume] runs. */
internal fun <T> withRgbUploadPhoto(asset: AssetFileDescriptor, cacheDir: File, consume: (RgbUploadPhoto) -> T): T {
    val statSize = asset.parcelFileDescriptor.statSize
    val wholeFile = statSize >= 0 && asset.startOffset == 0L &&
        (asset.declaredLength == AssetFileDescriptor.UNKNOWN_LENGTH || asset.declaredLength == statSize)
    val canRewind = wholeFile && try {
        Os.lseek(asset.fileDescriptor, 0, OsConstants.SEEK_SET)
        true
    } catch (_: ErrnoException) { false }

    if (!canRewind) {
        // A provider may return a pipe, a one-shot cloud stream or a slice of another file.
        return asset.createInputStream().use { withSnapshot(it, cacheDir, consume) }
    }
    require(statSize <= MAX_PHOTO_BYTES) { "사진은 24MiB 이하여야 합니다." }
    return ParcelFileDescriptor.AutoCloseInputStream(ParcelFileDescriptor.dup(asset.fileDescriptor)).use { input ->
        val type = mediaType { BitmapFactory.decodeFileDescriptor(input.fd, null, it) }
        input.channel.position(0)
        val hash = readAndHash(input)
        val photo = RgbUploadPhoto(hash.size, hash.hex(), type) { output ->
            input.channel.position(0)
            val sent = readAndHash(input, output, expected = hash.size)
            // The multipart closing boundary is written by the caller only after this check.
            if (!sent.bytes.contentEquals(hash.bytes)) throw SourceChanged()
        }
        try {
            consume(photo)
        } catch (_: SourceChanged) {
            // Another writer changed the open inode. Freeze its current bytes once before retrying.
            input.channel.position(0)
            withSnapshot(input, cacheDir, consume)
        }
    }
}
