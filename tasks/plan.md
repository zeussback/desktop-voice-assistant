# Implementation Plan: Phase 3 — Vision (Ekran Görme & İnceleme)

## Overview
Jarvis sesli kişisel asistanına, kullanıcının sesli talebiyle bilgisayar ekranını görüp analiz edebilmesini sağlayan **Ekran İnceleme Aracı (`ScreenInspectionTool` / `inspect_screen`)** kazandırmak. Kullanıcı *"Ekranda ne görüyorsun?"*, *"Buradaki hatayı açıkla"*, *"Şu tablodaki toplam nedir?"* dediğinde; Gemini modeli Araç Motoru üzerinden `inspect_screen` fonksiyonunu çağıracak, ekran görüntüsü tamamen RAM bellekte yakalanıp Gemini Multimodal Vision API'sine iletilecek ve Jarvis 1-3 cümlelik özlü, sesli bir yanıt dönecektir.

## Architecture Decisions
- **Modüler Araç Mimarisi ile Kusursuz Uyum (`BaseTool` & `ToolRegistry`):**
  Ekran inceleme yeteneği, Aşama 2'de inşa ettiğimiz `BaseTool` sınıfından türetilen `ScreenInspectionTool` olarak sisteme dahil edilir. Bu sayede hem tek başına hem de birleşik komutlarda (örn: *"Müziği durdur ve ekrandaki hataya bak"*) paralel fonksiyon çağırma mekanizmasıyla doğal şekilde çalışır.
- **Gizlilik & Sıfır Disk I/O (RAM Prensibi):**
  Ekran görüntüleri kesinlikle yerel diske (`.jpg`, `.png`) yazılmaz. `Pillow` (`PIL.ImageGrab`) ile birincil ekrandan doğrudan yakalanıp bellek içi tamponda (`io.BytesIO`) JPEG olarak tutulur ve API çağrısı sonrası bellekten serbest bırakılır.
- **Hafiflik ve Hızlı Yanıt (1080p Ölçekleme):**
  2K veya 4K ekranlarda gereksiz token ve bant genişliği tüketimini önlemek, yanıt süresini minimumda tutmak için yakalanan görüntü en-boy oranı korunarak maksimum 1920x1080 çözünürlüğe ölçeklendirilir.
- **Jarvis & Piper TTS Uyumlu Ses Formatı:**
  Gemini Vision istemine (prompt) net talimat verilerek yanıtın markdown, kod bloku veya madde imi içermemesi; doğrudan seslendirmeye uygun, net ve en fazla 1-3 cümle olması ve tek bir *"efendim"* ile bitmesi sağlanır.
- **Yedek Model Havuzu (Fallback Resiliency):**
  Gemini Vision çağrısı, `GeminiProvider`'ın 9 modelli fallback havuzu (`gemini-3.5-flash`, `gemini-2.5-flash`, `gemini-flash-latest` vb.) üzerinden çalışır; kota (429) veya sunucu yoğunluğunda anında diğer modele geçilir.

---

## Task List Summary

### Phase 3: Vision
- **Task 1: Pillow Bağımlılığı & Bellek İçi Ekran Yakalama Motoru (`_capture_screen_bytes`)**
- **Task 2: Screen Inspection Tool (`ScreenInspectionTool`) & Tool Registry Entegrasyonu**
- **Task 3: Gemini Multimodal Vision Entegrasyonu & Hata/Fallback Dayanıklılığı**
- **Checkpoint: Uçtan Uca Vision Doğrulaması & Sıfır Regresyon (Tüm Testler Yeşil)**

---

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Ekran kilitliyken veya kullanıcı oturumu kapalıyken `ImageGrab.grab()` çağrısının hata vermesi | Düşük | `ScreenInspectionTool` içinde istisnayı yakalayıp kullanıcıya *"Ekran görüntüsü alınamadı efendim"* şeklinde zarif sesli bilgi dönme |
| 4K ekranlarda yüksek çözünürlüğün API süresini uzatması | Orta | `img.thumbnail((1920, 1080))` ile RAM içinde anında ölçeklendirme ve JPEG %85 optimize sıkıştırma |
| Modelin kod veya markdown blokları üretip Piper TTS'in garip sesler çıkarması | Orta | Vision sistem talimatında seslendirilebilir düz Türkçe metin üretmeyi kesin kural olarak belirtme |
| Gemini API geçici kota veya 429 hatası | Orta | Mevcut 9 modelli fallback listesiyle otomatik yedek modele geçiş |

---

## Verification Checkpoints
1. **Checkpoint 1 (Capture):** Bellek içi ekran yakalama fonksiyonu diske dokunmadan geçerli JPEG baytları ve ölçeklenmiş boyut üretir (`tests/test_vision.py`).
2. **Checkpoint 2 (Tool & Registry):** `inspect_screen` aracı `ToolRegistry`'ye kaydedilir, Gemini FunctionDeclaration şeması üretir ve mock Gemini yanıtıyla başarılı `ToolResult` döner.
3. **Final Checkpoint (Regression):** Mevcut 90 test + yeni vision testleri (toplam 96+ test) hatasız geçer (`pytest tests/ -v`).
