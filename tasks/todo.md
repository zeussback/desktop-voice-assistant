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

## Phase 2: OS Control & Tool Engine — COMPLETED ✅
- [x] Task 1: Tool Engine Core (`BaseTool`, `ToolResult`, `ToolRegistry`)
- [x] Task 2: System Audio & Media Control Tools
- [x] Task 3: Display Brightness & Web Browser Tools
- [x] Task 4: Application Control & Power Management Tools
- [x] Task 5: Gemini Provider Tool Calling Loop & Function Execution
- [x] Task 6: Assistant Controller Confirmation State Machine & End-to-End Orchestration
- [x] Final Checkpoint: Phase 2 OS Control Complete (90 unit tests passing, commit `ffb4970`)

---

## Phase 3: Vision (Ekran Görme & İnceleme)

### Task 1: Pillow Bağımlılığı & Bellek İçi Ekran Yakalama Motoru
**Description:** `Pillow` kütüphanesini projeye ekler; birincil ekranı diske dokunmadan doğrudan RAM bellekte (`io.BytesIO`) JPEG formatında yakalayan, RGBA modunu RGB'ye dönüştüren ve 1920x1080 sınırına ölçeklendiren yardımcı fonksiyonu yazar.
**Acceptance criteria:**
- [x] `Pillow` paketi `requirements.txt` dosyasına eklenir.
- [x] `capture_screen_bytes(max_width=1920, max_height=1080)` fonksiyonu geçerli JPEG baytları (`bytes`) döner.
- [x] Görüntü diske dosya olarak asla yazılmaz (`os.path.exists` ile dosya oluşmadığı test edilir).
- [x] 1920x1080'den büyük görüntüler orantılı olarak küçültülür.
**Verification:**
- [x] `pytest tests/test_vision.py -k "capture"` testleri başarıyla geçer.
**Dependencies:** None
**Files likely touched:**
- `requirements.txt`
- `src/tools/screen_inspection.py`
- `tests/test_vision.py`
**Estimated scope:** Small (2-3 files)

---

### Task 2: Screen Inspection Tool (`ScreenInspectionTool`) & Tool Registry Entegrasyonu
**Description:** `BaseTool` sınıfından türetilen `ScreenInspectionTool` sınıfını oluşturur, Gemini multimodal API'si üzerinden ekranı analiz eden metodu uygular ve aracı `ToolRegistry` fabrikasına (`create_default_tool_registry`) kaydeder.
**Acceptance criteria:**
- [x] `ScreenInspectionTool`, `inspect_screen` adıyla ve Gemini yönlendirici açıklamasıyla tanımlanır.
- [x] `execute(query=...)` metodu ekranı yakalayıp Gemini Vision modeliyle analiz eder ve `ToolResult(success=True, message=...)` döner.
- [x] Ekran yakalama veya API hatası durumunda çökmez; `"Ekran görüntüsü alınamadı veya analiz edilemedi efendim."` şeklinde nazik hata mesajı döner.
- [x] `create_default_tool_registry()` çağrıldığında `inspect_screen` aracı otomatik olarak kaydedilir.
**Verification:**
- [x] `pytest tests/test_vision.py -k "tool or registry"` testleri başarıyla geçer.
**Dependencies:** Task 1
**Files likely touched:**
- `src/tools/screen_inspection.py`
- `src/tools/__init__.py`
- `tests/test_vision.py`
**Estimated scope:** Small (3 files)

---

### Task 3: Gemini Multimodal Entegrasyonu & Model Fallback Dayanıklılığı
**Description:** `GeminiProvider` ve `ScreenInspectionTool` arasındaki multimodal veri akışını, sistem istemi ve TTS optimizasyonunu sağlar; geçici 429 veya sunucu hatalarında yedek modellere geçişi garanti altına alır.
**Acceptance criteria:**
- [x] Gemini Vision istemi yanıtı 1-3 cümle, kod ve madde imi içermeyen akıcı Türkçe ve tek bir *"efendim"* ile sınırlandırır.
- [x] `GeminiProvider`, Gemini'ın `inspect_screen` fonksiyon çağrısını yakalayıp başarıyla çalıştırır.
- [x] Fallback modelleri (`gemini-3.5-flash`, `gemini-2.5-flash` vb.) multimodal istekleri de destekleyecek şekilde çalışır.
**Verification:**
- [x] `pytest tests/test_vision.py` ve `pytest tests/test_brain.py` testleri başarıyla geçer.
**Dependencies:** Tasks 1, 2
**Files likely touched:**
- `src/tools/screen_inspection.py`
- `src/brain/gemini_provider.py`
- `tests/test_vision.py`
**Estimated scope:** Small (2-3 files)

---

## Checkpoint: Phase 3 Vision Complete & Full Regression
- [x] `pytest tests/test_vision.py` testleri 100% geçer.
- [x] `pytest tests/ -v` ile tüm test süiti (104 test) sıfır regresyon ile yeşil tamamlanır.
- [x] Diskte hiçbir geçici ekran görüntüsü dosyası oluşmadığı doğrulanır.
- [x] Asistan başlatıldığında *"Ekranda ne var?"* dendiğinde anında görme ve seslendirme döngüsü çalışır.

---

## Phase 4: Kişisel Asistan & Sekreterlik (Google Calendar, Deadlines, Gmail & Morning Briefing)

