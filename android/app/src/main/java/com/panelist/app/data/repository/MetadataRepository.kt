package com.panelist.app.data.repository

import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.MetadataResult

class MetadataRepository(private val api: PanelistApi) {
    suspend fun search(query: String): List<MetadataResult> = api.metadataSearch(query)
}