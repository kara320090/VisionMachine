package org.visionmachine.agriclinic

import android.graphics.Bitmap
import android.net.Uri
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.ExternalResource
import org.junit.rules.RuleChain
import org.junit.rules.TestRule
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class AnalysisNavigationTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private var previousMode = "auto"
    private var previousRecords = emptyList<RgbRecord>()
    private val isolatedData = object : ExternalResource() {
        override fun before() {
            previousMode = AutomaticServerSettings(context).mode()
            AutomaticServerSettings(context).setMode("local")
            previousRecords = RgbHistory(context).read()
            RgbHistory(context).write(emptyList())
        }
        override fun after() {
            RgbHistory(context).write(previousRecords)
            AutomaticServerSettings(context).setMode(previousMode)
        }
    }
    private val ui = createAndroidComposeRule<AnalysisActivity>()
    @get:Rule val rules: TestRule = RuleChain.outerRule(isolatedData).around(ui)

    private fun model(): RgbAnalysisViewModel = ViewModelProvider(ui.activity)[RgbAnalysisViewModel::class.java]
    private fun awaitIdleModel() {
        ui.waitUntil(60_000) {
            var idle = false
            ui.runOnIdle { idle = !model().busy }
            idle
        }
    }

    @Test fun captureActionsAndOptionalSettingsStayReachable() {
        awaitIdleModel()
        ui.onNodeWithText("바로 촬영").assertIsDisplayed().assertHasClickAction()
        ui.onNode(hasText("사진 추가") and hasClickAction()).assertIsDisplayed()
        ui.onNodeWithText("개체 ID (선택)").assertDoesNotExist()
        ui.onNodeWithContentDescription("촬영·분석 옵션").performClick()
        ui.onNodeWithText("개체 ID (선택)").assertIsDisplayed().performTextInput("ui-subject")
        // Rotation/recreation must keep the optional ID and the open settings panel.
        ui.activityRule.scenario.recreate()
        ui.onNodeWithText("ui-subject").assertIsDisplayed()
    }

    @Test fun emptyHistoryReturnsToPhotoActionsWithoutCreatingResults() {
        awaitIdleModel()
        ui.onNodeWithText("분석 기록").performClick()
        ui.onNodeWithText("첫 번째 기록을 남겨보세요").assertIsDisplayed()
        ui.onNodeWithText("이상 의심").performClick()
        ui.onNodeWithText("이상 의심 기록이 없습니다").assertIsDisplayed()
        ui.onNodeWithText("전체 기록 보기").performClick()
        ui.onNodeWithText("사진 분석하러 가기").performClick()
        ui.onNodeWithText("바로 촬영").assertIsDisplayed()
        ui.runOnIdle { assertTrue(model().records.isEmpty()) }
    }

    @Test fun realLocalResultFromSyntheticPhotoOpensFromHistoryAndKeepsRawScores() {
        assumeTrue("Private local ONNX asset required", runCatching { context.assets.open("vision_rgb_cseed42.onnx").close() }.isSuccess)
        awaitIdleModel()
        val file = File(context.cacheDir, "synthetic-ui-pattern.png")
        val bitmap = Bitmap.createBitmap(64, 64, Bitmap.Config.ARGB_8888)
        bitmap.eraseColor(0xff648b58.toInt())
        try {
            file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
            ui.runOnIdle { model().select(listOf(Uri.fromFile(file))) }
            awaitIdleModel()
            ui.onNodeWithText("선택 1장 모두 분석").assertIsDisplayed().performClick()
            awaitIdleModel()
            ui.onNodeWithContentDescription("선택한 작물 사진").assertIsDisplayed()
            ui.onNodeWithText("사진 AI 분석").performScrollTo().assertIsDisplayed()
            InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()?.let { screenshot ->
                try { File(context.filesDir, "ui_result_synthetic.png").outputStream().use { screenshot.compress(Bitmap.CompressFormat.PNG, 100, it) } }
                finally { screenshot.recycle() }
            }
            lateinit var record: RgbRecord
            ui.runOnIdle { record = requireNotNull(model().current); assertEquals(1, model().records.size) }
            ui.onNodeWithText("분석 기록").performClick()
            ui.onNode(hasText(record.name) and hasClickAction()).performClick()
            ui.onNodeWithText("저장된 분석 결과").assertIsDisplayed()
            ui.onNodeWithText("%.6f".format(java.util.Locale.US, record.abnormal)).performScrollTo().assertIsDisplayed()
            ui.onNodeWithText("모델 출력값이며 보정된 진단 확률이 아닙니다.").performScrollTo().assertIsDisplayed()
        } finally { bitmap.recycle(); file.delete() }
    }
}
