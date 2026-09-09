package com.panelist.app.viewmodel

import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.Recommendation
import com.panelist.app.data.repository.RecommendationRepository
import java.lang.reflect.Proxy
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {
    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun feedbackSuccessAdvancesToNextRecommendation() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val first = recommendation("first")
        val second = recommendation("second")
        val repository = FakeRecommendationRepository(recommendations = listOf(first, second))
        val viewModel = HomeViewModel(repository)
        advanceUntilIdle()

        viewModel.submitFeedback(liked = true)
        advanceUntilIdle()

        assertEquals(1, viewModel.uiState.value.currentIndex)
        assertFalse(viewModel.uiState.value.isSubmitting)
        assertEquals(listOf("first"), repository.likedIds)
    }

    @Test
    fun feedbackFailureKeepsCardAndRetryCanSucceed() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val first = recommendation("first")
        val repository = FakeRecommendationRepository(recommendations = listOf(first), failLike = true)
        val viewModel = HomeViewModel(repository)
        advanceUntilIdle()

        viewModel.submitFeedback(liked = true)
        advanceUntilIdle()

        assertEquals(0, viewModel.uiState.value.currentIndex)
        assertNotNull(viewModel.uiState.value.feedbackErrorMessage)
        assertFalse(viewModel.uiState.value.isSubmitting)

        repository.failLike = false
        viewModel.retryFeedback()
        advanceUntilIdle()

        assertEquals(1, viewModel.uiState.value.currentIndex)
        assertEquals(null, viewModel.uiState.value.feedbackErrorMessage)
    }

    @Test
    fun duplicateFeedbackIsIgnoredWhileSubmitting() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val first = recommendation("first")
        val request = CompletableDeferred<Unit>()
        val repository = FakeRecommendationRepository(recommendations = listOf(first), likeRequest = request)
        val viewModel = HomeViewModel(repository)
        advanceUntilIdle()

        viewModel.submitFeedback(liked = true)
        runCurrent()
        viewModel.submitFeedback(liked = true)
        advanceUntilIdle()

        assertEquals(1, repository.likeCallCount)
        assertTrue(viewModel.uiState.value.isSubmitting)

        request.complete(Unit)
        advanceUntilIdle()

        assertEquals(1, viewModel.uiState.value.currentIndex)
        assertFalse(viewModel.uiState.value.isSubmitting)
    }

    @Test
    fun staleFilterResponseDoesNotReplaceNewerFilter() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val comicRequest = CompletableDeferred<List<Recommendation>>()
        val mangaRequest = CompletableDeferred<List<Recommendation>>()
        val repository = FakeRecommendationRepository(
            recommendations = listOf(recommendation("all")),
            filteredRequests = mapOf("comic" to comicRequest, "manga" to mangaRequest)
        )
        val viewModel = HomeViewModel(repository)
        advanceUntilIdle()

        viewModel.setMediaTypeFilter("comic")
        viewModel.setMediaTypeFilter("manga")
        mangaRequest.complete(listOf(recommendation("manga", "manga")))
        comicRequest.complete(listOf(recommendation("comic", "comic")))
        advanceUntilIdle()

        assertEquals("manga", viewModel.uiState.value.mediaTypeFilter)
        assertEquals(listOf("manga"), viewModel.uiState.value.recommendations.map { it.id })
    }

    private fun recommendation(id: String, mediaType: String? = null) = Recommendation(
        id = id,
        title = id,
        creator = null,
        genres = emptyList(),
        rating = null,
        description = null,
        why = "Because you may like it",
        media_type = mediaType
    )
}

private class FakeRecommendationRepository(
    private val recommendations: List<Recommendation>,
    var failLike: Boolean = false,
    private val likeRequest: CompletableDeferred<Unit>? = null,
    private val filteredRequests: Map<String, CompletableDeferred<List<Recommendation>>> = emptyMap()
) : RecommendationRepository(fakeApi()) {
    val likedIds = mutableListOf<String>()
    var likeCallCount = 0
        private set

    override suspend fun recommendedForYou(): List<Recommendation> = recommendations

    override suspend fun recommendedForYou(mediaType: String): List<Recommendation> =
        filteredRequests[mediaType]?.await() ?: recommendations.filter { it.media_type == mediaType }

    override suspend fun like(mediaId: String) {
        likeCallCount++
        if (failLike) error("Feedback unavailable")
        likeRequest?.await()
        likedIds += mediaId
    }

    override suspend fun dismiss(mediaId: String) = Unit
}

@Suppress("UNCHECKED_CAST")
private fun fakeApi(): PanelistApi = Proxy.newProxyInstance(
    PanelistApi::class.java.classLoader,
    arrayOf(PanelistApi::class.java)
) { _, _, _ -> null } as PanelistApi
