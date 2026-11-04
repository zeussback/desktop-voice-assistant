# Task List: Desktop Voice Assistant (Phase 1 MVP)

## Phase 1: Foundation & Brain Integration

### Task 1: Project Setup, Dependencies & Configuration
**Description:** Proje dizin yapısını, Python sanal ortam bağımlılıklarını (`requirements.txt`), tip güvenli konfigürasyon sınıfını (`config.py`) ve `.env.example` şablonunu oluşturur.
**Acceptance criteria:**
- [x] `requirements.txt` PySide6, pynput, sounddevice, numpy, google-genai, ollama, edge-tts, pygame içerir.
- [x] `src/config.py` Pydantic ile `.env` dosyasını okuyup varsayılan kısayolu (`Ctrl+Space`), Gemini model adını ve VoiceStudio URL'sini yönetir.
**Verification:**
- [x] `python -c "import pydantic; from src.config import settings; print(settings.HOTKEY)"` başarıyla çalışır.
**Dependencies:** None
**Files likely touched:**
- `requirements.txt`
- `.env.example`
- `src/__init__.py`
- `src/config.py`
- `pytest.ini`
- `tests/test_config.py`
**Estimated scope:** Small (2-3 files)

### Task 2: Brain Providers (Gemini Primary + Ollama Fallback)
**Description:** `BaseBrainProvider` soyut sınıfı tanımlanır; `GeminiProvider` (Google AI Studio / Gemini API) ve `OllamaProvider` (yerel hafif model) implementasyonları ile otomatik fallback mekanizması kurulur.
**Acceptance criteria:**
- [x] `GeminiProvider` kullanıcının API anahtarı ile Türkçe isteme yanıt üretir.
- [x] Gemini hata verirse veya bağlantı yoksa `OllamaProvider` otomatik devreye girer.
- [x] Her iki sağlayıcı da standart `BrainResponse` formatı döner.
**Verification:**
- [x] `pytest tests/test_brain.py` testleri başarılı geçer.
**Dependencies:** Task 1
**Files likely touched:**
- `src/brain/provider_base.py`
- `src/brain/gemini_provider.py`
- `src/brain/ollama_provider.py`
- `src/brain/hybrid_brain.py`
- `tests/test_brain.py`
**Estimated scope:** Medium (3-4 files)

## Checkpoint 1: Brain Integration
- [x] Brain provider testleri (`test_brain.py`) geçer.
- [x] Hem Gemini hem Ollama arayüzleri standart formatta yanıt döndürür.

---

## Phase 2: Audio & Voice Engines

### Task 3: Microphone Audio Capture & Buffer
**Description:** `sounddevice` ve `numpy` kullanarak mikrofon sesini başlatan ve durduran (`start_recording`, `stop_recording`) thread-safe ses kayıt modülü oluşturur.
**Acceptance criteria:**
- [x] Toggle ile kayıt başlatılıp durdurulduğunda geçici WAV tamponu elde edilir.
- [x] Mikrofon sessizlik / ses seviyesi (RMS) hesaplanarak ileride ses animasyonlarında kullanılacak seviye verisi sağlanır.
**Verification:**
- [x] `pytest tests/test_audio_recorder.py` veya loopback test başarıyla çalışır.
**Dependencies:** Task 1
**Files likely touched:**
- `src/core/audio_recorder.py`
- `tests/test_audio_recorder.py`
**Estimated scope:** Small (2 files)

### Task 4: Voice Synthesis & Audio Player (VoiceStudio + Edge-TTS)
**Description:** Metni sese dönüştüren `VoiceStudioClient` (birincil) ve `EdgeTTSClient` (yedek) motorları ile üretilen sesi UI'ı dondurmadan çalan `AudioPlayer` modülü geliştirilir.
**Acceptance criteria:**
- [x] `VoiceStudioClient` yerel sunucuyu (`http://localhost:3900`) kontrol eder; yanıt alamazsa otomatik `EdgeTTSClient` devreye girer.
- [x] Üretilen ses `AudioPlayer` ile kesintisiz ve temiz oynatılır.
**Verification:**
- [x] `pytest tests/test_voice.py` testleri çalışır ve kısa bir Türkçe metin test amaçlı sese dönüştürülür.
**Dependencies:** Task 1
**Files likely touched:**
- `src/voice/tts_base.py`
- `src/voice/voicestudio_client.py`
- `src/voice/edge_tts_client.py`
- `src/voice/hybrid_tts.py`
- `src/voice/audio_player.py`
- `tests/test_voice.py`
**Estimated scope:** Medium (4 files)

