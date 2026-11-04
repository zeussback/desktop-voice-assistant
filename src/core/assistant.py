import logging
import threading
from typing import Optional
from PySide6.QtCore import QObject, QTimer, Signal

from src.brain.provider_base import BaseBrainProvider
from src.core.audio_recorder import AudioRecorder
from src.ui.widget import AssistantUIState, GlassLiquidWidget
from src.voice.audio_player import AudioPlayer
from src.voice.tts_base import BaseTTSClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen kullanıcının bilgisayarında çalışan kişisel sesli asistanısın. 
Kullanıcı seninle Türkçe konuşuyor. 
Yanıtlarını samimi, net, doğal ve seslendirileceği için özlü (gereksiz uzun olmayan) şekilde ver. 
Markdown yıldızları, başlıkları veya karmaşık listelemeler yerine konuşma diline uygun akıcı cümleler kur."""


class AssistantController(QObject):
    """Asistanın tüm bileşenlerini (Zeka, Ses, UI, Kısayol) koordine eden ana durum yöneticisi."""

    sig_state_changed = Signal(str, str)
    sig_audio_level = Signal(float)

    def __init__(
        self,
        brain: BaseBrainProvider,
        voice: BaseTTSClient,
        recorder: AudioRecorder,
        widget: GlassLiquidWidget,
        player: Optional[AudioPlayer] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.brain = brain
        self.voice = voice
        self.recorder = recorder
        self.widget = widget
        self.player = player or AudioPlayer()

        self.current_state = AssistantUIState.IDLE

        # Sinyalleri arayüze güvenle bağla (Thread-Safe UI Updates)
        self.sig_state_changed.connect(self._on_state_changed_ui)
        self.sig_audio_level.connect(self.widget.update_audio_level)

        # Mikrofon seviyesi anlık izleme zamanlayıcısı
        self._rms_timer = QTimer(self)
        self._rms_timer.timeout.connect(self._poll_rms_level)

    def _poll_rms_level(self):
        if self.recorder.is_recording:
            rms = self.recorder.get_current_rms()
            self.sig_audio_level.emit(rms)

    def _on_state_changed_ui(self, state_str: str, subtext: str):
        state = AssistantUIState(state_str)
        self.current_state = state
        self.widget.set_state(state, subtext)

    def handle_toggle(self, is_active: bool) -> None:
        """Kısayola basıldığında çağrılan toggle yöneticisi."""
        if is_active:
            # 1. Basış -> Dinleme Başlar
            started = self.recorder.start_recording()
            if started:
                self.sig_state_changed.emit(
                    AssistantUIState.LISTENING.value, "Konuşmanız dinleniyor"
                )
                self._rms_timer.start(50)  # Her 50ms'de bir ses seviyesi güncelle
            else:
                self.sig_state_changed.emit(
                    AssistantUIState.ERROR.value, "Mikrofon başlatılamadı"
                )
        else:
            # 2. Basış -> Dinleme Durur, Düşünme & Cevap Başlar
            self._rms_timer.stop()
            self.sig_audio_level.emit(0.0)
            audio_bytes = self.recorder.stop_recording()

            self.sig_state_changed.emit(
                AssistantUIState.THINKING.value, "Yapay zeka yanıt hazırlıyor"
            )

            # Ağ ve sentez işlemlerini UI thread'ini kilitlemeden arka planda çalıştır
            worker_thread = threading.Thread(
                target=self._process_audio_worker,
                args=(audio_bytes,),
                daemon=True,
            )
            worker_thread.start()

    def _process_audio_worker(self, audio_bytes: bytes) -> None:
        """Arka planda zekaya danışan ve sesi sentezleyip çalan işlemci."""
        try:
            logger.info("Ses verisi işleniyor...")

            # 1. Zeka katmanından yanıt al
            response = self.brain.generate_response(
                prompt=SYSTEM_PROMPT,
                audio_bytes=audio_bytes if len(audio_bytes) > 100 else None,
            )

            response_text = response.text.strip()
            if not response_text:
                response_text = "Sizi tam duyamadım, lütfen tekrar söyler misiniz?"

            logger.info(f"Yanıt ({response.provider}): {response_text}")

            # 2. UI durumunu Konuşuyor olarak güncelle
            short_preview = (
                response_text[:35] + "..." if len(response_text) > 35 else response_text
            )
            self.sig_state_changed.emit(
                AssistantUIState.SPEAKING.value, short_preview
            )

            # 3. Metni sese çevir
            audio_data = self.voice.synthesize(response_text)

            # 4. Sesi çal
            def on_finished():
                logger.info("Konuşma bitti, asistan hazır moduna geçiyor.")
                self.sig_state_changed.emit(AssistantUIState.IDLE.value, "Hazır")

            self.player.play_bytes(audio_data, on_finished=on_finished)

        except Exception as e:
            logger.error(f"İşleme hatası: {e}", exc_info=True)
            self.sig_state_changed.emit(
                AssistantUIState.ERROR.value, str(e)[:40]
            )
            # 3 saniye hata durumunu gösterdikten sonra hazır durumuna dön
            import time
            time.sleep(3)
            self.sig_state_changed.emit(
                AssistantUIState.IDLE.value, "Hazır"
            )
