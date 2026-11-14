package org.visionmachine.agriclinic

import android.graphics.Bitmap
import android.os.Handler
import android.os.Looper
import android.view.PixelCopy
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.Assert.*
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class AnalysisActivityTest {
    @Test fun photoAnalysisScreenRendersAfterModelStartup() {
        val inst=InstrumentationRegistry.getInstrumentation()
        val connection=AutomaticServerSettings(inst.targetContext);val previousMode=connection.mode();connection.setMode("local")
        try {
        ActivityScenario.launch(AnalysisActivity::class.java).use {scenario ->
            inst.waitForIdleSync()
            Thread.sleep(700) // allow the first compositor frame, not a processing speed measurement
            val done=CountDownLatch(1)
            var code=-1
            lateinit var bitmap:Bitmap
            scenario.onActivity {a ->
                val view=a.window.decorView
                assertTrue(view.width>0&&view.height>0)
                bitmap=Bitmap.createBitmap(view.width,view.height,Bitmap.Config.ARGB_8888)
                PixelCopy.request(a.window,bitmap,{r->code=r;done.countDown()},Handler(Looper.getMainLooper()))
            }
            assertTrue(done.await(10,TimeUnit.SECONDS));assertEquals(PixelCopy.SUCCESS,code)
            try {
                // Both the forest header and cream body should be present in the actual rendered frame.
                var forest=0;var cream=0
                for(y in 0 until bitmap.height step 10) for(x in 0 until bitmap.width step 10) {
                    val p=bitmap.getPixel(x,y) and 0xffffff
                    if(p==0x1f4d3a) forest++
                    if(p==0xf7f1e2) cream++
                }
                assertTrue("Header must be visible",forest>50);assertTrue("Body must be visible",cream>50)
                File(inst.targetContext.filesDir,"analysis_ui_smoke.png").outputStream().use {bitmap.compress(Bitmap.CompressFormat.PNG,100,it)}
            } finally {bitmap.recycle()}
        }
        } finally {connection.setMode(previousMode)}
    }
}
