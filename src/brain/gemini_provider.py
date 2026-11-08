import logging
from typing import List, Optional
from src.brain.provider_base import BaseBrainProvider, BrainResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseBrainProvider):
    """Google Gemini API sağlayıcısı (Otomatik zaman aşımı ve yedek model destekli)."""

    FALLBACK_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3.5-flash",
        timeout_ms: int = 12000,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY tanımlanmamış!")
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=self.timeout_ms),
            )
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

        # Denenecek modeller listesi: Seçilen model başa, alternatifler arkaya
        models_to_try: List[str] = [self.model]
        for m in self.FALLBACK_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        for candidate_model in models_to_try:
            try:
                logger.info(f"Gemini API modeli deneniyor: {candidate_model}")
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=contents,
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e).lower()
                last_error = e
                # 503, 504, 429, timeout, deadline_exceeded veya geçici sunucu yoğunluklarında diğer modele geç
                is_transient = any(
                    err_code in err_str
                    for err_code in [
                        "503",
                        "504",
                        "429",
                        "timeout",
                        "deadline",
                        "unavailable",
                        "high demand",
                        "temporary",
                        "overloaded",
                    ]
                )
                if is_transient:
                    logger.warning(
                        f"Model ({candidate_model}) yanıt vermedi veya gecikti ({e}). Bir sonraki modele geçiliyor..."
                    )
                    continue
                else:
                    raise e

        if last_error:
            raise last_error
        return ""

    def generate_response(
        self, prompt: str, audio_bytes: Optional[bytes] = None
    ) -> BrainResponse:
        text = self._call_api(prompt, audio_bytes)
        return BrainResponse(text=text.strip(), provider="gemini")
