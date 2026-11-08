import logging
import signal
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
from src.tools import create_default_tool_registry
from src.ui.widget import GlassLiquidWidget
from src.voice.audio_player import AudioPlayer
from src.voice.edge_tts_client import EdgeTTSClient
from src.voice.hybrid_tts import HybridTTS
from src.voice.piper_client import PiperTTSClient

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

    # 2. Araç Motoru (Tool Engine)
    tool_registry = create_default_tool_registry()

    # 3. Zeka Sağlayıcıları (Gemini Primary + Ollama Fallback)
    gemini_brain = GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        tool_registry=tool_registry,
    )
    ollama_brain = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
    )
    hybrid_brain = HybridBrain(primary=gemini_brain, fallback=ollama_brain)

    # 4. Ses Sağlayıcıları (1: Piper Yerel Ultra Hızlı -> 2: Edge-TTS Son Çare)
    piper_tts = PiperTTSClient(
        model_path=settings.PIPER_MODEL_PATH,
        length_scale=settings.PIPER_LENGTH_SCALE,
        pitch_factor=settings.PIPER_PITCH_FACTOR,
    )
    edge_tts = EdgeTTSClient(voice=settings.FALLBACK_TTS_VOICE)
    hybrid_voice = HybridTTS(providers=[piper_tts, edge_tts])

    # 5. Ses Kayıt ve Oynatıcı
    recorder = AudioRecorder(
        sample_rate=settings.SAMPLE_RATE,
        channels=settings.CHANNELS,
    )
    player = AudioPlayer()

    # 6. Ana Orkestratör
    controller = AssistantController(
        brain=hybrid_brain,
        voice=hybrid_voice,
        recorder=recorder,
        widget=widget,
        player=player,
        tool_registry=tool_registry,
    )

    # 7. Küresel Kısayol Dinleyici
    hotkey_listener = GlobalHotkeyListener(
        hotkey=settings.HOTKEY,
        on_toggle=controller.handle_toggle,
    )
    started = hotkey_listener.start()
    if not started:
        logger.warning(f"Küresel kısayol ({settings.HOTKEY}) başlatılamadı!")

    # 7. Terminalden Ctrl+C (SIGINT) ile temiz çıkış desteği
    def sigint_handler(sig, frame):
        logger.info("Terminalden Ctrl+C sinyali alındı. Asistan kapatılıyor...")
        app.quit()

    signal.signal(signal.SIGINT, sigint_handler)

    # Qt olay döngüsünün Python sinyallerini işleyebilmesi için periyodik timer (200ms)
    sigint_timer = QTimer()
    sigint_timer.timeout.connect(lambda: None)
    sigint_timer.start(200)

    # 8. Başlangıçta widget'ı 'Dinlemeye Hazır' olarak 4.5 saniye göster
    # Kullanıcı 4-5 saniye içinde kısayola basmazsa widget otomatik yukarı kayıp gizlenir.
    widget.show_ready_banner(duration_ms=4500)

    logger.info(f"Asistan hazır! Dinleme kısayolu: {settings.HOTKEY.upper()}")

    # 9. Olay döngüsü ve çıkış işlemi temizliği
    exit_code = app.exec()
    logger.info("Asistan sonlandırılıyor, kaynaklar temizleniyor...")
    hotkey_listener.stop()
    recorder.stop_recording()
    player.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
