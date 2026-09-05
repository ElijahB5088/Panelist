package com.panelist.app.ui.screens

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
fun LibraryScreen() {
    Column(modifier = Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Your library", style = MaterialTheme.typography.headlineLarge)
        Text("Everything you are reading, finished, or saving for later.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text("Reading   Completed   Planned   Dropped   Rated", modifier = Modifier.padding(top = 16.dp), style = MaterialTheme.typography.labelLarge)
        Text("Your synced library will appear here.", style = MaterialTheme.typography.headlineSmall)
        Text("Connect Floppy from Profile to bring your reading history into Panelist.", style = MaterialTheme.typography.bodyLarge)
    }
}
