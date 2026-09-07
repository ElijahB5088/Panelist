package com.panelist.app.data.model

data class LibraryItem(
    val id: String,
    val media_id: String? = null,
    val source: String? = null,
    val library_media_type: String? = null,
    val status: String?,
    val progress: Int?,
    val progress_max: Int? = null,
    val progress_unit: String? = null,
    val progress_scope: String? = null,
    val progress_percent: Int? = null,
    val user_rating: Double?,
    val title: String,
    val creator: String? = null,
    val genres: List<String>,
    val rating: Double?,
    val image_url: String? = null,
    val source_url: String? = null
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
    val sync_error: String?,
    val auto_sync_enabled: Boolean = false,
    val auto_sync_interval_minutes: Int = 60,
    val next_sync_at: String? = null
)

data class FloppyConfig(val server_url: String, val api_token: String)

data class KitsuConfig(val server_url: String = "https://kitsu.io", val api_token: String)

data class MALAuthorizeResponse(val authorization_url: String)

data class FloppyConnectionResponse(
    val connected: Boolean,
    val server_url: String? = null,
    val error: String? = null
)

data class FloppySyncSettings(
    val enabled: Boolean,
    val interval_minutes: Int = 60,
    val next_sync_at: String? = null
)

data class SyncStatus(val sync_status: String, val last_sync: String? = null, val error: String? = null)