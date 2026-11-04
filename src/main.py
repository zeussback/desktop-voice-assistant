import logging
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.brain.gemini_provider import GeminiProvider
from src.brain.hybrid_brain import HybridBrain
from src.brain.ollama_provider import OllamaProvider
from src.config import settings
from src.core.assistant import AssistantController
from src.core.audio_recorder import AudioRecorder
from src.core.hotkey_listener import GlobalHotkeyListener
from src.ui.widget import AssistantUIState, GlassLiquidWidget
from src.voice.audio_player import AudioPlayer
from src.voice.edge_tts_client import EdgeTTSClient
from src.voice.hybrid_tts import HybridTTS
from src.voice.voicestudio_client import VoiceStudioClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("DesktopAssistant")


def main():
    logger.info("Masaüstü Sesli Asistan başlatılıyor...")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 1. UI Widget'ı oluştur
    widget = GlassLiquidWidget()

    # 2. Zeka Sağlayıcıları (Gemini Primary + Ollama Fallback)
    gemini_brain = GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
    )
    ollama_brain = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
    )
    hybrid_brain = HybridBrain(primary=gemini_brain, fallback=ollama_brain)

    # 3. Ses Sağlayıcıları (VoiceStudio Primary + Edge-TTS Fallback)
    voice_studio = VoiceStudioClient(
        base_url=settings.VOICESTUDIO_BASE_URL,
        voice=settings.VOICESTUDIO_DEFAULT_VOICE,
    )
    edge_tts = EdgeTTSClient(voice=settings.FALLBACK_TTS_VOICE)
    hybrid_voice = HybridTTS(primary=voice_studio, fallback=edge_tts)

    # 4. Ses Kayıt ve Oynatıcı
    recorder = AudioRecorder(
        sample_rate=settings.SAMPLE_RATE,
        channels=settings.CHANNELS,
    )
    player = AudioPlayer()

    # 5. Ana Orkestratör
    controller = AssistantController(
        brain=hybrid_brain,
        voice=hybrid_voice,
        recorder=recorder,
        widget=widget,
        player=player,
    )

    # 6. Küresel Kısayol Dinleyici
    hotkey_listener = GlobalHotkeyListener(
        hotkey=settings.HOTKEY,
        on_toggle=controller.handle_toggle,
    )
    started = hotkey_listener.start()
    if not started:
        logger.warning(f"Küresel kısayol ({settings.HOTKEY}) başlatılamadı!")

    # Başlangıçta widget'ı 2 saniye gösterip kullanıcıya hazır olduğunu bildir
    widget.set_state(
        AssistantUIState.LISTENING,
        f"{settings.HOTKEY.upper()} ile konuşmaya başlayın",
    )
    QTimer.singleShot(2500, lambda: widget.set_state(AssistantUIState.IDLE))

    logger.info(f"Asistan hazır! Dinleme kısayolu: {settings.HOTKEY.upper()}")

    # Çıkış işlemi temizliği
    exit_code = app.exec()
    hotkey_listener.stop()
    recorder.stop_recording()
    player.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
