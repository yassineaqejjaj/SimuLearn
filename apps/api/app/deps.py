"""Fabriques de fournisseurs (substituables dans les tests)."""
from functools import lru_cache

from app.config import get_settings
from app.providers.base import EvaluationProvider, VoiceSimulationProvider
from app.providers.claude_eval import ClaudeEvaluationProvider
from app.providers.mock import MockVoiceProvider
from app.providers.mock_eval import MockEvaluationProvider
from app.providers.openai_live import OpenAILiveProvider


@lru_cache
def _mock_voice() -> MockVoiceProvider:
    return MockVoiceProvider()


def get_voice_provider() -> VoiceSimulationProvider:
    s = get_settings()
    return _mock_voice() if s.voice_provider == "mock" else OpenAILiveProvider(s)


def get_evaluation_provider() -> EvaluationProvider:
    s = get_settings()
    return MockEvaluationProvider() if s.evaluation_provider == "mock" else ClaudeEvaluationProvider(s)
