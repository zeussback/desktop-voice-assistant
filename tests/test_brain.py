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
    provider = GeminiProvider(api_key="fake_key", model="gemini-3.8-flash")

    mock_response = MagicMock()
    mock_response.text = "Gemini cevabı"

    with patch.object(provider, "_call_api", return_value="Gemini cevabı"):
        result = provider.generate_response("Merhaba")
        assert result.text == "Gemini cevabı"
        assert result.provider == "gemini"


def test_gemini_provider_fallback_on_503():
    """Model 503 (yüksek yoğunluk) hatası verdiğinde diğer modele geçmeli."""
    provider = GeminiProvider(api_key="fake_key", model="gemini-3.8-flash")

    mock_client = MagicMock()
    # 1. model 503 fırlatır, 2. model başarılı yanıt döner
    mock_resp = MagicMock()
    mock_resp.text = "Yedek model cevabı"
    mock_client.models.generate_content.side_effect = [
        Exception("503 UNAVAILABLE. This model is currently experiencing high demand"),
        mock_resp,
    ]

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.generate_response("Merhaba")
        assert result.text == "Yedek model cevabı"
        assert mock_client.models.generate_content.call_count == 2


def test_gemini_provider_fallback_on_timeout():
    """Model 504 Gateway Timeout veya Timeout hatası verdiğinde diğer modele geçmeli."""
    provider = GeminiProvider(api_key="fake_key", model="gemini-3.5-flash")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Timeout sonrası yedek cevabı"
    mock_client.models.generate_content.side_effect = [
        Exception("504 DEADLINE_EXCEEDED. Deadline expired before operation could complete."),
        mock_resp,
    ]

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.generate_response("Merhaba")
        assert result.text == "Timeout sonrası yedek cevabı"
        assert mock_client.models.generate_content.call_count == 2



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


def test_gemini_provider_executes_function_call():
    """Gemini API'den function call geldiğinde ToolRegistry üzerinden çalıştırmalı."""
    from src.tools.registry import ToolRegistry
    from src.tools.base import BaseTool, ToolResult

    class TestMockTool(BaseTool):
        name = "mock_calc"
        description = "Mock calculator"

        def get_declaration(self):
            return {"name": self.name, "description": self.description}

        def execute(self, a=0, b=0):
            return ToolResult(success=True, message=f"Sonuç: {a + b}")

    registry = ToolRegistry()
    registry.register(TestMockTool())

    provider = GeminiProvider(api_key="fake_key", tool_registry=registry)

    # Mock Gemini client response with function_calls
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_call = MagicMock()
    mock_call.name = "mock_calc"
    mock_call.args = {"a": 10, "b": 25}
    mock_resp.function_calls = [mock_call]
    mock_client.models.generate_content.return_value = mock_resp

    with patch.object(provider, "_get_client", return_value=mock_client):
        res = provider.generate_response("10 ile 25'i topla")
        assert res.tool_called == "mock_calc"
        assert res.text == "Sonuç: 35"
        assert res.tool_result["success"] is True


def test_gemini_provider_executes_multiple_parallel_function_calls():
    """Gemini API'den birden fazla paralel araç çağrısı geldiğinde sırayla çalıştırmalı."""
    from src.tools.registry import ToolRegistry
    from src.tools.base import BaseTool, ToolResult

    class ToolA(BaseTool):
        name = "tool_a"
        description = "Tool A"
        def get_declaration(self): return {"name": self.name}
        def execute(self, val=""): return ToolResult(success=True, message=f"A:{val}")

    class ToolB(BaseTool):
        name = "tool_b"
        description = "Tool B"
        def get_declaration(self): return {"name": self.name}
        def execute(self, val=""): return ToolResult(success=True, message=f"B:{val}")

    registry = ToolRegistry()
    registry.register(ToolA())
    registry.register(ToolB())

    provider = GeminiProvider(api_key="fake_key", tool_registry=registry)

    mock_client = MagicMock()
    mock_resp = MagicMock()
    call1 = MagicMock()
    call1.name = "tool_a"
    call1.args = {"val": "1"}
    call2 = MagicMock()
    call2.name = "tool_b"
    call2.args = {"val": "2"}
    mock_resp.function_calls = [call1, call2]
    mock_client.models.generate_content.return_value = mock_resp

    with patch.object(provider, "_get_client", return_value=mock_client):
        res = provider.generate_response("A ve B'yi çalıştır")
        assert "tool_a" in res.tool_called
        assert "tool_b" in res.tool_called
        assert "A:1" in res.text
        assert "B:2" in res.text
        assert res.tool_result["success"] is True
        assert len(res.tool_result["results"]) == 2


def test_gemini_provider_handles_confirmation_tool():
    """Kritik araç çağrıldığında needs_confirmation ve prompt dönmeli."""
    from src.tools.registry import ToolRegistry
    from src.tools.system_power import SystemPowerTool

    registry = ToolRegistry()
    registry.register(SystemPowerTool())

    provider = GeminiProvider(api_key="fake_key", tool_registry=registry)

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_call = MagicMock()
    mock_call.name = "control_system_power"
    mock_call.args = {"action": "shutdown"}
    mock_resp.function_calls = [mock_call]
    mock_client.models.generate_content.return_value = mock_resp

    with patch.object(provider, "_get_client", return_value=mock_client):
        res = provider.generate_response("Bilgisayarı kapat")
        assert res.tool_called == "control_system_power"
        assert res.needs_confirmation is True
        assert "emin misiniz" in res.text
