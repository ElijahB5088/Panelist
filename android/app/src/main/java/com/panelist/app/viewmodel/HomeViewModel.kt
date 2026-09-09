package com.panelist.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
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
	val isFilterLoading: Boolean = false,
	val errorMessage: String? = null,
	val feedbackErrorMessage: String? = null
) {
	val visibleRecommendations: List<Recommendation>
	get() = if (isFilterLoading) {
		recommendations
	} else {
		recommendations.filter { mediaTypeFilter == null || normalizeMediaType(it.media_type, it.source) == mediaTypeFilter }
	}
}

class HomeViewModel(private val repository: RecommendationRepository) : ViewModel() {
	private val _uiState = MutableStateFlow(HomeUiState())
	val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()
	private var requestGeneration = 0
	private var pendingFeedbackLiked: Boolean? = null

	init {
		refresh()
	}

	fun refresh() {
		val generation = ++requestGeneration
		val activeFilter = _uiState.value.mediaTypeFilter
		viewModelScope.launch {
			_uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
			runCatching {
				if (activeFilter == null) repository.recommendedForYou()
				else repository.recommendedForYou(activeFilter)
			}
				.onSuccess { recommendations ->
					if (generation == requestGeneration && _uiState.value.mediaTypeFilter == activeFilter) {
						_uiState.value = _uiState.value.copy(
							isLoading = false,
							recommendations = recommendations,
							currentIndex = 0
						)
					}
				}
				.onFailure { error ->
					if (generation == requestGeneration && _uiState.value.mediaTypeFilter == activeFilter) {
						_uiState.value = _uiState.value.copy(
							isLoading = false,
							errorMessage = error.message ?: "Recommendations are unavailable right now."
						)
					}
				}
		}
	}

	fun submitFeedback(liked: Boolean) {
		val state = _uiState.value
		val recommendation = state.visibleRecommendations.getOrNull(state.currentIndex) ?: return
		if (state.isSubmitting) return
		pendingFeedbackLiked = liked

		viewModelScope.launch {
			_uiState.value = state.copy(isSubmitting = true, feedbackErrorMessage = null)
			runCatching {
				if (liked) repository.like(recommendation.id) else repository.dismiss(recommendation.id)
			}.onSuccess {
				pendingFeedbackLiked = null
				_uiState.value = _uiState.value.copy(
					currentIndex = _uiState.value.currentIndex + 1,
					isSubmitting = false,
					feedbackErrorMessage = null
				)
			}.onFailure { error ->
				_uiState.value = _uiState.value.copy(
					isSubmitting = false,
					feedbackErrorMessage = error.message ?: "Your feedback could not be saved."
				)
			}
		}
	}

	fun retryFeedback() {
		pendingFeedbackLiked?.let(::submitFeedback)
	}

	fun setMediaTypeFilter(mediaType: String?) {
		val normalizedMediaType = mediaType?.let(::normalizeMediaType)
		val generation = ++requestGeneration
		_uiState.value = _uiState.value.copy(
			mediaTypeFilter = normalizedMediaType,
			currentIndex = 0,
			isLoading = normalizedMediaType != null,
			isFilterLoading = normalizedMediaType != null,
			errorMessage = null
		)
		if (normalizedMediaType == null) return

		viewModelScope.launch {
			runCatching { repository.recommendedForYou(normalizedMediaType) }
				.onSuccess { additionalRecommendations ->
					if (generation == requestGeneration && _uiState.value.mediaTypeFilter == normalizedMediaType) {
						_uiState.value = _uiState.value.copy(
							recommendations = additionalRecommendations,
							isLoading = false,
							isFilterLoading = false
						)
					}
				}
				.onFailure { error ->
					if (generation == requestGeneration && _uiState.value.mediaTypeFilter == normalizedMediaType) {
						_uiState.value = _uiState.value.copy(
							isLoading = false,
							isFilterLoading = false,
							errorMessage = error.message ?: "Recommendations are unavailable right now."
						)
					}
				}
		}
	}
}

class HomeViewModelFactory(
	private val repository: RecommendationRepository
) : ViewModelProvider.Factory {
	@Suppress("UNCHECKED_CAST")
	override fun <T : ViewModel> create(modelClass: Class<T>): T {
		if (modelClass.isAssignableFrom(HomeViewModel::class.java)) {
			return HomeViewModel(repository) as T
		}
		throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
	}
}

private fun normalizeMediaType(mediaType: String?, source: String? = null): String? {
	val normalizedSource = source?.trim()?.lowercase()
	if (normalizedSource in setOf("anilist", "kitsu", "mal")) return "manga"
	val normalizedType = when (mediaType?.trim()?.lowercase()) {
		"comic", "comics" -> "comic"
		"manga", "manhwa", "manhua" -> mediaType.trim().lowercase()
		else -> mediaType?.trim()?.lowercase()?.takeIf { it.isNotEmpty() }
	}
	return normalizedType
}
