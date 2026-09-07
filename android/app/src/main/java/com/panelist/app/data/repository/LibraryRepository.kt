package com.panelist.app.data.repository

import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.LibraryItem

class LibraryRepository(private val api: PanelistApi) {
    suspend fun library(status: String? = null): List<LibraryItem> = api.library(status)
}