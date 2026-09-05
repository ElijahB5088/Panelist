package com.panelist.app.data.model

data class LibraryItem(
    val id: String,
    val status: String?,
    val progress: Int?,
    val user_rating: Double?,
    val title: String,
    val creator: String,
    val genres: List<String>,
    val rating: Double?
)

data class ProfileResponse(
    val user: ProfileUser,
    val connected_tracker: ConnectedTracker?
)

data class ProfileUser(val id: Int, val username: String)

data class ConnectedTracker(
    val provider: String,
    val server_url: String,
    val connected: Boolean,
    val last_sync: String?,
    val sync_status: String?,
    val sync_error: String?
)

data class FloppyConfig(val server_url: String, val api_token: String)

data class FloppyConnectionResponse(val connected: Boolean, val server_url: String? = null)

data class SyncStatus(val sync_status: String, val last_sync: String? = null, val error: String? = null)