# Implementation Plan: Phase 4 — Kişisel Asistan & Sekreterlik (Google Calendar, Deadlines, Gmail & Morning Briefing)

## Overview
Jarvis kişisel asistanına sesli sekreterlik yetenekleri kazandırmak: Resmi Google OAuth 2.0 protokolü ile Google Calendar ve Gmail API'lerine bağlanarak takvim randevuları oluşturma, son teslim tarihlerini (*deadlines*) takip etme, gelen e-postaları sesli özetleme, reklam/bülten aboneliklerini sesli teyit ile sonlandırma ve sabahları *"Günaydın"* dendiğinde günün tüm ajandasını tek bir sesli brifing olarak sunma.

## Architecture Decisions
- **Modüler Araç Motoru Uyumu (`BaseTool` & `ToolRegistry`):**
  Aşama 2 ve 3'te kurduğumuz `BaseTool` altyapısı üzerine üç yeni bağımsız araç inşa edilir:
  1. `GoogleCalendarTool` (`manage_calendar`): Takvim ve teslim tarihi yönetimi.
  2. `GmailManagerTool` (`manage_gmail`): Gelen kutusu özetleme ve teyitli abonelikten çıkma.
  3. `MorningBriefingTool` (`get_morning_briefing`): Takvim, teslim tarihleri ve e-posta verilerini sabahları birleştiren üst sekreterlik aracı.
- **Merkezi OAuth 2.0 Kimlik Yöneticisi (`GoogleAuthManager`):**
  Calendar ve Gmail araçları kimlik doğrulama mantığını kopyalamaz; `src/tools/google_auth.py` içindeki merkezi yöneticiden servis nesneleri (`build('calendar', 'v3')`, `build('gmail', 'v1')`) talep eder.
  `token.json` yerel olarak saklanır ve süresi dolduğunda otomatik yenilenir (`refresh token`). Kimlik dosyaları (`credentials.json`, `token.json`) `.gitignore` ile depodan kesinlikle hariç tutulur.
- **Teslim Tarihleri (Deadlines) Mimarisi:**
  Ayrı bir veritabanı veya harici todo sistemi gereksinimi olmadan, teslim tarihleri Google Takvim üzerinde `[Son Tarih]` etiketiyle saklanır. Bu sayede hem Jarvis sesli olarak takip edebilir, hem de kullanıcının telefonundaki Google Takvim uygulamasında anında görünür.
- **Güvenlik Teyidi Prensibi:**
  E-posta aboneliklerinden çıkma (`unsubscribe`) işlemi geri döndürülemez bir dış eylem olduğu için `ConfirmationPolicy.REQUIRE_CONFIRMATION` ile işaretlenir; Jarvis kullanıcıdan sesli onay (*"Evet / Onaylıyorum"*) almadan işlemi yürütmez.
- **Piper TTS ve Efendim Kuralı:**
  Tüm yanıtlar kod, markdown veya madde işareti içermeyen, doğrudan seslendirmeye uygun akıcı 1-3 cümle ve tek bir *"efendim"* ile sınırlandırılır.

---

## Task List Summary

### Phase 4: Kişisel Asistan & Sekreterlik
- **Task 1: Google API Bağımlılıkları, Güvenlik Yapılandırması & Kimlik Doğrulama Katmanı (`GoogleAuthManager`)**
- **Task 2: Google Calendar & Teslim Tarihi Yönetimi (`GoogleCalendarTool` / `manage_calendar`)**
- **Task 3: Gmail Yönetimi & Sesli Teyitli Abonelikten Çıkma (`GmailManagerTool` / `manage_gmail`)**
- **Task 4: Sabah Brifingi & Ajanda Birleştirici (`MorningBriefingTool` / `get_morning_briefing`)**
- **Checkpoint: Kişisel Sekreterlik Tamamlanma & Tam Regresyon Doğrulaması (~120+ Test Yeşil)**

---

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| `credentials.json` dosyasının kullanıcı tarafından henüz eklenmemiş olması | Düşük | `GoogleAuthManager` eksikliği tespit ettiğinde çökmez, sesli olarak kullanıcıya dosyanın nereye konması gerektiğini söyler |
| Yerel `token.json` yetkisinin süresinin dolması | Orta | Her API çağrısı öncesi `creds.expired` kontrol edilip `creds.refresh(Request())` ile otomatik yenilenir |
| Farklı e-postalardaki List-Unsubscribe başlık formatlarının çeşitliliği (mailto vs http) | Orta | RFC 2369 standartlarına uygun regex ile hem `mailto:` hem de `https://` bağlantılarını güvenle ayrıştırma |
| Doğal dil tarih ifadelerinin ("yarın saat 3", "3 gün sonra") takvim saatine dönüştürülmesi | Orta | `python-dateutil` ve Gemini'ın fonksiyon parametresi olarak standart ISO formatı üretmesi |

---

## Verification Checkpoints
1. **Checkpoint 1 (Auth):** `test_google_auth.py` ile eksik dosya durumu, geçerli token ve yenileme akışı mock'larla doğrulanır.
2. **Checkpoint 2 (Calendar & Deadlines):** `test_google_calendar.py` ile randevu ekleme, bugünün etkinlikleri ve deadline sorguları doğrulanır.
3. **Checkpoint 3 (Gmail & Safety):** `test_gmail.py` ile gelen kutusu özetleme ve abonelikten çıkma teyit mekanizması doğrulanır.
4. **Final Checkpoint (Full Regression):** Tüm test süiti (`pytest tests/ -v`) 120+ testle hatasız geçer.
