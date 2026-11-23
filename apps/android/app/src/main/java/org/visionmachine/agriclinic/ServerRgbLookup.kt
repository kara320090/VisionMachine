package org.visionmachine.agriclinic

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL

/** GET uses the same authenticated inspection and is safe across endpoint or credential changes. */
internal fun lookupServerRgbResponse(config: ServerConfig, id: String): String? {
    val url = URL("${checkedServerUrl(config.baseUrl)}/api/v1/inspections/$id")
    val connection = url.openConnection() as HttpURLConnection
    try {
        connection.instanceFollowRedirects = false
        connection.useCaches = false
        connection.connectTimeout = 10_000
        connection.readTimeout = 15_000
        connection.setRequestProperty("X-API-Key", config.apiKey)
        connection.setRequestProperty("Cache-Control", "no-store")
        val status = connection.responseCode
        return when (status) {
            HttpURLConnection.HTTP_OK -> connection.readRgbResponse(status)
            HttpURLConnection.HTTP_NOT_FOUND, HttpURLConnection.HTTP_BAD_METHOD,
            HttpURLConnection.HTTP_NOT_IMPLEMENTED -> null
            else -> throw rgbRequestError(status, connection.readRgbResponse(status))
        }
    } finally {
        connection.disconnect()
    }
}

internal fun HttpURLConnection.readRgbResponse(status: Int): String {
    val stream = if (status in 200..299) inputStream else errorStream
    return stream?.use { input ->
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            require(output.size() + count <= 1024 * 1024) { "서버 응답이 너무 큽니다." }
            output.write(buffer, 0, count)
        }
        output.toString("UTF-8")
    }.orEmpty()
}

internal fun rgbRequestError(status: Int, body: String): ServerRequestException {
    val code = runCatching { JSONObject(body).getJSONObject("detail").getString("code") }.getOrNull()
        ?: if (status == HttpURLConnection.HTTP_UNAUTHORIZED) "UNAUTHORIZED" else "HTTP_$status"
    val message = when (code) {
        "MODEL_NOT_READY" -> "서버 모델이 준비되지 않았습니다. ONNX 파일과 GPU 준비 상태를 확인해 주세요."
        "UNAUTHORIZED" -> "서버 인증 연결을 갱신하지 못했습니다. 다시 연결해 주세요."
        "ID_CONFLICT" -> "같은 검사 ID의 내용이 다릅니다. 서버 기록을 확인해 주세요."
        "RATE_LIMITED" -> "요청이 많습니다. 잠시 후 다시 분석해 주세요."
        else -> "서버 요청 실패: $code"
    }
    return ServerRequestException(code, message)
}
