package com.nextpanel.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun DiscoverScreen() {
    Column(modifier = Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Discover", style = MaterialTheme.typography.headlineLarge)
        Text("Search the catalog when you want to browse beyond your picks.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text("Search comics, manga, and graphic novels", modifier = Modifier.padding(top = 16.dp), style = MaterialTheme.typography.titleMedium)
        Text("Popular right now", style = MaterialTheme.typography.headlineSmall)
        Text("Saga  •  Monstress  •  Descender", style = MaterialTheme.typography.bodyLarge)
    }
}
