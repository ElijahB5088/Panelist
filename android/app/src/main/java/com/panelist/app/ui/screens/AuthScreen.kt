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
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.panelist.app.data.repository.AuthRepository
import kotlinx.coroutines.launch

@Composable
fun AuthScreen(repository: AuthRepository, onAuthenticated: () -> Unit) {
    var isRegistering by remember { mutableStateOf(false) }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isSubmitting by remember { mutableStateOf(false) }
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
        Text(if (isRegistering) "Create your account" else "Welcome back", style = MaterialTheme.typography.headlineLarge)
        Text("Your recommendations stay tied to your private library.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        OutlinedTextField(
            value = username,
            onValueChange = { username = it; errorMessage = null },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Username") },
            singleLine = true,
            enabled = !isSubmitting
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it; errorMessage = null },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Password") },
            singleLine = true,
            enabled = !isSubmitting,
            visualTransformation = PasswordVisualTransformation()
        )
        errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(
            onClick = {
                if (username.isBlank() || password.isBlank()) {
                    errorMessage = "Enter a username and password."
                } else {
                    scope.launch {
                        isSubmitting = true
                        errorMessage = null
                        runCatching {
                            if (isRegistering) repository.register(username.trim(), password) else repository.login(username.trim(), password)
                        }.onSuccess { onAuthenticated() }
                            .onFailure { exception -> errorMessage = exception.message ?: "Authentication failed." }
                        isSubmitting = false
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isSubmitting
        ) {
            Text(if (isSubmitting) "Connecting..." else if (isRegistering) "Create account" else "Sign in")
        }
        OutlinedButton(
            onClick = { isRegistering = !isRegistering; errorMessage = null },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isSubmitting
        ) {
            Text(if (isRegistering) "I already have an account" else "Create a new account")
        }
    }
}