package com.panelist.app.data.session

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.nio.charset.StandardCharsets
import java.security.GeneralSecurityException
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class SessionStore(context: Context) {
    private val preferences = context.getSharedPreferences("panelist_session", Context.MODE_PRIVATE)

    fun token(): String? {
        val stored = preferences.getString(KEY_TOKEN, null) ?: return null
        return try {
            if (!stored.contains(DELIMITER)) {
                saveToken(stored)
                stored
            } else {
                decrypt(stored)
            }
        } catch (_: GeneralSecurityException) {
            preferences.edit().remove(KEY_TOKEN).apply()
            null
        } catch (_: IllegalArgumentException) {
            preferences.edit().remove(KEY_TOKEN).apply()
            null
        }
    }

    fun serverUrl(): String? = preferences.getString(KEY_SERVER_URL, null)

    fun preferredSource(): String? = preferences.getString(KEY_PREFERRED_SOURCE, null)

    fun saveServerUrl(url: String) {
        preferences.edit().putString(KEY_SERVER_URL, url).apply()
    }

    fun saveToken(token: String) {
        preferences.edit().putString(KEY_TOKEN, encrypt(token)).apply()
    }

    fun savePreferredSource(source: String?) {
        preferences.edit().apply {
            if (source.isNullOrBlank()) remove(KEY_PREFERRED_SOURCE) else putString(KEY_PREFERRED_SOURCE, source)
        }.apply()
    }

    fun clear() {
        preferences.edit().remove(KEY_TOKEN).apply()
    }

    companion object {
        private const val KEY_TOKEN = "access_token"
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_PREFERRED_SOURCE = "preferred_metadata_source"
        private const val KEY_ALIAS = "panelist_session_key"
        private const val DELIMITER = ":"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
    }

    private fun key(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = keyStore.getKey(KEY_ALIAS, null)
        if (existing is SecretKey) return existing
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .build()
        )
        return generator.generateKey()
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encodedIv = Base64.encodeToString(cipher.iv, Base64.NO_WRAP)
        val encodedValue = Base64.encodeToString(
            cipher.doFinal(value.toByteArray(StandardCharsets.UTF_8)),
            Base64.NO_WRAP
        )
        return "$encodedIv$DELIMITER$encodedValue"
    }

    private fun decrypt(value: String): String {
        val parts = value.split(DELIMITER, limit = 2)
        require(parts.size == 2)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            key(),
            GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP))
        )
        return String(
            cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)),
            StandardCharsets.UTF_8
        )
    }
}