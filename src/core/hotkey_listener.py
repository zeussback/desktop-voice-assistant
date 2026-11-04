import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class GlobalHotkeyListener:
    """Sistem genelinde klavye kısayolunu dinleyen ve toggle durumu yöneten modül."""

    def __init__(self, hotkey: str = "ctrl+space", on_toggle: Optional[Callable[[bool], None]] = None):
        self.hotkey = hotkey.lower().strip()
        self.on_toggle = on_toggle
        self.is_active = False
        self._listener = None

    def _normalize_hotkey_for_pynput(self, key_str: str) -> str:
        """'ctrl+space' gibi formatları pynput için '<ctrl>+<space>' formatına dönüştürür."""
        parts = key_str.split("+")
        normalized = []
        for p in parts:
            p = p.strip()
            if p in ["ctrl", "alt", "shift", "cmd", "space", "caps_lock", "tab", "esc"]:
                normalized.append(f"<{p}>")
            else:
                normalized.append(p)
        return "+".join(normalized)

    def trigger_toggle(self) -> None:
        """Kısayola basıldığında çağrılır; durumu tersine çevirir ve callback'i tetikler."""
        self.is_active = not self.is_active
        logger.info(f"Kısayol tetiklendi. Yeni durum: {'Dinleme Açık' if self.is_active else 'Dinleme Kapalı'}")
        if self.on_toggle:
            try:
                self.on_toggle(self.is_active)
            except Exception as e:
                logger.error(f"Hotkey callback hatası: {e}")

    def start(self) -> bool:
        """Küresel dinleme thread'ini başlatır."""
        try:
            from pynput import keyboard

            pynput_key = self._normalize_hotkey_for_pynput(self.hotkey)
            hotkeys_map = {pynput_key: self.trigger_toggle}

            self._listener = keyboard.GlobalHotKeys(hotkeys_map)
            self._listener.start()
            logger.info(f"Küresel kısayol dinleyici başlatıldı ({self.hotkey}).")
            return True
        except Exception as e:
            logger.error(f"Küresel kısayol başlatılamadı: {e}")
            return False

    def stop(self) -> None:
        """Dinleyiciyi durdurur."""
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception as e:
                logger.warning(f"Kısayol dinleyici kapatılırken hata: {e}")
            finally:
                self._listener = None
