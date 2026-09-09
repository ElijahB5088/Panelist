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
) : java.io.Serializable

data class MetadataGroup(
    val id: String,
    val primary: MetadataResult,
    val variants: List<MetadataResult>
) : java.io.Serializable {
    fun preferred(preferredSource: String? = null): MetadataResult =
        variants.firstOrNull { it.source == preferredSource } ?: primary
}