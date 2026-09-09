package com.panelist.app.data.repository

import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.Recommendation

open class RecommendationRepository(private val api: PanelistApi) {
    open suspend fun recommendedForYou(): List<Recommendation> = api.recommendations()

    open suspend fun recommendedForYou(mediaType: String): List<Recommendation> =
        api.recommendations(mediaType = mediaType)

    open suspend fun like(mediaId: String) {
        api.like(mediaId)
    }

    open suspend fun dismiss(mediaId: String) {
        api.dismiss(mediaId)
    }
}
