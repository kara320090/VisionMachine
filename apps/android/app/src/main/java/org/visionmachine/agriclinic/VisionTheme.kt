package org.visionmachine.agriclinic

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.path
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

internal object VisionColors {
    val Forest = Color(0xFF1F4D3A)
    val Cream = Color(0xFFF7F1E2)
    val Mint = Color(0xFFE8F0E7)
    val Sage = Color(0xFFB8D3B8)
    val Ink = Color(0xFF22392D)
    val Muted = Color(0xFF637166)
    val Line = Color(0xFFDCE2D7)
    val Terra = Color(0xFFAC482B)
    val Peach = Color(0xFFFFEDE4)
}

@Composable internal fun VisionTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = VisionColors.Forest, onPrimary = Color.White,
            primaryContainer = VisionColors.Mint, onPrimaryContainer = VisionColors.Forest,
            secondary = VisionColors.Terra, secondaryContainer = VisionColors.Mint, onSecondaryContainer = VisionColors.Forest,
            background = VisionColors.Cream, onBackground = VisionColors.Ink,
            surface = Color.White, onSurface = VisionColors.Ink,
            surfaceVariant = VisionColors.Mint, onSurfaceVariant = VisionColors.Muted,
            outline = VisionColors.Muted, outlineVariant = VisionColors.Line,
            error = VisionColors.Terra, errorContainer = VisionColors.Peach,
        ),
        typography = Typography(
            headlineLarge = androidx.compose.ui.text.TextStyle(fontSize = 30.sp, lineHeight = 39.sp, fontWeight = FontWeight.Bold),
            headlineMedium = androidx.compose.ui.text.TextStyle(fontSize = 26.sp, lineHeight = 35.sp, fontWeight = FontWeight.Bold),
            titleLarge = androidx.compose.ui.text.TextStyle(fontSize = 21.sp, lineHeight = 29.sp, fontWeight = FontWeight.Bold),
            titleMedium = androidx.compose.ui.text.TextStyle(fontSize = 16.sp, lineHeight = 24.sp, fontWeight = FontWeight.SemiBold),
            bodyLarge = androidx.compose.ui.text.TextStyle(fontSize = 16.sp, lineHeight = 25.sp),
            bodyMedium = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, lineHeight = 22.sp),
            bodySmall = androidx.compose.ui.text.TextStyle(fontSize = 12.sp, lineHeight = 19.sp),
            labelLarge = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, lineHeight = 20.sp, fontWeight = FontWeight.SemiBold),
            labelMedium = androidx.compose.ui.text.TextStyle(fontSize = 12.sp, lineHeight = 18.sp, fontWeight = FontWeight.Medium),
        ),
        shapes = Shapes(small = RoundedCornerShape(12.dp), medium = RoundedCornerShape(20.dp), large = RoundedCornerShape(26.dp)),
        content = content,
    )
}

@Composable internal fun VisionCard(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Surface(modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp), color = Color.White,
        border = BorderStroke(1.dp, VisionColors.Line.copy(alpha = .65f))) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp), content = content)
    }
}

@Composable internal fun SectionHeading(title: String, subtitle: String? = null, action: @Composable () -> Unit = {}) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, Modifier.semantics { heading() }, style = MaterialTheme.typography.titleLarge)
            if (subtitle != null) Text(subtitle, style = MaterialTheme.typography.bodySmall, color = VisionColors.Muted)
        }
        action()
    }
}

@Composable internal fun StatusPill(text: String, warning: Boolean = false) {
    Surface(shape = RoundedCornerShape(50), color = if (warning) VisionColors.Peach else VisionColors.Mint) {
        Text(text, Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
            style = MaterialTheme.typography.labelMedium, color = if (warning) VisionColors.Terra else VisionColors.Forest)
    }
}

internal fun displayRecordTime(value: String, pattern: String = "MM.dd  HH:mm"): String = runCatching {
    DateTimeFormatter.ofPattern(pattern, Locale.KOREA).withZone(ZoneId.systemDefault()).format(Instant.parse(value))
}.getOrDefault(value)

