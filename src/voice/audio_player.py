import io
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Ses baytlarını arka planda kesintisiz çalan oynatıcı."""

    def __init__(self):
        self._is_initialized = False
        self._lock = threading.Lock()
        self._current_thread: Optional[threading.Thread] = None
        self._stop_requested = False

    def _ensure_init(self):
        if not self._is_initialized:
            try:
                import os
                # Pygame konsol mesajlarını gizle
                os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
                import pygame

                pygame.mixer.init()
                self._is_initialized = True
            except Exception as e:
                logger.warning(f"Pygame mixer başlatılamadı: {e}")

    def is_playing(self) -> bool:
        """Şu anda ses çalınıyor mu?"""
        if not self._is_initialized:
            return False
        try:
            import pygame

            return pygame.mixer.music.get_busy()
        except Exception:
            return False

    def play_bytes(self, audio_bytes: bytes, on_finished=None) -> None:
        """Ses baytlarını arka planda çalar."""
        self.stop()

        def _play_worker():
            try:
                self._ensure_init()
                import pygame

                bio = io.BytesIO(audio_bytes)
                pygame.mixer.music.load(bio)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy() and not self._stop_requested:
                    time.sleep(0.05)

                if on_finished and not self._stop_requested:
                    on_finished()
            except Exception as e:
                logger.error(f"Ses çalınırken hata: {e}")

        self._stop_requested = False
        self._current_thread = threading.Thread(target=_play_worker, daemon=True)
        self._current_thread.start()

    def stop(self) -> None:
        """Çalmakta olan sesi durdurur."""
        self._stop_requested = True
        if self._is_initialized:
            try:
                import pygame

                pygame.mixer.music.stop()
            except Exception:
                pass
