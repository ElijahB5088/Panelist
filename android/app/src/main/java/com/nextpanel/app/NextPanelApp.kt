package com.nextpanel.app

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
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
import com.nextpanel.app.ui.theme.PanelistTheme

private data class Tab(val route: String, val label: String, val icon: String)

private val tabs = listOf(
    Tab("home", "For you", "H"),
    Tab("discover", "Discover", "D"),
    Tab("library", "Library", "L"),
    Tab("profile", "Profile", "P")
)

@Composable
fun NextPanelApp() {
    val nav = rememberNavController()
    PanelistTheme {
        Scaffold(
            bottomBar = {
                val entry by nav.currentBackStackEntryAsState()
                val route = entry?.destination?.route ?: "home"
                NavigationBar {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            selected = tab.route == route,
                            onClick = {
                                nav.navigate(tab.route) {
                                    popUpTo("home") { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { androidx.compose.material3.Text(tab.icon, style = androidx.compose.material3.MaterialTheme.typography.labelLarge) },
                            label = { androidx.compose.material3.Text(tab.label) }
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
