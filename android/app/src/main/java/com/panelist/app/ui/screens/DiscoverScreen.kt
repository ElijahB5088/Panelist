package com.panelist.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.layout.ContentScale
import coil.compose.SubcomposeAsyncImage
import kotlinx.coroutines.delay
import com.panelist.app.data.model.MetadataGroup
import com.panelist.app.data.model.MetadataResult
import com.panelist.app.data.repository.MetadataRepository
import com.panelist.app.data.session.SessionStore

@Composable
fun DiscoverScreen(
    repository: MetadataRepository? = null,
    sessionStore: SessionStore? = null,
    onOpenDetail: (MetadataGroup) -> Unit = {}
) {
    var query by remember { mutableStateOf("") }
    var selectedSource by remember { mutableStateOf("All") }
    var results by remember { mutableStateOf(demoMetadata.map { MetadataGroup(it.source + it.source_id, it, listOf(it)) }) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(query, repository) {
        delay(350)
        if (query.trim().length < 2 || repository == null) {
                results = demoMetadata.map { MetadataGroup(it.source + it.source_id, it, listOf(it)) }
            isLoading = false
            errorMessage = null
        } else {
            isLoading = true
            errorMessage = null
            runCatching { repository.search(query.trim()) }
                .onSuccess { results = it }
                .onFailure { errorMessage = "Metadata search is unavailable right now." }
            isLoading = false
        }
    }
    val preferredSource = sessionStore?.preferredSource()
    val filteredResults = results.filter { group ->
        val matchesSource = selectedSource == "All" || group.variants.any { it.source == selectedSource }
        matchesSource
    }

    Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Discover", style = MaterialTheme.typography.headlineLarge)
        Text("Search across comic, book, and manga catalogs.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
            label = { Text("Search titles or creators") },
            singleLine = true
        )
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("All", "comicvine", "openlibrary", "anilist").forEach { source ->
                FilterChip(
                    selected = selectedSource == source,
                    onClick = { selectedSource = source },
                    label = { Text(source) }
                )
            }
        }
        when {
            isLoading -> Text("Searching metadata sources...", style = MaterialTheme.typography.bodyLarge)
            errorMessage != null -> Text(errorMessage!!, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.primary)
            else -> Text("${filteredResults.size} results", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (!isLoading && errorMessage == null && filteredResults.isEmpty()) {
            Surface(shape = RoundedCornerShape(18.dp), tonalElevation = 2.dp) {
                Text("No matching titles yet. Try a broader search.", modifier = Modifier.padding(20.dp), style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(filteredResults, key = { it.id }) { group ->
                    MetadataCard(group.preferred(if (selectedSource == "All") preferredSource else selectedSource), group.variants.size, onClick = { onOpenDetail(group) })
                }
            }
        }
    }
}

@Composable
private fun MetadataCard(result: MetadataResult, variantCount: Int, onClick: () -> Unit) {
    Surface(shape = RoundedCornerShape(18.dp), tonalElevation = 2.dp, modifier = Modifier.clickable(onClick = onClick)) {
        Row(modifier = Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.Top) {
            val accent = when (result.source) {
                "comicvine" -> Color(0xFFB94632)
                "anilist" -> Color(0xFF415E55)
                else -> Color(0xFF3D5875)
            }
            Surface(shape = RoundedCornerShape(12.dp), color = accent, modifier = Modifier.size(width = 82.dp, height = 116.dp)) {
                SubcomposeAsyncImage(
                    model = result.image_url,
                    contentDescription = "Cover for ${result.title}",
                    contentScale = ContentScale.Crop,
                    loading = { CoverFallback(result, accent) },
                    error = { CoverFallback(result, accent) }
                )
            }
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(result.title, style = MaterialTheme.typography.titleMedium)
                if (variantCount > 1) Text("$variantCount versions", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelLarge)
                Text(result.creator ?: "Creator unknown", color = MaterialTheme.colorScheme.primary)
                Text(listOfNotNull(result.publisher, result.release_date).joinToString("  /  "), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                result.rating?.let { Text("Rating ${"%.1f".format(it)} / 10", style = MaterialTheme.typography.labelLarge) }
                result.genres.take(3).joinToString("  /  ").takeIf { it.isNotBlank() }?.let { Text(it, style = MaterialTheme.typography.bodyLarge) }
                result.description?.let { Text(it.replace(Regex("<[^>]*>"), "").take(120), style = MaterialTheme.typography.bodyLarge, maxLines = 2) }
            }
        }
    }
}

@Composable
private fun CoverFallback(result: MetadataResult, accent: Color) {
    Column(
        modifier = Modifier.fillMaxSize().background(accent),
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        Text(result.title.take(1).uppercase(), modifier = Modifier.padding(12.dp), color = Color.White, style = MaterialTheme.typography.headlineLarge)
        Text(result.source, modifier = Modifier.padding(8.dp), color = Color.White.copy(alpha = 0.78f), style = MaterialTheme.typography.labelLarge)
    }
}

private val demoMetadata = listOf(
    MetadataResult("comicvine", "4050", "Saga", "Brian K. Vaughan", listOf("Sci-fi", "Drama"), "Image", "A family crosses a war-torn galaxy.", 8.8, "2012-01-01", "https://example.com/saga.jpg", "https://comicvine.gamespot.com/saga/"),
    MetadataResult("comicvine", "4051", "Monstress", "Marjorie Liu", listOf("Fantasy", "Drama"), "Image", "A young woman shares a psychic link with a monster.", 8.7, "2015-01-01", "https://example.com/monstress.jpg", "https://comicvine.gamespot.com/monstress/"),
    MetadataResult("anilist", "30002", "Witch Hat Atelier", "Kamome Shirahama", listOf("Fantasy", "Adventure"), null, "A girl discovers that magic is drawn, not born.", 9.0, "2016-07-22", "https://example.com/witch-hat.jpg", "https://anilist.co/manga/100572"),
    MetadataResult("openlibrary", "OL123W", "The Sandman", "Neil Gaiman", listOf("Fantasy", "Comics"), "DC Comics", "Dreams, stories, and the cost of immortality.", 8.6, "1989-01-01", "https://example.com/sandman.jpg", "https://openlibrary.org/works/OL123W")
)
