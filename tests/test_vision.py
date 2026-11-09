"""Tests for Vision and Screen Inspection capabilities (Phase 3)."""

import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from PIL import Image
import pytest

from src.tools.screen_inspection import ScreenInspectionTool, capture_screen_bytes
from src.tools.base import ConfirmationPolicy
from src.tools import create_default_tool_registry


class TestScreenCaptureBytes:
    """Bellek içi ekran görüntüsü yakalama ve optimizasyon testleri."""

    def test_capture_screen_bytes_returns_jpeg_and_resizes(self, tmp_path):
        """2560x1440 boyutundaki ekranın 1920x1080'e küçültülüp JPEG baytları döndüğünü doğrular."""
        fake_img = Image.new("RGBA", (2560, 1440), color=(255, 0, 0, 255))

        with patch("PIL.ImageGrab.grab", return_value=fake_img) as mock_grab:
            jpeg_bytes = capture_screen_bytes(max_width=1920, max_height=1080)

            mock_grab.assert_called_once_with(all_screens=False)
            assert isinstance(jpeg_bytes, bytes)
            assert len(jpeg_bytes) > 0
            assert jpeg_bytes.startswith(b"\xff\xd8")

            with Image.open(io.BytesIO(jpeg_bytes)) as decoded:
                assert decoded.format == "JPEG"
                assert decoded.width <= 1920
                assert decoded.height <= 1080
                assert decoded.size == (1920, 1080)

    def test_capture_screen_bytes_smaller_screen_not_enlarged(self):
        """1280x720 boyutundaki ekranın gereksiz yere büyütülmediğini doğrular."""
        fake_img = Image.new("RGB", (1280, 720), color=(0, 255, 0))

        with patch("PIL.ImageGrab.grab", return_value=fake_img):
            jpeg_bytes = capture_screen_bytes(max_width=1920, max_height=1080)
            with Image.open(io.BytesIO(jpeg_bytes)) as decoded:
                assert decoded.size == (1280, 720)

    def test_capture_screen_bytes_converts_palette_mode(self):
        """Palette modundaki ('P') görüntünün RGB'ye dönüştürülüp hatasız JPEG olarak kodlandığını doğrular."""
        fake_img = Image.new("P", (800, 600))

        with patch("PIL.ImageGrab.grab", return_value=fake_img):
            jpeg_bytes = capture_screen_bytes()
            assert isinstance(jpeg_bytes, bytes)
            with Image.open(io.BytesIO(jpeg_bytes)) as decoded:
                assert decoded.format == "JPEG"

    def test_capture_screen_bytes_raises_on_error(self):
        """Ekran yakalama esnasında her iki yöntem de hata verirse hatanın fırlatıldığını doğrular."""
        with patch("PIL.ImageGrab.grab", side_effect=RuntimeError("Kilitli ekran")):
            with patch("src.tools.screen_inspection._capture_with_qscreen", side_effect=RuntimeError("Kilitli ekran")):
                with pytest.raises(RuntimeError, match="Kilitli ekran"):
                    capture_screen_bytes()

    def test_capture_screen_bytes_falls_back_to_qscreen(self):
        """Pillow grab başarısız olduğunda PySide6 QScreen yedeğinin çalıştığını doğrular."""
        with patch("PIL.ImageGrab.grab", side_effect=OSError("screen grab failed")):
            with patch("src.tools.screen_inspection._capture_with_qscreen", return_value=b"\xff\xd8qscreen") as mock_qscreen:
                result = capture_screen_bytes()
                assert result == b"\xff\xd8qscreen"
                mock_qscreen.assert_called_once()


