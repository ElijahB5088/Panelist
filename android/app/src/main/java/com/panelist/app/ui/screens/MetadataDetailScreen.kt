package com.panelist.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.rememberScrollState
import com.panelist.app.data.model.MetadataResult
import com.panelist.app.data.model.MetadataGroup
import com.panelist.app.data.session.SessionStore

@Composable
fun MetadataDetailScreen(group: MetadataGroup, sessionStore: SessionStore? = null, onBack: () -> Unit) {
    val preferredSource = sessionStore?.preferredSource()
    var selectedSource by remember(group.id, preferredSource) { mutableStateOf(group.preferred(preferredSource).source) }
    val result = group.variants.firstOrNull { it.source == selectedSource } ?: group.primary
    Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        IconButton(onClick = onBack) {
            Icon(Icons.Outlined.ArrowBack, contentDescription = "Back")
        }
        if (group.variants.size > 1) {
            Text("Versions", style = MaterialTheme.typography.titleMedium)
            Row(modifier = Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                group.variants.forEach { variant ->
                    FilterChip(
                        selected = variant.source == result.source,
                        onClick = { selectedSource = variant.source },
                        label = { Text(variant.source) }
                    )
                }
            }
        }
        Surface(shape = RoundedCornerShape(24.dp), tonalElevation = 2.dp) {
            Column(modifier = Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(result.title, style = MaterialTheme.typography.headlineLarge)
                Text(result.creator ?: "Creator unknown", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.titleMedium)
                Text(listOfNotNull(result.publisher, result.release_date).joinToString("  /  "), color = MaterialTheme.colorScheme.onSurfaceVariant)
                result.rating?.let { Text("Rating ${"%.1f".format(it)} / 10", style = MaterialTheme.typography.labelLarge) }
                result.genres.takeIf { it.isNotEmpty() }?.let { Text(it.joinToString("  /  "), style = MaterialTheme.typography.labelLarge) }
                result.description?.let { Text(it.replace(Regex("<[^>]*>"), ""), style = MaterialTheme.typography.bodyLarge) }
                Text("Source: ${result.source}", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelLarge)
                androidx.compose.material3.Button(
                    onClick = { sessionStore?.savePreferredSource(result.source) },
                    enabled = sessionStore != null
                ) { Text(if (preferredSource == result.source) "Preferred copy" else "Use this copy by default") }
            }
        }
    }
}