### Task 1: Google API Bağımlılıkları, Güvenlik Yapılandırması & Kimlik Doğrulama Katmanı
**Description:** `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2`, `python-dateutil` bağımlılıklarını ekler; `.gitignore`'a `credentials.json` ve `token.json` ekler; `src/tools/google_auth.py` içinde `GoogleAuthManager` sınıfını ve servis sağlayıcılarını yazar.
**Acceptance criteria:**
- [x] Bağımlılıklar `requirements.txt` dosyasına eklenir.
- [x] `credentials.json` ve `token.json` `.gitignore` içine eklenerek güvenlik sağlanır.
- [x] `GoogleAuthManager`, `token.json` varsa otomatik yükler, süresi dolmuşsa `refresh` eder.
- [x] `credentials.json` bulunamadığında çökmek yerine kullanıcıya anlaşılır sesli rehberlik döner.
**Verification:**
- [x] `pytest tests/test_google_auth.py -v` testleri başarıyla geçer.
**Dependencies:** None
**Files likely touched:**
- `requirements.txt`
- `.gitignore`
- `src/tools/google_auth.py`
- `tests/test_google_auth.py`
**Estimated scope:** Small (3-4 files)

---

### Task 2: Google Calendar & Teslim Tarihi Yönetimi (`GoogleCalendarTool` / `manage_calendar`)
**Description:** Google Calendar v3 API'si ile entegre `GoogleCalendarTool` sınıfını oluşturur; toplantı/etkinlik ekleme, günün ajandasını listeleme, `[Son Tarih]` etiketli teslim tarihlerini ekleme ve sorgulama yeteneklerini sağlar.
**Acceptance criteria:**
- [x] `manage_calendar` aracı `list_events`, `add_event`, `list_deadlines`, `add_deadline` eylemlerini destekler.
- [x] Tarih ve saatler RFC 3339 formatında doğru işlenir.
- [x] Teslim tarihleri Google Takvim'de `[Son Tarih]` etiketiyle saklanır ve *"Yarına ne yetişmeli?"*, *"3 gün sonraya ne var?"* sorgularında doğru filtrelenir.
- [x] `create_default_tool_registry()` fabrikasına kaydedilir.
**Verification:**
- [x] `pytest tests/test_google_calendar.py -v` testleri başarıyla geçer.
**Dependencies:** Task 1
**Files likely touched:**
- `src/tools/google_calendar.py`
- `src/tools/__init__.py`
- `tests/test_google_calendar.py`
**Estimated scope:** Medium (3-4 files)

---

### Task 3: Gmail Yönetimi & Sesli Teyitli Abonelikten Çıkma (`GmailManagerTool` / `manage_gmail`)
**Description:** Gmail v1 API'si ile entegre `GmailManagerTool` sınıfını oluşturur; son 24 saatteki önemli/okunmamış mailleri 1-2 cümlede sesli özetler, `List-Unsubscribe` başlığına sahip bültenleri tespit eder ve sesli onay alındığında (`ConfirmationPolicy.REQUIRE_CONFIRMATION`) abonelikten çıkar.
**Acceptance criteria:**
- [x] `manage_gmail` aracı `summarize_inbox`, `list_newsletters`, `unsubscribe` eylemlerini destekler.
- [x] `summarize_inbox` okunmamış mailleri Piper TTS için net, kısa bir Türkçe özete dönüştürür.
- [x] `unsubscribe` eylemi teyitsiz çalıştırıldığında `needs_confirmation=True` ve sesli teyit sorusu üretir.
- [x] `create_default_tool_registry()` fabrikasına kaydedilir.
**Verification:**
- [x] `pytest tests/test_gmail.py -v` testleri başarıyla geçer.
**Dependencies:** Task 1
**Files likely touched:**
- `src/tools/gmail_manager.py`
- `src/tools/__init__.py`
- `tests/test_gmail.py`
**Estimated scope:** Medium (3-4 files)

---

### Task 4: Sabah Brifingi & Ajanda Birleştirici (`MorningBriefingTool` / `get_morning_briefing`)
**Description:** Kullanıcı *"Günaydın"* veya *"Bugün neyim var?"* dediğinde takvim randevularını, yaklaşan teslim tarihlerini ve acil gelen kutusu durumunu tek bir akıcı 2-3 cümlelik sesli brifinge dönüştüren `MorningBriefingTool` aracını oluşturur.
**Acceptance criteria:**
- [x] `get_morning_briefing` aracı bugünün takvimini, 3 günlük teslim tarihlerini ve önemli okunmamış e-postaları sorgulayıp birleştirir.
- [x] Çıktı doğrudan seslendirmeye uygun, kod/markdown içermeyen akıcı Türkçe ve tek bir *"efendim"* ile tamamlanır.
- [x] `create_default_tool_registry()` fabrikasına kaydedilir.
**Verification:**
- [x] `pytest tests/test_morning_briefing.py -v` testleri başarıyla geçer.
**Dependencies:** Tasks 1, 2, 3
**Files likely touched:**
- `src/tools/morning_briefing.py`
- `src/tools/__init__.py`
- `tests/test_morning_briefing.py`
**Estimated scope:** Small (3 files)

---

## Checkpoint: Phase 4 Secretary Complete & Full Regression
- [x] `pytest tests/test_google_auth.py tests/test_google_calendar.py tests/test_gmail.py tests/test_morning_briefing.py -v` testleri 100% geçer.
- [x] `pytest tests/ -v` ile tüm test süiti (131 test) sıfır regresyon ile yeşil tamamlanır.
- [x] Kullanıcı sesli olarak takvime etkinlik/deadline ekleyebilir, gelen kutusunu özetletebilir ve sabah brifingi alabilir.
