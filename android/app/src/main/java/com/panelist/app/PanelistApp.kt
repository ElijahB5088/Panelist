package com.panelist.app

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.panelist.app.ui.screens.DiscoverScreen
import com.panelist.app.ui.screens.AuthScreen
import com.panelist.app.ui.screens.HomeScreen
import com.panelist.app.ui.screens.LibraryScreen
import com.panelist.app.ui.screens.ProfileScreen
import com.panelist.app.ui.theme.PanelistTheme
import com.panelist.app.data.api.ApiFactory
import com.panelist.app.data.repository.MetadataRepository
import com.panelist.app.data.repository.AuthRepository
import com.panelist.app.data.repository.RecommendationRepository

private data class Tab(val route: String, val label: String, val icon: String)

private val tabs = listOf(
    Tab("home", "For you", "H"),
    Tab("discover", "Discover", "D"),
    Tab("library", "Library", "L"),
    Tab("profile", "Profile", "P")
)

@Composable
fun PanelistApp() {
    val nav = rememberNavController()
    val context = LocalContext.current
    val sessionStore = remember { com.panelist.app.data.session.SessionStore(context) }
    val api = remember { ApiFactory.create(context, sessionStore) }
    val authRepository = remember { AuthRepository(api, sessionStore) }
    val metadataRepository = remember { MetadataRepository(api) }
    var isAuthenticated by remember { mutableStateOf(authRepository.isAuthenticated()) }
    PanelistTheme {
        if (!isAuthenticated) {
            AuthScreen(authRepository) { isAuthenticated = true }
            return@PanelistTheme
        }
        val recommendationRepository = remember { RecommendationRepository(api) }
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
                composable("home") { HomeScreen(recommendationRepository) }
                composable("discover") { DiscoverScreen(metadataRepository) }
                composable("library") { LibraryScreen() }
                composable("profile") { ProfileScreen() }
            }
        }
    }
}
