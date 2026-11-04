import logging
from typing import Optional
from src.brain.provider_base import BaseBrainProvider, BrainResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseBrainProvider):
    """Google Gemini API sağlayıcısı."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY tanımlanmamış!")
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _call_api(self, prompt: str, audio_bytes: Optional[bytes] = None) -> str:
        client = self._get_client()

        contents = []
        if audio_bytes:
            from google.genai import types

            contents.append(
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
            )
        contents.append(prompt)

        response = client.models.generate_content(
            model=self.model,
            contents=contents,
        )
        return response.text or ""

    def generate_response(
        self, prompt: str, audio_bytes: Optional[bytes] = None
    ) -> BrainResponse:
        text = self._call_api(prompt, audio_bytes)
        return BrainResponse(text=text.strip(), provider="gemini")
