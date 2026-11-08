# Task List: Desktop Voice Assistant

## Phase 1: MVP (Voice Loop, Jarvis Persona & Liquid Glass UI) — COMPLETED ✅
- [x] Task 1: Project Setup, Dependencies & Configuration
- [x] Task 2: Brain Providers (Gemini Primary + Ollama Fallback)
- [x] Task 3: Microphone Audio Capture & Buffer
- [x] Task 4: Voice Synthesis & Audio Player (Piper TTS + Edge-TTS)
- [x] Task 5: Glass-Liquid PySide6 Widget & State Animations
- [x] Task 6: Global Hotkey Listener (Toggle Mode)
- [x] Task 7: Assistant State Machine & Orchestrator
- [x] Task 8: Polishing, CLI Startup & User Guide
- [x] Final Checkpoint: Phase 1 MVP Complete (34 unit tests passing, commit `b48503c`)

---

## Phase 2: OS Control & Tool Engine

### Task 1: Tool Engine Core (`BaseTool`, `ToolResult`, `ToolRegistry`)
**Description:** Araçların tanımlanacağı `BaseTool` soyut sınıfını, standart `ToolResult` sonucunu ve araçları kaydedip Gemini Function Calling JSON şemalarına dönüştüren `ToolRegistry` merkezi motorunu oluşturur.
**Acceptance criteria:**
- [x] `BaseTool` sınıfı `name`, `description`, `confirmation_policy`, `get_declaration()` ve `execute(**kwargs)` arayüzlerini içerir.
- [x] `ToolResult` (Pydantic) başarı durumu (`success`), seslendirilecek mesaj (`message`), veri sözlüğü (`data`) ve teyit alanlarını (`needs_confirmation`, `confirmation_prompt`) barındırır.
- [x] `ToolRegistry` araçları kaydeder (`register`), isim çakışmalarını önler, Gemini `types.FunctionDeclaration` uyumlu şema listesi üretir ve araçları çağırır (`execute`).
**Verification:**
- [x] `pytest tests/test_tools.py` testleri başarıyla geçer.
**Dependencies:** None
**Files likely touched:**
- `src/tools/__init__.py`
- `src/tools/base.py`
- `src/tools/registry.py`
- `tests/test_tools.py`
**Estimated scope:** Small (4 files)

---

### Task 2: System Audio & Media Control Tools
**Description:** Windows ana ses düzeyini okuma/ayarlama (`pycaw`) ve klavye sanal tuşlarıyla medya oynatma/durdurma (`ctypes` keybd_event) araçlarını geliştirir.
**Acceptance criteria:**
- [x] `SystemAudioTool` eylemleri: `set_volume` (0-100 aralığında sınırlandırılmış), `change_volume` (artır/azalt), `mute` ve `unmute`.
- [x] `MediaControlTool` eylemleri: `play_pause`, `next_track`, `prev_track`, `stop`.
- [x] Ses ve medya işlemleri sonucunda Jarvis'in söyleyeceği doğal Türkçe mesajlar üretilir.
**Verification:**
- [x] `pytest tests/test_os_control.py -k "audio or media"` testleri geçer.
**Dependencies:** Task 1
**Files likely touched:**
- `src/tools/system_audio.py`
- `src/tools/media_control.py`
- `tests/test_os_control.py`
- `requirements.txt`
**Estimated scope:** Small (3-4 files)

---

### Task 3: Display Brightness & Web Browser Tools
**Description:** Monitör parlaklığını kontrol eden `SystemBrightnessTool` (`screen_brightness_control`) ve varsayılan tarayıcıda URL açıp Google araması yapan `WebBrowserTool` araçlarını geliştirir.
**Acceptance criteria:**
- [x] `SystemBrightnessTool` eylemleri: `set_brightness` (0-100), `change_brightness` (artır/azalt), `get_brightness`. Monitör desteklemiyorsa çökmek yerine kullanıcıya anlaşılır bilgi döner.
- [x] `WebBrowserTool` eylemleri: `open_url` (http/https doğrulamalı) ve `search_google` (arama terimlerini URL kodlamalı).
**Verification:**
- [x] `pytest tests/test_os_control.py -k "brightness or browser"` testleri geçer.
**Dependencies:** Task 1
**Files likely touched:**
- `src/tools/system_brightness.py`
- `src/tools/web_browser.py`
- `tests/test_os_control.py`
- `requirements.txt`
**Estimated scope:** Small (3-4 files)

---

