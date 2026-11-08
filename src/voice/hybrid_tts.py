import logging
from typing import List, Optional
from src.voice.tts_base import BaseTTSClient

logger = logging.getLogger(__name__)


class HybridTTS(BaseTTSClient):
    """Sırayla TTS motorlarını deneyen (Piper -> Edge-TTS) hibrit ses yöneticisi."""

    def __init__(
        self,
        providers: Optional[List[BaseTTSClient]] = None,
        primary: Optional[BaseTTSClient] = None,
        fallback: Optional[BaseTTSClient] = None,
    ):
        if providers is not None:
            self.providers = [p for p in providers if p is not None]
        else:
            self.providers = []
            if primary is not None:
                self.providers.append(primary)
            if fallback is not None:
                self.providers.append(fallback)

    def is_available(self) -> bool:
        return any(p.is_available() for p in self.providers)

    def synthesize(self, text: str) -> bytes:
        last_error = None
        for provider in self.providers:
            if provider.is_available():
                try:
                    logger.info(f"TTS motoru kullanılıyor: {provider.__class__.__name__}")
                    return provider.synthesize(text)
                except Exception as e:
                    logger.warning(
                        f"TTS motoru ({provider.__class__.__name__}) hata verdi: {e}. Bir sonraki motora geçiliyor."
                    )
                    last_error = e
                    continue

        if last_error:
            raise last_error
        raise RuntimeError("Kullanılabilir hiçbir TTS motoru bulunamadı!")
