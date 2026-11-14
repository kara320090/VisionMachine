package org.visionmachine.agriclinic

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier

@Composable fun ServerSettingsCard(vm: RgbAnalysisViewModel) {
    Text(if (!vm.serverMode) "기기 내 사진 분석" else if (vm.serverConnected) "4090 서버 연결됨" else "4090 서버 자동 연결 대기")
    if (vm.serverMode) {
        Text("별도 설정 없이 연결합니다. 사진 분석을 누르면 사진과 연결 센서 기록을 서버로 전송합니다.")
        OutlinedButton({ vm.useAutomaticServer() }, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) {
            Text("서버 연결 다시 확인")
        }
        TextButton({ vm.useLocalModel() }, enabled = !vm.busy) { Text("기기에서 분석하기") }
    } else {
        OutlinedButton({ vm.useAutomaticServer() }, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) {
            Text("4090 서버 자동 연결 사용")
        }
    }
}
