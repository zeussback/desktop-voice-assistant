import math
from enum import Enum
from typing import Optional
from PySide6.QtCore import (
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
    QRectF,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.styles import UITheme


class AssistantUIState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class GlassLiquidWidget(QWidget):
    """Ekranın üstünde beliren şık, animasyonlu 'glass-liquid' kapsül durum widget'ı."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Çerçevesiz, şeffaf ve her zaman en üstte
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.current_state = AssistantUIState.IDLE
        self.audio_level: float = 0.0
        self.pulse_phase: float = 0.0

        # Kapsül Boyutları
        self.widget_width = 320
        self.widget_height = 56
        self.setFixedSize(self.widget_width, self.widget_height)

        # Arayüz Elemanları
        self._init_layout()

        # Dalgalanma / Nabız Zamanlayıcısı (Animasyon döngüsü)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_animation_tick)
        self.anim_timer.start(30)  # ~33 FPS

        # Konumlandırma
        self._position_on_screen()

    def _init_layout(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 8, 20, 8)
        main_layout.setSpacing(12)

        # Sol taraf: Animasyonlu ikon / dalga alanı için boşluk
        self.indicator_box = QWidget()
        self.indicator_box.setFixedSize(28, 28)
        main_layout.addWidget(self.indicator_box)

        # Sağ taraf: Metinler (Durum + Detay)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignVCenter)

        self.status_label = QLabel("Hazır")
        status_font = QFont("Segoe UI", 11, QFont.DemiBold)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #F0F5FF;")

        self.sub_label = QLabel("Asistan aktif")
        sub_font = QFont("Segoe UI", 8)
        self.sub_label.setFont(sub_font)
        self.sub_label.setStyleSheet("color: #8C9BB5;")

        text_layout.addWidget(self.status_label)
        text_layout.addWidget(self.sub_label)
        main_layout.addLayout(text_layout)

    def _position_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.widget_width) // 2
            y = 25  # Ekranın üst kenarından 25px aşağıda
            self.move(x, y)

    def _on_animation_tick(self):
        self.pulse_phase += 0.1
        if self.pulse_phase > 2 * math.pi:
            self.pulse_phase -= 2 * math.pi
        self.update()

    def set_state(self, state: AssistantUIState, subtext: Optional[str] = None):
        """Asistanın görsel durumunu günceller."""
        self.current_state = state

        if state == AssistantUIState.LISTENING:
            self.status_label.setText("Dinleniyor...")
            self.sub_label.setText(subtext or "Konuşmanız dinleniyor")
            self.show_animated()
        elif state == AssistantUIState.THINKING:
            self.status_label.setText("Düşünülüyor...")
            self.sub_label.setText(subtext or "Yapay zeka yanıt hazırlıyor")
        elif state == AssistantUIState.SPEAKING:
            self.status_label.setText("Konuşuyor...")
            self.sub_label.setText(subtext or "Asistan cevap veriyor")
        elif state == AssistantUIState.ERROR:
            self.status_label.setText("Bir Sorun Oluştu")
            self.sub_label.setText(subtext or "Lütfen tekrar deneyin")
        elif state == AssistantUIState.IDLE:
            self.status_label.setText("Hazır")
            self.sub_label.setText(subtext or "Ctrl+Space ile başlatın")
            self.hide_animated()

        self.update()

    def update_audio_level(self, level: float):
        """Mikrofondan gelen anlık genlik değerini (0.0 - 1.0) günceller."""
        self.audio_level = max(0.0, min(1.0, level))
        self.update()

    def show_animated(self):
        """Üstten yumuşak yaylanarak açılma animasyonu."""
        self.show()
        self.raise_()

    def hide_animated(self):
        """Kapanma animasyonu ve gizleme."""
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)

        # 1. Glass-Liquid Arka Plan Çizimi
        path = QPainterPath()
        path.addRoundedRect(rect, 24, 24)

        # Yarı saydam buzlu cam dolgusu
        painter.fillPath(path, QBrush(UITheme.BG_COLOR))

        # 2. İnce Vurgu Kenarlığı
        pen = QPen(UITheme.BORDER_COLOR, 1.2)
        painter.strokePath(path, pen)

        # 3. Durum Glow / Gradient Göstergesi
        self._paint_state_indicator(painter)

    def _paint_state_indicator(self, painter: QPainter):
        # Gösterge alanı: Sol kutucuk (x=24, y=14)
        cx = 34
        cy = self.height() / 2

        if self.current_state == AssistantUIState.LISTENING:
            # Dinleme Modu: Ses seviyesine göre boyu uzayan 3 adet cyan ses dalga çubuğu
            bars = 3
            spacing = 6
            start_x = cx - (bars * spacing) / 2

            for i in range(bars):
                # Dalgalanma yüksekliği
                wave = math.sin(self.pulse_phase + i * 1.2) * 4
                h = 6 + (self.audio_level * 18) + wave
                h = max(4, min(22, h))

                bx = start_x + (i * spacing)
                by = cy - (h / 2)

                grad = QLinearGradient(bx, by, bx, by + h)
                grad.setColorAt(0, UITheme.LISTENING_GRAD_START)
                grad.setColorAt(1, UITheme.LISTENING_GRAD_END)

                painter.setPen(Qt.NoPen)
                painter.setBrush(grad)
                painter.drawRoundedRect(QRectF(bx, by, 3, h), 1.5, 1.5)

        elif self.current_state == AssistantUIState.THINKING:
            # Düşünme Modu: Dönen / nabız atan mor parıltılı daire
            pulse = (math.sin(self.pulse_phase * 1.5) + 1.0) / 2.0  # 0.0 - 1.0
            r = 7 + (pulse * 3)

            grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
            grad.setColorAt(0, UITheme.THINKING_GRAD_START)
            grad.setColorAt(1, UITheme.THINKING_GRAD_END)

            painter.setPen(Qt.NoPen)
            painter.setBrush(grad)
            painter.drawEllipse(QPoint(int(cx), int(cy)), int(r), int(r))

        elif self.current_state == AssistantUIState.SPEAKING:
            # Konuşma Modu: Zümrüt yeşili yumuşak atan dalga halkası
            pulse = (math.sin(self.pulse_phase * 2.0) + 1.0) / 2.0
            r = 6 + (pulse * 4)

            grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
            grad.setColorAt(0, UITheme.SPEAKING_GRAD_START)
            grad.setColorAt(1, UITheme.SPEAKING_GRAD_END)

            painter.setPen(Qt.NoPen)
            painter.setBrush(grad)
            painter.drawEllipse(QPoint(int(cx), int(cy)), int(r), int(r))

        elif self.current_state == AssistantUIState.ERROR:
            # Hata Modu: Kırmızı sabit nokta
            painter.setPen(Qt.NoPen)
            painter.setBrush(UITheme.ERROR_GRAD_START)
            painter.drawEllipse(QPoint(int(cx), int(cy)), 7, 7)
