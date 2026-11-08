from dataclasses import dataclass
from PySide6.QtGui import QColor


@dataclass
class UITheme:
    """Masaüstü sesli asistan arayüz tema ve renk tanımları.
    
    Tasarım: Derin Obsidyen Siyahı Buzlu Cam (Obsidian Frosted Glass),
    Mor ve mavi yerine modern Nane Yeşili, Sıcak Kehribar ve Mercan tonları.
    """

    # Derin Obsidyen Buzlu Cam (Deep Obsidian Frosted Glass)
    BG_COLOR = QColor(12, 14, 20, 235)
    BADGE_BG_COLOR = QColor(22, 26, 36, 230)
    BORDER_COLOR = QColor(255, 255, 255, 38)
    BORDER_HIGHLIGHT = QColor(255, 255, 255, 60)
    TEXT_COLOR = QColor(255, 255, 255)
    SUBTEXT_COLOR = QColor(148, 163, 184)  # Slate Gray

    # 1. LISTENING: Canlı Nane / Zümrüt Yeşili (Emerald Mint) - Taze, dikkatli, dinleyen
    LISTENING_ACCENT = QColor(16, 212, 144)
    LISTENING_GLOW = QColor(16, 212, 144, 90)
    LISTENING_GRAD_START = QColor(52, 235, 169)
    LISTENING_GRAD_END = QColor(5, 180, 120)

    # 2. THINKING: Sıcak Kehribar / Güneş Sarısı (Warm Amber / Gold) - Düşünen, enerjik
    THINKING_ACCENT = QColor(251, 180, 36)
    THINKING_GLOW = QColor(251, 180, 36, 90)
    THINKING_GRAD_START = QColor(254, 212, 92)
    THINKING_GRAD_END = QColor(235, 140, 16)

    # 3. SPEAKING: Canlı Mercan / Gün Batımı Şeftalisi (Lively Coral / Sunset Rose) - Konuşan, canlı
    SPEAKING_ACCENT = QColor(255, 107, 107)
    SPEAKING_GLOW = QColor(255, 107, 107, 90)
    SPEAKING_GRAD_START = QColor(255, 138, 128)
    SPEAKING_GRAD_END = QColor(245, 80, 80)

    # 4. IDLE: Minimalist Titanyum / Buz Işıltısı (Titanium Slate)
    IDLE_ACCENT = QColor(148, 163, 184)
    IDLE_GLOW = QColor(148, 163, 184, 50)
    IDLE_GRAD_START = QColor(203, 213, 225)
    IDLE_GRAD_END = QColor(100, 116, 139)

    # 5. ERROR: Saf Yakut Kırmızısı (Ruby Red)
    ERROR_ACCENT = QColor(239, 68, 68)
    ERROR_GLOW = QColor(239, 68, 68, 90)
    ERROR_GRAD_START = QColor(248, 113, 113)
    ERROR_GRAD_END = QColor(220, 38, 38)
