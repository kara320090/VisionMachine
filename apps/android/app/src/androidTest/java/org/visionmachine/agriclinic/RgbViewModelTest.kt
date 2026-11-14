package org.visionmachine.agriclinic

import android.app.Application
import android.net.Uri
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelProvider
import org.junit.Test
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class RgbViewModelTest {
    @Test fun selectionResetSingleBatchHistoryAndExportUseRealModel() {
        val inst=InstrumentationRegistry.getInstrumentation()
        val app=inst.targetContext.applicationContext as Application
        assumeTrue(runCatching {inst.context.assets.open("private/basil.png").close()}.isSuccess)
        val connection=AutomaticServerSettings(app);val previousMode=connection.mode();connection.setMode("local")
        val files=listOf("basil.png","rosemary.png").map {n ->File(app.cacheDir,n).also {f->inst.context.assets.open("private/$n").use {input->f.outputStream().use {input.copyTo(it)}}}}
        val store=ViewModelStore()
        lateinit var vm:RgbAnalysisViewModel
        fun main(block:()->Unit)=inst.runOnMainSync(block)
        fun await(condition:()->Boolean) {val until=System.currentTimeMillis()+60000;while(System.currentTimeMillis()<until) {var ok=false;main {ok=condition()};if(ok)return;Thread.sleep(50)};fail("Timed out waiting for actual model/UI state")}
        try {
            main {vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory(app))[RgbAnalysisViewModel::class.java]}
            await {vm.ready}
            var before=0;main {before=vm.records.size;vm.select(listOf(Uri.fromFile(files[0])))}
            await {!vm.busy&&vm.selected.isNotEmpty()}
            main {assertNull(vm.current);vm.analyze(false)}
            await {!vm.busy&&vm.current!=null}
            main {assertEquals(before+1,vm.records.size);assertTrue(vm.current!!.abnormal>.99f);vm.select(files.map {Uri.fromFile(it)})}
            await {!vm.busy}
            main {assertNull(vm.current);assertEquals(before+1,vm.records.size);vm.analyze(true)}
            await {!vm.busy&&vm.current!=null}
            main {assertEquals(before+3,vm.records.size);assertEquals(before+3,RgbHistory(app).read().size);assertEquals(before+4,RgbHistory.csv(vm.records).trim().lines().size);vm.saved(true);assertTrue(vm.message.contains("CSV 저장 완료"))}
        } finally {main {store.clear()};files.forEach {it.delete()};connection.setMode(previousMode)}
    }
}
