"""Assistant state machine and orchestrator coordinating Brain, Voice, UI, and Tools."""

from datetime import datetime
import logging
import re
import threading
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from src.brain.provider_base import BaseBrainProvider
from src.core.audio_recorder import AudioRecorder
from src.tools.registry import ToolRegistry
from src.ui.widget import AssistantUIState, GlassLiquidWidget
from src.voice.audio_player import AudioPlayer
from src.voice.tts_base import BaseTTSClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Senin adın Jarvis. Kullanıcının bilgisayarında çalışan son derece zeki, esprili, samimi ve güvenilir kişisel asistanısın.
Kullanıcı seninle Türkçe konuşuyor.
Kullanıcıya her zaman saygılı ve samimi bir üslupla "efendim" diye hitap et (örneğin: "Tabii ki efendim", "Hemen bakıyorum efendim", "Nasıl arzu ederseniz efendim").
Robotik, soğuk ya da kalıplaşmış yapay zeka klişelerinden (örneğin "Ben bir dil modeliyim", "Size bugün nasıl yardımcı olabilirim?" gibi yapmacık kalıplardan) kesinlikle kaçın.
Karşında bir makine değil; zeki, canlı, sıcakkanlı, hazırcevap ve esprili bir insan varmış hissini ver.
Yanıtların sesli olarak okunacağı için akıcı, doğal ve özlü olsun; gereksiz uzun paragraflar kurma.
Markdown yıldızları (*), başlıkları (#) veya karmaşık listelemeler yerine konuşma diline uygun akıcı cümleler kur.

BİLGİSAYAR KONTROLÜ VE ARAÇ KULLANIMI:
Sistem ayarları (ses, parlaklık, medya), uygulama açma/kapama, web sitelerini açma, Google Takvim veya Gmail işlemleri için sana sağlanan araçları (tools) kullan.
1. Medya Kontrolü: Kullanıcı 'müziği başlat', 'müziği aç', 'şarkı çal', 'müziği durdur' gibi komutlar verdiğinde 'control_application' DEĞİL, 'control_media' (action='play_pause') aracını kullan.
2. Çoklu Komutlar: Kullanıcı tek cümlede birden fazla işlem istediğinde, gerekli araçları arka arkaya çağır (parallel function call).
3. E-Posta ve Ajanda Özetleme Kuralları:
   - E-posta Özeti: Kullanıcı e-postalarını sorduğunda (örn: 'son gelen mailim ne', 'maillerimi oku'), ASLA sadece kuru başlıkları okuyup geçme! Gönderenin kim olduğunu, konuyu ve e-postanın NE ANLATTIĞINI (içeriğin kısa özetini) akıcı bir dille aktar.
   - Önem Sınıflandırması: Kullanıcı birden fazla e-posta istediğinde veya 'önemli/önemsiz özetle' dediğinde; kişisel ve iş mesajlarını bülten, reklam ve sosyal medya bildirimlerinden ayırarak özetle.
   - Okundu Olarak İşaretleme: Kullanıcı 'okundu yap', 'okundu olarak işaretle', 'özetlediğin mailleri okundu yap/işaretle' gibi komutlar verdiğinde 'manage_gmail' aracını action='mark_as_read' ile çağır. Kesinlikle yeniden e-posta özeti geçme.
   - Sesli Okuma Kuralları: Yanıtlarında asla emoji, Unicode kodları, ham URL bağlantıları veya teknik e-posta formatları kullanma. Yabancı kelimeleri ve kısaltmaları Türkçe konuşma akışına uygun telaffuz edilecek şekilde doğal aktar.

ÜSLUP VE HİTAP KURALI:
- 'efendim' hitabını yanıtında yalnızca BİR KEZ (tercihen cümlenin sonunda veya başında) kullan. Asla her cümlenin sonuna papağan gibi arka arkaya 'efendim' ekleme.
- Birden fazla eylemi özetlerken cümleleri ayrı ayrı kurmak yerine 've' bağlacıyla birbirine bağla (örneğin: 'Sesi yüzde 80 yaptım ve YouTube'u açtım efendim').

ÖNEMLİ FORMAT KURALLARI:
1. ASLA yanıtına ses zaman damgası (örneğin 00:01, 00:03, 00:06 gibi süreler) veya altyazı zaman kodları ekleme. Yalnızca doğrudan konuşma diline uygun doğal metin üret.
2. UYGULAMADAN ÇIKIŞ: Kullanıcı uygulamayı veya seni kapatmak, çıkış yapmak ya da vedalaşmak istediğinde:
Samimi ve zarif bir veda cümlesi söyle ve yanıtının EN SONUNA mutlaka [EXIT] etiketini ekle.
Örnek: "Görüşmek üzere efendim, kendinize çok iyi bakın! [EXIT]"
"""

DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
MONTHS_TR = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
]


def get_current_datetime_prompt() -> str:
    """Yapay zekanın güncel sistem tarih ve saatini bilmesini sağlayan dinamik prompt parçasını döner."""
    now = datetime.now()
    day_name = DAYS_TR[now.weekday()]
    month_name = MONTHS_TR[now.month - 1]
    formatted = f"{now.day} {month_name} {now.year} {day_name}, Saat: {now.strftime('%H:%M')}"
    return (
        f"\n\nGÜNCEL SİSTEM TARİHİ VE ZAMANI:\n"
        f"Şu anki gerçek sistem zamanı: {formatted}.\n"
        f"Kullanıcı bugünün tarihini veya saatini sorduğunda, ya da 'bugün', 'yarın', 'bu hafta' gibi zaman planlamaları yaptığında "
        f"kesinlikle bu güncel tarihi ve saati esas al. Asla kafandan farklı bir tarih, gün ya da yıl uydurma."
    )


EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]|"
    r"[\u200d\uFE0E\uFE0F]|"
    r"[\u2600-\u27bf]|"
    r"[\u2300-\u23ff]|"
    r"[\u2b50\u2b55\u2934\u2935\u25aa\u25ab\u25fe\u25fd]"
)


def clean_repeated_efendim(text: str) -> str:
    """Metin içinde birden fazla geçen 'efendim' kelimesini temizleyip yalnızca sonuncuyu bırakır."""
    matches = list(re.finditer(r'\befendim\b', text, flags=re.IGNORECASE))
    if len(matches) <= 1:
        return text
    new_text = ""
    last_idx = 0
    for m in matches[:-1]:
        new_text += text[last_idx:m.start()]
        last_idx = m.end()
    new_text += text[last_idx:]
    # Noktalama öncesi boşlukları ve çift noktalamaları düzelt
    new_text = re.sub(r'\s+([,.\?!])', r'\1', new_text)
    new_text = re.sub(r'([,])\s*([.])', r'.', new_text)
    new_text = re.sub(r'\s+', ' ', new_text).strip()
    # Başta kalan gereksiz virgül veya noktalama işaretlerini temizle
    new_text = new_text.lstrip(" ,;:.")
    if new_text and new_text[0].islower():
        new_text = new_text[0].upper() + new_text[1:]
    return new_text


def sanitize_speech_text(text: str) -> str:
    """TTS ve arayüz için yanıt metninden ses zaman damgalarını, emojileri ve gereksiz formatları temizler."""
    if not text:
        return ""
    # [EXIT] etiketini temizle
    text = text.replace("[EXIT]", "")
    # Zaman damgalarını temizle: 00:03, (00:02), [00:05], 00:07Sen vb.
    text = re.sub(r'[\[\(]?\s*(?<!\d)0\d:\d{2}(?::\d{2})?\s*[\]\)]?', ' ', text)
    text = re.sub(r'[\[\(]\s*\d{1,2}:\d{2}\s*[\]\)]', ' ', text)
    # Markdown formatlama yıldızlarını ve başlık işaretlerini temizle (*, **, #, `)
    text = re.sub(r'[\*\_#`]', '', text)
    # Emojileri temizle (TTS'in garip kod veya harf okumasını engeller)
    text = EMOJI_PATTERN.sub('', text)
    # Web adreslerini temizle (TTS'in http:// harf harf okumasını engeller)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # Üç nokta ve tire tekrarlarını konuşma duraklamasına dönüştür
    text = text.replace('…', '. ')
    text = re.sub(r'\.{2,}', '. ', text)
    text = re.sub(r'\-{2,}', ' ', text)
    # Türkçe TTS için sık karşılaşılan kısaltma ve marka telaffuz düzenlemeleri
    text = re.sub(r'\bUI\b', 'kullanıcı arayüzü', text)
    text = re.sub(r'\bUX\b', 'kullanıcı deneyimi', text)
    text = re.sub(r'\bAI\b', 'yapay zeka', text)
    text = re.sub(r'\bLinkedIn\b', 'Linkdin', text, flags=re.IGNORECASE)
    text = re.sub(r'\bYouTube\b', 'Yutub', text, flags=re.IGNORECASE)
    text = re.sub(r'\bGmail\b', 'Gimeyl', text, flags=re.IGNORECASE)
    # Özel sembolleri düzelt
    text = text.replace('&', ' ve ')
    text = text.replace('@', ' ')
    # Tekrarlanan 'efendim' hitaplarını temizle (yalnızca 1 adet bırak)
    text = clean_repeated_efendim(text)
    # Çift boşlukları ve noktalama öncesi boşlukları düzelt
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.\?!])', r'\1', text)
    return text.strip()


class AssistantController(QObject):
    """Asistanın tüm bileşenlerini (Zeka, Ses, UI, Araçlar, Kısayol) koordine eden ana durum yöneticisi."""

    sig_state_changed = Signal(str, str)
    sig_audio_level = Signal(float)
    sig_quit_requested = Signal()
    sig_start_rms_timer = Signal(int)
    sig_stop_rms_timer = Signal()

    def __init__(
        self,
        brain: BaseBrainProvider,
        voice: BaseTTSClient,
        recorder: AudioRecorder,
        widget: GlassLiquidWidget,
        player: Optional[AudioPlayer] = None,
        tool_registry: Optional[ToolRegistry] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.brain = brain
        self.voice = voice
        self.recorder = recorder
        self.widget = widget
        self.player = player or AudioPlayer()
        self.tool_registry = tool_registry

        self.current_state = AssistantUIState.IDLE
        self.pending_confirmation: Optional[Dict[str, Any]] = None

        # Sinyalleri arayüze ve çıkış yönetimine bağla (Thread-Safe)
        self.sig_state_changed.connect(self._on_state_changed_ui)
        self.sig_audio_level.connect(self.widget.update_audio_level)
        self.sig_quit_requested.connect(self._on_quit_ui)

        # Mikrofon seviyesi anlık izleme zamanlayıcısı (Thread-Safe Sinyal/Slot)
        self._rms_timer = QTimer(self)
        self._rms_timer.timeout.connect(self._poll_rms_level)
        self.sig_start_rms_timer.connect(self._rms_timer.start)
        self.sig_stop_rms_timer.connect(self._rms_timer.stop)

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
                self.sig_start_rms_timer.emit(50)  # Thread-safe sinyal ile zamanlayıcıyı başlat
            else:
                self.sig_state_changed.emit(
                    AssistantUIState.ERROR.value, "Mikrofon başlatılamadı"
                )
        else:
            # 2. Basış -> Dinleme Durur, Düşünme & Cevap Başlar
            self.sig_stop_rms_timer.emit()  # Thread-safe sinyal ile zamanlayıcıyı durdur
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

            active_prompt = SYSTEM_PROMPT + get_current_datetime_prompt()
            if self.pending_confirmation:
                conf_prompt = self.pending_confirmation.get("prompt", "")
                active_prompt += (
                    f"\n\n[DURUM: Kullanıcıya az önce şu teyit sorusunu sordun: '{conf_prompt}'. "
                    f"Kullanıcının yanıtını dinle. Eğer onaylıyorsa (evet, yap, kapat, onaylıyorum vb.), teyit ettiğini belirt. "
                    f"Eğer reddediyorsa (hayır, iptal, vazgeç vb.), işlemi iptal ettiğini kibarca söyle.]"
                )

            # 1. Zeka katmanından yanıt al
            response = self.brain.generate_response(
                prompt=active_prompt,
                audio_bytes=audio_bytes if len(audio_bytes) > 100 else None,
            )

            # Eğer daha önce onay bekleyen bir işlem varsa ve bu turda yanıt geldiyse
            if self.pending_confirmation:
                resp_lower = response.text.lower()
                is_cancelled = any(w in resp_lower for w in ["iptal", "vazgeç", "hayır", "yapma", "istemiyorum"])
                if is_cancelled:
                    logger.info("Kullanıcı işlemi iptal etti.")
                    self.pending_confirmation = None
                    raw_response_text = "İşlemi iptal ettim efendim."
                else:
                    # Onaylandı -> bekleyen aracı confirmed=True ile çalıştır
                    pending = self.pending_confirmation
                    self.pending_confirmation = None
                    tool_name = pending["tool_name"]
                    tool_args = pending.get("args", {})
                    logger.info(f"Onaylanan araç çalıştırılıyor: {tool_name}({tool_args})")
                    if self.tool_registry:
                        exec_res = self.tool_registry.execute(tool_name, tool_args, confirmed=True)
                        raw_response_text = exec_res.message
                    else:
                        raw_response_text = "İşlem onaylandı efendim."

            elif response.needs_confirmation:
                # Yeni bir teyit gerektiren araç tetiklendi
                logger.info(f"Araç teyit bekliyor: {response.tool_called}")
                self.pending_confirmation = {
                    "tool_name": response.tool_called,
                    "args": (response.tool_result or {}).get("data", {}).get("pending_args", {}),
                    "prompt": response.confirmation_prompt or response.text,
                }
                raw_response_text = response.text.strip()

            else:
                raw_response_text = response.text.strip()

            if not raw_response_text:
                raw_response_text = "Sizi tam duyamadım, lütfen tekrar söyler misiniz?"

            # Çıkış / Kapatma isteği kontrolü ([EXIT] etiketi veya belirgin kapanma ifadesi)
            if "[EXIT]" in raw_response_text:
                is_exit_request = True
                cleaned_resp = raw_response_text.replace("[EXIT]", "").strip()
            else:
                cleaned_resp = raw_response_text
                lower_resp = cleaned_resp.lower()
                if any(w in lower_resp for w in ["asistan kapatılıyor", "kendine iyi bak", "görüşmek üzere", "hoşça kal", "kendinize iyi bakın", "bay bay"]):
                    if any(cmd in lower_resp for cmd in ["kapatılıyor", "kapatıyorum", "görüşürüz", "hoşça kal", "kendinize iyi bakın", "bay bay"]):
                        is_exit_request = True

            # Yanıt metninden ses zaman damgalarını (00:03 vb.) ve markdown karakterlerini temizle
            response_text = sanitize_speech_text(cleaned_resp)
            if not response_text:
                response_text = "Sizi dinliyorum efendim, nasıl yardımcı olabilirim?"

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
