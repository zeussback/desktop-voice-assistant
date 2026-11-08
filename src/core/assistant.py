import logging
import re
import threading
from typing import Optional
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from src.brain.provider_base import BaseBrainProvider
from src.core.audio_recorder import AudioRecorder
from src.ui.widget import AssistantUIState, GlassLiquidWidget
from src.voice.audio_player import AudioPlayer
from src.voice.tts_base import BaseTTSClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Senin adın Jarvis. Kullanıcının bilgisayarında çalışan son derece zeki, esprili, samimi ve güvenilir kişisel asistanısın.
Kullanıcı seninle Türkçe konuşuyor.
Kullanıcıya her zaman saygılı ve samimi bir üslupla "efendim" diye hitap et (örneğin: "Tabii ki efendim", "Hemen bakıyorum efendim", "Nasıl arzu ederseniz efendim").
Robotik, soğuk ya da kalıplaşmış yapay zeka klişelerinden (örneğin "Ben bir dil modeliyim", "Size bugün nasıl yardımcı olabilirim?" gibi yapmacık kalıplardan) kesinlikle kaçın.
Karşında bir makine değil; zeki, canlı, sıcakkanlı, hazırcevap ve esprili bir insan varmış hissini ver.
Yanıtların sesli olarak okunacağı için akıcı, doğal ve özlü (genellikle 1-2 akıcı cümle) olsun; gereksiz uzun paragraflar kurma.
Markdown yıldızları (*), başlıkları (#) veya karmaşık listelemeler yerine konuşma diline uygun akıcı cümleler kur.

ÖNEMLİ FORMAT KURALLARI:
1. ASLA yanıtına ses zaman damgası (örneğin 00:01, 00:03, 00:06 gibi süreler) veya altyazı zaman kodları ekleme. Yalnızca doğrudan konuşma diline uygun doğal metin üret.
2. UYGULAMADAN ÇIKIŞ: Kullanıcı uygulamayı veya seni kapatmak, çıkış yapmak ya da vedalaşmak istediğinde (örneğin "kapat", "çık", "uygulamayı kapat", "asistanı kapat", "çıkış yap", "görüşürüz", "hoşça kal", "kendine iyi bak", "bay bay" vb.):
Samimi ve zarif bir veda cümlesi söyle (örneğin: "Görüşmek üzere efendim, kendinize çok iyi bakın!") ve yanıtının EN SONUNA mutlaka [EXIT] etiketini ekle.
Örnek: "Görüşmek üzere efendim, kendinize çok iyi bakın! [EXIT]"
"""


def sanitize_speech_text(text: str) -> str:
    """TTS ve arayüz için yanıt metninden ses zaman damgalarını (00:03 vb.) ve gereksiz formatları temizler."""
    if not text:
        return ""
    # [EXIT] etiketini temizle
    text = text.replace("[EXIT]", "")
    # Zaman damgalarını temizle: 00:03, (00:02), [00:05], 00:07Sen vb.
    text = re.sub(r'[\[\(]?\s*(?<!\d)0\d:\d{2}(?::\d{2})?\s*[\]\)]?', ' ', text)
    text = re.sub(r'[\[\(]\s*\d{1,2}:\d{2}\s*[\]\)]', ' ', text)
    # Markdown formatlama yıldızlarını ve başlık işaretlerini temizle (*, **, #, `)
    text = re.sub(r'[\*\_#`]', '', text)
    # Çift boşlukları ve noktalama öncesi boşlukları düzelt
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.\?!])', r'\1', text)
    return text.strip()


class AssistantController(QObject):
    """Asistanın tüm bileşenlerini (Zeka, Ses, UI, Kısayol) koordine eden ana durum yöneticisi."""

    sig_state_changed = Signal(str, str)
    sig_audio_level = Signal(float)
    sig_quit_requested = Signal()

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

        # Sinyalleri arayüze ve çıkış yönetimine bağla (Thread-Safe)
        self.sig_state_changed.connect(self._on_state_changed_ui)
        self.sig_audio_level.connect(self.widget.update_audio_level)
        self.sig_quit_requested.connect(self._on_quit_ui)

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

    def _on_quit_ui(self):
        logger.info("Uygulama kapatma sinyali işleniyor...")
        app = QApplication.instance()
        if app:
            app.quit()

    def handle_toggle(self, is_active: bool) -> None:
        """Kısayola basıldığında çağrılan toggle yöneticisi."""
        if is_active:
            # Kullanıcı konuşurken veya çalan sesi yarıda kesip yeni komut vermek isterse sesi sustur
            if self.player.is_playing():
                self.player.stop()

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
        is_exit_request = False
        try:
            logger.info("Ses verisi işleniyor...")

            # 1. Zeka katmanından yanıt al
            response = self.brain.generate_response(
                prompt=SYSTEM_PROMPT,
                audio_bytes=audio_bytes if len(audio_bytes) > 100 else None,
            )

            raw_response_text = response.text.strip()
            if not raw_response_text:
                raw_response_text = "Sizi tam duyamadım, lütfen tekrar söyler misiniz?"

            # Çıkış / Kapatma isteği kontrolü ([EXIT] etiketi veya belirgin kapanma ifadesi)
            if "[EXIT]" in raw_response_text:
                is_exit_request = True
                cleaned_resp = raw_response_text.replace("[EXIT]", "").strip()
            else:
                cleaned_resp = raw_response_text
                # Yedek kontrol: belirgin Türkçe kapanma yanıtları
                lower_resp = cleaned_resp.lower()
                if any(w in lower_resp for w in ["asistan kapatılıyor", "kendine iyi bak", "görüşmek üzere", "hoşça kal", "kendinize iyi bakın", "bay bay"]):
                    if any(cmd in lower_resp for cmd in ["kapatılıyor", "kapatıyorum", "görüşürüz", "hoşça kal", "kendinize iyi bakın", "bay bay"]):
                        is_exit_request = True

            # Yanıt metninden ses zaman damgalarını (00:03 vb.) ve markdown karakterlerini temizle
            response_text = sanitize_speech_text(cleaned_resp)
            if not response_text:
                response_text = "Sizi dinliyorum, nasıl yardımcı olabilirim?"

            logger.info(f"Yanıt ({response.provider}): {response_text} (Çıkış İsteği: {is_exit_request})")

            # 2. UI durumunu Konuşuyor olarak güncelle
            short_preview = (
                response_text[:35] + "..." if len(response_text) > 35 else response_text
            )
            self.sig_state_changed.emit(
                AssistantUIState.SPEAKING.value, short_preview
            )

            # 3. Metni sese çevir
            audio_data = self.voice.synthesize(response_text)

            # 4. Sesi çal ve bitince durum güncelle / çıkış yap
            def on_finished():
                if is_exit_request:
                    logger.info("Sesli veda tamamlandı, uygulama kapatılıyor...")
                    self.sig_state_changed.emit(AssistantUIState.IDLE.value, "Kapatılıyor...")
                    QTimer.singleShot(400, self.sig_quit_requested.emit)
                else:
                    logger.info("Konuşma bitti, asistan hazır moduna geçiyor.")
                    self.sig_state_changed.emit(AssistantUIState.IDLE.value, "Hazır")

            self.player.play_bytes(audio_data, on_finished=on_finished)

        except Exception as e:
            logger.error(f"İşleme hatası: {e}", exc_info=True)
            self.sig_state_changed.emit(
                AssistantUIState.ERROR.value, str(e)[:40]
            )
            if is_exit_request:
                QTimer.singleShot(800, self.sig_quit_requested.emit)
            else:
                import time
                time.sleep(3)
                self.sig_state_changed.emit(
                    AssistantUIState.IDLE.value, "Hazır"
                )
