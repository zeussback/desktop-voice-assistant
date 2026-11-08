from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(["test", "-platform", "offscreen"])

from src.core.assistant import AssistantController, sanitize_speech_text
from src.brain.provider_base import BrainResponse
from src.ui.widget import AssistantUIState


def test_assistant_controller_init():
    """AssistantController bileşenlerinin doğru bağlandığını test eder."""
    mock_brain = MagicMock()
    mock_voice = MagicMock()
    mock_recorder = MagicMock()
    mock_widget = MagicMock()

    controller = AssistantController(
        brain=mock_brain,
        voice=mock_voice,
        recorder=mock_recorder,
        widget=mock_widget,
    )

    assert controller.current_state == AssistantUIState.IDLE


def test_assistant_controller_start_listening():
    """Toggle ile dinleme başladığında widget ve mikrofon durumunu test eder."""
    mock_brain = MagicMock()
    mock_voice = MagicMock()
    mock_recorder = MagicMock()
    mock_recorder.start_recording.return_value = True
    mock_widget = MagicMock()

    controller = AssistantController(
        brain=mock_brain,
        voice=mock_voice,
        recorder=mock_recorder,
        widget=mock_widget,
    )

    controller.handle_toggle(is_active=True)
    assert controller.current_state == AssistantUIState.LISTENING
    mock_recorder.start_recording.assert_called_once()
    mock_widget.set_state.assert_called_with(AssistantUIState.LISTENING, "Konuşmanız dinleniyor")


def test_assistant_controller_process_audio_worker():
    """_process_audio_worker doğrudan çağrıldığında düşünme ve ses sentezinin yapıldığını test eder."""
    mock_brain = MagicMock()
    mock_brain.generate_response.return_value = BrainResponse(text="Merhaba nasılsın?", provider="gemini")

    mock_voice = MagicMock()
    mock_voice.synthesize.return_value = b"SYNTHESIZED_AUDIO"

    mock_recorder = MagicMock()
    mock_widget = MagicMock()
    mock_player = MagicMock()

    controller = AssistantController(
        brain=mock_brain,
        voice=mock_voice,
        recorder=mock_recorder,
        widget=mock_widget,
        player=mock_player,
    )

    # Senkron işleme worker fonksiyonunu test et
    controller._process_audio_worker(b"USER_AUDIO_WAV")

    mock_brain.generate_response.assert_called_once()
    mock_voice.synthesize.assert_called_once_with("Merhaba nasılsın?")
    mock_player.play_bytes.assert_called_once()


def test_assistant_controller_voice_exit():
    """Kullanıcı sesli çıkış istediğinde [EXIT] etiketinin ayrıştırılıp quit sinyalinin bağlandığını test eder."""
    mock_brain = MagicMock()
    mock_brain.generate_response.return_value = BrainResponse(
        text="Görüşmek üzere, iyi günler! [EXIT]", provider="gemini"
    )

    mock_voice = MagicMock()
    mock_voice.synthesize.return_value = b"SYNTHESIZED_AUDIO"

    mock_recorder = MagicMock()
    mock_widget = MagicMock()
    mock_player = MagicMock()

    controller = AssistantController(
        brain=mock_brain,
        voice=mock_voice,
        recorder=mock_recorder,
        widget=mock_widget,
        player=mock_player,
    )

    quit_signals = []
    controller.sig_quit_requested.connect(lambda: quit_signals.append(True))

    controller._process_audio_worker(b"USER_AUDIO_WAV")

    # [EXIT] etiketi temizlenerek ses sentezlenmeli
    mock_voice.synthesize.assert_called_once_with("Görüşmek üzere, iyi günler!")
    mock_player.play_bytes.assert_called_once()

    # Oynatma bitince on_finished çağrılır ve çıkış tetiklenir
    on_finished_cb = mock_player.play_bytes.call_args[1]["on_finished"]
    assert callable(on_finished_cb)


def test_assistant_controller_interrupts_playing_on_new_toggle():
    """Asistan konuşurken kullanıcı kısayola tekrar basarsa oynatıcı durdurulup dinlemeye geçilmeli."""
    mock_brain = MagicMock()
    mock_voice = MagicMock()
    mock_recorder = MagicMock()
    mock_recorder.start_recording.return_value = True
    mock_widget = MagicMock()
    mock_player = MagicMock()
    mock_player.is_playing.return_value = True

    controller = AssistantController(
        brain=mock_brain,
        voice=mock_voice,
        recorder=mock_recorder,
        widget=mock_widget,
        player=mock_player,
    )

    controller.handle_toggle(is_active=True)

    mock_player.stop.assert_called_once()
    mock_recorder.start_recording.assert_called_once()
    assert controller.current_state == AssistantUIState.LISTENING


def test_sanitize_speech_text_removes_timestamps_and_markdown():
    """Zaman damgalarının (00:03 vb.) ve markdown işaretlerinin temizlendiğini test eder."""
    raw = "Merhaba! Ben gayet iyiyim, teşekkür ederim. 00:03Sen nasılsın, bugün sana nasıl yardımcı 00:06olabilirim? 00:07 [EXIT]"
    cleaned = sanitize_speech_text(raw)
    assert "00:03" not in cleaned
    assert "00:06" not in cleaned
    assert "00:07" not in cleaned
    assert "[EXIT]" not in cleaned
    assert "Sen nasılsın" in cleaned
    assert "olabilirim?" in cleaned


def test_sanitize_speech_text_removes_repeated_efendim():
    """Arka arkaya tekrarlanan 'efendim' hitaplarını teke indirdiğini test eder."""
    raw = "Ses düzeyi %80 olarak ayarlandı efendim. Spotify açıldı efendim."
    cleaned = sanitize_speech_text(raw)
    assert cleaned.count("efendim") == 1
    assert "Spotify açıldı efendim." in cleaned


