import logging
from typing import Optional
from src.brain.provider_base import BaseBrainProvider, BrainResponse

logger = logging.getLogger(__name__)


class HybridBrain(BaseBrainProvider):
    """Bulut ve yerel LLM sağlayıcılarını koordine eden hibrit zeka yöneticisi."""

    def __init__(
        self,
        primary: BaseBrainProvider,
        fallback: Optional[BaseBrainProvider] = None,
    ):
        self.primary = primary
        self.fallback = fallback

    def generate_response(
        self, prompt: str, audio_bytes: Optional[bytes] = None
    ) -> BrainResponse:
        try:
            return self.primary.generate_response(prompt, audio_bytes)
        except Exception as e:
            logger.warning(
                f"Birincil LLM ({getattr(self.primary, 'model', 'Primary')}) başarısız oldu: {e}."
            )
            if self.fallback:
                logger.info("Yerel yedek model devreye alınıyor...")
                return self.fallback.generate_response(prompt, audio_bytes)
            raise e
