package com.panelist.app.data.repository

import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.Recommendation

class RecommendationRepository(private val api: PanelistApi) {
    suspend fun recommendedForYou(): List<Recommendation> = api.recommendations()

    suspend fun recommendedForYou(mediaType: String): List<Recommendation> =
        api.recommendations(mediaType = mediaType)

    suspend fun like(mediaId: String) {
        api.like(mediaId)
    }

    suspend fun dismiss(mediaId: String) {
        api.dismiss(mediaId)
    }
}
