package org.visionmachine.agriclinic

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class RgbWorkflowTest {
    private val inst=InstrumentationRegistry.getInstrumentation()
    private val app=inst.targetContext.applicationContext as Application
    private fun main(block:()->Unit)=inst.runOnMainSync(block)
    private fun await(condition:()->Boolean) {
        val until=System.currentTimeMillis()+90000
        while(System.currentTimeMillis()<until) {var done=false;main {done=condition()};if(done)return;Thread.sleep(40)}
        fail("App workflow did not complete")
    }
    @Test fun eightActualModelInputsHaveIndividualResultsAndOneBadImageDoesNotStopTheRest() {
        val assets=inst.context.assets
        assumeTrue(runCatching {assets.open("private/expected.json").close()}.isSuccess)
        val expected=JSONArray(assets.open("private/expected.json").bufferedReader().use {it.readText()})
        val files=(0 until 8).map {i -> val name=expected.getJSONObject(i).getString("file")
            File(app.cacheDir,"vm040_${UUID.randomUUID()}_$name").also {file ->assets.open("private/$name").use {input ->file.outputStream().use {input.copyTo(it)}}}}
        val holder=ViewModelStore();lateinit var vm:RgbAnalysisViewModel
        try {
            main {vm=ViewModelProvider(holder,ViewModelProvider.AndroidViewModelFactory(app))[RgbAnalysisViewModel::class.java]}
            await {vm.ready}
            main {vm.select(files.take(3).map {Uri.fromFile(it)})};await {!vm.busy&&vm.selected.size==3}
            main {vm.append(files.drop(3).map {Uri.fromFile(it)})};await {!vm.busy&&vm.selected.size==8}
            for(index in 0 until 8) {
                val crop=expected.getJSONObject(index).getString("file").removeSuffix(".png")
                main {vm.changeCrop(index,crop)};await {!vm.busy}
            }
            main {vm.analyze(true)};await {!vm.busy&&vm.items.all {it.status=="완료"}}
            main {
                assertEquals(8,vm.items.size)
                vm.items.forEachIndexed {index,item ->
                    assertEquals(expected.getJSONObject(index).getDouble("abnormal"),item.result!!.abnormal.toDouble(),1e-5)
                    assertEquals(expected.getJSONObject(index).getString("file").removeSuffix(".png"),item.result!!.cropCode)
                }
                vm.focus(7)
            }
            await {!vm.busy};main {assertEquals(vm.items[7].result,vm.current)}
            main {vm.select(listOf(Uri.fromFile(File(app.cacheDir,"missing-synthetic-image.png")),Uri.fromFile(files[0])))}
            await {!vm.busy&&vm.selected.size==2};main {vm.analyze(true)};await {!vm.busy}
            main {assertEquals("실패",vm.items[0].status);assertEquals("완료",vm.items[1].status);assertTrue(vm.message.contains("성공 1장 / 실패 1장"))}
        } finally {main {holder.clear()};files.forEach {it.delete()}}
    }
    @Test fun syntheticCameraReturnEntersAnalysisAndOnlyMatchingPhotoHashGetsASensorIndex() {
        val holder=ViewModelStore();lateinit var vm:RgbAnalysisViewModel
        try {
            main {vm=ViewModelProvider(holder,ViewModelProvider.AndroidViewModelFactory(app))[RgbAnalysisViewModel::class.java]};await {vm.ready}
            var uri:Uri?=null
            main {vm.chooseDefaultCrop("basil");uri=vm.prepareCamera("synthetic-subject","synthetic-batch")}
            assertNotNull(uri)
            // Simulate an external camera's file result with an explicitly synthetic JPEG.
            app.contentResolver.openOutputStream(uri!!)!!.use {out ->val bitmap=Bitmap.createBitmap(32,32,Bitmap.Config.ARGB_8888);try {bitmap.compress(Bitmap.CompressFormat.JPEG,90,out)} finally {bitmap.recycle()}}
            main {vm.completeCamera(true)};await {!vm.busy&&vm.items.size==1}
            lateinit var reference:CaptureRecord;main {reference=vm.items.single().reference}
            assertEquals("synthetic-subject",reference.subjectId)
            assertTrue(reference.capturedAt.isNotBlank())
            val id=UUID.randomUUID()
            val packet=syntheticExtendedSensorPacket(id).put("mode","real") // synthetic wire-mode branch test only
            val frame=SensorPacketFramer(id).feed((packet.toString()+"\n").toByteArray()).single() as SensorFrame.Measurement
            val profile=SensorProfile("basil",mapOf("air_temp_c" to ReferenceBand(20.0,30.0)),"synthetic reference","synthetic fixture",true,"synthetic-v1")
            val assessment=SensorScoring.assess(packet,profile).toString()
            SensorStore(app).save(id,frame,reference,cropCode="basil",assessmentJson=assessment,photoSha256="0".repeat(64))
            main {vm.analyze(true)};await {!vm.busy&&vm.current!=null};main {assertNull(vm.current!!.compositeJson)}
            val secondId=UUID.randomUUID();packet.put("request_id",secondId.toString())
            val secondFrame=SensorPacketFramer(secondId).feed((packet.toString()+"\n").toByteArray()).single() as SensorFrame.Measurement
            SensorStore(app).save(secondId,secondFrame,reference,cropCode="basil",assessmentJson=assessment,photoSha256=PhotoReferenceStore.hash(app,uri!!))
            main {vm.refreshSensors()};await {vm.current?.compositeJson!=null}
            main {assertEquals(secondId.toString(),vm.current!!.sensorRecordId);assertTrue(JSONObject(vm.current!!.compositeJson!!).getDouble("index") in 0.0..100.0)}
        } finally {main {holder.clear()}}
    }
}
