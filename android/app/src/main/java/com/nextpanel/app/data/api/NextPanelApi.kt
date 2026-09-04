package com.nextpanel.app.data.api

import com.nextpanel.app.data.model.Recommendation
import com.nextpanel.app.data.model.MetadataResult
import retrofit2.http.GET
import retrofit2.http.Query

interface NextPanelApi {
    @GET("/api/recommendations")
    suspend fun recommendations(): List<Recommendation>

    @GET("/api/metadata/search")
    suspend fun metadataSearch(
        @Query("q") query: String,
        @Query("limit") limit: Int = 10
    ): List<MetadataResult>
}
