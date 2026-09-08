package com.panelist.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.panelist.app.data.model.FloppyConfig
import com.panelist.app.data.model.KitsuConfig
import com.panelist.app.data.model.ProfileResponse
import com.panelist.app.data.repository.ProfileRepository
import com.panelist.app.data.session.SessionStore
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen(repository: ProfileRepository? = null, sessionStore: SessionStore? = null) {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    var profile by remember { mutableStateOf<ProfileResponse?>(null) }
    var serverUrl by remember { mutableStateOf("") }
    var token by remember { mutableStateOf("") }
    var status by remember { mutableStateOf<String?>(null) }
    var syncStatus by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    var preferredSource by remember { mutableStateOf(sessionStore?.preferredSource()) }
    var trackerChoice by remember { mutableStateOf("floppy") }
    var connected by remember { mutableStateOf(false) }

    LaunchedEffect(repository) {
        if (repository != null) runCatching { repository.profile() }.onSuccess { loaded ->
            profile = loaded
            serverUrl = loaded.connected_tracker?.server_url.orEmpty()
            trackerChoice = loaded.connected_tracker?.provider ?: "floppy"
            connected = loaded.connected_tracker?.connected == true
            if (trackerChoice == "kitsu" && serverUrl.isBlank()) serverUrl = "https://kitsu.io"
        }
    }

    val tracker = profile?.connected_tracker
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Profile", style = MaterialTheme.typography.headlineLarge)
        Text(profile?.user?.username?.let { "Signed in as $it" } ?: "Your account and tracker connection", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Surface(tonalElevation = 2.dp, modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Tracker connection", style = MaterialTheme.typography.headlineSmall)
                Text(if (connected) "${trackerChoice.replaceFirstChar { it.uppercase() }} connected" else "${trackerChoice.replaceFirstChar { it.uppercase() }} is not connected", color = MaterialTheme.colorScheme.primary)
                tracker?.last_sync?.let { Text("Last sync: $it", style = MaterialTheme.typography.bodyLarge) }
                tracker?.sync_error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                syncStatus?.let { Text("Sync status: $it", style = MaterialTheme.typography.labelLarge) }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(selected = trackerChoice == "floppy", onClick = { trackerChoice = "floppy" }, label = { Text("Floppy") })
                    FilterChip(selected = trackerChoice == "kitsu", onClick = { trackerChoice = "kitsu"; if (serverUrl.isBlank()) serverUrl = "https://kitsu.io" }, label = { Text("Kitsu manga") })
                    FilterChip(selected = trackerChoice == "mal", onClick = { trackerChoice = "mal" }, label = { Text("MAL manga") })
                }
                if (trackerChoice == "mal") {
                    Button(
                        enabled = repository != null && !busy,
                        onClick = {
                            val activeRepository = repository ?: return@Button
                            scope.launch {
                                busy = true
                                status = runCatching {
                                    val authorizationUrl = activeRepository.authorizeMAL()
                                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(authorizationUrl)))
                                    "Complete MAL authorization in your browser, then refresh connection."
                                }.getOrElse { it.message ?: "Could not start MAL authorization." }
                                busy = false
                            }
                        }
                    ) { Text(if (busy) "Opening MAL..." else "Connect MAL") }
                    Button(
                        enabled = repository != null && !busy,
                        onClick = {
                            val activeRepository = repository ?: return@Button
                            scope.launch {
                                busy = true
                                status = runCatching {
                                    val loaded = activeRepository.profile()
                                    profile = loaded
                                    connected = loaded.connected_tracker?.connected == true
                                    "MAL connection refreshed."
                                }.getOrElse { it.message ?: "Could not refresh connection." }
                                busy = false
                            }
                        }
                    ) { Text("Refresh connection") }
                } else {
                    OutlinedTextField(serverUrl, { serverUrl = it }, modifier = Modifier.fillMaxWidth(), label = { Text("${trackerChoice.replaceFirstChar { it.uppercase() }} server URL") }, singleLine = true)
                    OutlinedTextField(token, { token = it }, modifier = Modifier.fillMaxWidth(), label = { Text("API token") }, visualTransformation = PasswordVisualTransformation(), singleLine = true)
                    Button(
                        enabled = repository != null && serverUrl.isNotBlank() && token.isNotBlank() && !busy,
                        onClick = {
                            val activeRepository = repository ?: return@Button
                            scope.launch {
                                busy = true
                                status = runCatching {
                                    val testResult = if (trackerChoice == "kitsu") {
                                        val config = KitsuConfig(serverUrl.trim(), token)
                                        val result = activeRepository.testKitsu(config)
                                        if (result.connected) activeRepository.connectKitsu(config)
                                        result
                                    } else {
                                        val config = FloppyConfig(serverUrl.trim(), token)
                                        val result = activeRepository.test(config)
                                        if (result.connected) activeRepository.connect(config)
                                        result
                                    }
                                    if (!testResult.connected) error(testResult.error ?: "Connection test failed")
                                    connected = true
                                    "${trackerChoice.replaceFirstChar { it.uppercase() }} connected."
                                }.getOrElse { it.message ?: "Connection failed." }
                                busy = false
                            }
                        }
                    ) { Text(if (busy) "Connecting..." else "Test and connect") }
                }
                Button(
                    enabled = repository != null && connected && !busy,
                    onClick = {
                        val activeRepository = repository ?: return@Button
                        scope.launch {
                            busy = true
                            status = runCatching {
                                    activeRepository.sync()
                                    val loaded = activeRepository.profile()
                                    profile = loaded
                                    syncStatus = loaded.connected_tracker?.sync_status
                                    "Sync complete."
                            }.getOrElse { it.message ?: "Sync failed." }
                            busy = false
                        }
                    }
                ) { Text("Sync library") }
                status?.let { Text(it, style = MaterialTheme.typography.bodyLarge) }
            }
        }
        Surface(tonalElevation = 2.dp, modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Preferred metadata copy", style = MaterialTheme.typography.headlineSmall)
                Text("Choose which catalog to open first when several versions are available.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                Row(
                    modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf(null to "Any source", "comicvine" to "Comic Vine", "openlibrary" to "Open Library", "anilist" to "AniList", "metron" to "Metron").forEach { (source, label) ->
                        FilterChip(
                            selected = preferredSource == source,
                            onClick = {
                                preferredSource = source
                                sessionStore?.savePreferredSource(source)
                            },
                            label = { Text(label) }
                        )
                    }
                }
            }
        }
    }
}
