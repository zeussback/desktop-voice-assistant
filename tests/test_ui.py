import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Test için QApplication örneğini garantiye al
app = QApplication.instance()
if app is None:
    app = QApplication(["test", "-platform", "offscreen"])

from src.ui.widget import GlassLiquidWidget, AssistantUIState


def test_widget_creation_and_flags():
    """Widget'ın çerçevesiz, her zaman üstte ve şeffaf özelliklerle oluşturulduğunu test eder."""
    widget = GlassLiquidWidget()
    assert widget.windowFlags() & Qt.FramelessWindowHint
    assert widget.windowFlags() & Qt.WindowStaysOnTopHint
    assert widget.testAttribute(Qt.WA_TranslucentBackground)


def test_widget_state_transitions():
    """Widget'ın durum geçişlerini ve metin güncellemelerini test eder."""
    widget = GlassLiquidWidget()

    widget.set_state(AssistantUIState.LISTENING)
    assert widget.current_state == AssistantUIState.LISTENING
    assert "Dinleniyor" in widget.status_label.text()

    widget.set_state(AssistantUIState.THINKING)
    assert widget.current_state == AssistantUIState.THINKING
    assert "Düşünülüyor" in widget.status_label.text()

    widget.set_state(AssistantUIState.SPEAKING)
    assert widget.current_state == AssistantUIState.SPEAKING
    assert "Konuşuyor" in widget.status_label.text()

    widget.set_state(AssistantUIState.IDLE)
    assert widget.current_state == AssistantUIState.IDLE


def test_widget_audio_level():
    """Mikrofon ses seviyesi güncellendiğinde wave animasyon seviyesinin değiştiğini test eder."""
    widget = GlassLiquidWidget()
    widget.update_audio_level(0.75)
    assert widget.audio_level == 0.75
