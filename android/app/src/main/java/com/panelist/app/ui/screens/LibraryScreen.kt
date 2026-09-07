package com.panelist.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import com.panelist.app.data.model.LibraryItem
import com.panelist.app.data.repository.LibraryRepository

@Composable
fun LibraryScreen(repository: LibraryRepository? = null) {
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
                items(items, key = { it.id }) { LibraryRow(it) }
            }
        }
    }
}

@Composable
private fun LibraryRow(item: LibraryItem) {
    Surface(tonalElevation = 2.dp, modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(item.title, style = MaterialTheme.typography.titleMedium)
            Text(item.creator, color = MaterialTheme.colorScheme.primary)
            Text("${item.progress ?: 0}% progress  /  ${item.user_rating?.let { "Your rating ${"%.1f".format(it)}" } ?: "Not rated"}", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
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
