import math
from enum import Enum
from typing import Optional
from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QTimer,
    Qt,
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
    """Ekranın üstünde beliren şık, animasyonlu 'obsidian glass' ve canlı yüz ifadeli kapsül durum widget'ı."""

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

        # Canlı Yüz İfadesi & Göz Kırpma Durumu
        self.blink_counter: int = 0
        self.is_blinking: bool = False

        # Kapsül Boyutları
        self.widget_width = 340
        self.widget_height = 58
        self.setFixedSize(self.widget_width, self.widget_height)

        # Açılış / Kapanış Animasyonları
        self._is_animating_hide: bool = False
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._slide_anim.finished.connect(self._on_slide_anim_finished)

        # Arayüz Elemanları
        self._init_layout()

        # Animasyon Döngüsü (~33 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_animation_tick)
        self.anim_timer.start(30)

        # Konumlandırma
        self._target_x, self._target_y = self._get_screen_target_pos()
        self.move(self._target_x, self._target_y)

    def _get_screen_target_pos(self) -> tuple[int, int]:
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.widget_width) // 2
            y = 25  # Ekranın üst kenarından 25px aşağıda
            return x, y
        return 100, 25

    def _init_layout(self):
        main_layout = QHBoxLayout(self)
        # Sol 56px yüz rozetine, sağ 40px mikro dalga göstergesine ayrılır
        main_layout.setContentsMargins(56, 6, 42, 6)
        main_layout.setSpacing(8)

        # Metinler (Durum + Detay)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setAlignment(Qt.AlignVCenter)

        self.status_label = QLabel("Hazır")
        status_font = QFont("Segoe UI", 11, QFont.DemiBold)
        status_font.setStyleHint(QFont.SansSerif)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #FFFFFF;")

        self.sub_label = QLabel("Asistan aktif")
        sub_font = QFont("Segoe UI", 8)
        sub_font.setStyleHint(QFont.SansSerif)
        self.sub_label.setFont(sub_font)
        self.sub_label.setStyleSheet("color: #94A3B8;")

        text_layout.addWidget(self.status_label)
        text_layout.addWidget(self.sub_label)
        main_layout.addLayout(text_layout)

    def _on_animation_tick(self):
        # 1. Nabız fazını ilerlet
        self.pulse_phase += 0.1
        if self.pulse_phase > 2 * math.pi:
            self.pulse_phase -= 2 * math.pi

        # 2. Doğal Göz Kırpma Döngüsü (~3.5 saniyede bir 180ms kırpma)
        self.blink_counter += 1
        if not self.is_blinking and self.blink_counter > 105:
            self.is_blinking = True
            self.blink_counter = 0
        elif self.is_blinking and self.blink_counter > 6:
            self.is_blinking = False
            self.blink_counter = 0

        self.update()

    def show_ready_banner(self, duration_ms: int = 4500):
        """Uygulama ilk açıldığında 'Dinlemeye Hazır' olarak belirir ve süre dolunca otomatik kapanır."""
        self.current_state = AssistantUIState.IDLE
        self.status_label.setText("Dinlemeye Hazır")
        self.sub_label.setText("Ctrl+Space ile başlatın")
        self.show_animated()

        # Süre dolunca eğer kullanıcı henüz dinleme moduna geçmediyse otomatik gizle
        if hasattr(self, "_ready_timer") and self._ready_timer.isActive():
            self._ready_timer.stop()
        self._ready_timer = QTimer(self)
        self._ready_timer.setSingleShot(True)
        self._ready_timer.timeout.connect(self._auto_hide_ready_banner)
        self._ready_timer.start(duration_ms)

    def _auto_hide_ready_banner(self):
        """Kullanıcı kısayola basmadıysa hazır karşılama penceresini kapatır."""
        if self.current_state == AssistantUIState.IDLE:
            self.hide_animated()

    def set_state(self, state: AssistantUIState, subtext: Optional[str] = None):
        """Asistanın görsel durumunu günceller."""
        # Eğer hazır olma karşılama zamanlayıcısı açıksa durdur
        if hasattr(self, "_ready_timer") and self._ready_timer.isActive():
            self._ready_timer.stop()

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
        """Yukarıdan aşağıya yumuşak kayarak ve belirerek açılma animasyonu."""
        target_x, target_y = self._get_screen_target_pos()

        # Eğer zaten ekranda görünüyorsa ve kapanma animasyonunda değilse animasyonu tekrar başlatma
        if self.isVisible() and not self._is_animating_hide and self.y() == target_y:
            self.setWindowOpacity(1.0)
            self.raise_()
            return

        # Eğer kapanma animasyonu devam ediyorsa durdur
        if self._is_animating_hide:
            self._slide_anim.stop()
            self._opacity_anim.stop()
            self._is_animating_hide = False

        start_pos = QPoint(target_x, -self.height() - 15)
        self.move(start_pos)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        # Kayma animasyonu (Slide Down)
        self._slide_anim.stop()
        self._slide_anim.setDuration(320)
        self._slide_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(QPoint(target_x, target_y))

        # Şeffaflık animasyonu (Fade In)
        self._opacity_anim.stop()
        self._opacity_anim.setDuration(260)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)

        self._slide_anim.start()
        self._opacity_anim.start()

    def _on_slide_anim_finished(self):
        """Kapanma animasyonu tamamlandığında pencereyi gizler."""
        if self._is_animating_hide:
            super().hide()
            self._is_animating_hide = False

    def hide_animated(self):
        """Yukarı kayarak ve solarak kapanma animasyonu."""
        if not self.isVisible() or self._is_animating_hide:
            return

        self._is_animating_hide = True
        target_x, _ = self._get_screen_target_pos()
        current_pos = self.pos()
        end_pos = QPoint(target_x, -self.height() - 15)

        self._slide_anim.stop()
        self._slide_anim.setDuration(250)
        self._slide_anim.setEasingCurve(QEasingCurve.InCubic)
        self._slide_anim.setStartValue(current_pos)
        self._slide_anim.setEndValue(end_pos)

        self._opacity_anim.stop()
        self._opacity_anim.setDuration(200)
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)

        self._slide_anim.start()
        self._opacity_anim.start()

    def _get_current_colors(self):
        """Mevcut duruma ait vurgu, parıltı ve gradient renklerini döner."""
        if self.current_state == AssistantUIState.LISTENING:
            return UITheme.LISTENING_ACCENT, UITheme.LISTENING_GLOW, UITheme.LISTENING_GRAD_START, UITheme.LISTENING_GRAD_END
        elif self.current_state == AssistantUIState.THINKING:
            return UITheme.THINKING_ACCENT, UITheme.THINKING_GLOW, UITheme.THINKING_GRAD_START, UITheme.THINKING_GRAD_END
        elif self.current_state == AssistantUIState.SPEAKING:
            return UITheme.SPEAKING_ACCENT, UITheme.SPEAKING_GLOW, UITheme.SPEAKING_GRAD_START, UITheme.SPEAKING_GRAD_END
        elif self.current_state == AssistantUIState.ERROR:
            return UITheme.ERROR_ACCENT, UITheme.ERROR_GLOW, UITheme.ERROR_GRAD_START, UITheme.ERROR_GRAD_END
        return UITheme.IDLE_ACCENT, UITheme.IDLE_GLOW, UITheme.IDLE_GRAD_START, UITheme.IDLE_GRAD_END

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)

        # 1. Derin Obsidyen Buzlu Cam (Obsidian Glass) Kapsül Çizimi
        path = QPainterPath()
        path.addRoundedRect(rect, 27, 27)

        # Arka plan dolgusu
        painter.fillPath(path, QBrush(UITheme.BG_COLOR))

        # Üstten vuran hafif cam ışıltısı
        glass_grad = QLinearGradient(0, 2, 0, self.height())
        glass_grad.setColorAt(0.0, QColor(255, 255, 255, 18))
        glass_grad.setColorAt(0.3, QColor(255, 255, 255, 4))
        glass_grad.setColorAt(1.0, QColor(0, 0, 0, 40))
        painter.fillPath(path, QBrush(glass_grad))

        # İnce kenarlık
        pen_border = QPen(UITheme.BORDER_COLOR, 1.2)
        painter.strokePath(path, pen_border)

        # 2. Canlı Yüz İfadesi (Sol Rozet)
        self._paint_face(painter, cx=32, cy=self.height() / 2)

        # 3. Sağ Taraf Mikro Aktivite / Ses Göstergesi
        self._paint_activity_visualizer(painter, cx=self.width() - 25, cy=self.height() / 2)

    def _paint_face(self, painter: QPainter, cx: float, cy: float):
        """Asistanın durumuna göre animasyonlu, canlı yüz ifadesini çizer."""
        accent_color, glow_color, _, _ = self._get_current_colors()

        # Dış Halka / Rozet
        badge_r = 18.0
        badge_rect = QRectF(cx - badge_r, cy - badge_r, badge_r * 2, badge_r * 2)

        # Aktifken yumuşak nabız parıltısı
        if self.current_state in (AssistantUIState.LISTENING, AssistantUIState.SPEAKING, AssistantUIState.THINKING):
            pulse = (math.sin(self.pulse_phase * 2.2) + 1.0) / 2.0
            glow_r = badge_r + 2.0 + (pulse * 2.5)
            glow_rect = QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2)

            glow_color_pulse = QColor(glow_color)
            glow_color_pulse.setAlpha(int(35 + pulse * 45))
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow_color_pulse)
            painter.drawEllipse(glow_rect)

        # Rozet iç zemini
        painter.setPen(QPen(accent_color, 1.4))
        painter.setBrush(UITheme.BADGE_BG_COLOR)
        painter.drawEllipse(badge_rect)

        # Göz ve Ağız Kalemi / Fırçası
        pen_feature = QPen(accent_color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        brush_feature = QBrush(accent_color)

        eye_y = cy - 3.0
        mouth_y = cy + 5.5

        if self.current_state == AssistantUIState.IDLE:
            # --- DURURKEN / HAZIR (IDLE) ---
            # Sakin, dostça gözler ve doğal göz kırpma
            if self.is_blinking:
                # Göz kırpma anı: ince yatay çizgiler
                painter.setPen(pen_feature)
                painter.drawLine(QPointF(cx - 8.5, eye_y), QPointF(cx - 4.5, eye_y))
                painter.drawLine(QPointF(cx + 4.5, eye_y), QPointF(cx + 8.5, eye_y))
            else:
                # Normal gözler: iki sevimli oval
                painter.setPen(Qt.NoPen)
                painter.setBrush(brush_feature)
                painter.drawRoundedRect(QRectF(cx - 8.0, eye_y - 2.5, 3.2, 5.0), 1.6, 1.6)
                painter.drawRoundedRect(QRectF(cx + 4.8, eye_y - 2.5, 3.2, 5.0), 1.6, 1.6)

            # Hafif tebessüm
            smile = QPainterPath()
            smile.moveTo(cx - 4.0, mouth_y)
            smile.quadTo(cx, mouth_y + 2.2, cx + 4.0, mouth_y)
            painter.setPen(pen_feature)
            painter.setBrush(Qt.NoBrush)
            painter.strokePath(smile, pen_feature)

        elif self.current_state == AssistantUIState.LISTENING:
            # --- DİNLERKEN (LISTENING) ---
            # Dikkatli, geniş gözler + mikrofona göre büyüyen göz/ağız
            sound_factor = min(1.0, self.audio_level * 1.8)
            eye_r = 2.4 + (sound_factor * 1.6)

            # Gözler
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush_feature)
            painter.drawEllipse(QPointF(cx - 6.5, eye_y), eye_r, eye_r)
            painter.drawEllipse(QPointF(cx + 6.5, eye_y), eye_r, eye_r)

            # Göz içi parlak beyaz nokta
            painter.setBrush(Qt.white)
            painter.drawEllipse(QPointF(cx - 6.5 + 0.8, eye_y - 0.8), 0.9, 0.9)
            painter.drawEllipse(QPointF(cx + 6.5 + 0.8, eye_y - 0.8), 0.9, 0.9)

            # Dinleme Ağzı: Konuşma seviyesine göre genişleyen dikkatli "o"
            mouth_h = 2.2 + (sound_factor * 4.5)
            mouth_w = 3.6 + (sound_factor * 1.5)
            painter.setPen(pen_feature)
            painter.setBrush(UITheme.BADGE_BG_COLOR)
            painter.drawRoundedRect(QRectF(cx - (mouth_w / 2), mouth_y - (mouth_h / 2) + 0.5, mouth_w, mouth_h), 1.8, 1.8)

        elif self.current_state == AssistantUIState.THINKING:
            # --- DÜŞÜNÜRKEN (THINKING) ---
            # Gözler merakla yukarı-yana bakar, meraklı ve düşünceli ifade
            gaze_x = math.sin(self.pulse_phase * 2.0) * 1.8
            gaze_y = -2.0 + math.cos(self.pulse_phase * 2.0) * 0.8

            painter.setPen(Qt.NoPen)
            painter.setBrush(brush_feature)
            painter.drawEllipse(QPointF(cx - 6.5 + gaze_x, eye_y + gaze_y), 2.5, 2.5)
            painter.drawEllipse(QPointF(cx + 6.5 + gaze_x, eye_y + gaze_y), 2.5, 2.5)

            # Meraklı kaşlar (Biri hafif yukarı kalkık, zeki/düşünceli bakış)
            painter.setPen(pen_feature)
            painter.drawLine(QPointF(cx - 8.5, eye_y - 5.5), QPointF(cx - 4.5, eye_y - 6.5))
            painter.drawLine(QPointF(cx + 4.5, eye_y - 7.5), QPointF(cx + 8.5, eye_y - 6.0))

            # Meraklı, hafif tebessümlü düşünce ağzı
            think_mouth = QPainterPath()
            think_mouth.moveTo(cx - 3.5, mouth_y)
            think_mouth.quadTo(cx, mouth_y + 1.2, cx + 3.5, mouth_y)
            painter.setBrush(Qt.NoBrush)
            painter.strokePath(think_mouth, pen_feature)

        elif self.current_state == AssistantUIState.SPEAKING:
            # --- KONUŞURKEN (SPEAKING) ---
            # Neşeli gülen gözler (^ ^) ve konuşma ritmine göre açılıp kapanan canlı ağız!
            bob = math.sin(self.pulse_phase * 3.5) * 0.6

            # Gülen Gözler (Ters yaylar)
            painter.setPen(pen_feature)
            painter.setBrush(Qt.NoBrush)

            left_eye = QPainterPath()
            left_eye.moveTo(cx - 9.0, eye_y + 0.5 + bob)
            left_eye.quadTo(cx - 6.5, eye_y - 3.2 + bob, cx - 4.0, eye_y + 0.5 + bob)
            painter.strokePath(left_eye, pen_feature)

            right_eye = QPainterPath()
            right_eye.moveTo(cx + 4.0, eye_y + 0.5 + bob)
            right_eye.quadTo(cx + 6.5, eye_y - 3.2 + bob, cx + 9.0, eye_y + 0.5 + bob)
            painter.strokePath(right_eye, pen_feature)

            # Konuşan Canlı Ağız (Yükseklik ritmik olarak 2px ile 6.5px arası değişir)
            mouth_open = abs(math.sin(self.pulse_phase * 3.5)) * 4.8 + 2.0
            mouth_w = 6.2
            mouth_rect = QRectF(cx - (mouth_w / 2), mouth_y - (mouth_open / 2) + 0.5, mouth_w, mouth_open)

            painter.setPen(pen_feature)
            painter.setBrush(brush_feature)
            painter.drawRoundedRect(mouth_rect, 2.2, 2.2)

        elif self.current_state == AssistantUIState.ERROR:
            # --- HATA (ERROR) ---
            # (> <) şaşkın / üzgün gözler ve dalgalı ağız
            painter.setPen(pen_feature)
            painter.drawLine(QPointF(cx - 8.5, eye_y - 2.5), QPointF(cx - 5.0, eye_y))
            painter.drawLine(QPointF(cx - 8.5, eye_y + 2.5), QPointF(cx - 5.0, eye_y))

            painter.drawLine(QPointF(cx + 8.5, eye_y - 2.5), QPointF(cx + 5.0, eye_y))
            painter.drawLine(QPointF(cx + 8.5, eye_y + 2.5), QPointF(cx + 5.0, eye_y))

            err_mouth = QPainterPath()
            err_mouth.moveTo(cx - 4.0, mouth_y + 1.5)
            err_mouth.quadTo(cx, mouth_y - 1.5, cx + 4.0, mouth_y + 1.5)
            painter.setBrush(Qt.NoBrush)
            painter.strokePath(err_mouth, pen_feature)

    def _paint_activity_visualizer(self, painter: QPainter, cx: float, cy: float):
        """Widget'ın sağ kenarında duruma özel zarif mikro aktivite dalgaları çizer."""
        accent_color, _, grad_start, grad_end = self._get_current_colors()

        if self.current_state == AssistantUIState.LISTENING:
            # 3 adet ses seviyesiyle dans eden nane yeşili mini dalga çubuğu
            bars = 3
            spacing = 5.0
            start_x = cx - ((bars - 1) * spacing) / 2

            for i in range(bars):
                wave = math.sin(self.pulse_phase * 2.5 + i * 1.1) * 3.0
                h = 5.0 + (self.audio_level * 16.0) + wave
                h = max(3.0, min(22.0, h))

                bx = start_x + (i * spacing)
                by = cy - (h / 2)

                grad = QLinearGradient(bx, by, bx, by + h)
                grad.setColorAt(0, grad_start)
                grad.setColorAt(1, grad_end)

                painter.setPen(Qt.NoPen)
                painter.setBrush(grad)
                painter.drawRoundedRect(QRectF(bx - 1.2, by, 2.4, h), 1.2, 1.2)

        elif self.current_state == AssistantUIState.SPEAKING:
            # 3 adet konuşma ritmine göre salınan mercan mini ses çubuğu
            bars = 3
            spacing = 5.0
            start_x = cx - ((bars - 1) * spacing) / 2

            for i in range(bars):
                speech_wave = abs(math.sin(self.pulse_phase * 3.0 + i * 1.3)) * 14.0 + 4.0
                bx = start_x + (i * spacing)
                by = cy - (speech_wave / 2)

                grad = QLinearGradient(bx, by, bx, by + speech_wave)
                grad.setColorAt(0, grad_start)
                grad.setColorAt(1, grad_end)

                painter.setPen(Qt.NoPen)
                painter.setBrush(grad)
                painter.drawRoundedRect(QRectF(bx - 1.2, by, 2.4, speech_wave), 1.2, 1.2)

        elif self.current_state == AssistantUIState.THINKING:
            # Sırayla nabız atan 3 kehribar sarısı nokta
            dots = 3
            spacing = 6.0
            start_x = cx - ((dots - 1) * spacing) / 2

            for i in range(dots):
                alpha = int(((math.sin(self.pulse_phase * 3.0 + i * 1.2) + 1.0) / 2.0) * 190 + 65)
                dot_color = QColor(accent_color)
                dot_color.setAlpha(alpha)

                bx = start_x + (i * spacing)
                painter.setPen(Qt.NoPen)
                painter.setBrush(dot_color)
                painter.drawEllipse(QPointF(bx, cy), 2.2, 2.2)
