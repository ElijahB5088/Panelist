package com.panelist.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.IconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.snap
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.layout.ContentScale
import coil.compose.SubcomposeAsyncImage
import com.panelist.app.data.model.Recommendation
import com.panelist.app.data.repository.RecommendationRepository
import com.panelist.app.viewmodel.HomeViewModel
import com.panelist.app.ui.rememberReducedMotion
import kotlin.math.roundToInt

@Composable
fun HomeScreen(repository: RecommendationRepository) {
    HomeScreen(repository, {})
}

@Composable
fun HomeScreen(repository: RecommendationRepository, onRecommendationClick: (Recommendation) -> Unit) {
    val viewModel = remember { HomeViewModel(repository) }
    val state by viewModel.uiState.collectAsState()
    val visibleRecommendations = state.visibleRecommendations
    val pick = visibleRecommendations.getOrNull(state.currentIndex)
    var dragOffset by remember { mutableFloatStateOf(0f) }
    val reducedMotion = rememberReducedMotion()
    val animatedDragOffset by animateFloatAsState(
        dragOffset,
        animationSpec = if (reducedMotion) snap() else spring(),
        label = "recommendation drag"
    )

    Column(
        modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("PANELIST", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
            Column {
                Text("Find your next", style = MaterialTheme.typography.headlineLarge)
                Text("great read.", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.primary)
            }
            if (pick != null) {
                Text("${state.currentIndex + 1} / ${visibleRecommendations.size}", style = MaterialTheme.typography.labelLarge)
            }
        }
        Text("Swipe through picks shaped by your taste.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = state.mediaTypeFilter == null,
                onClick = { viewModel.setMediaTypeFilter(null) },
                label = { Text("All") }
            )
            FilterChip(
                selected = state.mediaTypeFilter == "comic",
                onClick = { viewModel.setMediaTypeFilter("comic") },
                label = { Text("Comics") }
            )
            FilterChip(
                selected = state.mediaTypeFilter == "manga",
                onClick = { viewModel.setMediaTypeFilter("manga") },
                label = { Text("Manga") }
            )
        }
        Spacer(Modifier.height(4.dp))

        when {
            state.isLoading -> LoadingDeck()
            state.errorMessage != null -> ErrorDeck(state.errorMessage!!, viewModel::refresh)
            pick == null -> EmptyDeck()
            else -> {
                val nextPick = visibleRecommendations.getOrNull(state.currentIndex + 1)
                Box(
                    modifier = Modifier.fillMaxWidth().weight(1f),
                    contentAlignment = Alignment.Center
                ) {
                    if (nextPick != null) {
                        DeckCard(nextPick, Modifier.offset(y = 12.dp).padding(horizontal = 8.dp), {})
                    }
                    DeckCard(
                        pick,
                        Modifier
                            .semantics {
                                customActions = listOf(
                                    CustomAccessibilityAction("Like recommendation") {
                                        viewModel.submitFeedback(true)
                                        true
                                    },
                                    CustomAccessibilityAction("Dismiss recommendation") {
                                        viewModel.submitFeedback(false)
                                        true
                                    }
                                )
                            }
                            .pointerInput(state.currentIndex) {
                                detectHorizontalDragGestures(
                                    onHorizontalDrag = { _, amount -> dragOffset += amount },
                                    onDragEnd = {
                                        if (kotlin.math.abs(dragOffset) > 180f) {
                                            viewModel.submitFeedback(dragOffset > 0f)
                                        }
                                        dragOffset = 0f
                                    }
                                )
                            }
                            .graphicsLayer {
                                translationX = animatedDragOffset
                                rotationZ = animatedDragOffset / 32f
                            },
                        onClick = { onRecommendationClick(pick) }
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    ActionButton(Icons.Outlined.Close, "Dismiss", MaterialTheme.colorScheme.primary) { viewModel.submitFeedback(false) }
                    Spacer(Modifier.size(42.dp))
                    ActionButton(Icons.Outlined.FavoriteBorder, "Like", MaterialTheme.colorScheme.tertiary) { viewModel.submitFeedback(true) }
                }
            }
        }
    }
}

