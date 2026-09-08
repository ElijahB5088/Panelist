package com.panelist.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.panelist.app.data.model.Recommendation
import com.panelist.app.data.repository.RecommendationRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class HomeUiState(
	val isLoading: Boolean = true,
	val recommendations: List<Recommendation> = emptyList(),
	val mediaTypeFilter: String? = null,
	val currentIndex: Int = 0,
	val isSubmitting: Boolean = false,
	val errorMessage: String? = null
) {
	val visibleRecommendations: List<Recommendation>
        get() = recommendations.filter { mediaTypeFilter == null || normalizeMediaType(it.media_type) == mediaTypeFilter }
}

class HomeViewModel(private val repository: RecommendationRepository) : ViewModel() {
	private val _uiState = MutableStateFlow(HomeUiState())
	val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()
	private val refillAttempts = mutableSetOf<String>()

	init {
		refresh()
	}

	fun refresh() {
		viewModelScope.launch {
			refillAttempts.clear()
			_uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
			runCatching { repository.recommendedForYou() }
				.onSuccess { recommendations ->
					_uiState.value = HomeUiState(isLoading = false, recommendations = recommendations)
				}
				.onFailure { error ->
					_uiState.value = _uiState.value.copy(
						isLoading = false,
						errorMessage = error.message ?: "Recommendations are unavailable right now."
					)
				}
		}
	}

	fun submitFeedback(liked: Boolean) {
		val state = _uiState.value
		val recommendation = state.visibleRecommendations.getOrNull(state.currentIndex) ?: return
		if (state.isSubmitting) return

		viewModelScope.launch {
			_uiState.value = state.copy(isSubmitting = true, errorMessage = null)
			runCatching {
				if (liked) repository.like(recommendation.id) else repository.dismiss(recommendation.id)
			}.onSuccess {
				_uiState.value = _uiState.value.copy(
					currentIndex = _uiState.value.currentIndex + 1,
					isSubmitting = false
				)
			}.onFailure { error ->
				_uiState.value = _uiState.value.copy(
					isSubmitting = false,
					errorMessage = error.message ?: "Your feedback could not be saved."
				)
			}
		}
	}

	fun setMediaTypeFilter(mediaType: String?) {
		val normalizedMediaType = mediaType?.let(::normalizeMediaType)
		_uiState.value = _uiState.value.copy(mediaTypeFilter = normalizedMediaType, currentIndex = 0)
		if (normalizedMediaType == null || normalizedMediaType in refillAttempts) return
		if (_uiState.value.visibleRecommendations.size >= 10) return

		refillAttempts += normalizedMediaType
		viewModelScope.launch {
			runCatching { repository.recommendedForYou(normalizedMediaType) }
				.onSuccess { additionalRecommendations ->
					if (_uiState.value.mediaTypeFilter == normalizedMediaType) {
						val merged = (_uiState.value.recommendations + additionalRecommendations).distinctBy { it.id }
						_uiState.value = _uiState.value.copy(recommendations = merged)
					}
				}
				.onFailure { refillAttempts -= normalizedMediaType }
		}
	}
}

private fun normalizeMediaType(mediaType: String?): String? = when (mediaType?.trim()?.lowercase()) {
	"comic", "comics" -> "comic"
	"manga", "manhwa", "manhua" -> "manga"
	else -> mediaType?.trim()?.lowercase()?.takeIf { it.isNotEmpty() }
}
