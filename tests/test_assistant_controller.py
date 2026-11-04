from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(["test", "-platform", "offscreen"])

from src.core.assistant import AssistantController
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