/** Small, bundled vector icons; no remote assets or extra icon font. */
internal object VisionIcons {
    private fun icon(name: String, draw: androidx.compose.ui.graphics.vector.PathBuilder.() -> Unit): ImageVector =
        ImageVector.Builder(name, 24.dp, 24.dp, 24f, 24f).apply {
            path(fill = null, stroke = SolidColor(Color.Black), strokeLineWidth = 1.7f,
                strokeLineCap = StrokeCap.Round, strokeLineJoin = StrokeJoin.Round, pathBuilder = draw)
        }.build()
    val Leaf = icon("Leaf") {
        moveTo(19f, 4f); curveTo(8f, 2f, 3f, 7f, 5f, 14f); curveTo(7f, 21f, 21f, 19f, 19f, 4f); close()
        moveTo(4f, 21f); curveTo(7f, 15f, 10f, 11f, 15f, 8f)
        moveTo(8f, 15f); lineTo(8f, 10f); moveTo(11f, 12f); lineTo(16f, 13f)
    }
    val Camera = icon("Camera") {
        moveTo(8f, 6f); lineTo(9.5f, 3.5f); lineTo(14.5f, 3.5f); lineTo(16f, 6f); lineTo(20f, 6f)
        curveTo(21f, 6f, 22f, 7f, 22f, 8f); lineTo(22f, 19f); lineTo(2f, 19f); lineTo(2f, 8f)
        curveTo(2f, 7f, 3f, 6f, 4f, 6f); close()
        moveTo(16f, 12.5f); curveTo(16f, 7.2f, 8f, 7.2f, 8f, 12.5f); curveTo(8f, 17.8f, 16f, 17.8f, 16f, 12.5f); close()
    }
    val Gallery = icon("Gallery") {
        moveTo(4f, 3f); lineTo(20f, 3f); lineTo(20f, 21f); lineTo(4f, 21f); close()
        moveTo(4f, 16f); lineTo(10f, 10f); lineTo(14f, 14f); lineTo(16f, 12f); lineTo(20f, 16f)
        moveTo(16f, 7f); lineTo(16.1f, 7f)
    }
    val Sensor = icon("Sensor") {
        moveTo(6f, 8f); lineTo(18f, 8f); lineTo(18f, 20f); lineTo(6f, 20f); close()
        moveTo(10f, 8f); lineTo(10f, 3f); lineTo(14f, 3f); lineTo(14f, 8f)
        moveTo(9f, 14f); lineTo(11f, 14f); lineTo(12f, 11f); lineTo(14f, 17f); lineTo(15f, 14f)
    }
    val History = icon("History") {
        moveTo(5f, 7f); curveTo(11f, 0f, 22f, 4f, 21f, 13f); curveTo(20f, 22f, 8f, 24f, 4f, 16f)
        moveTo(4f, 3f); lineTo(4f, 9f); lineTo(10f, 9f)
        moveTo(12f, 7f); lineTo(12f, 13f); lineTo(16f, 15f)
    }
    val Spark = icon("Spark") {
        moveTo(12f, 3f); lineTo(14.5f, 9.5f); lineTo(21f, 12f); lineTo(14.5f, 14.5f)
        lineTo(12f, 21f); lineTo(9.5f, 14.5f); lineTo(3f, 12f); lineTo(9.5f, 9.5f); close()
    }
    val Arrow = icon("Arrow") { moveTo(4f, 12f); lineTo(20f, 12f); moveTo(14f, 6f); lineTo(20f, 12f); lineTo(14f, 18f) }
    val Back = icon("Back") { moveTo(20f, 12f); lineTo(4f, 12f); moveTo(10f, 6f); lineTo(4f, 12f); lineTo(10f, 18f) }
    val Chevron = icon("Chevron") { moveTo(9f, 5f); lineTo(16f, 12f); lineTo(9f, 19f) }
    val Down = icon("Down") { moveTo(6f, 9f); lineTo(12f, 15f); lineTo(18f, 9f) }
    val Tune = icon("Tune") {
        moveTo(3f, 7f); lineTo(8f, 7f); moveTo(12f, 7f); lineTo(21f, 7f)
        moveTo(8f, 4f); lineTo(12f, 4f); lineTo(12f, 10f); lineTo(8f, 10f); close()
        moveTo(3f, 17f); lineTo(13f, 17f); moveTo(17f, 17f); lineTo(21f, 17f)
        moveTo(13f, 14f); lineTo(17f, 14f); lineTo(17f, 20f); lineTo(13f, 20f); close()
    }
    val Download = icon("Download") {
        moveTo(12f, 3f); lineTo(12f, 15f); moveTo(7f, 10f); lineTo(12f, 15f); lineTo(17f, 10f)
        moveTo(4f, 16f); lineTo(4f, 21f); lineTo(20f, 21f); lineTo(20f, 16f)
    }
    val Check = icon("Check") { moveTo(5f, 12f); lineTo(10f, 17f); lineTo(20f, 6f) }
}
