from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Masaüstü sesli asistan konfigürasyon sınıfı."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Kısayol Tuşu (Toggle)
    HOTKEY: str = "ctrl+space"

    # Google Gemini API
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Yerel LLM Fallback (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"

    # Yerel TTS (VoiceStudio)
    VOICESTUDIO_BASE_URL: str = "http://localhost:3900"
    VOICESTUDIO_DEFAULT_VOICE: Optional[str] = None

    # Yedek TTS (Edge-TTS)
    FALLBACK_TTS_VOICE: str = "tr-TR-AhmetNeural"

    # Ses Kayıt Parametreleri
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1


settings = Settings()
