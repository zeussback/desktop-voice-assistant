# 🎙️ Desktop Voice Assistant (Masaüstü Sesli Asistan)

Windows üzerinde çalışan; bas-konuş/toggle kısayolu (`Ctrl + Space`) ile tetiklenen; ekranın üstünde modern ve animasyonlu **"glass-liquid" (buzlu/akışkan cam)** durum widget'ı beliren; Google Gemini ve yerel ses motorlarıyla güçlendirilmiş kişisel masaüstü yapay zeka asistanı.

---

## ✨ Özellikler (1. Aşama / MVP)

* **💎 Glass-Liquid UI Widget (PySide6):**
  * Ekranın üst-orta kısmında beliren şık, çerçevesiz ve yarı saydam buzlu cam kapsül.
  * *Dinleniyor* (Cyan dalga animasyonu), *Düşünülüyor* (Mor dönen parıltı), *Konuşuyor* (Zümrüt yeşili dalga) durum geçişleri.
  * Mikrofondaki ses şiddetine (RMS) göre dinamik tepki veren ses dalgaları.

* **⌨️ Global Toggle Kısayolu:**
  * Sistem genelinde `Ctrl + Space` tuşlarına bastığınızda asistan dinlemeye başlar.
  * Konuşmanız bittiğinde tekrar `Ctrl + Space` tuşuna basmanız yeterlidir.

* **🧠 Hibrit Zeka (Brain):**
  * **Birincil (Primary):** Google Gemini 2.0 / 1.5 Flash (Google AI Studio / Pro avantajıyla ultra hızlı, multimodal ve doğrudan Türkçe anlama).
  * **Yedek (Fallback / Offline):** Bilgisayarı kasmayan hafif yerel LLM desteği (Ollama üzerinden `qwen2.5:3b` veya `llama3.2:3b`).

* **🔊 Doğal Türkçe Ses Motoru (TTS):**
  * **Birincil (Yerel & Ultra Hızlı):** **Piper TTS** — Tamamen yerel, ~60 MB, **0.2 saniyede** anında konuşan doğal Türkçe model (`tr_TR-fahrettin-medium`).
  * **Yedek (Son Çare):** Microsoft Edge Neural TTS (`edge-tts` ile çevrimiçi yedek).

---

## 🚀 Hızlı Başlangıç

### 1. Kurulum ve Ortam Hazırlığı

Python 3.11 sanal ortamı ve gerekli kütüphaneler kurulmuştur:

```powershell
cd C:\dev\desktop-voice-assistant
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Yapay Zeka API Anahtarı (.env)

Proje kök dizinindeki `.env.example` dosyasını kopyalayarak `.env` oluşturun:

```powershell
Copy-Item .env.example .env
```

Ardından `.env` dosyasını açıp [Google AI Studio](https://aistudio.google.com/)'dan aldığınız ücretsiz API anahtarınızı girin:

```env
GEMINI_API_KEY=AIzaSy...Sizin_Gemini_API_Anahtariniz...
HOTKEY=ctrl+space
```

*(Not: Google AI Pro üyeliğiniz olduğu için Gemini API anahtarınızı aynı Google hesabınızla oluşturduğunuzda yüksek kotalardan ve en hızlı modellerden faydalanırsınız.)*

### 3. Asistanı Başlatma

```powershell
.\.venv\Scripts\python.exe -m src.main
```

Asistan açıldığında ekranın üstünde kısa bir süre *"CTRL+SPACE ile konuşmaya başlayın"* bildirimi belirecek ve hazır moda geçecektir.

---

## 🧪 Testleri Çalıştırma

Tüm modüller TDD (Test-Driven Development) döngüsüyle test kapsamına alınmıştır:

```powershell
.\.venv\Scripts\pytest.exe -v
```

---

## 🗺️ Proje Yol Haritası (Roadmap)

- [x] **1. Aşama (MVP):** Sesli İletişim Döngüsü + Glass-Liquid Durum Widget'ı + Hibrit Gemini/Ollama & Yerel Piper/EdgeTTS mimarisi + Jarvis Persona.
- [ ] **2. Aşama (İşletim Sistemi Kontrolü & Tool Engine):** Sesle bilgisayarda program açma/kapatma, ses ve medya kontrolleri, pencere yönetimi, web araması ve güvenli fonksiyon çağırma (Function Calling / Tool Use) altyapısı.
- [ ] **3. Aşama (Vision / Ekran Görme):** *"Ekranda ne görüyorsun?"* veya *"Buradaki hatayı açıkla"* dendiğinde anlık ekran görüntüsü alıp Gemini Multimodal ile analiz etme (Tool Engine üzerinden tetiklenir).
