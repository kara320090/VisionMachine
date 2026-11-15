package org.visionmachine.agriclinic

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun AnalysisScreen(
    vm: RgbAnalysisViewModel, open: () -> Unit, save: () -> Unit, camera: () -> Unit,
    sensors: (String?) -> Unit, takePicture: (String, String) -> Unit, files: () -> Unit,
) {
    var page by rememberSaveable { mutableStateOf("photos") }
    var sheet by rememberSaveable { mutableStateOf<String?>(null) }
    var subject by rememberSaveable { mutableStateOf("") }
    var batch by rememberSaveable { mutableStateOf("") }
    var recordDetail by remember { mutableStateOf<RgbRecord?>(null) }
    BackHandler(page != "photos") { page = "photos" }

    Scaffold(Modifier.fillMaxSize().systemBarsPadding(), containerColor = VisionColors.Cream,
        contentWindowInsets = WindowInsets(0, 0, 0, 0), bottomBar = {
            Column {
                if (page == "photos" && vm.items.isNotEmpty()) {
                    Surface(color = Color.White, shadowElevation = 8.dp) {
                        Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 12.dp)) {
                            Button({ vm.analyze(true) }, enabled = vm.ready && !vm.busy && !vm.cameraPending,
                                modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp), shape = RoundedCornerShape(18.dp)) {
                                if (vm.busy) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                                else Icon(VisionIcons.Spark, null, Modifier.size(20.dp))
                                Spacer(Modifier.width(10.dp))
                                Text(if (vm.busy) "사진 처리 중…" else "선택 ${vm.items.size}장 모두 분석", Modifier.weight(1f))
                                Icon(VisionIcons.Arrow, null, Modifier.size(20.dp))
                            }
                        }
                    }
                }
                NavigationBar(containerColor = Color.White, tonalElevation = 0.dp, windowInsets = WindowInsets(0, 0, 0, 0)) {
                    NavigationBarItem(selected = page == "photos", onClick = { page = "photos" },
                        icon = { Icon(VisionIcons.Leaf, null) }, label = { Text("사진 분석") })
                    NavigationBarItem(selected = false, onClick = { sensors(null) },
                        icon = { Icon(VisionIcons.Sensor, null) }, label = { Text("USB 센서") })
                    NavigationBarItem(selected = page == "history", onClick = { page = "history" },
                        icon = { Icon(VisionIcons.History, null) }, label = { Text("분석 기록") })
                }
            }
        }) { padding ->
        if (page == "photos") PhotoScreen(vm, Modifier.padding(padding), open, { takePicture(subject, batch) }, files, sensors, { sheet = it })
        else HistoryScreen(vm, Modifier.padding(padding), save, { recordDetail = it }, { page = "photos" })
    }
    if (sheet != null) {
        ModalBottomSheet(onDismissRequest = { sheet = null }, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true), containerColor = Color.White) {
            Column(Modifier.fillMaxWidth().imePadding().verticalScroll(rememberScrollState())
                .padding(start = 24.dp, end = 24.dp, bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                when (sheet) {
                    "connection" -> {
                        Text("분석 연결", style = MaterialTheme.typography.titleLarge)
                        ServerSettingsCard(vm)
                        Text(vm.message, style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
                    }
                    "options" -> {
                        Text("촬영·분석 옵션", style = MaterialTheme.typography.titleLarge)
                        Text("개체·묶음 ID", style = MaterialTheme.typography.titleMedium)
                        Text("새로 촬영하는 사진에 기록합니다. 비워 두면 미지정으로 저장합니다.", style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
                        OutlinedTextField(subject, { subject = it }, enabled = !vm.busy && !vm.cameraPending,
                            label = { Text("개체 ID (선택)") }, supportingText = { Text("영문·숫자·_·- / 최대 80자") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(batch, { batch = it }, enabled = !vm.busy && !vm.cameraPending,
                            label = { Text("묶음 ID (선택)") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                        HorizontalDivider(color = VisionColors.Line)
                        Text("종합 지수 가중치", style = MaterialTheme.typography.titleMedium)
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            StatusPill("사진 ${100 - (vm.sensorWeight * 100).roundToInt()}%")
                            StatusPill("센서 ${(vm.sensorWeight * 100).roundToInt()}%")
                        }
                        Slider(vm.sensorWeight, vm::changeSensorWeight, enabled = !vm.busy, onValueChangeFinished = vm::saveSensorWeight, steps = 9)
                        Text("두 점수의 사용자 가중평균입니다. 학습된 융합 AI가 아니며, 변경한 가중치는 다음 분석부터 적용합니다.", style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
                    }
                    else -> {
                        Text("분석 범위와 안내", style = MaterialTheme.typography.titleLarge)
                        Text("바질 · 청경채 · 오이 · 케일 · 상추 · 고추 · 로즈마리 · 토마토", style = MaterialTheme.typography.titleMedium)
                        Text("사진 분석은 작물 상태 점검을 돕는 시험 기능입니다. 병명·원인·섭취 안전이나 현장 정확도를 보장하지 않습니다.")
                        Text("사진 AI 출력과 센서 기준 이탈 점수는 별개입니다. 센서는 사진마다 직접 연결하며 다른 대상의 최근 측정값을 자동으로 붙이지 않습니다.")
                        OutlinedButton(camera, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) { Text("기존 촬영·기록 화면 열기") }
                    }
                }
                FilledTonalButton({ sheet = null }, modifier = Modifier.fillMaxWidth()) { Text("확인") }
            }
        }
    }
    recordDetail?.let { record ->
        ModalBottomSheet(onDismissRequest = { recordDetail = null }, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true), containerColor = Color.White) {
            Column(Modifier.verticalScroll(rememberScrollState()).padding(start = 24.dp, end = 24.dp, bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Text("저장된 분석 결과", style = MaterialTheme.typography.titleLarge)
                Text("${record.cropCode?.let(::cropLabel) ?: "작물 미지정"} · ${displayRecordTime(record.timestamp)}", color = VisionColors.Muted)
                Text(record.name, style = MaterialTheme.typography.bodySmall)
                RgbResultContent(record)
                FilledTonalButton({ recordDetail = null }, modifier = Modifier.fillMaxWidth()) { Text("닫기") }
            }
        }
    }
}

@Composable private fun PhotoScreen(vm: RgbAnalysisViewModel, modifier: Modifier, open: () -> Unit,
    takePicture: () -> Unit, files: () -> Unit, sensors: (String?) -> Unit, showSheet: (String) -> Unit) {
    val canAdd = !vm.busy && !vm.cameraPending && vm.items.size < 8
    val configuration = LocalConfiguration.current
    val showIllustration = configuration.screenWidthDp >= 360 && configuration.fontScale <= 1.15f
    val listState = rememberLazyListState()
    LaunchedEffect(vm.current?.timestamp) {
        // The filled screen has header, add controls, status, and photo selector before the preview.
        if (vm.current != null) listState.animateScrollToItem(4)
    }
    LazyColumn(modifier.fillMaxSize(), state = listState, contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Icon(VisionIcons.Leaf, null, Modifier.size(25.dp), tint = VisionColors.Forest)
                Text("비전머신", Modifier.weight(1f).padding(start = 9.dp), style = MaterialTheme.typography.titleMedium)
                Surface(onClick = { showSheet("connection") }, shape = RoundedCornerShape(50), color = Color.White) {
                    Row(Modifier.heightIn(min = 48.dp).padding(horizontal = 12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        Box(Modifier.size(7.dp).background(if ((vm.serverMode && !vm.serverConnected) || (!vm.serverMode && !vm.ready)) VisionColors.Terra else VisionColors.Forest, CircleShape))
                        Text(if (!vm.serverMode) { if (vm.ready) "기기 내 분석" else "모델 확인 필요" } else if (vm.serverConnected) "서버 연결됨" else "서버 연결 확인", style = MaterialTheme.typography.labelMedium)
                        Icon(VisionIcons.Down, null, Modifier.size(14.dp))
                    }
                }
            }
        }
        if (vm.items.isEmpty()) item {
            Surface(shape = RoundedCornerShape(26.dp), color = VisionColors.Forest) {
                Row(Modifier.fillMaxWidth().padding(24.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text("GROW WITH VISION", color = VisionColors.Sage, style = MaterialTheme.typography.labelMedium, letterSpacing = 1.4.sp)
                        Text("오늘의 작물,\n어떤 상태일까요?", color = Color.White, style = MaterialTheme.typography.headlineMedium)
                        Text("사진으로 살피고, 센서로 기록하세요.", color = Color(0xFFD7E5D7), style = MaterialTheme.typography.bodySmall)
                    }
                    if (showIllustration) Icon(VisionIcons.Leaf, null, Modifier.padding(start = 10.dp).size(68.dp), tint = VisionColors.Sage)
                }
            }
        }
        item {
            VisionCard {
                if (vm.items.isEmpty()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("사진 준비", style = MaterialTheme.typography.titleLarge)
                        Text("먼저 작물을 골라주세요", color = VisionColors.Muted, style = MaterialTheme.typography.bodySmall)
                    }
                    IconButton({ showSheet("options") }) { Icon(VisionIcons.Tune, "촬영·분석 옵션") }
                }
                CropChooser(vm.defaultCrop, enabled = !vm.busy && !vm.cameraPending, choose = vm::chooseDefaultCrop)
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    CaptureAction("바로 촬영", "카메라 열기", VisionIcons.Camera, true, canAdd, Modifier.weight(1f), takePicture)
                    CaptureAction("사진 추가", "갤러리 열기", VisionIcons.Gallery, false, canAdd, Modifier.weight(1f), open)
                }
                } else {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        CropChooser(vm.defaultCrop, enabled = !vm.busy && !vm.cameraPending, modifier = Modifier.weight(1f), choose = vm::chooseDefaultCrop)
                        IconButton(takePicture, enabled = canAdd) { Icon(VisionIcons.Camera, "바로 촬영") }
                        IconButton(open, enabled = canAdd) { Icon(VisionIcons.Gallery, "사진 추가") }
                    }
                }
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text("한 번에 최대 8장", Modifier.weight(1f), color = VisionColors.Muted, style = MaterialTheme.typography.bodySmall)
                    TextButton(files, enabled = canAdd, contentPadding = PaddingValues(horizontal = 0.dp)) { Text("파일에서 추가", style = MaterialTheme.typography.labelMedium) }
                    if (vm.items.isNotEmpty()) IconButton({ showSheet("options") }) { Icon(VisionIcons.Tune, "촬영·분석 옵션") }
                }
                if (vm.cameraPending) OutlinedButton({ vm.completeCamera(true) }, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) { Text("미완료 촬영 복구·정리") }
            }
        }
        item {
            Column(Modifier.semantics { liveRegion = LiveRegionMode.Polite }, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (vm.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                Text(vm.message, color = VisionColors.Muted, style = MaterialTheme.typography.bodySmall)
            }
        }
        if (vm.items.isNotEmpty()) {
            item {
                SectionHeading("선택한 사진", "${vm.items.size} / 8장 · 사진별로 결과를 확인하세요") {
                    TextButton(vm::clearSelection, enabled = !vm.busy && !vm.cameraPending) { Text("비우기") }
                }
                Spacer(Modifier.height(12.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    itemsIndexed(vm.items, key = { _, item -> item.reference.inspectionId }) { index, item ->
                        val active = index == vm.focusIndex
                        Surface(onClick = { vm.focus(index) }, enabled = !vm.busy && !vm.cameraPending,
                            modifier = Modifier.semantics { selected = active; stateDescription = item.status },
                            shape = RoundedCornerShape(16.dp), color = if (active) VisionColors.Forest else Color.White,
                            border = if (active) null else BorderStroke(1.dp, VisionColors.Line)) {
                            Column(Modifier.widthIn(min = 92.dp).padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text("사진 ${"%02d".format(index + 1)}", color = if (active) Color.White else VisionColors.Ink, style = MaterialTheme.typography.titleMedium)
                                Text("${cropLabel(item.reference.cropCode)} · ${item.status}", color = if (active) Color(0xFFD7E5D7) else VisionColors.Muted, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
            item(key = "preview") {
                val focused = vm.items.getOrNull(vm.focusIndex)
                VisionCard {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("사진 ${vm.focusIndex + 1}", Modifier.weight(1f), style = MaterialTheme.typography.titleMedium)
                        focused?.let { StatusPill(it.status, it.error != null) }
                    }
                    Surface(shape = RoundedCornerShape(16.dp), color = VisionColors.Mint) {
                        Box(Modifier.fillMaxWidth().height(210.dp), contentAlignment = Alignment.Center) {
                            vm.preview?.let { Image(it.asImageBitmap(), "선택한 작물 사진", Modifier.fillMaxSize(), contentScale = ContentScale.Fit) }
                                ?: Icon(VisionIcons.Gallery, "사진 미리보기 없음", Modifier.size(36.dp), tint = VisionColors.Muted)
                        }
                    }
                    Text(vm.filename, style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    focused?.let { item ->
                        CropChooser(item.reference.cropCode, enabled = !vm.busy && !vm.cameraPending) { vm.changeCrop(vm.focusIndex, it) }
                        if (item.error != null) Text(item.error, color = VisionColors.Terra, style = MaterialTheme.typography.bodyMedium)
                        vm.current?.let { RgbResultContent(it) }
                        if (vm.current == null && item.error == null) Text("사진을 준비했어요. 아래 분석 버튼을 눌러 주세요.", color = VisionColors.Muted, style = MaterialTheme.typography.bodyMedium)
                        OutlinedButton({ sensors(item.reference.inspectionId) }, enabled = !vm.busy && !vm.cameraPending, modifier = Modifier.fillMaxWidth()) {
                            Icon(VisionIcons.Sensor, null, Modifier.size(18.dp)); Spacer(Modifier.width(8.dp)); Text("이 사진에 센서 측정")
                        }
                        TextButton({ vm.analyze(false) }, enabled = vm.ready && !vm.busy && !vm.cameraPending, modifier = Modifier.align(Alignment.CenterHorizontally)) { Text("이 사진만 분석") }
                    }
                }
            }
        } else {
            item {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("작물 선택", "사진 추가", "분석 확인").forEachIndexed { index, text ->
                        if (index > 0) Icon(VisionIcons.Chevron, null, Modifier.size(14.dp), tint = VisionColors.Muted)
                        Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("0${index + 1}", color = VisionColors.Forest, style = MaterialTheme.typography.titleMedium)
                            Text(text, color = VisionColors.Muted, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
        item {
            Text(if (vm.serverMode) "분석 시 사진과 연결 센서 기록을 서버로 전송합니다." else "사진은 이 기기에서 분석합니다.", color = VisionColors.Muted, style = MaterialTheme.typography.bodySmall)
            TextButton({ showSheet("info") }, contentPadding = PaddingValues(horizontal = 0.dp)) { Text("시험 기능 · 분석 범위와 주의사항", style = MaterialTheme.typography.labelMedium) }
        }
    }
}

@Composable private fun CaptureAction(title: String, subtitle: String, icon: ImageVector, primary: Boolean,
    enabled: Boolean, modifier: Modifier, action: () -> Unit) {
    Surface(onClick = action, enabled = enabled, modifier = modifier,
        color = if (!enabled) VisionColors.Mint else if (primary) VisionColors.Forest else VisionColors.Cream,
        contentColor = if (!enabled) VisionColors.Muted else if (primary) Color.White else VisionColors.Forest,
        shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(vertical = 20.dp, horizontal = 12.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Icon(icon, null, Modifier.size(28.dp))
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(subtitle, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable private fun HistoryScreen(vm: RgbAnalysisViewModel, modifier: Modifier, save: () -> Unit,
    details: (RgbRecord) -> Unit, start: () -> Unit) {
    var filter by rememberSaveable { mutableStateOf(false) }
    val records = vm.records.asReversed().filter { !filter || it.abnormal >= .5f }
    LazyColumn(modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item {
            SectionHeading("분석 기록", "작물의 변화를 차곡차곡 기록하세요") {
                IconButton(save, enabled = vm.records.isNotEmpty() && !vm.busy) { Icon(VisionIcons.Download, "전체 기록 CSV 저장") }
            }
        }
        item {
            Surface(shape = RoundedCornerShape(24.dp), color = VisionColors.Forest) {
                Row(Modifier.fillMaxWidth().padding(24.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("기기에 저장된 분석", color = VisionColors.Sage, style = MaterialTheme.typography.bodyMedium)
                        Text("${vm.records.size}건", color = Color.White, style = MaterialTheme.typography.headlineLarge)
                    }
                    Icon(VisionIcons.History, null, Modifier.size(42.dp), tint = VisionColors.Sage)
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(!filter, { filter = false }, label = { Text("전체") })
                FilterChip(filter, { filter = true }, label = { Text("이상 의심") })
            }
        }
        if (records.isEmpty()) item {
            VisionCard {
                Icon(VisionIcons.History, null, Modifier.align(Alignment.CenterHorizontally).padding(top = 16.dp).size(40.dp), tint = VisionColors.Muted)
                Text(if (filter) "이상 의심 기록이 없습니다" else "첫 번째 기록을 남겨보세요", Modifier.align(Alignment.CenterHorizontally), style = MaterialTheme.typography.titleMedium)
                Text(if (filter) "전체 탭에서 저장된 분석을 확인할 수 있어요." else "사진을 분석하면 결과가 이곳에 저장됩니다.", style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
                OutlinedButton(if (filter) ({ filter = false }) else start, modifier = Modifier.fillMaxWidth()) { Text(if (filter) "전체 기록 보기" else "사진 분석하러 가기") }
            }
        }
        items(records) { record ->
            Surface(onClick = { details(record) }, color = Color.White, shape = RoundedCornerShape(20.dp), border = BorderStroke(1.dp, VisionColors.Line)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(record.cropCode?.let(::cropLabel) ?: "작물 미지정", Modifier.weight(1f), style = MaterialTheme.typography.titleMedium)
                        StatusPill(record.label, record.abnormal >= .5f)
                        Icon(VisionIcons.Chevron, null, Modifier.padding(start = 6.dp).size(16.dp), tint = VisionColors.Muted)
                    }
                    Text(record.name, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
                    Text(displayRecordTime(record.timestamp), style = MaterialTheme.typography.labelMedium, color = VisionColors.Muted)
                }
            }
        }
        item { Text("최근 200건을 기기에 보관합니다. 기록을 누르면 사진 AI·연결 센서·종합 지수를 확인할 수 있습니다.", color = VisionColors.Muted, style = MaterialTheme.typography.bodySmall) }
    }
}

@Composable internal fun RgbResultContent(record: RgbRecord) {
    var technical by rememberSaveable(record.sha256, record.timestamp) { mutableStateOf(false) }
    val abnormal = record.abnormal >= .5f
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        HorizontalDivider(color = VisionColors.Line)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("사진 AI 분석", style = MaterialTheme.typography.labelMedium, color = VisionColors.Muted)
                Text(record.label, style = MaterialTheme.typography.headlineMedium, color = if (abnormal) VisionColors.Terra else VisionColors.Forest)
            }
            Icon(if (abnormal) VisionIcons.Leaf else VisionIcons.Check, null, Modifier.size(30.dp), tint = if (abnormal) VisionColors.Terra else VisionColors.Forest)
        }
        ScoreBar("정상 출력", record.normal, VisionColors.Forest)
        ScoreBar("이상 출력", record.abnormal, VisionColors.Terra)
        Text("모델 출력값이며 보정된 진단 확률이 아닙니다.", style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
        SensorAssessmentCard(record.sensorAssessmentJson)
        CompositeIndexCard(record.compositeJson)
        TextButton({ technical = !technical }, contentPadding = PaddingValues(0.dp)) { Text(if (technical) "분석 정보 접기" else "분석 정보 자세히") }
        if (technical) {
            Text(if (record.executionProvider == "CUDAExecutionProvider") "4090 서버 GPU 결과" else "기기 내 분석 결과", style = MaterialTheme.typography.bodySmall)
            Text("처리 ${record.millis}ms · ${displayRecordTime(record.timestamp, "yyyy.MM.dd HH:mm:ss")}", style = MaterialTheme.typography.bodySmall)
            Text("모델 ${record.model}", style = MaterialTheme.typography.bodySmall)
            record.serverInspectionId?.let { Text("서버 검사 ID $it", style = MaterialTheme.typography.bodySmall) }
            Text("사진 SHA-256 ${record.sha256}", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable private fun ScoreBar(label: String, value: Float, color: Color) {
    Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, style = MaterialTheme.typography.bodySmall)
            Text("%.6f".format(Locale.US, value), style = MaterialTheme.typography.labelMedium, color = color)
        }
        LinearProgressIndicator(progress = { value.coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth().height(6.dp), color = color, trackColor = VisionColors.Mint)
    }
}
