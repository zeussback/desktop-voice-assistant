import logging
from typing import Optional
from src.voice.tts_base import BaseTTSClient

logger = logging.getLogger(__name__)


class HybridTTS(BaseTTSClient):
    """VoiceStudio (birincil) ve Edge-TTS (yedek) arasında geçiş sağlayan ses yöneticisi."""

    def __init__(
        self,
        primary: BaseTTSClient,
        fallback: Optional[BaseTTSClient] = None,
    ):
        self.primary = primary
        self.fallback = fallback

    def is_available(self) -> bool:
        return self.primary.is_available() or (
            self.fallback is not None and self.fallback.is_available()
        )

    def synthesize(self, text: str) -> bytes:
        if self.primary.is_available():
            try:
                return self.primary.synthesize(text)
            except Exception as e:
                logger.warning(
                    f"Birincil TTS motoru hata verdi ({e}), yedek motora geçiliyor."
                )

        if self.fallback is not None:
            logger.info("Yedek TTS motoru (Edge-TTS) kullanılıyor.")
            return self.fallback.synthesize(text)

        raise RuntimeError("Kullanılabilir hiçbir TTS motoru bulunamadı!")
