import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap

# Test için QApplication örneğini garantiye al
app = QApplication.instance()
if app is None:
    app = QApplication(["test", "-platform", "offscreen"])

from src.ui.widget import GlassLiquidWidget, AssistantUIState
from src.ui.styles import UITheme


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
    """Mikrofon ses seviyesi güncellendiğinde seviyenin güncellendiğini test eder."""
    widget = GlassLiquidWidget()
    widget.update_audio_level(0.75)
    assert widget.audio_level == 0.75


def test_widget_theme_colors():
    """Yeni temada mor/mavi yerine nane, kehribar ve mercan renklerinin tanımlı olduğunu doğrular."""
    widget = GlassLiquidWidget()

    widget.set_state(AssistantUIState.LISTENING)
    accent, _, _, _ = widget._get_current_colors()
    assert accent == UITheme.LISTENING_ACCENT

    widget.set_state(AssistantUIState.THINKING)
    accent, _, _, _ = widget._get_current_colors()
    assert accent == UITheme.THINKING_ACCENT

    widget.set_state(AssistantUIState.SPEAKING)
    accent, _, _, _ = widget._get_current_colors()
    assert accent == UITheme.SPEAKING_ACCENT


def test_widget_paint_all_states():
    """Tüm arayüz ve yüz ifadelerinin çiziminde hata oluşmadığını doğrular."""
    widget = GlassLiquidWidget()
    pixmap = QPixmap(widget.size())

    for state in AssistantUIState:
        widget.set_state(state)
        widget.is_blinking = True
        widget.render(pixmap)
        widget.is_blinking = False
        widget.render(pixmap)


def test_widget_animations_lifecycle():
    """Açılma ve kapanma animasyon metotlarının hatasız çalıştığını test eder."""
    widget = GlassLiquidWidget()
    widget.show_animated()
    assert widget.isVisible()

    widget.hide_animated()
    # Kapanma animasyonu tetiklenmiş olmalı
    assert widget._is_animating_hide is True
    # Animasyon tamamlandığında gizlenir
    widget._on_slide_anim_finished()
    assert widget._is_animating_hide is False
    assert not widget.isVisible()


def test_widget_show_ready_banner():
    """show_ready_banner metodu çağrıldığında 'Dinlemeye Hazır' metninin gösterildiğini test eder."""
    widget = GlassLiquidWidget()
    widget.show_ready_banner(duration_ms=4500)

    assert widget.current_state == AssistantUIState.IDLE
    assert "Dinlemeye Hazır" in widget.status_label.text()
    assert widget.isVisible()

    # Otomatik gizleme fonksiyonunu test et
    widget._auto_hide_ready_banner()
    assert widget._is_animating_hide is True

