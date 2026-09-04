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
fun ProfileScreen() {
    Column(modifier = Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Profile", style = MaterialTheme.typography.headlineLarge)
        Text("Your account, taste profile, and tracker connection.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text("Tracker connection", modifier = Modifier.padding(top = 16.dp), style = MaterialTheme.typography.headlineSmall)
        Text("Floppy is not connected", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
        Text("Connect your self-hosted tracker to sync your library and get personal recommendations.", style = MaterialTheme.typography.bodyLarge)
        Text("Connect Floppy", modifier = Modifier.padding(top = 8.dp), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
    }
}
