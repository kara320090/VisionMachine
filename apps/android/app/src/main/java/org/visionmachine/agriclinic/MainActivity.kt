package org.visionmachine.agriclinic

import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.view.WindowCompat
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

private val crops = listOf(
    "cherry_tomato" to "방울토마토", "pepper" to "고추",
    "cucumber" to "오이", "lettuce" to "상추", "bok_choy" to "청경채",
    "eggplant" to "가지", "basil" to "바질", "rosemary" to "로즈마리",
)
private val validId = Regex("[A-Za-z0-9_-]{1,80}")

class MainActivity : ComponentActivity() {
    private val store by lazy { CaptureStore(this) }
    private var records by mutableStateOf<List<CaptureRecord>>(emptyList())
    private var capturePending by mutableStateOf(false)
    private var message by mutableStateOf("촬영한 원본 사진만 기기에 저장합니다. 센서·AI 연결은 아직 없습니다.")

    private val camera = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        try {
            val saved = store.finish(success)
            capturePending = false
            records = store.all()
            message = if (saved) "원본 사진을 저장했습니다." else "촬영이 취소되었거나 사진 파일이 비어 있습니다."
        } catch (error: Exception) {
            message = "사진 기록 저장 실패: ${error.javaClass.simpleName}"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars = true
        try {
            records = store.all()
            capturePending = store.pending() != null
        } catch (error: Exception) {
            message = "저장 기록 읽기 실패: ${error.javaClass.simpleName}"
        }
        setContent {
            MaterialTheme {
                CaptureScreen(
                    records = records, message = message, capturePending = capturePending,
                    onCapture = ::startCapture, onOpen = ::openPhoto, onRecover = ::recoverCapture,
                )
            }
        }
    }

    private fun startCapture(subjectId: String, batchId: String, cropCode: String) {
        if (capturePending) {
            message = "미완료 촬영을 먼저 복구하거나 정리하세요."
            return
        }
        if (!validId.matches(subjectId) || !validId.matches(batchId)) {
            message = "개체 ID와 묶음 ID는 영문·숫자·_·-로 1~80자 입력하세요."
            return
        }
        var prepared = false
        try {
            val pending = store.prepare(subjectId, batchId, cropCode)
            prepared = true
            capturePending = true
            camera.launch(android.net.Uri.parse(pending.photoUri))
        } catch (error: ActivityNotFoundException) {
            if (prepared) store.finish(false)
            capturePending = false
            message = "사용 가능한 카메라 앱이 없습니다."
        } catch (error: Exception) {
            if (prepared) store.finish(false)
            capturePending = false
            message = "촬영 준비 실패: ${error.javaClass.simpleName}"
        }
    }

    private fun recoverCapture() {
        try {
            val saved = store.finish(true)
            records = store.all()
            capturePending = false
            message = if (saved) "미완료 촬영의 사진 파일을 복구했습니다." else "미완료 촬영을 정리했습니다."
        } catch (error: Exception) {
            message = "촬영 복구 실패: ${error.javaClass.simpleName}"
        }
    }

    private fun openPhoto(record: CaptureRecord) {
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(store.fileFor(record), "image/jpeg")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            startActivity(intent)
        } catch (_: ActivityNotFoundException) {
            message = "사진을 열 수 있는 앱이 없습니다."
        }
    }
}

@Composable
private fun CaptureScreen(
    records: List<CaptureRecord>,
    message: String,
    capturePending: Boolean,
    onCapture: (String, String, String) -> Unit,
    onOpen: (CaptureRecord) -> Unit,
    onRecover: () -> Unit,
) {
    var subjectId by rememberSaveable { mutableStateOf("") }
    var batchId by rememberSaveable { mutableStateOf("") }
    var cropCode by rememberSaveable { mutableStateOf(crops.first().first) }
    Column(
        modifier = Modifier.fillMaxSize().systemBarsPadding().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text("비전머신 · 촬영 저장", style = MaterialTheme.typography.headlineSmall)
        Text(message, style = MaterialTheme.typography.bodyMedium)
        OutlinedTextField(subjectId, { subjectId = it }, label = { Text("개체 ID") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(batchId, { batchId = it }, label = { Text("구매·수집 묶음 ID") }, modifier = Modifier.fillMaxWidth())
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(crops) { (code, label) ->
                FilterChip(selected = cropCode == code, onClick = { cropCode = code }, label = { Text(label) })
            }
        }
        Button(onClick = { onCapture(subjectId.trim(), batchId.trim(), cropCode) }, enabled = !capturePending) {
            Text("기존 카메라로 촬영")
        }
        if (capturePending) {
            Button(onClick = onRecover) { Text("미완료 촬영 복구·정리") }
        }
        Text("저장된 사진 ${records.size}개", style = MaterialTheme.typography.titleMedium)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(records, key = { it.inspectionId }) { record ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Row(modifier = Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("${record.cropCode} · ${record.subjectId}")
                            Text(record.capturedAt, style = MaterialTheme.typography.bodySmall)
                        }
                        Button(onClick = { onOpen(record) }) { Text("사진 보기") }
                    }
                }
            }
        }
    }
}
