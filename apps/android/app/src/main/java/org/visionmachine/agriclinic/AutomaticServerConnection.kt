package org.visionmachine.agriclinic

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.security.KeyStore
import java.security.SecureRandom
import java.time.Instant
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

internal const val SERVER_DISCOVERY_URL = "https://raw.githubusercontent.com/kara320090/VisionMachine/main/config/android-server.json"
internal const val DEFAULT_SERVER_URL = "https://cruz-processor-enabling-dropped.trycloudflare.com"
internal const val DEFAULT_SERVER_ID = "visionmachine-4090"

internal data class InstallationIdentity(val id: String, val secret: String)
internal data class AutomaticSession(val config: ServerConfig, val expiresAt: Instant)

/** Identity, proof and per-install token stay encrypted; no shared server credential is packaged. */
internal class AutomaticServerSettings(context: Context) {
    private val prefs = context.getSharedPreferences("automatic_server_v1", Context.MODE_PRIVATE)
    private val alias = "visionmachine-auto-credential-v1"
    fun mode(): String = prefs.getString("mode", "auto").orEmpty()
    fun setMode(mode: String) { require(mode in setOf("auto", "local", "manual")); check(prefs.edit().putString("mode", mode).commit()) }
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    private fun read(): JSONObject {
        val ciphertext = prefs.getString("data", null) ?: return JSONObject()
        val iv = Base64.decode(prefs.getString("iv", null) ?: error("Missing identity IV"), Base64.NO_WRAP)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, iv))
        return JSONObject(String(cipher.doFinal(Base64.decode(ciphertext, Base64.NO_WRAP)), Charsets.UTF_8))
    }
    private fun write(value: JSONObject) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encrypted = cipher.doFinal(value.toString().toByteArray(Charsets.UTF_8))
        check(prefs.edit().putString("data", Base64.encodeToString(encrypted, Base64.NO_WRAP))
            .putString("iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP)).commit())
    }
    fun identity(): InstallationIdentity {
        val value = read()
        if (!value.has("id")) {
            val proof = ByteArray(32).also { SecureRandom().nextBytes(it) }.joinToString("") { "%02x".format(it.toInt() and 255) }
            value.put("id", UUID.randomUUID().toString()).put("proof", proof)
            write(value)
        }
        return InstallationIdentity(value.getString("id"), value.getString("proof"))
    }
    fun cached(): AutomaticSession? {
        val value = read()
        if (!value.has("token")) return null
        return AutomaticSession(ServerConfig(checkedAutomaticServerUrl(value.getString("url")), value.getString("token")),
            Instant.parse(value.getString("expires_at")))
    }
    fun save(session: AutomaticSession) {
        val value = read().put("url", session.config.baseUrl).put("token", session.config.apiKey)
            .put("expires_at", session.expiresAt.toString())
        write(value)
    }
    internal fun clearForTest() { check(prefs.edit().clear().commit()) }
}

internal fun checkedAutomaticServerUrl(value: String, debug: Boolean = BuildConfig.DEBUG): String {
    val uri = URI(value.trim().trimEnd('/'))
    require(uri.userInfo == null && uri.query == null && uri.fragment == null && uri.path.orEmpty().isEmpty())
    require(!uri.host.isNullOrBlank() && (uri.scheme == "https" ||
        (debug && uri.scheme == "http" && uri.host in setOf("127.0.0.1", "10.0.2.2"))))
    require(uri.port == -1 || uri.port in 1..65535)
    return uri.toASCIIString()
}

class ServerRequestException(val code: String, message: String) : java.io.IOException(message)

