# Spec: Phase 4 — Kişisel Asistan & Sekreterlik (Google Calendar, Deadlines, Gmail & Morning Briefing)

## Objective
Jarvis masaüstü sesli asistanına; kullanıcının sesli komutlarıyla Google Calendar ve Gmail hesaplarına (resmi Google OAuth 2.0 protokolü ile) bağlanabilmesini, takvim randevularını ve teslim tarihlerini (*deadlines*) yönetebilmesini, gelen e-postalarını özetleyebilmesini, gereksiz reklam/bülten aboneliklerini sesli teyit ile temizleyebilmesini ve sabahları güne başlarken tek bir sesli komutla (*"Günaydın"*, *"Bugün neyim var?"*) günün ajandasını ve acil işlerini sunan **Kişisel Sekreterlik Motorunu** kazandırmak.

---

## Tech Stack
- **Language / Runtime:** Python 3.11+
- **Google Workspace API İstemcileri:**
  - `google-api-python-client>=2.100.0` (Resmi Google Calendar v3 ve Gmail v1 REST API istemcisi)
  - `google-auth-oauthlib>=1.2.0` (Yerel tarayıcı üzerinden OAuth 2.0 PKCE / Authorization Code akışı)
  - `google-auth-httplib2>=0.2.0` (Kimlik doğrulama taşıma katmanı)
- **Tarih & Zaman Ayrıştırma:**
  - `python-dateutil>=2.8.2` (ISO 8601, RFC 3339 ve bağıl zamanlar — "bugün", "yarın", "3 gün sonra")
- **Araç Motoru (Tool Engine):**
  - Mevcut `BaseTool`, `ToolRegistry`, `ToolResult`, `ConfirmationPolicy` (`src/tools/`)
- **Ses & Konuşma:**
  - Piper TTS (`tr_TR-dfki-medium.onnx` / `tr_TR-fahrettin-medium`) - 1-3 cümlelik akıcı sekreterlik çıktısı
