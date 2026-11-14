package org.visionmachine.agriclinic

import android.app.Application
import android.content.Context
import android.content.ContextWrapper
import android.content.SharedPreferences
import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.ViewModelProvider
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.time.Instant
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class AutomaticServerConnectionTest {
    @Test fun installationIdentityAndIssuedTokenAreEncryptedAndPersistAcrossModeChanges() {
        val base=InstrumentationRegistry.getInstrumentation().targetContext
        val prefix="synthetic_auto_${UUID.randomUUID()}_"
        val context=object:ContextWrapper(base) {
            override fun getSharedPreferences(name:String,mode:Int):SharedPreferences=super.getSharedPreferences(prefix+name,mode)
        }
        val settings=AutomaticServerSettings(context)
        val identity=settings.identity()
        assertTrue(identity.secret.matches(Regex("[0-9a-f]{64}")))
        assertTrue(identity==AutomaticServerSettings(context).identity())
        val token="vm_device_"+"synthetic-test-only".repeat(3)
        settings.save(AutomaticSession(ServerConfig("https://example.invalid",token),Instant.now().plusSeconds(3600)))
        settings.setMode("local");settings.setMode("auto")
        assertTrue(settings.cached()!!.config.apiKey==token && settings.identity()==identity)
        val stored=context.getSharedPreferences("automatic_server_v1",0).all.values.joinToString()
        assertFalse(stored.contains(identity.secret));assertFalse(stored.contains(token));assertFalse(stored.contains(identity.id))
        settings.clearForTest()
    }

    /** Opt-in real deployed 4090 connection. No URL, API key or HTTP/model stub is injected. */
    @Test fun freshInstallAutomaticallyRegistersAndAnalyzesEightPhotosOnTheRealServer() {
        val inst=InstrumentationRegistry.getInstrumentation()
        assumeTrue("Live automatic-server test is opt-in",InstrumentationRegistry.getArguments().getString("vm_live_auto")=="true")
        val app=inst.targetContext.applicationContext as Application
        val settings=AutomaticServerSettings(app)
        settings.clearForTest();ServerSettings(app).clear()
        assertEquals("auto",settings.mode());assertNull(settings.cached())
        val files=(0..7).map {i -> File(app.cacheDir,"synthetic-auto-${UUID.randomUUID()}-$i.png").also {file ->
            val bitmap=Bitmap.createBitmap(32+i,40+i,Bitmap.Config.ARGB_8888)
            try {bitmap.eraseColor(0xff227744.toInt()+i);file.outputStream().use {bitmap.compress(Bitmap.CompressFormat.PNG,100,it)}}
            finally {bitmap.recycle()}
        }}
        lateinit var vm:RgbAnalysisViewModel
        fun main(block:()->Unit)=inst.runOnMainSync(block)
        fun await(condition:()->Boolean) {
            val until=System.currentTimeMillis()+180000
            while(System.currentTimeMillis()<until) {var ok=false;main {ok=condition()};if(ok)return;Thread.sleep(50)}
            fail("Actual automatic 4090 connection or analysis did not complete")
        }
        try {
            ActivityScenario.launch(AnalysisActivity::class.java).use {scenario ->
                scenario.onActivity {vm=ViewModelProvider(it)[RgbAnalysisViewModel::class.java]}
                await {vm.ready&&!vm.busy}
                main {assertTrue("Default connection must reach real GPU readiness",vm.serverMode&&vm.serverConnected)}
                assertNull(ServerSettings(app).load())
                assertNotNull(settings.cached());assertEquals("auto",settings.mode())
                val identity=settings.identity()
                main {vm.chooseDefaultCrop("basil");vm.append(files.map {Uri.fromFile(it)})}
                await {!vm.busy&&vm.items.size==8}
                val first=vm.items.first().reference
                val sensorId=UUID.randomUUID()
                val packet=syntheticExtendedSensorPacket(sensorId)
                val frame=SensorPacketFramer(sensorId).feed((packet.toString()+"\n").toByteArray()).single() as SensorFrame.Measurement
                SensorStore(app).save(sensorId,frame,first,photoSha256=LocalRgbEngine.sha(files.first().readBytes()))
                main {vm.analyze(true)}
                await {!vm.busy}
                main {
                    assertTrue("All eight requests must return real server GPU results",vm.items.all {it.status=="완료"&&it.result?.executionProvider=="CUDAExecutionProvider"})
                    assertNotNull(vm.items.first().result!!.sensorRecordId)
                    assertNull(vm.items.first().result!!.compositeJson)
                }
                assertTrue(identity==settings.identity())
                val before=settings.cached()!!.config.apiKey
                val reopened=AutomaticServerConnection(app).connect()
                assertTrue(before==reopened.apiKey)
                inst.waitForIdleSync();Thread.sleep(700)
                val screenshot=inst.uiAutomation.takeScreenshot()
                assertNotNull(screenshot)
                try {File(app.filesDir,"automatic_server_result.png").outputStream().use {screenshot.compress(Bitmap.CompressFormat.PNG,100,it)}}
                finally {screenshot.recycle()}
            }
        } finally {files.forEach {it.delete()}}
    }
}
