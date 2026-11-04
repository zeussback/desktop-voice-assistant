from dataclasses import dataclass
from PySide6.QtGui import QColor


@dataclass
class UITheme:
    # Glassmorphism arka plan
    BG_COLOR = QColor(18, 20, 28, 215)
    BORDER_COLOR = QColor(255, 255, 255, 45)
    TEXT_COLOR = QColor(240, 245, 255)
    SUBTEXT_COLOR = QColor(160, 175, 200)

    # Durum Renkleri & Parıltılar
    LISTENING_GLOW = QColor(0, 210, 255, 180)     # Neon Cyan
    LISTENING_GRAD_START = QColor(0, 180, 255)
    LISTENING_GRAD_END = QColor(50, 100, 255)

    THINKING_GLOW = QColor(180, 80, 255, 180)     # Mor / Eflatun
    THINKING_GRAD_START = QColor(140, 40, 255)
    THINKING_GRAD_END = QColor(220, 80, 255)

    SPEAKING_GLOW = QColor(0, 240, 150, 180)     # Zümrüt Yeşili
    SPEAKING_GRAD_START = QColor(0, 210, 140)
    SPEAKING_GRAD_END = QColor(40, 245, 180)

    ERROR_GLOW = QColor(255, 60, 90, 180)        # Kırmızı
    ERROR_GRAD_START = QColor(255, 50, 80)
    ERROR_GRAD_END = QColor(255, 120, 100)
