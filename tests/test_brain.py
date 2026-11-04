from unittest.mock import MagicMock, patch
import pytest

from src.brain.provider_base import BaseBrainProvider, BrainResponse
from src.brain.gemini_provider import GeminiProvider
from src.brain.ollama_provider import OllamaProvider
from src.brain.hybrid_brain import HybridBrain


def test_brain_response_model():
    """BrainResponse veri modelini doğrular."""
    resp = BrainResponse(text="Merhaba!", provider="gemini")
    assert resp.text == "Merhaba!"
    assert resp.provider == "gemini"


def test_gemini_provider_mocked():
    """Gemini API çağrısının mock ile doğru format döndürdüğünü test eder."""
    provider = GeminiProvider(api_key="fake_key", model="gemini-2.0-flash")

    mock_response = MagicMock()
    mock_response.text = "Gemini cevabı"

    with patch.object(provider, "_call_api", return_value="Gemini cevabı"):
        result = provider.generate_response("Merhaba")
        assert result.text == "Gemini cevabı"
        assert result.provider == "gemini"


def test_ollama_provider_mocked():
    """Ollama API çağrısının mock ile doğru format döndürdüğünü test eder."""
    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen2.5:3b")

    with patch.object(provider, "_call_api", return_value="Ollama cevabı"):
        result = provider.generate_response("Nasılsın?")
        assert result.text == "Ollama cevabı"
        assert result.provider == "ollama"


def test_hybrid_brain_primary_success():
    """Birincil model (Gemini) başarılıysa fallback çağrılmamalıdır."""
    mock_primary = MagicMock(spec=BaseBrainProvider)
    mock_primary.generate_response.return_value = BrainResponse(text="Bulut yanıtı", provider="gemini")

    mock_fallback = MagicMock(spec=BaseBrainProvider)

    brain = HybridBrain(primary=mock_primary, fallback=mock_fallback)
    result = brain.generate_response("Test")

    assert result.text == "Bulut yanıtı"
    assert result.provider == "gemini"
    mock_fallback.generate_response.assert_not_called()


def test_hybrid_brain_fallback_on_error():
    """Birincil model hata verirse otomatik olarak fallback devreye girmelidir."""
    mock_primary = MagicMock(spec=BaseBrainProvider)
    mock_primary.generate_response.side_effect = RuntimeError("API Limit Exceeded or Network Error")

    mock_fallback = MagicMock(spec=BaseBrainProvider)
    mock_fallback.generate_response.return_value = BrainResponse(text="Yerel yedek yanıtı", provider="ollama")

    brain = HybridBrain(primary=mock_primary, fallback=mock_fallback)
    result = brain.generate_response("Test")

    assert result.text == "Yerel yedek yanıtı"
    assert result.provider == "ollama"
    mock_fallback.generate_response.assert_called_once_with("Test", None)
