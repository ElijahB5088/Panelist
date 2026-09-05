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
	val currentIndex: Int = 0,
	val isSubmitting: Boolean = false,
	val errorMessage: String? = null
)

class HomeViewModel(private val repository: RecommendationRepository) : ViewModel() {
	private val _uiState = MutableStateFlow(HomeUiState())
	val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

	init {
		refresh()
	}

	fun refresh() {
		viewModelScope.launch {
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
		val recommendation = state.recommendations.getOrNull(state.currentIndex) ?: return
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
}