## Checkpoint 2: Voice & Audio Subsystem
- [x] Ses kaydı ve ses sentezi izolasyon testlerinden geçer.
- [x] Yedekleme mantığı (VoiceStudio kapalıysa edge-tts) sorunsuz çalışır.

---

## Phase 3: Liquid Glass UI Widget & Global Hotkey

### Task 5: Glass-Liquid PySide6 Widget & State Animations
**Description:** Ekranın üst-orta kısmında konumlanan, çerçevesiz, yarı saydam, modern buzlu cam (acrylic/blur) efektli ve animasyonlu durum göstergesi (IDLE, LISTENING, THINKING, SPEAKING) geliştirilir.
**Acceptance criteria:**
- [x] Widget ekranın en üstünde (`WindowStaysOnTopHint`), çerçevesiz ve şeffaf arka planla açılır.
- [x] "Dinleniyor", "Düşünülüyor", "Konuşuyor" geçişlerinde yumuşak yaylanma/genişleme ve renk geçiş animasyonu çalışır.
- [x] Dinleme bittiğinde veya konuşma tamamlandığında widget şık bir şekilde küçülür/gizlenir.
**Verification:**
- [x] `python -m src.ui.widget` ile widget bağımsız olarak çalıştırılıp görsel durumları test edilir.
**Dependencies:** Task 1
**Files likely touched:**
- `src/ui/widget.py`
- `src/ui/styles.py`
- `tests/test_ui.py`
**Estimated scope:** Medium (3 files)

### Task 6: Global Hotkey Listener (Toggle Mode)
**Description:** `pynput` ile sistem genelinde basıldığında (`Ctrl+Space` veya `Alt+Space`) `toggle` sinyali üreten küresel kısayol yakalayıcı thread oluşturur.
**Acceptance criteria:**
- [x] Diğer pencereler odaktayken dahi kısayola basıldığında sinyal yakalanır.
- [x] İlk basışta `ON_START`, ikinci basışta `ON_STOP` sinyali üretilir.
**Verification:**
- [x] Kısayol testi ile basışların doğru toggle durumunu tetiklediği doğrulanır.
**Dependencies:** Task 1
**Files likely touched:**
- `src/core/hotkey_listener.py`
- `tests/test_hotkey.py`
**Estimated scope:** Small (2 files)

## Checkpoint 3: UI & Hotkey Integration
- [x] Kısayola basıldığında widget ekranın üstünde animasyonla açılır ve kapanır.
- [x] Kullanıcı deneyimi akıcı ve takılmasızdır.

---

## Phase 4: Integration & End-to-End Orchestration

### Task 7: Assistant State Machine & Orchestrator
**Description:** Hotkey, UI Widget, Audio Recorder, Brain ve Voice modüllerini `AssistantController` çatısı altında birbirine bağlar.
**Acceptance criteria:**
- [ ] 1. Basış (Ctrl+Space): Widget "Dinleniyor..." animasyonuyla açılır, mikrofon kayda başlar.
- [ ] 2. Basış (Ctrl+Space): Mikrofon durur, widget "Düşünülüyor..." durumuna geçer, ses Brain'e (Gemini) aktarılır.
- [ ] Yanıt geldiğinde: Widget "Konuşuyor..." durumuna geçer, Voice motoru sesi üretir ve hoparlörden çalar.
- [ ] Konuşma bittiğinde: Widget yumuşak bir animasyonla kapanır (IDLE).
**Verification:**
- [ ] Uçtan uca diyalog testi başarıyla tamamlanır.
**Dependencies:** Tasks 2, 3, 4, 5, 6
**Files likely touched:**
- `src/core/assistant.py`
- `src/main.py`
**Estimated scope:** Medium (2 files)

### Task 8: Polishing, CLI Startup & User Guide
**Description:** `.env` kurulum rehberi, hata yakalama (mikrofon yok, API kotası, internet kesintisi), masaüstü başlatıcı ve `README.md` dokümantasyonu tamamlanır.
**Acceptance criteria:**
- [ ] Kullanıcı kolayca `.env` dosyasını oluşturup Gemini API anahtarını girebilir.
- [ ] İnternet veya servis hatalarında widget kırmızı/uyarı animasyonuyla kullanıcıyı bilgilendirir, uygulama çökmez.
**Verification:**
- [ ] `python -m src.main` ile asistan hatasız ayağa kalkar.
**Dependencies:** Task 7
**Files likely touched:**
- `README.md`
- `src/main.py`
**Estimated scope:** Small (2 files)

## Final Checkpoint: Phase 1 MVP Complete
- [ ] Tüm testler geçer (`pytest`).
- [ ] Asistan kesintisiz sesli konuşma döngüsünü tamamlar.
- [ ] Kullanıcı ile birlikte ilk canlı deneme gerçekleştirilir.
