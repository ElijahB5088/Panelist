package com.nextpanel.app.data.api

import com.nextpanel.app.data.model.Recommendation
import retrofit2.http.GET

interface NextPanelApi {
    @GET("/api/recommendations")
    suspend fun recommendations(): List<Recommendation>
}
