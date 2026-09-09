package com.panelist.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.Recommendation
import com.panelist.app.data.repository.RecommendationRepository
import com.panelist.app.viewmodel.HomeViewModel
import java.lang.reflect.Proxy
import kotlinx.coroutines.CompletableDeferred
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class HomeScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun filterRefreshKeepsCardVisibleAndShowsOverlay() {
        val filteredRequest = CompletableDeferred<List<Recommendation>>()
        val repository = FakeHomeRepository(
            initial = listOf(recommendation("Saga")),
            filtered = mapOf("manga" to filteredRequest)
        )
        composeRule.setContent { HomeScreen(HomeViewModel(repository)) }
        composeRule.waitForIdle()

        composeRule.onNodeWithText("Manga").performClick()

        composeRule.onNodeWithText("Saga").assertIsDisplayed()
        composeRule.onNodeWithText("Updating picks...").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Like").assertIsNotEnabled()

        filteredRequest.complete(listOf(recommendation("Witch Hat Atelier", "manga")))
        composeRule.waitForIdle()
        assertEquals(0, composeRule.onAllNodesWithText("Updating picks...").fetchSemanticsNodes().size)
        composeRule.onNodeWithText("Witch Hat Atelier").assertIsDisplayed()
    }

    @Test
    fun feedbackActionsDisableWhileSaving() {
        val likeRequest = CompletableDeferred<Unit>()
        val repository = FakeHomeRepository(
            initial = listOf(recommendation("Saga")),
            likeRequest = likeRequest
        )
        composeRule.setContent { HomeScreen(HomeViewModel(repository)) }
        composeRule.waitForIdle()

        composeRule.onNodeWithContentDescription("Like").performClick()
        composeRule.waitForIdle()

        composeRule.onNodeWithText("Saving your choice...").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Like").assertIsNotEnabled()
        composeRule.onNodeWithContentDescription("Dismiss").assertIsNotEnabled()

        likeRequest.complete(Unit)
        composeRule.waitForIdle()
        assertEquals(0, composeRule.onAllNodesWithText("Saving your choice...").fetchSemanticsNodes().size)
    }

    @Test
    fun fetchFailureOffersRetry() {
        val repository = FakeHomeRepository(
            initial = listOf(recommendation("Saga")),
            failInitial = true
        )
        composeRule.setContent { HomeScreen(HomeViewModel(repository)) }
        composeRule.waitForIdle()

        composeRule.onNodeWithText("Recommendations are unavailable").assertIsDisplayed()
        composeRule.onNodeWithText("Retry").performClick()
        composeRule.waitForIdle()
        composeRule.onNodeWithText("Saga").assertIsDisplayed()
    }

    @Test
    fun emptyStateOffersRefresh() {
        val repository = FakeHomeRepository(initial = emptyList())
        composeRule.setContent { HomeScreen(HomeViewModel(repository)) }
        composeRule.waitForIdle()

        composeRule.onNodeWithText("You reached the end.").assertIsDisplayed()
        composeRule.onNodeWithText("Refresh picks").performClick()
        composeRule.waitForIdle()
        composeRule.onNodeWithText("You reached the end.").assertIsDisplayed()
    }

    private fun recommendation(title: String, mediaType: String? = null) = Recommendation(
        id = title,
        title = title,
        creator = "Creator",
        genres = emptyList(),
        rating = null,
        description = null,
        why = "Because you may like it",
        media_type = mediaType
    )
}

private class FakeHomeRepository(
    private val initial: List<Recommendation>,
    private val filtered: Map<String, CompletableDeferred<List<Recommendation>>> = emptyMap(),
    private val likeRequest: CompletableDeferred<Unit>? = null,
    var failInitial: Boolean = false
) : RecommendationRepository(fakeApi()) {
    override suspend fun recommendedForYou(): List<Recommendation> {
        if (failInitial) error("Recommendations unavailable")
        return initial
    }

    override suspend fun recommendedForYou(mediaType: String): List<Recommendation> =
        filtered[mediaType]?.await() ?: initial.filter { it.media_type == mediaType }

    override suspend fun like(mediaId: String) {
        likeRequest?.await()
    }

    override suspend fun dismiss(mediaId: String) = Unit
}

@Suppress("UNCHECKED_CAST")
private fun fakeApi(): PanelistApi = Proxy.newProxyInstance(
    PanelistApi::class.java.classLoader,
    arrayOf(PanelistApi::class.java)
) { _, _, _ -> null } as PanelistApi
