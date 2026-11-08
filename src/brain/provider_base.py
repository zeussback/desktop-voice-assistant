from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class BrainResponse(BaseModel):
    """Zeka katmanından dönen standart yanıt modeli."""

    text: str
    provider: str
    tool_called: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None
    needs_confirmation: bool = False
    confirmation_prompt: Optional[str] = None


class BaseBrainProvider(ABC):
    """Tüm LLM sağlayıcıları için temel soyut sınıf."""

    @abstractmethod
    def generate_response(
        self, prompt: str, audio_bytes: Optional[bytes] = None
    ) -> BrainResponse:
        """Metin veya ses girdisi alıp BrainResponse döndürür."""
        pass
