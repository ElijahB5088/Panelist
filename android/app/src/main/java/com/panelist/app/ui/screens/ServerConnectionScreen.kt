package com.panelist.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.imePadding
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import java.net.URI

@Composable
fun ServerConnectionScreen(
    onConnected: (String) -> Unit,
    testConnection: suspend (String) -> Unit
) {
    var serverUrl by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isConnecting by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .imePadding()
            .padding(28.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("PANELIST", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
        Text("Connect to your server", style = MaterialTheme.typography.headlineLarge)
        Text(
            "Enter the HTTPS address of your self-hosted Panelist backend.",
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        OutlinedTextField(
            value = serverUrl,
            onValueChange = { serverUrl = it; errorMessage = null },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Server URL") },
            placeholder = { Text("https://panelist.example.com") },
            singleLine = true,
            enabled = !isConnecting
        )
        errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(
            onClick = {
                val normalizedUrl = normalizeServerUrl(serverUrl)
                val validationError = validateServerUrl(normalizedUrl)
                if (validationError != null) {
                    errorMessage = validationError
                    return@Button
                }
                scope.launch {
                    isConnecting = true
                    errorMessage = null
                    runCatching { testConnection(normalizedUrl) }
                        .onSuccess { onConnected(normalizedUrl) }
                        .onFailure { exception -> errorMessage = exception.message ?: "Could not connect to the server." }
                    isConnecting = false
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isConnecting
        ) {
            Text(if (isConnecting) "Checking server..." else "Connect")
        }
    }
}

private fun normalizeServerUrl(value: String): String = value.trim().trimEnd('/') + "/"

private fun validateServerUrl(value: String): String? {
    val uri = runCatching { URI(value) }.getOrNull()
    if (uri?.host.isNullOrBlank() || uri?.path != "/") return "Enter a valid server URL."
    val isLocalDebugServer = uri.scheme == "http" && (uri.host == "10.0.2.2" || uri.host == "localhost")
    if (uri.scheme != "https" && !isLocalDebugServer) return "Use an HTTPS server URL."
    return null
}