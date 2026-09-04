package com.nextpanel.app.data.repository

import com.nextpanel.app.data.api.NextPanelApi
import com.nextpanel.app.data.model.Recommendation

class RecommendationRepository(private val api: NextPanelApi) {
    suspend fun recommendedForYou(): List<Recommendation> = api.recommendations()
}
