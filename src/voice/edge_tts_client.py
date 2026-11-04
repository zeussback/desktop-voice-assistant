import asyncio
import io
import logging
from src.voice.tts_base import BaseTTSClient

logger = logging.getLogger(__name__)


class EdgeTTSClient(BaseTTSClient):
    """Microsoft Edge Neural TTS (Ücretsiz, çevrimiçi, doğal Türkçe sesler)."""

    def __init__(self, voice: str = "tr-TR-AhmetNeural"):
        self.voice = voice

    def is_available(self) -> bool:
        return True

    async def _synthesize_async(self, text: str) -> bytes:
        import edge_tts

        communicate = edge_tts.Communicate(text, self.voice)
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        return audio_stream.getvalue()

    def _synthesize_async_wrapper(self, text: str) -> bytes:
        """Asenkron çağrıyı senkron koda bağlar."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(self._synthesize_async(text))
            else:
                return loop.run_until_complete(self._synthesize_async(text))
        except RuntimeError:
            return asyncio.run(self._synthesize_async(text))

    def synthesize(self, text: str) -> bytes:
        return self._synthesize_async_wrapper(text)
