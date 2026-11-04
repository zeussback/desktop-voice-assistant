import logging
from typing import Optional
import httpx
from src.voice.tts_base import BaseTTSClient

logger = logging.getLogger(__name__)


class VoiceStudioClient(BaseTTSClient):
    """debpalash/VoiceStudio (localhost:3900) yerel API istemcisi."""

    def __init__(
        self,
        base_url: str = "http://localhost:3900",
        voice: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.voice = voice
        self.timeout = timeout

    def is_available(self) -> bool:
        """VoiceStudio API sunucusunun ayakta olup olmadığını kontrol eder."""
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    def _synthesize_remote(self, text: str) -> bytes:
        """VoiceStudio API üzerinden ses sentezler."""
        url = f"{self.base_url}/api/tts/generate"
        payload = {"text": text}
        if self.voice:
            payload["voice"] = self.voice

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.content

    def synthesize(self, text: str) -> bytes:
        if not self.is_available():
            raise RuntimeError(f"VoiceStudio sunucusu ({self.base_url}) çevrimdışı!")
        return self._synthesize_remote(text)
