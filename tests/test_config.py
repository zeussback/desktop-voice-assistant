import os
import pytest


def test_default_config():
    """Varsayılan ayarların doğru yüklendiğini test eder."""
    from src.config import Settings

    settings = Settings(_env_file=None)
    assert settings.HOTKEY == "ctrl+space"
    assert settings.GEMINI_MODEL == "gemini-2.0-flash"
    assert settings.OLLAMA_BASE_URL == "http://localhost:11434"
    assert settings.VOICESTUDIO_BASE_URL == "http://localhost:3900"
    assert "tr-TR" in settings.FALLBACK_TTS_VOICE


def test_env_override(monkeypatch):
    """Ortam değişkenlerinin varsayılanları ezdiğini test eder."""
    monkeypatch.setenv("HOTKEY", "alt+space")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "test_api_key_123")

    from src.config import Settings

    settings = Settings(_env_file=None)
    assert settings.HOTKEY == "alt+space"
    assert settings.GEMINI_MODEL == "gemini-1.5-flash"
    assert settings.GEMINI_API_KEY == "test_api_key_123"