internal class AutomaticServerConnection(private val context: Context,
    private val discoveryUrl: String = SERVER_DISCOVERY_URL, private val fallbackUrl: String = DEFAULT_SERVER_URL) {
    private val settings = AutomaticServerSettings(context)

    fun connect(forceRegistration: Boolean = false): ServerConfig {
        val cached = settings.cached()
        val endpoint = try {
            val discovery = requestJson(discoveryUrl)
            require(discovery.getString("schema_version") == "0.1.0" && discovery.getString("server_id") == DEFAULT_SERVER_ID)
            if (discovery.getInt("minimum_app_version_code") > BuildConfig.VERSION_CODE) {
                throw ServerRequestException("APP_UPDATE_REQUIRED", "Play 스토어에서 앱을 업데이트해 주세요.")
            }
            checkedAutomaticServerUrl(discovery.getString("base_url"))
        } catch (error: Exception) {
            if (error is ServerRequestException && error.code == "APP_UPDATE_REQUIRED") throw error
            cached?.config?.baseUrl ?: checkedAutomaticServerUrl(fallbackUrl)
        }
        val health = requestJson("$endpoint/health/ready")
        val card = JSONObject(context.assets.open("vision_rgb_model.json").bufferedReader().use { it.readText() })
        check(health.getString("status") == "ready" && health.getJSONObject("model").getString("model_sha256") == card.getString("model_sha256")) {
            "서버의 사진 분석 모델을 확인하지 못했습니다."
        }
        val providers = health.getJSONArray("providers")
        check((0 until providers.length()).any { providers.getString(it) == "CUDAExecutionProvider" }) { "4090 서버 GPU가 준비되지 않았습니다." }
        if (!forceRegistration && cached != null && cached.config.baseUrl == endpoint && cached.expiresAt.isAfter(Instant.now().plusSeconds(60))) {
            return cached.config
        }
        val identity = settings.identity()
        val payload = JSONObject().put("schema_version", "0.1.0").put("installation_id", identity.id)
            .put("registration_secret", identity.secret).put("app_version_code", BuildConfig.VERSION_CODE)
        val response = requestJson("$endpoint/api/v1/devices/register", payload)
        require(response.getString("schema_version") == "0.1.0" && response.getString("server_id") == DEFAULT_SERVER_ID &&
            response.getString("installation_id") == identity.id) { "서버 기기 등록 응답이 올바르지 않습니다." }
        val token = response.getString("api_key")
        require(token.startsWith("vm_device_") && token.length in 32..128)
        val expiry = Instant.parse(response.getString("expires_at"))
        require(expiry.isAfter(Instant.now()) && expiry.isBefore(Instant.now().plusSeconds(31L * 24 * 3600)))
        val session = AutomaticSession(ServerConfig(endpoint, token), expiry)
        settings.save(session)
        return session.config
    }

    private fun requestJson(url: String, payload: JSONObject? = null): JSONObject {
        val connection = URL(url).openConnection() as HttpURLConnection
        try {
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 5_000; connection.readTimeout = 10_000
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Cache-Control", "no-cache")
            if (payload != null) {
                val bytes = payload.toString().toByteArray(Charsets.UTF_8)
                connection.requestMethod = "POST"; connection.doOutput = true
                connection.setFixedLengthStreamingMode(bytes.size)
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(bytes) }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.use { input ->
                val out = ByteArrayOutputStream(); val buffer = ByteArray(4096)
                while (true) { val n = input.read(buffer); if (n < 0) break
                    require(out.size() + n <= 65536); out.write(buffer, 0, n) }
                out.toString("UTF-8")
            }.orEmpty()
            if (status !in 200..299) {
                val code = runCatching { JSONObject(text).getJSONObject("detail").getString("code") }
                    .getOrDefault(if (status == 503 && url.endsWith("/health/ready")) "MODEL_NOT_READY" else "HTTP_$status")
                throw ServerRequestException(code, when (code) {
                    "DEVICE_REVOKED" -> "이 기기의 서버 사용이 중지되었습니다."
                    "DEVICE_LIMIT_REACHED" -> "서버의 기기 등록 한도에 도달했습니다."
                    "RATE_LIMITED" -> "요청이 많습니다. 잠시 후 다시 분석해 주세요."
                    "MODEL_NOT_READY" -> "4090 서버의 분석 모델이 준비되지 않았습니다."
                    "ENROLLMENT_DISABLED", "HTTP_404" -> "서버 자동 연결 기능이 아직 준비되지 않았습니다."
                    else -> "4090 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
                })
            }
            return JSONObject(text)
        } finally { connection.disconnect() }
    }
}
