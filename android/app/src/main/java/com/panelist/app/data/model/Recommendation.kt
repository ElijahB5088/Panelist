package com.panelist.app.data.model

data class Recommendation(
    val id: String,
    val title: String,
    val creator: String?,
    val genres: List<String>,
    val rating: Double?,
    val description: String?,
    val why: String,
    val source: String? = null,
    val source_id: String? = null,
    val image_url: String? = null,
    val source_url: String? = null,
    val media_type: String? = null,
    val release_date: String? = null
)
