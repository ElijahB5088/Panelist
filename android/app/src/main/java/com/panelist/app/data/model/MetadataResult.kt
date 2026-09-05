package com.panelist.app.data.model

data class MetadataResult(
    val source: String,
    val source_id: String,
    val title: String,
    val creator: String?,
    val genres: List<String>,
    val publisher: String?,
    val description: String?,
    val rating: Double?,
    val release_date: String?,
    val image_url: String?,
    val source_url: String?
)