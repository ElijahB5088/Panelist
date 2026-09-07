package com.panelist.app.data.repository

import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.MetadataGroup

class MetadataRepository(private val api: PanelistApi) {
    suspend fun search(query: String): List<MetadataGroup> = api.metadataSearch(query)

    suspend fun featured(surface: String): List<MetadataGroup> = api.featured(surface)
}