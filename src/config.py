from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Masaüstü sesli asistan konfigürasyon sınıfı."""

    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Kısayol Tuşu (Toggle)
    HOTKEY: str = "ctrl+space"

    # Google Gemini API
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # Yerel LLM Fallback (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"

    # Yerel Ultra Hızlı TTS (Piper)
    PIPER_MODEL_PATH: str = "models/piper/tr_TR-dfki-medium.onnx"
    PIPER_LENGTH_SCALE: float = 0.85  # Hız ölçeği (1.0 varsayılan, 0.85 ~%15 daha akıcı)
    PIPER_PITCH_FACTOR: float = 1.05  # Perde / Tını (1.0 normal, 1.05 daha net ve canlı)

    # Yedek TTS (Edge-TTS)
    FALLBACK_TTS_VOICE: str = "tr-TR-AhmetNeural"

    # Ses Kayıt Parametreleri
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1


settings = Settings()
