package org.visionmachine.agriclinic

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ColorSpace
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import org.json.JSONObject
import java.nio.FloatBuffer
import java.security.MessageDigest

class LocalRgbEngine(private val context: Context) : AutoCloseable {
    private val env = OrtEnvironment.getEnvironment()
    private val modelBytes = context.assets.open("vision_rgb_cseed42.onnx").use { it.readBytes() }
    val modelCard = JSONObject(context.assets.open("vision_rgb_model.json").bufferedReader().use { it.readText() })
    private val session: OrtSession
    init {
        require(sha(modelBytes) == modelCard.getString("model_sha256")) { "모델 파일 검증 실패" }
        OrtSession.SessionOptions().use { options ->
            options.setIntraOpNumThreads(minOf(4, Runtime.getRuntime().availableProcessors()))
            options.setInterOpNumThreads(1)
            session = env.createSession(modelBytes, options)
        }
    }
    data class Result(val normal: Float, val abnormal: Float, val elapsedMs: Long, val sha256: String)
    fun analyze(uri: Uri): Result {
        val started = android.os.SystemClock.elapsedRealtime()
        val digest = MessageDigest.getInstance("SHA-256")
        context.contentResolver.openInputStream(uri)!!.use { stream ->
            val buffer = ByteArray(65536); var total = 0L
            while (true) { val n=stream.read(buffer); if(n<0) break
                total += n; require(total<=24L*1024*1024) { "사진 파일은 24MB 이하를 선택해 주세요." }; digest.update(buffer,0,n) }
        }
        val orientation=context.contentResolver.openInputStream(uri)!!.use {
            runCatching { ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION,1) }.getOrDefault(1)
        }
        val bounds=BitmapFactory.Options().apply { inJustDecodeBounds=true }
        context.contentResolver.openInputStream(uri)!!.use { BitmapFactory.decodeStream(it,null,bounds) }
        require(bounds.outWidth>0 && bounds.outHeight>0 && bounds.outWidth.toLong()*bounds.outHeight<=24_000_000) { "읽을 수 없는 사진이거나 2,400만 화소를 넘었습니다." }
        require(maxOf(bounds.outWidth,bounds.outHeight)<=16384 && maxOf(bounds.outWidth,bounds.outHeight).toDouble()/minOf(bounds.outWidth,bounds.outHeight)<=40) { "사진의 가로·세로 비율이나 크기가 지원 범위를 넘었습니다." }
        val options=BitmapFactory.Options().apply { inScaled=false; inPreferredConfig=Bitmap.Config.ARGB_8888
            inPreferredColorSpace=ColorSpace.get(ColorSpace.Named.SRGB); inPremultiplied=false }
        val bitmap=context.contentResolver.openInputStream(uri)!!.use { BitmapFactory.decodeStream(it,null,options) }
            ?: error("사진을 읽을 수 없습니다.")
        val x=try { preprocess(bitmap,orientation) } finally { bitmap.recycle() }
        val probabilities=predictTensor(x)
        return Result(probabilities[0],probabilities[1],android.os.SystemClock.elapsedRealtime()-started,digest.digest().joinToString(""){"%02x".format(it)})
    }
    fun predictTensor(x: FloatArray): FloatArray {
        OnnxTensor.createTensor(env,FloatBuffer.wrap(x),longArrayOf(1,3,224,224)).use { input ->
            session.run(mapOf("image" to input)).use { results ->
                @Suppress("UNCHECKED_CAST")
                val p=(results[0].value as Array<FloatArray>)[0]
                require(p.size==2 && p.all { it.isFinite() && it in 0f..1f } && kotlin.math.abs(p.sum()-1)<1e-4)
                return p.copyOf()
            }
        }
    }
    companion object {
        fun sha(bytes: ByteArray)=MessageDigest.getInstance("SHA-256").digest(bytes).joinToString(""){"%02x".format(it)}
        fun preprocess(bitmap: Bitmap, orientation: Int): FloatArray {
            val rotated=orientation in 5..8
            val w=if(rotated) bitmap.height else bitmap.width
            val h=if(rotated) bitmap.width else bitmap.height
            val rgb=RgbPreprocessor.cropRgb(w,h) { y,row ->
                if(!rotated) {
                    val sy=if(orientation==3||orientation==4) bitmap.height-1-y else y
                    bitmap.getPixels(row,0,w,0,sy,w,1)
                    if(orientation==2||orientation==3) row.reverse()
                } else {
                    val sx=if(orientation==7||orientation==8) bitmap.width-1-y else y
                    bitmap.getPixels(row,0,1,sx,0,1,bitmap.height)
                    if(orientation==6||orientation==7) row.reverse()
                }
            }
            return RgbPreprocessor.normalize(rgb)
        }
    }
    override fun close() { session.close() }
}
