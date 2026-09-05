package com.panelist.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.panelist.app.data.model.MetadataResult

@Composable
fun MetadataDetailScreen(result: MetadataResult, onBack: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        IconButton(onClick = onBack) {
            Icon(Icons.Outlined.ArrowBack, contentDescription = "Back")
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
            }
        }
    }
}