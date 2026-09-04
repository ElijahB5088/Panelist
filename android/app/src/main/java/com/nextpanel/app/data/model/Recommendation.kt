package com.nextpanel.app.data.model

data class Recommendation(
    val id: String,
    val title: String,
    val creator: String,
    val genres: List<String>,
    val rating: Double?,
    val description: String?,
    val why: String
)
