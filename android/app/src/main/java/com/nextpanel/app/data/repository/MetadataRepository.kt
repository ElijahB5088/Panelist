package com.nextpanel.app.data.repository

import com.nextpanel.app.data.api.NextPanelApi
import com.nextpanel.app.data.model.MetadataResult

class MetadataRepository(private val api: NextPanelApi) {
    suspend fun search(query: String): List<MetadataResult> = api.metadataSearch(query)
}