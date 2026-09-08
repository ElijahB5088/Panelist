package com.panelist.app.data.repository

import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.LibraryItem

class LibraryRepository(private val api: PanelistApi) {
    suspend fun library(status: String? = null, sort: String = "title_asc"): List<LibraryItem> = api.library(status, sort)
}