class TestScreenInspectionTool:
    """ScreenInspectionTool ve Gemini Vision entegrasyon testleri."""

    def test_screen_inspection_tool_declaration(self):
        """Aracın adı, parametreleri ve teyit politikasını doğrular."""
        tool = ScreenInspectionTool(api_key="test-key")
        assert tool.name == "inspect_screen"
        assert tool.confirmation_policy == ConfirmationPolicy.IMMEDIATE
        assert "ekran" in tool.description.lower()

        decl = tool.get_declaration()
        assert decl["name"] == "inspect_screen"
        assert "query" in decl["parameters"]["properties"]

    def test_screen_inspection_tool_registered_in_default_registry(self):
        """create_default_tool_registry() fabrikasının inspect_screen aracını içerdiğini doğrular."""
        registry = create_default_tool_registry()
        tool = registry.get("inspect_screen")
        assert tool is not None
        assert isinstance(tool, ScreenInspectionTool)

    def test_screen_inspection_execute_success(self):
        """Mock Gemini client ile başarılı ekran analizini doğrular."""
        mock_client = MagicMock()
        mock_response = SimpleNamespace(text="Ekranda VS Code penceresi açık ve testler çalışıyor efendim.")
        mock_client.models.generate_content.return_value = mock_response

        dummy_bytes = b"\xff\xd8fakejpegbytes"
        tool = ScreenInspectionTool(
            client=mock_client,
            capture_fn=lambda: dummy_bytes,
        )

        result = tool.execute(query="Ekranda ne görüyorsun?")

        assert result.success is True
        assert "VS Code" in result.message
        assert result.message.endswith("efendim.")
        assert mock_client.models.generate_content.called

    def test_screen_inspection_cleans_markdown_for_tts(self):
        """Model yanıtındaki markdown formatlamalarını Piper TTS için temizlediğini doğrular."""
        mock_client = MagicMock()
        mock_response = SimpleNamespace(
            text="**Ekranda** şu detaylar görünüyor:\n* Hata: `SyntaxError`\n* Satır: 42 efendim."
        )
        mock_client.models.generate_content.return_value = mock_response

        tool = ScreenInspectionTool(
            client=mock_client,
            capture_fn=lambda: b"\xff\xd8fake",
        )

        result = tool.execute(query="Hata nedir?")
        assert result.success is True
        assert "*" not in result.message
        assert "`" not in result.message
        assert result.message.endswith("efendim.")

    def test_screen_inspection_execute_capture_error(self):
        """Ekran yakalama hatasında kullanıcıya nazik hata mesajı döndüğünü doğrular."""
        def failing_capture():
            raise RuntimeError("Ekran yakalanamadı")

        tool = ScreenInspectionTool(
            api_key="test-key",
            capture_fn=failing_capture,
        )

        result = tool.execute(query="Ekrana bak")
        assert result.success is False
        assert "alınamadı" in result.message.lower()

    def test_screen_inspection_execute_model_fallback_on_429(self):
        """Model 429 döndüğünde yedek modele geçildiğini doğrular."""
        mock_client = MagicMock()
        # İlk model 429 hatası fırlatır, ikincisi başarılı yanıt döner
        mock_client.models.generate_content.side_effect = [
            Exception("429 Resource has been exhausted"),
            SimpleNamespace(text="Yedek modelden gelen analiz efendim."),
        ]

        tool = ScreenInspectionTool(
            client=mock_client,
            capture_fn=lambda: b"\xff\xd8fake",
            fallback_models=["gemini-3.5-flash", "gemini-2.5-flash"],
        )

        result = tool.execute(query="Ekranda ne var?")
        assert result.success is True
        assert "Yedek modelden" in result.message
        assert mock_client.models.generate_content.call_count == 2

    def test_screen_inspection_execute_no_api_key_or_client(self):
        """API anahtarı ve client olmadan çalıştırıldığında nazik hata döndüğünü doğrular."""
        with patch("src.config.settings.GEMINI_API_KEY", None):
            tool = ScreenInspectionTool(
                api_key=None,
                client=None,
                capture_fn=lambda: b"\xff\xd8fake",
            )
            result = tool.execute(query="Ekrana bak")
            assert result.success is False
            assert "api anahtarı" in result.message.lower()


class TestGeminiProviderVisionIntegration:
    """GeminiProvider ve ScreenInspectionTool entegrasyon testleri."""

    def test_gemini_provider_executes_inspect_screen_tool(self):
        """GeminiProvider inspect_screen çağrısını yakalayıp ekran analizini seslendirir."""
        from src.brain.gemini_provider import GeminiProvider
        from src.tools.base import ToolResult

        registry = create_default_tool_registry()
        mock_vision_tool = MagicMock(spec=ScreenInspectionTool)
        mock_vision_tool.name = "inspect_screen"
        mock_vision_tool.get_declaration.return_value = {"name": "inspect_screen"}
        mock_vision_tool.execute.return_value = ToolResult(
            success=True,
            message="Ekranda VS Code penceresi açık ve testler yeşil efendim."
        )
        registry._tools["inspect_screen"] = mock_vision_tool

        provider = GeminiProvider(api_key="fake_key", tool_registry=registry)

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_call = MagicMock()
        mock_call.name = "inspect_screen"
        mock_call.args = {"query": "Ekranda ne görüyorsun?"}
        mock_resp.function_calls = [mock_call]
        mock_client.models.generate_content.return_value = mock_resp

        with patch.object(provider, "_get_client", return_value=mock_client):
            res = provider.generate_response("Ekranda ne var?")
            assert res.tool_called == "inspect_screen"
            assert "VS Code" in res.text
            assert res.text.endswith("efendim.")
            mock_vision_tool.execute.assert_called_once_with(query="Ekranda ne görüyorsun?")

    def test_gemini_provider_compound_command_with_vision(self):
        """Kullanıcı hem ses ayarı hem ekran incelemesi istediğinde iki aracı ardışık çalıştırıp 've' ile bağlar."""
        from src.brain.gemini_provider import GeminiProvider
        from src.tools.base import ToolResult

        registry = create_default_tool_registry()

        mock_audio_tool = MagicMock()
        mock_audio_tool.name = "control_system_audio"
        mock_audio_tool.get_declaration.return_value = {"name": "control_system_audio"}
        mock_audio_tool.execute.return_value = ToolResult(success=True, message="Ses kapatıldı efendim.")
        registry._tools["control_system_audio"] = mock_audio_tool

        mock_vision_tool = MagicMock()
        mock_vision_tool.name = "inspect_screen"
        mock_vision_tool.get_declaration.return_value = {"name": "inspect_screen"}
        mock_vision_tool.execute.return_value = ToolResult(success=True, message="Ekranda tarayıcı açık efendim.")
        registry._tools["inspect_screen"] = mock_vision_tool

        provider = GeminiProvider(api_key="fake_key", tool_registry=registry)

        mock_client = MagicMock()
        mock_resp = MagicMock()
        call1 = MagicMock()
        call1.name = "control_system_audio"
        call1.args = {"action": "mute"}
        call2 = MagicMock()
        call2.name = "inspect_screen"
        call2.args = {"query": "Ekrana bak"}
        mock_resp.function_calls = [call1, call2]
        mock_client.models.generate_content.return_value = mock_resp

        with patch.object(provider, "_get_client", return_value=mock_client):
            res = provider.generate_response("Sesi kapat ve ekrana bak")
            assert "control_system_audio" in res.tool_called
            assert "inspect_screen" in res.tool_called
            assert "Ses kapatıldı" in res.text
            assert "Ekranda tarayıcı açık" in res.text
            assert " ve " in res.text
            assert res.text.endswith("efendim.")