- **Test Çatısı:**
  - `pytest`, `unittest.mock` (Google API servislerinin tamamen mock'lanması sayesinde testler internet bağlantısına ihtiyaç duymadan milisaniyeler içinde çalışır)

---

## Commands
- **Bağımlılıkları Yükleme:**
  ```powershell
  .\.venv\Scripts\pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 python-dateutil
  ```
- **Aşama 4 Testlerini Çalıştırma:**
  ```powershell
  .\.venv\Scripts\pytest tests/test_google_calendar.py tests/test_gmail.py tests/test_morning_briefing.py -v
  ```
- **Tüm Testleri Koşma (Regresyon Kontrolü):**
  ```powershell
  .\.venv\Scripts\pytest tests/ -v
  ```
- **Asistanı Başlatma:**
  ```powershell
  .\.venv\Scripts\python -m src.main
  ```

---

## Project Structure
```
desktop-voice-assistant/
├── credentials.json               # Kullanıcının Google Cloud'dan indireceği kimlik dosyası (.gitignore'da)
├── token.json                     # İlk başarılı giriş sonrası oluşturulan yerel yetki anahtarı (.gitignore'da)
├── docs/
│   └── intent/
│       ├── desktop-voice-assistant.md
│       ├── phase2-os-control.md
│       ├── phase3-vision.md
│       └── phase4-secretary.md      # Onaylanan Intent dokümanı
├── src/
│   ├── tools/
│   │   ├── __init__.py              # Yeni araçların kayıt fabrikasına eklenmesi
│   │   ├── base.py                  # BaseTool, ConfirmationPolicy, ToolResult
│   │   ├── google_auth.py           # GoogleAuthManager (OAuth 2.0 akışı, token.json yönetimi)
│   │   ├── google_calendar.py       # GoogleCalendarTool (etkinlik & deadline ekleme/sorgulama)
│   │   ├── gmail_manager.py         # GmailManagerTool (özetleme, bülten tespiti, teyitli abonelikten çıkma)
│   │   ├── morning_briefing.py      # MorningBriefingTool (sabah karşılama ve ajanda birleştirici)
│   │   └── ...                      # Mevcut işletim sistemi ve vision araçları
│   ├── config.py                    # GOOGLE_CREDENTIALS_PATH ve GOOGLE_TOKEN_PATH ayarları
│   └── ...
├── tests/
│   ├── test_google_auth.py          # Token yenileme, eksik dosya ve yetki mock testleri
│   ├── test_google_calendar.py      # Takvim listeleme, etkinlik ekleme ve son tarih testleri
│   ├── test_gmail.py                # Gelen kutusu özetleme ve teyitli abonelikten çıkma testleri
│   └── test_morning_briefing.py     # Sabah brifingi derleme testleri
├── SPEC.md                          # 1. Aşama spesifikasyonu
├── SPEC-PHASE2.md                   # 2. Aşama spesifikasyonu
├── SPEC-PHASE3.md                   # 3. Aşama spesifikasyonu
├── SPEC-PHASE4.md                   # Bu teknik şartname
└── README.md
```

---

## Code Style & Architecture

### 1. Kimlik Doğrulama Katmanı (`GoogleAuthManager`)
`src/tools/google_auth.py` içinde yer alır. Calendar ve Gmail araçları bu yöneticiden servis nesnelerini talep eder:
- İstenen İzin Kapsamları (Scopes):
  - `https://www.googleapis.com/auth/calendar` (Takvim etkinliklerini okuma/yazma)
  - `https://www.googleapis.com/auth/gmail.modify` (E-postaları okuma, etiketleme ve List-Unsubscribe başlıklarını işleme)
- `token.json` mevcut ve geçerliyse arka planda otomatik kullanılır. Süresi dolmuşsa `creds.refresh(Request())` ile yenilenir.
- `token.json` yoksa ama `credentials.json` varsa tarayıcıda tek seferlik onay ekranı açar (`flow.run_local_server(port=0)`).
- `credentials.json` henüz yerleştirilmemişse asistan çökmez; `"Google kimlik bilgileri (credentials.json) bulunamadı efendim. Lütfen dosyayı proje ana dizinine ekleyin."` şeklinde nazik sesli bilgi döner.

### 2. Google Calendar Aracı (`GoogleCalendarTool` / `manage_calendar`)
- **İsim:** `manage_calendar`
- **Eylemler (Actions):**
  - `list_events`: Belirli bir gün veya aralıktaki randevu ve toplantıları listeler.
  - `add_event`: Başlık, başlangıç zamanı, süre veya bitiş zamanı ile takvime yeni kayıt girer.
  - `list_deadlines`: Başlığında `[Son Tarih]` veya `[Teslim]` etiketi olan ya da kullanıcının *"yarına ne yetişmeli?"* dediği teslim tarihlerini filtreler.
  - `add_deadline`: Belirtilen tarihe ve saate özel `[Son Tarih]` etiketiyle takvim kaydı oluşturur.
- **Teyit Politikası:** Okuma ve ekleme için `ConfirmationPolicy.IMMEDIATE`.

### 3. Gmail Yönetim Aracı (`GmailManagerTool` / `manage_gmail`)
- **İsim:** `manage_gmail`
- **Eylemler (Actions):**
  - `summarize_inbox`: Son 24 saat içinde gelen okunmamış veya önemli e-postaları alır. Konu, gönderen ve gövde özetini Piper TTS için 1-2 akıcı cümleye döker.
  - `list_newsletters`: Gelen kutusunda `List-Unsubscribe` başlığı (RFC 2369) taşıyan bülten ve reklam maillerini tespit eder.
  - `unsubscribe`: İlgili bültenin abonelikten çıkma bağlantısını veya `mailto:` adresini işler.
- **Teyit Politikası:** 
  - `summarize_inbox` ve `list_newsletters` için `ConfirmationPolicy.IMMEDIATE`.
  - `unsubscribe` için **`ConfirmationPolicy.REQUIRE_CONFIRMATION`** zorunludur (*"Efendim, X bülteninden aboneliğinizi sonlandırıyorum, onaylıyor musunuz?"*).

### 4. Sabah Brifingi Aracı (`MorningBriefingTool` / `get_morning_briefing`)
- **İsim:** `get_morning_briefing`
- **İşleyiş:** 
  Kullanıcı *"Günaydın Jarvis"* veya *"Bugün neyim var?"* dediğinde:
  1. Bugünün takvim randevularını çeker.
  2. Yarın ve sonraki 3 gün içindeki acil teslim tarihlerini (*deadlines*) çeker.
  3. Gelen kutusundaki okunmamış önemli e-posta sayısını ve gönderenleri derler.
  4. Hepsini doğal, akıcı ve Piper TTS'e uygun **2-3 cümlelik** bir sabah brifingi haline getirir (örn: *"Günaydın efendim. Bugün saat 14'te proje toplantınız var, ayrıca yarına yetişmesi gereken makale tesliminiz bulunuyor. Gelen kutunuzda 2 yeni önemli e-posta var efendim."*).

---

## Testing Strategy
- **Framework:** `pytest`, `unittest.mock`
- **Test Dosyaları:**
  1. `tests/test_google_auth.py`:
     - `credentials.json` eksikken zarif hata mesajı dönmesi.
     - `token.json` geçerli olduğunda kimlik doğrulanması.
     - Süresi dolmuş token'ın otomatik yenilenmesi (refresh).
  2. `tests/test_google_calendar.py`:
     - Etkinlik ekleme ve JSON istek gövdesinin RFC 3339 uyumluluğu.
     - *"Bugün neyim var?"* sorgusunda bugünün saat sınırlarının (00:00 - 23:59) doğru filtrelenmesi.
     - `[Son Tarih]` etiketli etkinliklerin teslim tarihi sorgularında doğru yakalanması.
  3. `tests/test_gmail.py`:
     - Okunmamış e-postaların özet formatı.
     - `List-Unsubscribe` başlığının (mailto / http url) doğru ayıklanması.
     - `unsubscribe` eyleminin `needs_confirmation=True` bayrağı üretmesi ve onay gelmeden çalışmaması.
  4. `tests/test_morning_briefing.py`:
     - Takvim, deadline ve mail verilerinin tek bir sesli metinde kusursuz birleştirilmesi.
     - Tek *"efendim"* kuralının korunması.
  5. **Regresyon Kontrolü:**
     - Mevcut 104 testin tamamının yeşil kalması (toplam ~120+ test).

---

## Boundaries
- **Always do:**
  - `credentials.json` ve `token.json` dosyalarını `.gitignore` içinde tut (asla depoya yükleme).
  - Abonelikten çıkma eyleminde sesli güvenlik onayı (`ConfirmationPolicy.REQUIRE_CONFIRMATION`) zorunlu kıl.
  - Yanıtları Piper TTS için markdown/liste işaretlerinden arındırılmış düz cümleler olarak biçimlendir.
  - Tüm testleri Google API mock'ları ile offline koşulabilir yap.
- **Ask first:**
  - Kullanıcı adına e-posta silme (çöp kutusuna taşıma harici kalıcı silme) veya takvim silme.
  - Kullanıcının doğrudan talimatı olmadan e-posta gönderme (draft / send).
- **Never do:**
  - Kullanıcı Google şifresini veya kimlik anahtarını log dosyalarına yazmak.
  - `credentials.json` yokken uygulamanın çökmesine (unhandled exception) izin vermek.

---

## Success Criteria
- [ ] `tests/test_google_auth.py`, `tests/test_google_calendar.py`, `tests/test_gmail.py`, `tests/test_morning_briefing.py` testleri 100% geçer.
- [ ] Toplam test sayısı en az 120+ olur ve 0 hata ile tamamlanır.
- [ ] Kullanıcı *"Yarın saat 14'e toplantı ekle"* dediğinde `manage_calendar` aracı çalışır.
- [ ] Kullanıcı *"Bugün yapmam gerekenler neler?"* veya *"Günaydın"* dediğinde bugünün randevuları ve teslim tarihleri seslendirilir.
- [ ] `requirements.txt` dosyasına Google API paketleri eklenir.

---

## Assumptions & Open Questions
### Varsayımlarımız (Assumptions):
1. **Google Takvimi Birincil Depodur:** Teslim tarihleri (*deadlines*), harici bir veritabanı veya karmaşık ayrı bir todo sistemi kurmaya gerek kalmadan; Google Calendar üzerinde `[Son Tarih]` etiketiyle saklanacak ve böylece kullanıcının telefonundaki Google Calendar uygulamasında da otomatik olarak görünecektir.
2. **Kimlik Kurulumu:** Kullanıcı `credentials.json` dosyasını Google Cloud Console üzerinden bir kereye mahsus proje klasörüne koyacaktır; asistan ilk çalışmada tarayıcıda yetki alıp `token.json` oluşturacaktır.

### Açık Sorular (Open Questions):
1. Teslim tarihlerinin (*deadlines*) telefonunuzdaki Google Calendar takviminizde de anında görünebilmesi için takvim etkinlikleri olarak `[Son Tarih] Tez Teslimi` şeklinde işaretlenmesi yaklaşımını uygun buluyor musunuz?
2. Şartnamede değiştirmek veya eklemek istediğiniz başka bir sekreterlik özelliği var mı?
