package com.panelist.app

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.panelist.app.ui.screens.DiscoverScreen
import com.panelist.app.ui.screens.AuthScreen
import com.panelist.app.ui.screens.HomeScreen
import com.panelist.app.ui.screens.LibraryScreen
import com.panelist.app.ui.screens.LibraryDetailScreen
import com.panelist.app.ui.screens.ProfileScreen
import com.panelist.app.ui.screens.MetadataDetailScreen
import com.panelist.app.ui.screens.ServerConnectionScreen
import com.panelist.app.data.model.MetadataGroup
import com.panelist.app.data.model.MetadataResult
import com.panelist.app.data.model.LibraryItem
import com.panelist.app.data.model.Recommendation
import com.panelist.app.ui.theme.PanelistTheme
import com.panelist.app.data.api.ApiFactory
import com.panelist.app.data.repository.MetadataRepository
import com.panelist.app.data.repository.AuthRepository
import com.panelist.app.data.repository.RecommendationRepository
import com.panelist.app.data.repository.LibraryRepository
import com.panelist.app.data.repository.ProfileRepository

private data class Tab(val route: String, val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

private val tabs = listOf(
    Tab("home", "For you", Icons.Outlined.Home),
    Tab("discover", "Discover", Icons.Outlined.Search),
    Tab("library", "Library", Icons.Outlined.FavoriteBorder),
    Tab("profile", "Profile", Icons.Outlined.Person)
)

@Composable
fun PanelistApp() {
    val nav = rememberNavController()
    val context = LocalContext.current
    val sessionStore = remember { com.panelist.app.data.session.SessionStore(context) }
    var serverUrl by remember { mutableStateOf(sessionStore.serverUrl()) }
    var selectedMetadata by rememberSaveable { mutableStateOf<MetadataGroup?>(null) }
    var selectedLibraryItem by rememberSaveable { mutableStateOf<LibraryItem?>(null) }
    PanelistTheme {
        if (serverUrl == null) {
            ServerConnectionScreen(
                onConnected = { connectedUrl ->
                    sessionStore.saveServerUrl(connectedUrl)
                    serverUrl = connectedUrl
                },
                testConnection = { url -> ApiFactory.create(sessionStore, url).health() }
            )
            return@PanelistTheme
        }
        val api = remember(serverUrl) { ApiFactory.create(sessionStore, serverUrl!!) }
        val authRepository = remember(api) { AuthRepository(api, sessionStore) }
        val metadataRepository = remember(api) { MetadataRepository(api) }
        var isAuthenticated by remember(serverUrl) { mutableStateOf(authRepository.isAuthenticated()) }
        if (!isAuthenticated) {
            AuthScreen(authRepository) { isAuthenticated = true }
            return@PanelistTheme
        }
        val recommendationRepository = remember { RecommendationRepository(api) }
        val libraryRepository = remember { LibraryRepository(api) }
        val profileRepository = remember { ProfileRepository(api) }
        val useRail = LocalConfiguration.current.screenWidthDp >= 600
        Row {
            if (useRail) {
                val entry by nav.currentBackStackEntryAsState()
                val route = entry?.destination?.route ?: "home"
                NavigationRail {
                    tabs.forEach { tab ->
                        NavigationRailItem(
                            selected = tab.route == route,
                            onClick = { navigateToTab(nav, tab.route) },
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                            label = { Text(tab.label) }
                        )
                    }
                }
            }
            Scaffold(
                modifier = Modifier.weight(1f),
                bottomBar = {
                    if (!useRail) {
                    val entry by nav.currentBackStackEntryAsState()
                    val route = entry?.destination?.route ?: "home"
                    NavigationBar {
                        tabs.forEach { tab ->
                            NavigationBarItem(
                                selected = tab.route == route,
                                onClick = { navigateToTab(nav, tab.route) },
                                icon = { Icon(tab.icon, contentDescription = tab.label) },
                                label = { Text(tab.label) }
                            )
                        }
                    }
                    }
                }
            ) { pad ->
                NavHost(navController = nav, startDestination = "home", modifier = Modifier.padding(pad)) {
                    composable("home") {
                        HomeScreen(recommendationRepository) { recommendation ->
                            selectedMetadata = recommendation.toMetadataGroup()
                            nav.navigate("metadata-detail")
                        }
                    }
                    composable("discover") {
                        DiscoverScreen(metadataRepository, sessionStore) { result ->
                            selectedMetadata = result
                            nav.navigate("metadata-detail")
                        }
                    }
                    composable("metadata-detail") {
                        selectedMetadata?.let { result ->
                            MetadataDetailScreen(result, sessionStore) { nav.popBackStack() }
                        }
                    }
                    composable("library") {
                        LibraryScreen(libraryRepository) {
                            selectedLibraryItem = it
                            nav.navigate("library-detail")
                        }
                    }
                    composable("library-detail") {
                        selectedLibraryItem?.let { LibraryDetailScreen(it) { nav.popBackStack() } }
                    }
                    composable("profile") {
                        ProfileScreen(
                            repository = profileRepository,
                            sessionStore = sessionStore,
                            onLoggedOut = {
                                sessionStore.clear()
                                isAuthenticated = false
                            }
                        )
                    }
                }
            }
        }
    }
}

private fun Recommendation.toMetadataGroup(): MetadataGroup {
    val result = MetadataResult(
        source = source ?: "Panelist",
        source_id = source_id ?: id,
        title = title,
        creator = creator,
        genres = genres,
        publisher = null,
        description = description,
        rating = rating,
        release_date = release_date,
        image_url = image_url,
        source_url = source_url
    )
    return MetadataGroup(id = id, primary = result, variants = listOf(result))
}

private fun navigateToTab(nav: androidx.navigation.NavHostController, route: String) {
    nav.navigate(route) {
        popUpTo("home") { saveState = true }
        launchSingleTop = true
        restoreState = true
    }
}
