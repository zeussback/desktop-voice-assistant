from unittest.mock import MagicMock, patch
import pytest

from src.voice.tts_base import BaseTTSClient
from src.voice.edge_tts_client import EdgeTTSClient
from src.voice.piper_client import PiperTTSClient
from src.voice.hybrid_tts import HybridTTS
from src.voice.audio_player import AudioPlayer


def test_edge_tts_client_mocked():
    """Edge-TTS istemcisinin mock ile ses ürettiğini test eder."""
    client = EdgeTTSClient(voice="tr-TR-AhmetNeural")
    with patch.object(client, "_synthesize_async_wrapper", return_value=b"EDGE_TTS_BYTES"):
        audio_bytes = client.synthesize("Selam")
        assert audio_bytes == b"EDGE_TTS_BYTES"


def test_hybrid_tts_uses_primary_when_available():
    """Birincil motor (Piper) aktifse o kullanılmalı."""
    mock_primary = MagicMock(spec=BaseTTSClient)
    mock_primary.is_available.return_value = True
    mock_primary.synthesize.return_value = b"PIPER_AUDIO"

    mock_fallback = MagicMock(spec=BaseTTSClient)

    hybrid = HybridTTS(providers=[mock_primary, mock_fallback])
    result = hybrid.synthesize("Test metni")

    assert result == b"PIPER_AUDIO"
    mock_fallback.synthesize.assert_not_called()


def test_hybrid_tts_falls_back_when_offline():
    """Birincil motor kapalıysa otomatik olarak fallback (EdgeTTS) kullanılmalı."""
    mock_primary = MagicMock(spec=BaseTTSClient)
    mock_primary.is_available.return_value = False

    mock_fallback = MagicMock(spec=BaseTTSClient)
    mock_fallback.is_available.return_value = True
    mock_fallback.synthesize.return_value = b"FALLBACK_AUDIO"

    hybrid = HybridTTS(providers=[mock_primary, mock_fallback])
    result = hybrid.synthesize("Test metni")

    assert result == b"FALLBACK_AUDIO"
    mock_fallback.synthesize.assert_called_once_with("Test metni")


def test_audio_player_state():
    """AudioPlayer başlatma ve durum testleri."""
    player = AudioPlayer()
    assert not player.is_playing()


def test_piper_client_not_available_when_model_missing(tmp_path):
    """Model dosyası yoksa is_available() False dönmeli."""
    client = PiperTTSClient(model_path=str(tmp_path / "non_existent.onnx"))
    assert not client.is_available()


def test_piper_client_mocked_synthesis(tmp_path):
    """Model mevcutken Piper'ın ses baytları ürettiğini test eder."""
    fake_model = tmp_path / "test.onnx"
    fake_model.write_text("model")
    client = PiperTTSClient(model_path=str(fake_model))
    with patch.object(client, "_synthesize_raw", return_value=b"PIPER_WAV_BYTES"):
        assert client.synthesize("Merhaba") == b"PIPER_WAV_BYTES"


def test_piper_real_model_available():
    """Gerçek indirilen modelin mevcut olduğunu ve is_available() döndüğünü doğrular."""
    client = PiperTTSClient()
    assert client.is_available() is True

