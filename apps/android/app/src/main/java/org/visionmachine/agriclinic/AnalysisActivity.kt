package org.visionmachine.agriclinic

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.PickVisualMediaRequest
import androidx.core.view.WindowCompat
import androidx.lifecycle.ViewModelProvider
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier

class AnalysisActivity:ComponentActivity() {
    private lateinit var vm:RgbAnalysisViewModel
    private val photos=registerForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(8)) { uris ->
        uris.forEach { uri -> runCatching {contentResolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION)} }
        vm.append(uris)
    }
    private val filePhotos=registerForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) {uris ->
        uris.forEach {uri ->runCatching {contentResolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION)}}
        vm.append(uris)
    }
    private val camera=registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->vm.completeCamera(success) }
    private val export=registerForActivityResult(ActivityResultContracts.CreateDocument("text/csv")) { uri ->
        if(uri!=null) vm.saved(runCatching {contentResolver.openOutputStream(uri,"wt")!!.bufferedWriter(Charsets.UTF_8).use {it.write(RgbHistory.csv(vm.records))}}.isSuccess)
    }
    override fun onResume() {super.onResume();if(::vm.isInitialized) vm.refreshSensors()}
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.getInsetsController(window,window.decorView).isAppearanceLightStatusBars=true
        vm=ViewModelProvider(this)[RgbAnalysisViewModel::class.java]
        setContent {
            VisionTheme {
                Surface(Modifier.fillMaxSize(),color=VisionColors.Cream) {
                    AnalysisScreen(vm,{photos.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))},{export.launch("VisionMachine_results.csv")},
                        {startActivity(Intent(this,MainActivity::class.java))},
                        {id ->startActivity(Intent(this,SensorActivity::class.java).apply {if(id!=null) putExtra("source_capture_id",id)})},
                        {subject,batch ->vm.prepareCamera(subject,batch)?.let {uri ->try {camera.launch(uri)} catch(_:Exception) {vm.completeCamera(false)}}},
                        {filePhotos.launch(arrayOf("image/jpeg","image/png"))})
                }
            }
        }
    }
}
