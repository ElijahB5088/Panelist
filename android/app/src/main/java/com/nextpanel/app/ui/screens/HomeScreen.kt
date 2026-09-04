package com.nextpanel.app.ui.screens

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
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.roundToInt

private data class DemoPick(val title: String, val creator: String, val genres: String, val why: String, val accent: Color)

private val demoPicks = listOf(
    DemoPick("Saga", "Brian K. Vaughan", "Sci-fi  /  Family  /  Drama", "Because you rated character-driven space opera highly.", Color(0xFFB94632)),
    DemoPick("Monstress", "Marjorie Liu", "Fantasy  /  Dark  /  Drama", "A dense world with the same emotional bite as your favorites.", Color(0xFF415E55)),
    DemoPick("Descender", "Jeff Lemire", "Sci-fi  /  Adventure", "A quieter robot odyssey with big, strange ideas.", Color(0xFF3D5875))
)

@Composable
fun HomeScreen() {
    var currentIndex by remember { mutableIntStateOf(0) }
    var dragOffset by remember { mutableFloatStateOf(0f) }
    val pick = demoPicks.getOrNull(currentIndex)

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
                Text("${currentIndex + 1} / ${demoPicks.size}", style = MaterialTheme.typography.labelLarge)
            }
        }
        Text("Swipe through picks shaped by your taste.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(4.dp))

        if (pick == null) {
            EmptyDeck()
        } else {
            Box(
                modifier = Modifier.fillMaxWidth().weight(1f),
                contentAlignment = Alignment.Center
            ) {
                if (currentIndex + 1 < demoPicks.size) {
                    DeckCard(demoPicks[currentIndex + 1], Modifier.offset(y = 12.dp).padding(horizontal = 8.dp))
                }
                DeckCard(
                    pick,
                    Modifier.offset { IntOffset(dragOffset.roundToInt(), 0) }
                        .pointerInput(currentIndex) {
                            detectHorizontalDragGestures(
                                onHorizontalDrag = { _, amount -> dragOffset += amount },
                                onDragEnd = {
                                    if (kotlin.math.abs(dragOffset) > 180f) currentIndex++
                                    dragOffset = 0f
                                }
                            )
                        }
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                ActionButton("X", "Dismiss", MaterialTheme.colorScheme.primary) { currentIndex++ }
                Spacer(Modifier.size(26.dp))
                ActionButton("i", "Details", MaterialTheme.colorScheme.secondary) { }
                Spacer(Modifier.size(26.dp))
                ActionButton("+", "Like", MaterialTheme.colorScheme.tertiary) { currentIndex++ }
            }
        }
    }
}

@Composable
private fun DeckCard(pick: DemoPick, modifier: Modifier = Modifier) {
    Surface(modifier = modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp), tonalElevation = 4.dp) {
        Column {
            Box(modifier = Modifier.fillMaxWidth().height(270.dp).background(pick.accent), contentAlignment = Alignment.Center) {
                Text("${pick.title.first()}", color = Color.White.copy(alpha = 0.9f), style = MaterialTheme.typography.headlineLarge.copy(fontSize = 120.sp), fontWeight = FontWeight.Black)
                Text("COVER PREVIEW", modifier = Modifier.align(Alignment.BottomStart).padding(18.dp), color = Color.White.copy(alpha = 0.75f), style = MaterialTheme.typography.labelLarge)
            }
            Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(pick.title, style = MaterialTheme.typography.headlineSmall)
                Text(pick.creator, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
                Text(pick.genres, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(pick.why, style = MaterialTheme.typography.bodyLarge)
            }
        }
    }
}

@Composable
private fun ActionButton(icon: String, label: String, color: Color, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        IconButton(onClick = onClick, modifier = Modifier.size(58.dp)) {
            Text(icon, color = color, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.size(30.dp))
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