## Checkpoint 1: Tool Registry & Core System Tools
- [x] `test_tools.py` ve `test_os_control.py` testleri geçer.
- [x] Ses, medya, parlaklık ve web araçları mock'larla doğrulanır.

---

### Task 4: Application Control & Power Management Tools
**Description:** Windows uygulamalarını açıp (`os.startfile` / Başlat Menüsü taraması) çalışan süreçleri kapatan (`psutil`) `AppControlTool` ile teyit gerektiren sistem kapatma/yeniden başlatma aracı `SystemPowerTool`'u geliştirir.
**Acceptance criteria:**
- [ ] `AppControlTool`: Uygulama adı verildiğinde Başlat menüsü kısayollarında (`.lnk`) ve sistem yollarında arayıp başlatır. Kapatma istendiğinde `psutil` ile çalışan süreci bulup güvenle sonlandırır. Bulunamazsa kibar geri bildirim verir.
- [ ] `SystemPowerTool`: `shutdown`, `restart`, `sleep` komutlarını içerir ve `ConfirmationPolicy.REQUIRE_CONFIRMATION` işaretlidir; doğrudan çalıştırmak yerine `needs_confirmation=True` ve sesli teyit sorusu döner.
**Verification:**
- [ ] `pytest tests/test_os_control.py -k "app or power"` testleri geçer.
**Dependencies:** Task 1
**Files likely touched:**
- `src/tools/app_control.py`
- `src/tools/system_power.py`
- `tests/test_os_control.py`
**Estimated scope:** Medium (3 files)

---

### Task 5: Gemini Provider Tool Calling Loop & Function Execution
**Description:** `GeminiProvider` sınıfını `ToolRegistry` ile entegre ederek Gemini'a tool tanımlarını gönderir, dönen `function_call` çağrılarını yakalar ve araç sonuçlarını modele veya kullanıcıya iletir.
**Acceptance criteria:**
- [ ] `GeminiProvider.generate_response` metodu `tools` parametresini destekler.
- [ ] Gemini yanıtında `function_calls` varsa, ilgili araç `ToolRegistry` üzerinden çalıştırılır ve sonuç alınır.
- [ ] Araç sonucuna göre doğrudan seslendirilecek mesaj veya ikinci tur model çıktısı üretilir.
**Verification:**
- [ ] `pytest tests/test_brain.py` testleri (mock function calling senaryoları dahil) geçer.
**Dependencies:** Tasks 1, 2, 3, 4
**Files likely touched:**
- `src/brain/provider_base.py`
- `src/brain/gemini_provider.py`
- `tests/test_brain.py`
**Estimated scope:** Medium (3 files)

---

### Task 6: Assistant Controller Confirmation State Machine & End-to-End Orchestration
**Description:** `AssistantController`'a `ToolRegistry`'yi bağlar; araç çalıştırma ve kritik eylemler için `AWAITING_CONFIRMATION` durumunu ekleyerek sesli onay döngüsünü tamamlar.
**Acceptance criteria:**
- [ ] Araç `needs_confirmation=True` döndüğünde asistan `AWAITING_CONFIRMATION` durumuna geçer ve teyit sorusunu seslendirir.
- [ ] Kullanıcının bir sonraki cevabında onay kelimesi ("evet", "kapat", "onayla") varsa eylem icra edilir; ret kelimesi ("hayır", "iptal") varsa eylem iptal edilir.
- [ ] Normal araçlarda işlem tamamlandıktan sonra sonuç metni Piper TTS ile seslendirilir.
- [ ] Tüm eski (34) ve yeni testler (toplam 50+) hatasız geçer.
**Verification:**
- [ ] `pytest tests/ -v` komutuyla tüm test süiti başarıyla tamamlanır.
- [ ] Canlı testte sesli olarak ses açma/kapama, uygulama açma ve web arama komutları doğrulanır.
**Dependencies:** Tasks 1, 2, 3, 4, 5
**Files likely touched:**
- `src/core/assistant.py`
- `src/main.py`
- `tests/test_assistant_tools.py`
- `tests/test_assistant_controller.py`
**Estimated scope:** Medium (4 files)

---

## Final Checkpoint: Phase 2 OS Control Complete
- [ ] Tüm testler yeşil (`pytest`).
- [ ] Jarvis sesli komutla ses ayarlarını, medyayı, parlaklığı, uygulamaları ve web aramalarını başarıyla yönetir.
- [ ] Bilgisayarı kapatma gibi kritik komutlarda sesli teyit güvenle çalışır.
