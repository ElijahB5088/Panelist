package com.nextpanel.app

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.nextpanel.app.ui.screens.DiscoverScreen
import com.nextpanel.app.ui.screens.HomeScreen
import com.nextpanel.app.ui.screens.LibraryScreen
import com.nextpanel.app.ui.screens.ProfileScreen

private val tabs = listOf("home", "discover", "library", "profile")

@Composable
fun NextPanelApp() {
    val nav = rememberNavController()
    MaterialTheme {
        Scaffold(
            bottomBar = {
                val entry by nav.currentBackStackEntryAsState()
                val route = entry?.destination?.route ?: "home"
                NavigationBar {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            selected = tab == route,
                            onClick = { nav.navigate(tab) },
                            icon = { Text(tab.take(1).uppercase()) },
                            label = { Text(tab.replaceFirstChar { it.uppercase() }) }
                        )
                    }
                }
            }
        ) { pad ->
            NavHost(navController = nav, startDestination = "home", modifier = Modifier.padding(pad)) {
                composable("home") { HomeScreen() }
                composable("discover") { DiscoverScreen() }
                composable("library") { LibraryScreen() }
                composable("profile") { ProfileScreen() }
            }
        }
    }
}
