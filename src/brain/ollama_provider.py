import logging
from typing import Optional
import httpx
from src.brain.provider_base import BaseBrainProvider, BrainResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseBrainProvider):
    """Yerel Ollama LLM sağlayıcısı (Kota aşımı ve çevrimdışı yedek)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b",
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _call_api(self, prompt: str, audio_bytes: Optional[bytes] = None) -> str:
        # Ollama /api/generate endpoint'ine istek atar
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    def generate_response(
        self, prompt: str, audio_bytes: Optional[bytes] = None
    ) -> BrainResponse:
        text = self._call_api(prompt, audio_bytes)
        return BrainResponse(text=text.strip(), provider="ollama")
