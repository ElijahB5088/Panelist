package com.panelist.app.data.session

import android.content.Context

class SessionStore(context: Context) {
    private val preferences = context.getSharedPreferences("panelist_session", Context.MODE_PRIVATE)

    fun token(): String? = preferences.getString(KEY_TOKEN, null)

    fun saveToken(token: String) {
        preferences.edit().putString(KEY_TOKEN, token).apply()
    }

    fun clear() {
        preferences.edit().remove(KEY_TOKEN).apply()
    }

    companion object {
        private const val KEY_TOKEN = "access_token"
    }
}