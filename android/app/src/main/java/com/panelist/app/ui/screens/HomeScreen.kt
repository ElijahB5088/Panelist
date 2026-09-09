package com.panelist.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.IconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.TextButton
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.snap
import androidx.compose.runtime.Composable
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
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.SubcomposeAsyncImage
import com.panelist.app.data.model.Recommendation
import com.panelist.app.data.repository.RecommendationRepository
import com.panelist.app.viewmodel.HomeViewModel
import com.panelist.app.viewmodel.HomeViewModelFactory
import com.panelist.app.ui.rememberReducedMotion
import kotlin.math.roundToInt

@Composable
fun HomeScreen(repository: RecommendationRepository) {
    HomeScreen(repository, {})
}

@Composable
fun HomeScreen(repository: RecommendationRepository, onRecommendationClick: (Recommendation) -> Unit) {
    val viewModel: HomeViewModel = viewModel(factory = HomeViewModelFactory(repository))
    HomeScreen(viewModel, onRecommendationClick)
}

@Composable
fun HomeScreen(viewModel: HomeViewModel, onRecommendationClick: (Recommendation) -> Unit = {}) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
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
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 24.dp),
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
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Swipe left to pass | right to like",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
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
            state.isLoading && pick == null -> LoadingDeck()
            state.errorMessage != null -> ErrorDeck(state.errorMessage!!, viewModel::refresh)
            pick == null -> EmptyDeck(viewModel::refresh)
            else -> {
                if (state.isLoading) {
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                }
                val nextPick = visibleRecommendations.getOrNull(state.currentIndex + 1)
                Box(
                    modifier = Modifier.fillMaxWidth(),
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
                                        if (!state.isSubmitting && !state.isLoading) viewModel.submitFeedback(true)
                                        !state.isSubmitting && !state.isLoading
                                    },
                                    CustomAccessibilityAction("Dismiss recommendation") {
                                        if (!state.isSubmitting && !state.isLoading) viewModel.submitFeedback(false)
                                        !state.isSubmitting && !state.isLoading
                                    }
                                )
                            }
                                .pointerInput(state.currentIndex, state.isSubmitting) {
                                detectHorizontalDragGestures(
                                        onHorizontalDrag = { _, amount -> if (!state.isSubmitting && !state.isLoading) dragOffset += amount },
                                    onDragEnd = {
                                            if (!state.isSubmitting && !state.isLoading && kotlin.math.abs(dragOffset) > 180f) {
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
                    if (state.isFilterLoading) {
                        Box(
                            modifier = Modifier
                                .matchParentSize()
                                .background(
                                    MaterialTheme.colorScheme.surface.copy(alpha = 0.82f),
                                    RoundedCornerShape(24.dp)
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(10.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                                Text("Updating picks...", style = MaterialTheme.typography.labelLarge)
                            }
                        }
                    }
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    ActionButton(Icons.Outlined.Close, "Dismiss", MaterialTheme.colorScheme.primary, enabled = !state.isSubmitting && !state.isLoading) { viewModel.submitFeedback(false) }
                    Spacer(Modifier.size(42.dp))
                    ActionButton(Icons.Outlined.FavoriteBorder, "Like", MaterialTheme.colorScheme.tertiary, enabled = !state.isSubmitting && !state.isLoading) { viewModel.submitFeedback(true) }
                }
                if (state.isSubmitting) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                        Text("Saving your choice...", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                state.feedbackErrorMessage?.let { message ->
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(message, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
                        TextButton(onClick = viewModel::retryFeedback) { Text("Try again") }
                    }
                }
            }
        }
    }
}

@Composable
private fun DeckCard(pick: Recommendation, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val (accent, onAccent) = when {
        pick.genres.any { it.contains("fantasy", ignoreCase = true) } ->
            MaterialTheme.colorScheme.secondaryContainer to MaterialTheme.colorScheme.onSecondaryContainer
        pick.genres.any { it.contains("science", ignoreCase = true) } ->
            MaterialTheme.colorScheme.tertiaryContainer to MaterialTheme.colorScheme.onTertiaryContainer
        else -> MaterialTheme.colorScheme.primaryContainer to MaterialTheme.colorScheme.onPrimaryContainer
    }
    Surface(modifier = modifier.fillMaxWidth(), onClick = onClick, shape = RoundedCornerShape(24.dp), tonalElevation = 4.dp) {
        Column {
            Box(modifier = Modifier.fillMaxWidth().aspectRatio(2f / 3f).background(accent), contentAlignment = Alignment.Center) {
                SubcomposeAsyncImage(
                    model = pick.image_url?.takeIf { it.isNotBlank() },
                    contentDescription = "Cover for ${pick.title}",
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop,
                    alpha = 0.92f,
                    error = { CoverFallback(pick, accent, onAccent) },
                    loading = {
                        Box(
                            modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceVariant)
                        )
                    }
                )
                Surface(
                    modifier = Modifier.align(Alignment.BottomStart).padding(18.dp),
                    color = Color.Black.copy(alpha = 0.45f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        "COVER PREVIEW",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp),
                        color = Color.White,
                        style = MaterialTheme.typography.labelLarge
                    )
                }
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
private fun CoverFallback(pick: Recommendation, accent: Color, onAccent: Color) {
    Box(modifier = Modifier.fillMaxSize().background(accent), contentAlignment = Alignment.Center) {
        Text("${pick.title.firstOrNull() ?: '?'}", color = onAccent, style = MaterialTheme.typography.headlineLarge.copy(fontSize = 120.sp), fontWeight = FontWeight.Black)
    }
}

@Composable
private fun LoadingDeck() {
    Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp), tonalElevation = 2.dp) {
        Column {
            Box(modifier = Modifier.fillMaxWidth().aspectRatio(2f / 3f).background(MaterialTheme.colorScheme.surfaceVariant))
            Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(modifier = Modifier.fillMaxWidth(0.78f).height(24.dp).background(MaterialTheme.colorScheme.surfaceVariant))
                Box(modifier = Modifier.fillMaxWidth(0.45f).height(18.dp).background(MaterialTheme.colorScheme.surfaceVariant))
                Box(modifier = Modifier.fillMaxWidth().height(18.dp).background(MaterialTheme.colorScheme.surfaceVariant))
                Text("Finding recommendations...", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun ErrorDeck(message: String, onRetry: () -> Unit) {
    Surface(shape = RoundedCornerShape(24.dp), tonalElevation = 2.dp) {
        Column(modifier = Modifier.padding(28.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Recommendations are unavailable", style = MaterialTheme.typography.headlineSmall)
            Text(message, style = MaterialTheme.typography.bodyLarge)
            Button(onClick = onRetry) { Text("Retry") }
        }
    }
}

@Composable
private fun ActionButton(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, color: Color, enabled: Boolean, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        IconButton(onClick = onClick, enabled = enabled, modifier = Modifier.size(58.dp)) {
            Icon(icon, contentDescription = label, tint = color, modifier = Modifier.size(30.dp))
        }
        Text(label, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
private fun EmptyDeck(onRefresh: () -> Unit) {
    Surface(shape = RoundedCornerShape(24.dp), tonalElevation = 2.dp) {
        Column(modifier = Modifier.padding(28.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("You reached the end.", style = MaterialTheme.typography.headlineSmall)
            Text("Rate a few more books or check back after your library syncs.", style = MaterialTheme.typography.bodyLarge)
            Button(onClick = onRefresh) { Text("Refresh picks") }
        }
    }
}
