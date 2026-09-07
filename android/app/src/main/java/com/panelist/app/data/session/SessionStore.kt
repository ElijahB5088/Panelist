package com.panelist.app.data.session

import android.content.Context

class SessionStore(context: Context) {
    private val preferences = context.getSharedPreferences("panelist_session", Context.MODE_PRIVATE)

    fun token(): String? = preferences.getString(KEY_TOKEN, null)

    fun serverUrl(): String? = preferences.getString(KEY_SERVER_URL, null)

    fun preferredSource(): String? = preferences.getString(KEY_PREFERRED_SOURCE, null)

    fun saveServerUrl(url: String) {
        preferences.edit().putString(KEY_SERVER_URL, url).apply()
    }

    fun saveToken(token: String) {
        preferences.edit().putString(KEY_TOKEN, token).apply()
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
    }
}