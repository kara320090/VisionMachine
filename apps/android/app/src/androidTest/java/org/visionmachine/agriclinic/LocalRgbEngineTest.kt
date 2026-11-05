package org.visionmachine.agriclinic

import android.graphics.BitmapFactory
import android.graphics.Bitmap
import android.net.Uri
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.runner.RunWith
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import kotlin.math.abs

@RunWith(AndroidJUnit4::class)
class LocalRgbEngineTest {
    private val instrumentation=InstrumentationRegistry.getInstrumentation()
    private val app=instrumentation.targetContext
    private val assets=instrumentation.context.assets
    @Test fun eightPrivatePngInputsMatchDesktopModelAndPersistCsv() {
        assumeTrue("Private equivalence fixtures not included in public Git",runCatching {assets.open("private/expected.json").close()}.isSuccess)
        val expected=JSONArray(assets.open("private/expected.json").bufferedReader().use {it.readText()})
        val actual=JSONArray()
        LocalRgbEngine(app).use {engine ->
            for(i in 0 until expected.length()) {
                val e=expected.getJSONObject(i);val file=File(app.cacheDir,e.getString("file"))
                assets.open("private/${e.getString("file")}").use {input->file.outputStream().use {input.copyTo(it)}}
                val r=engine.analyze(Uri.fromFile(file))
                assertEquals(e.getDouble("normal"),r.normal.toDouble(),1e-5)
                assertEquals(e.getDouble("abnormal"),r.abnormal.toDouble(),1e-5)
                assertEquals(e.getDouble("abnormal")>=.5,r.abnormal>=.5f)
                actual.put(JSONObject().put("file",e.getString("file")).put("normal",r.normal.toDouble()).put("abnormal",r.abnormal.toDouble()).put("elapsed_ms",r.elapsedMs))
                file.delete()
            }
        }
        assertEquals(8,actual.length())
        File(app.filesDir,"android_model_test_results.json").writeText(actual.toString(2))
        val record=RgbRecord("=injection,photo.png",.1f,.9f,10,"0".repeat(64),"2026-11-05T00:00:00Z","test")
        val csv=RgbHistory.csv(listOf(record));assertTrue(csv.contains("\"'=injection,photo.png\""));assertTrue(csv.contains("0.9"))
    }
    @Test fun allExifOrientationsMatchPillowPixelGoldens() {
        assumeTrue(runCatching {assets.open("private/synthetic_orientation.png").close()}.isSuccess)
        val bitmap=assets.open("private/synthetic_orientation.png").use {BitmapFactory.decodeStream(it)}!!
        try {
            for(o in 1..8) {
                val expected=RgbPreprocessor.normalize(assets.open("private/orientation_${o}.rgb").use {it.readBytes()})
                val actual=LocalRgbEngine.preprocess(bitmap,o)
                assertArrayEquals("Orientation $o",expected,actual,0f)
            }
        } finally {bitmap.recycle()}
    }
    @Test fun twelveMegapixelBitmapPreprocessesWithoutFullPixelArray() {
        val bitmap=Bitmap.createBitmap(3000,4000,Bitmap.Config.ARGB_8888)
        try {bitmap.eraseColor(0xff3b7b26.toInt());val x=LocalRgbEngine.preprocess(bitmap,1);assertEquals(150528,x.size);assertTrue(x.all {it.isFinite()})}
        finally {bitmap.recycle()}
    }
}
