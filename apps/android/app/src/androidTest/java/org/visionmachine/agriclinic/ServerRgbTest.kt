package org.visionmachine.agriclinic

import android.app.Application
import android.content.Context
import android.content.ContextWrapper
import android.content.SharedPreferences
import android.graphics.Bitmap
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.view.PixelCopy
import androidx.lifecycle.ViewModelProvider
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.io.RandomAccessFile
import java.net.InetAddress
import java.net.ServerSocket
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.FutureTask
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class ServerRgbTest {
    @Test fun streamsOriginalPhotoWithMatchingDigestAndCleansUpCache() {
        val base = InstrumentationRegistry.getInstrumentation().targetContext
        val cache = File(base.cacheDir, "synthetic-rgb-upload-${UUID.randomUUID()}").apply { check(mkdir()) }
        val context = object : ContextWrapper(base) {
            override fun getCacheDir() = cache
        }
        val photo = File.createTempFile("synthetic-rgb-source-", ".png", base.cacheDir)
        try {
            val bitmap = Bitmap.createBitmap(3, 4, Bitmap.Config.ARGB_8888)
            try {
                bitmap.eraseColor(0xff387755.toInt())
                photo.outputStream().use { check(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)) }
            } finally {
                bitmap.recycle()
            }
            val original = photo.readBytes()
            val sha = LocalRgbEngine.sha(original)
            val uri = Uri.fromFile(photo)
            val reference = CaptureRecord(UUID.randomUUID().toString(), "synthetic", "test", "basil", uri.toString(), "")
            val card = JSONObject(base.assets.open("vision_rgb_model.json").bufferedReader().use { it.readText() })

            ServerSocket(0, 1, InetAddress.getByName("127.0.0.1")).use { server ->
                server.soTimeout = 10_000
                val responder = FutureTask {
                    server.accept().use { socket ->
                        socket.soTimeout = 10_000
                        val reader = socket.getInputStream().bufferedReader(Charsets.ISO_8859_1)
                        assertTrue(reader.readLine().startsWith("POST /api/v1/inspections HTTP/1."))
                        val headers = generateSequence { reader.readLine()?.takeIf { it.isNotEmpty() } }
                            .associate { it.substringBefore(':').lowercase() to it.substringAfter(':').trim() }
                        val boundary = headers.getValue("content-type").substringAfter("boundary=")
                        assertFalse(headers.containsKey("transfer-encoding"))
                        val body = CharArray(headers.getValue("content-length").toInt())
                        var offset = 0
                        while (offset < body.size) {
                            val count = reader.read(body, offset, body.size - offset)
                            check(count > 0) { "Multipart body ended before Content-Length" }
                            offset += count
                        }
                        val parts = body.concatToString().split("--$boundary")
                        assertEquals(4, parts.size)
                        val payload = JSONObject(parts[1].substringAfter("\r\n\r\n"))
                        val metadata = payload.getJSONArray("photos").getJSONObject(0)
                        assertEquals(sha, metadata.getString("image_sha256"))
                        assertEquals("image/png", metadata.getString("image_media_type"))
                        assertArrayEquals(original, parts[2].substringAfter("\r\n\r\n").removeSuffix("\r\n")
                            .toByteArray(Charsets.ISO_8859_1))

                        val id = payload.getString("client_inspection_id")
                        val result = JSONObject().put("source_photo_id", reference.inspectionId)
                            .put("image_sha256", sha).put("crop_code", "basil").put("status", "completed")
                            .put("normal", .2).put("abnormal", .8).put("elapsed_ms", 1)
                            .put("model_version", card.getString("model_version"))
                            .put("model_sha256", card.getString("model_sha256"))
                        val response = JSONObject().put("inspection_id", id).put("client_inspection_id", id)
                            .put("providers", JSONArray().put("CUDAExecutionProvider")).put("photos", JSONArray().put(result))
                            .toString().toByteArray(Charsets.UTF_8)
                        socket.getOutputStream().apply {
                            val headersOut = "HTTP/1.1 201 Created\r\nContent-Length: ${response.size}\r\n" +
                                "Server-Timing: vm_queue;dur=1.250, vm_infer;dur=1\r\nConnection: close\r\n\r\n"
                            write(headersOut.toByteArray(Charsets.US_ASCII))
                            write(response)
                            flush()
                        }
                    }
                }
                Thread(responder).start()
                val client = ServerRgbClient(context, ServerConfig("http://127.0.0.1:${server.localPort}", "synthetic-key"))
                assertEquals(sha, client.analyze(uri, reference).sha256)
                responder.get(10, TimeUnit.SECONDS)
                assertTrue(cache.listFiles()!!.isEmpty())

                RandomAccessFile(photo, "rw").use { it.setLength(24L * 1024 * 1024 + 1) }
                val error = assertThrows(IllegalArgumentException::class.java) { client.analyze(uri, reference) }
                assertTrue(error.message.orEmpty().contains("24MiB"))
                assertTrue(cache.listFiles()!!.isEmpty())
            }
        } finally {
            photo.delete()
            cache.delete()
        }
    }

    @Test fun credentialsAreRuntimeEncryptedAndParserRejectsWrongPhotoOrModel() {
        val base=InstrumentationRegistry.getInstrumentation().targetContext
        val prefix="synthetic_server_${UUID.randomUUID()}_"
        val context=object:ContextWrapper(base) {
            override fun getSharedPreferences(name:String,mode:Int):SharedPreferences=super.getSharedPreferences(prefix+name,mode)
        }
        val settings=ServerSettings(context)
        val secret="synthetic-protocol-test-key-only"
        settings.save("https://example.invalid",secret)
        assertEquals(secret,settings.load()!!.apiKey)
        assertFalse(context.getSharedPreferences("gpu_server_v1",0).all.values.joinToString().contains(secret))
        val card=JSONObject(base.assets.open("vision_rgb_model.json").bufferedReader().use {it.readText()})
        val id=UUID.randomUUID().toString();val photoId=UUID.randomUUID().toString();val sha="0".repeat(64)
        val result=JSONObject().put("source_photo_id",photoId).put("image_sha256",sha).put("crop_code","basil")
            .put("status","completed").put("normal",.2).put("abnormal",.8).put("elapsed_ms",10)
            .put("model_version",card.getString("model_version")).put("model_sha256",card.getString("model_sha256"))
        val response=JSONObject().put("inspection_id",id).put("client_inspection_id",id)
            .put("providers",JSONArray().put("CUDAExecutionProvider")).put("photos",JSONArray().put(result))
        assertEquals(.8f,parseServerRgbResponse(response.toString(),id,photoId,"basil",sha,card).abnormal,1e-6f)
        for(key in listOf("source_photo_id","model_sha256")) {
            val bad=JSONObject(response.toString());bad.getJSONArray("photos").getJSONObject(0).put(key,"mismatch")
            try {parseServerRgbResponse(bad.toString(),id,photoId,"basil",sha,card);fail("Mismatched response accepted")}
            catch(_:IllegalArgumentException) {}
        }
        settings.clear()
    }

    /** Opt-in real Ubuntu HTTP test. No HTTP/model stub is used in this test. */
    @Test fun actualServerEightPhotoRequestsReachViewModelAndHistory() {
        val args=InstrumentationRegistry.getArguments()
        val url=args.getString("vm_test_server_url")
        val key=args.getString("vm_test_server_key")
        assumeTrue("Actual server URL/key were not supplied",!url.isNullOrBlank()&&!key.isNullOrBlank())
        val expectReady=args.getString("vm_test_model_ready")=="true"
        val inst=InstrumentationRegistry.getInstrumentation()
        val app=inst.targetContext.applicationContext as Application
        val config=ServerSettings(app);val previous=config.load()
        val automatic=AutomaticServerSettings(app);val previousMode=automatic.mode()
        var scenario:ActivityScenario<AnalysisActivity>?=null
        lateinit var vm:RgbAnalysisViewModel
        fun main(block:()->Unit)=inst.runOnMainSync(block)
        fun await(condition:()->Boolean) {
            val until=System.currentTimeMillis()+180000
            while(System.currentTimeMillis()<until) {var ok=false;main {ok=condition()};if(ok)return;Thread.sleep(50)}
            fail("Timed out waiting for server request/result state")
        }
        val files=(0..7).map {index -> File(app.cacheDir,"synthetic-server-$index.png").also {file ->
            Bitmap.createBitmap(17+index,23+index,Bitmap.Config.ARGB_8888).also {bitmap ->
                bitmap.eraseColor(0xff227744.toInt()+index)
                file.outputStream().use {bitmap.compress(Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()
            }
        }}
        try {
            config.save(url!!,key!!)
            automatic.setMode("manual")
            scenario=ActivityScenario.launch(AnalysisActivity::class.java)
            scenario.onActivity {activity ->vm=ViewModelProvider(activity)[RgbAnalysisViewModel::class.java]}
            await {vm.ready}
            main {vm.chooseDefaultCrop("basil");vm.append(files.map {Uri.fromFile(it)})}
            await {!vm.busy&&vm.items.size==8}
            // Link an explicitly synthetic packet to precisely one of the selected photos.
            val photo=vm.items.first().reference
            val measurementId=UUID.randomUUID()
            val packet=syntheticExtendedSensorPacket(measurementId)
            val frame=SensorPacketFramer(measurementId).feed((packet.toString()+"\n").toByteArray()).single() as SensorFrame.Measurement
            SensorStore(app).save(measurementId,frame,photo,photoSha256=LocalRgbEngine.sha(files.first().readBytes()))
            main {vm.analyze(true)}
            await {!vm.busy}
            main {
                assertEquals(8,vm.items.size)
                if(expectReady) {
                    assertTrue(vm.items.all {it.status=="완료"&&it.result?.executionProvider=="CUDAExecutionProvider"})
                    assertNotNull(vm.items.first().result!!.sensorRecordId)
                    assertNull(vm.items.first().result!!.compositeJson) // mock sensor never gets an aggregate
                    assertTrue(RgbHistory(app).read().any {it.serverInspectionId!=null})
                } else {
                    assertTrue(vm.items.all {it.status=="실패"&&it.result==null})
                    assertTrue(vm.items.all {it.error.orEmpty().contains("서버 모델이 준비되지")})
                }
            }
            inst.waitForIdleSync()
            Thread.sleep(700) // wait for compositor frames, not an inference timing measurement
            val copied=CountDownLatch(1);var copyStatus=-1
            lateinit var screenshot:Bitmap
            scenario.onActivity {activity ->
                assertTrue(vm.serverMode)
                val view=activity.window.decorView
                assertTrue(view.width>0&&view.height>0)
                screenshot=Bitmap.createBitmap(view.width,view.height,Bitmap.Config.ARGB_8888)
                PixelCopy.request(activity.window,screenshot,{code ->copyStatus=code;copied.countDown()},Handler(Looper.getMainLooper()))
            }
            assertTrue(copied.await(10,TimeUnit.SECONDS));assertEquals(PixelCopy.SUCCESS,copyStatus)
            File(app.cacheDir,"server-connection-screen.png").outputStream().use {screenshot.compress(Bitmap.CompressFormat.PNG,100,it)}
            if(expectReady) {
                val x=screenshot.width/2
                val command="input swipe $x ${screenshot.height*8/10} $x ${screenshot.height*2/10} 500"
                ParcelFileDescriptor.AutoCloseInputStream(inst.uiAutomation.executeShellCommand(command)).use {it.readBytes()}
                inst.waitForIdleSync();Thread.sleep(300)
                val resultCopied=CountDownLatch(1);copyStatus=-1
                scenario.onActivity {activity ->PixelCopy.request(activity.window,screenshot,{code ->copyStatus=code;resultCopied.countDown()},Handler(Looper.getMainLooper()))}
                assertTrue(resultCopied.await(10,TimeUnit.SECONDS));assertEquals(PixelCopy.SUCCESS,copyStatus)
                File(app.cacheDir,"server-result-screen.png").outputStream().use {screenshot.compress(Bitmap.CompressFormat.PNG,100,it)}
            }
            screenshot.recycle()
        } finally {
            scenario?.close();files.forEach {it.delete()}
            // Explicit interactive emulator setup keeps runtime credentials out of the APK.
            if(args.getString("vm_keep_server_config")!="true") {
                if(previous!=null) config.save(previous.baseUrl,previous.apiKey) else config.clear()
                automatic.setMode(previousMode)
            }
        }
    }
}
