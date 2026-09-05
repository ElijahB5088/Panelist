package com.panelist.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.panelist.app.data.model.FloppyConfig
import com.panelist.app.data.model.ProfileResponse
import com.panelist.app.data.repository.ProfileRepository
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen(repository: ProfileRepository? = null) {
    val scope = rememberCoroutineScope()
    var profile by remember { mutableStateOf<ProfileResponse?>(null) }
    var serverUrl by remember { mutableStateOf("") }
    var token by remember { mutableStateOf("") }
    var status by remember { mutableStateOf<String?>(null) }
    var syncStatus by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(repository) {
        if (repository != null) runCatching { repository.profile() }.onSuccess { loaded ->
            profile = loaded
            serverUrl = loaded.connected_tracker?.server_url.orEmpty()
        }
    }

    val tracker = profile?.connected_tracker
    Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Profile", style = MaterialTheme.typography.headlineLarge)
        Text(profile?.user?.username?.let { "Signed in as $it" } ?: "Your account and tracker connection", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Surface(tonalElevation = 2.dp, modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Tracker connection", style = MaterialTheme.typography.headlineSmall)
                Text(if (tracker?.connected == true) "Floppy connected" else "Floppy is not connected", color = MaterialTheme.colorScheme.primary)
                tracker?.last_sync?.let { Text("Last sync: $it", style = MaterialTheme.typography.bodyLarge) }
                tracker?.sync_error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                syncStatus?.let { Text("Sync status: $it", style = MaterialTheme.typography.labelLarge) }
                OutlinedTextField(serverUrl, { serverUrl = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Floppy server URL") }, singleLine = true)
                OutlinedTextField(token, { token = it }, modifier = Modifier.fillMaxWidth(), label = { Text("API token") }, visualTransformation = PasswordVisualTransformation(), singleLine = true)
                Button(
                    enabled = repository != null && serverUrl.isNotBlank() && token.isNotBlank() && !busy,
                    onClick = {
                        val activeRepository = repository ?: return@Button
                        scope.launch {
                            busy = true
                            status = runCatching {
                                val config = FloppyConfig(serverUrl.trim(), token)
                                if (!activeRepository.test(config)) error("Connection test failed")
                                activeRepository.connect(config)
                                "Floppy connected."
                            }.getOrElse { it.message ?: "Connection failed." }
                            busy = false
                        }
                    }
                ) { Text(if (busy) "Connecting..." else "Test and connect") }
                Button(
                    enabled = repository != null && tracker?.connected == true && !busy,
                    onClick = {
                        val activeRepository = repository ?: return@Button
                        scope.launch {
                            busy = true
                            status = runCatching {
                                activeRepository.sync()
                                syncStatus = activeRepository.syncStatus().sync_status
                                "Sync started."
                            }.getOrElse { it.message ?: "Sync failed." }
                            busy = false
                        }
                    }
                ) { Text("Sync library") }
                status?.let { Text(it, style = MaterialTheme.typography.bodyLarge) }
            }
        }
    }
}
