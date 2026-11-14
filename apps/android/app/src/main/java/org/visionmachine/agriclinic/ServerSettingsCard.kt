package org.visionmachine.agriclinic

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation

@Composable fun ServerSettingsCard(vm: RgbAnalysisViewModel) {
    var open by remember { mutableStateOf(false) }
    var url by remember(vm.serverAddress) { mutableStateOf(vm.serverAddress) }
    // Keep credentials out of saved-instance state, screenshots and prefilled text.
    var key by remember { mutableStateOf("") }
    OutlinedButton({ open = !open }, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) {
        Text(if (vm.serverMode) "4090 서버 사용 중 · 연결 설정" else "4090 서버 연결 설정")
    }
    if (open) {
        OutlinedTextField(url, { url = it }, enabled = !vm.busy, singleLine = true,
            label = { Text("서버 기본 주소") }, placeholder = { Text("http://100.74.204.80:8000") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(key, { key = it }, enabled = !vm.busy, singleLine = true,
            label = { Text("내 기기용 인증키 · 비우면 기존 키 유지") }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
        Text("같은 Tailscale에 연결해 주세요. 설정 후 분석을 누르면 사진과 연결된 센서 기록을 서버로 전송합니다.")
        Row {
            Button({ vm.saveServer(url, key); key = "" }, enabled = !vm.busy) { Text("서버 사용·저장") }
            TextButton({ vm.useLocalModel(); key = "" }, enabled = !vm.busy) { Text("기기 모델 사용") }
        }
    }
}
