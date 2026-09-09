package com.panelist.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp
import androidx.compose.ui.layout.ContentScale
import coil.compose.SubcomposeAsyncImage
import androidx.compose.foundation.rememberScrollState
import com.panelist.app.data.model.MetadataResult
import com.panelist.app.data.model.MetadataGroup
import com.panelist.app.data.session.SessionStore

@Composable
fun MetadataDetailScreen(group: MetadataGroup, sessionStore: SessionStore? = null, onBack: () -> Unit) {
    var preferredSource by remember { mutableStateOf(sessionStore?.preferredSource()) }
    val preferredVariant = group.preferred(preferredSource)
    var selectedVariantKey by remember(group.id, preferredSource) {
        mutableStateOf(variantKey(preferredVariant.source, preferredVariant.source_id))
    }
    val result = group.variants.firstOrNull {
        variantKey(it.source, it.source_id) == selectedVariantKey
    } ?: group.primary
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        IconButton(onClick = onBack) {
            Icon(Icons.Outlined.ArrowBack, contentDescription = "Back")
        }
        if (group.variants.size > 1) {
            Text("Versions", style = MaterialTheme.typography.titleMedium)
            Row(modifier = Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                group.variants.forEach { variant ->
                    FilterChip(
                        selected = variantKey(variant.source, variant.source_id) == selectedVariantKey,
                        onClick = { selectedVariantKey = variantKey(variant.source, variant.source_id) },
                        label = { Text(variant.source) }
                    )
                }
            }
        }
        Surface(shape = RoundedCornerShape(24.dp), tonalElevation = 2.dp) {
            Column(modifier = Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                SubcomposeAsyncImage(
                    model = result.image_url,
                    contentDescription = "Cover for ${result.title}",
                    modifier = Modifier.fillMaxWidth().height(260.dp),
                    contentScale = ContentScale.Crop,
                    loading = { MetadataCoverFallback(result) },
                    error = { MetadataCoverFallback(result) }
                )
                Text(result.title, style = MaterialTheme.typography.headlineLarge)
                Text("Showing ${result.source}", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelLarge)
                Text(result.creator ?: "Creator unknown", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.titleMedium)
                Text(listOfNotNull(result.publisher, result.release_date).joinToString("  /  "), color = MaterialTheme.colorScheme.onSurfaceVariant)
                result.rating?.let { Text("Rating ${"%.1f".format(it)} / 10", style = MaterialTheme.typography.labelLarge) }
                result.genres.takeIf { it.isNotEmpty() }?.let { Text(it.joinToString("  /  "), style = MaterialTheme.typography.labelLarge) }
                Text(
                    result.description?.replace(Regex("<[^>]*>"), "")
                        ?.takeIf { it.isNotBlank() }
                        ?: "No description is available from this source.",
                    style = MaterialTheme.typography.bodyLarge
                )
                Text("Source: ${result.source}", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelLarge)
                androidx.compose.material3.Button(
                    onClick = {
                        preferredSource = result.source
                        sessionStore?.savePreferredSource(result.source)
                    },
                    enabled = sessionStore != null
                ) { Text(if (preferredSource == result.source) "Preferred copy" else "Use this copy by default") }
            }
        }
    }
}

@Composable
private fun MetadataCoverFallback(result: MetadataResult) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.primaryContainer),
        contentAlignment = Alignment.Center
    ) {
        Text(
            result.title.take(1).uppercase(),
            color = MaterialTheme.colorScheme.onPrimaryContainer,
            style = MaterialTheme.typography.displayLarge
        )
    }
}

private fun variantKey(source: String, sourceId: String): String = "$source:$sourceId"