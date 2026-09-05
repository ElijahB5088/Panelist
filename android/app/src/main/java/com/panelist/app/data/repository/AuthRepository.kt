package com.panelist.app.data.repository

import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.Credentials
import com.panelist.app.data.session.SessionStore

class AuthRepository(
    private val api: PanelistApi,
    private val sessionStore: SessionStore
) {
    fun isAuthenticated(): Boolean = sessionStore.token() != null

    suspend fun login(username: String, password: String) {
        val response = api.login(Credentials(username, password))
        sessionStore.saveToken(response.access_token)
    }

    suspend fun register(username: String, password: String) {
        api.register(Credentials(username, password))
        login(username, password)
    }

    fun logout() = sessionStore.clear()
}