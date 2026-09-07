package com.panelist.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.layout.size
import androidx.compose.material3.FilterChip
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
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.panelist.app.data.model.LibraryItem
import com.panelist.app.data.repository.LibraryRepository

@Composable
fun LibraryScreen(repository: LibraryRepository? = null, onOpenItem: (LibraryItem) -> Unit = {}) {
    val statuses = listOf("all", "reading", "completed", "planned", "dropped", "rated")
    var selectedStatus by remember { mutableStateOf(statuses.first()) }
    var items by remember { mutableStateOf<List<LibraryItem>>(emptyList()) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(selectedStatus, repository) {
        if (repository == null) return@LaunchedEffect
        loading = true
        error = null
        runCatching { repository.library(selectedStatus.takeUnless { it == "all" }) }
            .onSuccess { items = it }
            .onFailure { error = "Your library is unavailable right now." }
        loading = false
    }

    Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Your library", style = MaterialTheme.typography.headlineLarge)
        Text("A quick view of what you are reading and keeping close.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
            statuses.forEach { status ->
                FilterChip(selected = selectedStatus == status, onClick = { selectedStatus = status }, label = { Text(status.replaceFirstChar { it.uppercase() }) })
            }
        }
        when {
            loading -> Text("Loading your library...", style = MaterialTheme.typography.bodyLarge)
            error != null -> Text(error!!, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodyLarge)
            items.isEmpty() -> EmptyLibraryStatus(selectedStatus)
            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(items, key = { it.id }) { LibraryRow(it, onOpenItem) }
            }
        }
    }
}

@Composable
private fun LibraryRow(item: LibraryItem, onOpenItem: (LibraryItem) -> Unit) {
    Surface(tonalElevation = 2.dp, modifier = Modifier.fillMaxWidth().clickable { onOpenItem(item) }) {
        Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            AsyncImage(
                model = item.image_url,
                contentDescription = item.title,
                modifier = Modifier.size(56.dp)
            )
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(item.title, style = MaterialTheme.typography.titleMedium)
                Text(item.creator ?: "Creator unavailable", color = MaterialTheme.colorScheme.onSurfaceVariant)
                val progressLabel = item.progress_percent?.let { "$it% progress" }
                    ?: item.progress?.let { "${"%,d".format(it)} ${item.progress_unit ?: "items"}" }
                    ?: "Progress unavailable"
                Text("$progressLabel  /  ${item.user_rating?.let { "Your rating ${"%.1f".format(it)}" } ?: "Not rated"}", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
fun LibraryDetailScreen(item: LibraryItem, onBack: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Back", modifier = Modifier.clickable(onClick = onBack), color = MaterialTheme.colorScheme.primary)
        AsyncImage(
            model = item.image_url,
            contentDescription = item.title,
            modifier = Modifier.size(180.dp)
        )
        Text(item.title, style = MaterialTheme.typography.headlineLarge)
        item.creator?.let { Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        item.rating?.let { Text("Rating ${"%.1f".format(it)} / 10") }
        item.progress_percent?.let { Text("Progress $it%") }
            ?: item.progress?.let { Text("Progress ${"%,d".format(it)} ${item.progress_unit ?: "items"}") }
        Text("${item.source ?: "Unknown source"} / ${item.library_media_type ?: "media"} / ${item.media_id ?: item.id}", color = MaterialTheme.colorScheme.onSurfaceVariant)
        item.genres.takeIf { it.isNotEmpty() }?.let { Text(it.joinToString("  / ")) }
    }
}

@Composable
private fun EmptyLibraryStatus(status: String) {
    Surface(tonalElevation = 2.dp, modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(if (status == "all") "Your library is empty." else "Nothing ${status} yet.", style = MaterialTheme.typography.headlineSmall)
            Text("Sync your tracker from Profile to bring this shelf into Panelist.", style = MaterialTheme.typography.bodyLarge)
        }
    }
}
