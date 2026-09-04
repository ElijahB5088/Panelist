package com.nextpanel.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun DiscoverScreen() {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Discover")
        Text("Search, filters, popularity, recently added")
    }
}
