package com.panelist.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.layout.size
import androidx.compose.material3.FilterChip
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Search
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import coil.compose.SubcomposeAsyncImage
import com.panelist.app.data.model.LibraryItem
import com.panelist.app.data.repository.LibraryRepository

@Composable
fun LibraryScreen(repository: LibraryRepository? = null, onOpenItem: (LibraryItem) -> Unit = {}) {
    val statuses = listOf("all", "reading", "completed", "planned", "dropped", "rated")
    val sorts = listOf(
        "title_asc" to "Title A-Z",
        "title_desc" to "Title Z-A",
        "rating_desc" to "Highest rated",
        "rating_asc" to "Lowest rated",
        "progress_desc" to "Most progress",
        "progress_asc" to "Least progress",
        "added_desc" to "Recently added"
    )
    var selectedStatus by remember { mutableStateOf(statuses.first()) }
    var selectedSort by remember { mutableStateOf(sorts.first().first) }
    var sortMenuExpanded by remember { mutableStateOf(false) }
    var query by remember { mutableStateOf("") }
    var isGridView by remember { mutableStateOf(false) }
    var items by remember { mutableStateOf<List<LibraryItem>>(emptyList()) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(selectedStatus, selectedSort, repository) {
        if (repository == null) return@LaunchedEffect
        loading = true
        error = null
        runCatching { repository.library(selectedStatus.takeUnless { it == "all" }, selectedSort) }
            .onSuccess { items = it }
            .onFailure { error = "Your library is unavailable right now." }
        loading = false
    }

    val normalizedQuery = query.trim().lowercase()
    val displayedItems = if (normalizedQuery.isEmpty()) {
        items
    } else {
        items.filter { item ->
            listOfNotNull(item.title, item.creator)
                .plus(item.genres)
                .any { value -> value.lowercase().contains(normalizedQuery) }
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Your library", style = MaterialTheme.typography.headlineLarge)
        Text("A quick view of what you are reading and keeping close.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Search your library") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            trailingIcon = {
                if (query.isNotEmpty()) {
                    IconButton(onClick = { query = "" }) {
                        Icon(Icons.Default.Clear, contentDescription = "Clear search")
                    }
                }
            },
            singleLine = true
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
            statuses.forEach { status ->
                FilterChip(selected = selectedStatus == status, onClick = { selectedStatus = status }, label = { Text(status.replaceFirstChar { it.uppercase() }) })
            }
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Box {
                val selectedSortLabel = sorts.first { it.first == selectedSort }.second
                TextButton(onClick = { sortMenuExpanded = true }) {
                    Text("Sort: $selectedSortLabel")
                }
                DropdownMenu(expanded = sortMenuExpanded, onDismissRequest = { sortMenuExpanded = false }) {
                    sorts.forEach { (sort, label) ->
                        DropdownMenuItem(
                            text = { Text(label) },
                            onClick = {
                                selectedSort = sort
                                sortMenuExpanded = false
                            }
                        )
                    }
                }
            }
            Row {
                TextButton(onClick = { isGridView = false }) {
                    Text("List", color = if (!isGridView) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant)
                }
                TextButton(onClick = { isGridView = true }) {
                    Text("Grid", color = if (isGridView) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        when {
            loading -> Text("Loading your library...", style = MaterialTheme.typography.bodyLarge)
            error != null -> Text(error!!, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodyLarge)
            items.isEmpty() -> EmptyLibraryStatus(selectedStatus)
            displayedItems.isEmpty() -> EmptyLibrarySearchStatus()
            isGridView -> LazyVerticalGrid(
                columns = GridCells.Adaptive(minSize = 150.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(displayedItems, key = { it.id }) { LibraryGridCard(it, onOpenItem) }
            }
            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(displayedItems, key = { it.id }) { LibraryRow(it, onOpenItem) }
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
private fun LibraryGridCard(item: LibraryItem, onOpenItem: (LibraryItem) -> Unit) {
    Surface(
        tonalElevation = 2.dp,
        modifier = Modifier.fillMaxWidth().clickable { onOpenItem(item) }
    ) {
        Column {
            Surface(
                color = MaterialTheme.colorScheme.surfaceVariant,
                modifier = Modifier.fillMaxWidth().height(190.dp)
            ) {
                SubcomposeAsyncImage(
                    model = item.image_url,
                    contentDescription = "Cover for ${item.title}",
                    contentScale = ContentScale.Crop,
                    loading = { LibraryCoverFallback(item) },
                    error = { LibraryCoverFallback(item) }
                )
            }
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(item.title, style = MaterialTheme.typography.titleMedium, maxLines = 2)
                Text(item.creator ?: "Creator unavailable", color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
                val progressLabel = item.progress_percent?.let { "$it% progress" }
                    ?: item.progress?.let { "${"%,d".format(it)} ${item.progress_unit ?: "items"}" }
                    ?: "Progress unavailable"
                Text(progressLabel, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
            }
        }
    }
}

@Composable
private fun LibraryCoverFallback(item: LibraryItem) {
    Box(modifier = Modifier.fillMaxSize().padding(12.dp)) {
        Text(item.title.take(1).uppercase(), style = MaterialTheme.typography.displaySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
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

@Composable
private fun EmptyLibrarySearchStatus() {
    Surface(tonalElevation = 2.dp, modifier = Modifier.fillMaxWidth()) {
        Text("No library items match your search.", modifier = Modifier.padding(22.dp), style = MaterialTheme.typography.bodyLarge)
    }
}
