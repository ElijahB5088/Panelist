package com.panelist.app.data.model

data class Credentials(
    val username: String,
    val password: String
)

data class AuthResponse(
    val access_token: String
)

data class FeedbackResponse(
    val ok: Boolean
)