@Composable
private fun DeckCard(pick: Recommendation, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val accent = when {
        pick.genres.any { it.contains("fantasy", ignoreCase = true) } -> Color(0xFF415E55)
        pick.genres.any { it.contains("science", ignoreCase = true) } -> Color(0xFF3D5875)
        else -> Color(0xFFB94632)
    }
    Surface(modifier = modifier.fillMaxWidth(), onClick = onClick, shape = RoundedCornerShape(24.dp), tonalElevation = 4.dp) {
        Column {
            Box(modifier = Modifier.fillMaxWidth().height(270.dp).background(accent), contentAlignment = Alignment.Center) {
                Text("${pick.title.firstOrNull() ?: '?'}", color = Color.White.copy(alpha = 0.9f), style = MaterialTheme.typography.headlineLarge.copy(fontSize = 120.sp), fontWeight = FontWeight.Black)
                Text("COVER PREVIEW", modifier = Modifier.align(Alignment.BottomStart).padding(18.dp), color = Color.White.copy(alpha = 0.75f), style = MaterialTheme.typography.labelLarge)
                SubcomposeAsyncImage(
                    model = pick.image_url,
                    contentDescription = "Cover for ${pick.title}",
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop,
                    alpha = 0.92f,
                    error = { CoverFallback(pick, accent) },
                    loading = {
                        Box(
                            modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceVariant)
                        )
                    }
                )
            }
            Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(pick.title, style = MaterialTheme.typography.headlineSmall)
                Text(pick.creator ?: "Creator unknown", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
                Text(
                    listOfNotNull(pick.media_type?.replaceFirstChar { it.uppercase() }, pick.release_date?.take(4), pick.genres.joinToString("  / ").takeIf { it.isNotBlank() }).joinToString("  /  "),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(pick.why, style = MaterialTheme.typography.bodyLarge)
                pick.source?.let { Text("Source: $it", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                pick.description?.let { Text(it, style = MaterialTheme.typography.bodyLarge, maxLines = 2) }
            }
        }
    }
}

@Composable
private fun CoverFallback(pick: Recommendation, accent: Color) {
    Box(modifier = Modifier.fillMaxSize().background(accent), contentAlignment = Alignment.Center) {
        Text("${pick.title.firstOrNull() ?: '?'}", color = Color.White.copy(alpha = 0.9f), style = MaterialTheme.typography.headlineLarge.copy(fontSize = 120.sp), fontWeight = FontWeight.Black)
    }
}

@Composable
private fun LoadingDeck() {
    Surface(shape = RoundedCornerShape(24.dp), tonalElevation = 2.dp) {
        Text("Finding recommendations...", modifier = Modifier.padding(28.dp), style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
private fun ErrorDeck(message: String, onRetry: () -> Unit) {
    Surface(shape = RoundedCornerShape(24.dp), tonalElevation = 2.dp) {
        Column(modifier = Modifier.padding(28.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Recommendations are unavailable", style = MaterialTheme.typography.headlineSmall)
            Text(message, style = MaterialTheme.typography.bodyLarge)
            IconButton(onClick = onRetry) {
                Text("Retry", color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}

@Composable
private fun ActionButton(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, color: Color, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        IconButton(onClick = onClick, modifier = Modifier.size(58.dp)) {
            Icon(icon, contentDescription = label, tint = color, modifier = Modifier.size(30.dp))
        }
        Text(label, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
private fun EmptyDeck() {
    Surface(shape = RoundedCornerShape(24.dp), tonalElevation = 2.dp) {
        Column(modifier = Modifier.padding(28.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("You reached the end.", style = MaterialTheme.typography.headlineSmall)
            Text("Rate a few more books or check back after your library syncs.", style = MaterialTheme.typography.bodyLarge)
        }
    }
}
