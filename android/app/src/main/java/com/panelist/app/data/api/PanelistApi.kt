package com.panelist.app.data.api

import com.panelist.app.data.model.Recommendation
import com.panelist.app.data.model.MetadataGroup
import com.panelist.app.data.model.AuthResponse
import com.panelist.app.data.model.Credentials
import com.panelist.app.data.model.FeedbackResponse
import com.panelist.app.data.model.FloppyConfig
import com.panelist.app.data.model.FloppyConnectionResponse
import com.panelist.app.data.model.KitsuConfig
import com.panelist.app.data.model.MALAuthorizeResponse
import com.panelist.app.data.model.LibraryItem
import com.panelist.app.data.model.ProfileResponse
import com.panelist.app.data.model.SyncStatus
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

data class HealthResponse(val status: String)

interface PanelistApi {
    @GET("/health")
    suspend fun health(): HealthResponse

    @POST("/api/auth/login")
    suspend fun login(@Body credentials: Credentials): AuthResponse

    @POST("/api/auth/register")
    suspend fun register(@Body credentials: Credentials): FeedbackResponse

    @GET("/api/recommendations")
    suspend fun recommendations(@Query("limit") limit: Int = 20): List<Recommendation>

    @POST("/api/recommendations/{mediaId}/like")
    suspend fun like(@Path("mediaId") mediaId: String): FeedbackResponse

    @POST("/api/recommendations/{mediaId}/dismiss")
    suspend fun dismiss(@Path("mediaId") mediaId: String): FeedbackResponse

    @GET("/api/metadata/search")
    suspend fun metadataSearch(
        @Query("q") query: String,
        @Query("limit") limit: Int = 10
    ): List<MetadataGroup>

    @GET("/api/featured")
    suspend fun featured(
        @Query("surface") surface: String,
        @Query("limit") limit: Int = 10
    ): List<MetadataGroup>

    @GET("/api/library")
    suspend fun library(@Query("status") status: String? = null): List<LibraryItem>

    @GET("/api/profile")
    suspend fun profile(): ProfileResponse

    @POST("/api/integrations/floppy/test")
    suspend fun testFloppy(@Body config: FloppyConfig): FloppyConnectionResponse

    @POST("/api/integrations/floppy")
    suspend fun connectFloppy(@Body config: FloppyConfig): FloppyConnectionResponse

    @POST("/api/integrations/kitsu/test")
    suspend fun testKitsu(@Body config: KitsuConfig): FloppyConnectionResponse

    @POST("/api/integrations/kitsu")
    suspend fun connectKitsu(@Body config: KitsuConfig): FloppyConnectionResponse

    @POST("/api/integrations/mal/authorize")
    suspend fun authorizeMAL(): MALAuthorizeResponse

    @POST("/api/sync")
    suspend fun sync(): FeedbackResponse

    @GET("/api/sync/status")
    suspend fun syncStatus(): SyncStatus
}
