from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from src.voice.tts_base import BaseTTSClient
from src.voice.voicestudio_client import VoiceStudioClient
from src.voice.edge_tts_client import EdgeTTSClient
from src.voice.hybrid_tts import HybridTTS
from src.voice.audio_player import AudioPlayer


def test_voicestudio_client_health_check_offline():
    """VoiceStudio sunucusu kapalıyken is_available() False dönmeli."""
    client = VoiceStudioClient(base_url="http://127.0.0.1:9999")  # kapalı port
    assert not client.is_available()


def test_voicestudio_client_mocked_success():
    """VoiceStudio sunucusu aktifken ses sentezini test eder."""
    client = VoiceStudioClient(base_url="http://localhost:3900")
    with patch.object(client, "is_available", return_value=True):
        with patch.object(client, "_synthesize_remote", return_value=b"FAKE_WAV_BYTES"):
            audio_bytes = client.synthesize("Merhaba dünya")
            assert audio_bytes == b"FAKE_WAV_BYTES"


def test_edge_tts_client_mocked():
    """Edge-TTS istemcisinin mock ile ses ürettiğini test eder."""
    client = EdgeTTSClient(voice="tr-TR-AhmetNeural")
    with patch.object(client, "_synthesize_async_wrapper", return_value=b"EDGE_TTS_BYTES"):
        audio_bytes = client.synthesize("Selam")
        assert audio_bytes == b"EDGE_TTS_BYTES"


def test_hybrid_tts_uses_primary_when_available():
    """VoiceStudio erişilebilirse birincil motor kullanılmalı."""
    mock_vs = MagicMock(spec=BaseTTSClient)
    mock_vs.is_available.return_value = True
    mock_vs.synthesize.return_value = b"VOICESTUDIO_AUDIO"

    mock_fallback = MagicMock(spec=BaseTTSClient)

    hybrid = HybridTTS(primary=mock_vs, fallback=mock_fallback)
    result = hybrid.synthesize("Test metni")

    assert result == b"VOICESTUDIO_AUDIO"
    mock_fallback.synthesize.assert_not_called()


def test_hybrid_tts_falls_back_when_offline():
    """VoiceStudio kapalıysa otomatik olarak fallback (EdgeTTS) kullanılmalı."""
    mock_vs = MagicMock(spec=BaseTTSClient)
    mock_vs.is_available.return_value = False

    mock_fallback = MagicMock(spec=BaseTTSClient)
    mock_fallback.synthesize.return_value = b"FALLBACK_AUDIO"

    hybrid = HybridTTS(primary=mock_vs, fallback=mock_fallback)
    result = hybrid.synthesize("Test metni")

    assert result == b"FALLBACK_AUDIO"
    mock_fallback.synthesize.assert_called_once_with("Test metni")


def test_audio_player_state():
    """AudioPlayer başlatma ve durum testleri."""
    player = AudioPlayer()
    assert not player.is_playing()
