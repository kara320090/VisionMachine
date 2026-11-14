package org.visionmachine.agriclinic

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.net.URI
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class ServerConfig(val baseUrl: String, val apiKey: String)

/** Per-install credentials entered at runtime; neither key nor token is in the APK. */
class ServerSettings(context: Context) {
    private val prefs = context.getSharedPreferences("gpu_server_v1", Context.MODE_PRIVATE)
    private val alias = "visionmachine-server-credential-v1"
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    fun load(): ServerConfig? {
        val encrypted = prefs.getString("credential", null) ?: return null
        val iv = Base64.decode(prefs.getString("iv", null) ?: error("Missing credential IV"), Base64.NO_WRAP)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, iv))
        val value = JSONObject(String(cipher.doFinal(Base64.decode(encrypted, Base64.NO_WRAP)), Charsets.UTF_8))
        return ServerConfig(checkedServerUrl(value.getString("url")), value.getString("key"))
    }
    fun save(url: String, apiKey: String) {
        val checked = checkedServerUrl(url)
        val secret = apiKey.ifBlank { load()?.apiKey.orEmpty() }
        require(secret.length in 24..512 && secret.all { it.code in 33..126 }) { "서버 인증키를 입력해 주세요." }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val raw = JSONObject().put("url", checked).put("key", secret).toString().toByteArray(Charsets.UTF_8)
        val encrypted = cipher.doFinal(raw)
        check(prefs.edit().putString("credential", Base64.encodeToString(encrypted, Base64.NO_WRAP))
            .putString("iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP)).commit())
    }
    fun clear() { check(prefs.edit().clear().commit()) }
}

internal fun checkedServerUrl(value: String): String {
    val url = URI(value.trim().trimEnd('/'))
    require(url.userInfo == null && url.query == null && url.fragment == null && url.path.orEmpty().isEmpty()) { "서버 기본 주소만 입력해 주세요." }
    val debugLoopback = BuildConfig.DEBUG && url.host in setOf("127.0.0.1", "10.0.2.2")
    require(!url.host.isNullOrBlank() && (url.scheme == "https" ||
        (url.scheme == "http" && (url.host == "100.74.204.80" || debugLoopback)))) {
        "HTTPS 주소 또는 이 4090의 Tailscale 주소를 사용해 주세요."
    }
    require(url.port == -1 || url.port in 1..65535)
    return url.toASCIIString()
}
