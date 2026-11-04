# Spec: Desktop Voice Assistant (Phase 1: Voice Loop & Liquid Glass Widget)

## Objective
Windows işletim sisteminde çalışan, bas-konuş kısayoluyla tetiklenen, ekranın üst kısmında animasyonlu "glass-liquid" (buzlu cam / akışkan) tarzında modern bir durum göstergesi sunan kişisel yapay zeka sesli asistanı. 
Sıfır maliyet ve yüksek akıcılık için birincil olarak ücretsiz Google Gemini API'sini kullanır; kota aşımı veya çevrimdışı senaryolar için bilgisayarı yormayan yerel Ollama (Qwen/Llama) desteği sunar. Ses çıkışı için yerel VoiceStudio motorunu (OmniVoice/Kokoro) hedefler ve yedek olarak edge-tts barındırır.

## Tech Stack
- **Language / Runtime:** Python 3.11+
- **Desktop UI & Animations:** `PySide6` (Qt for Python) — Çerçevesiz, şeffaf, her zaman üstte (Always-on-top), Windows DWM blur / acrylic ve QPropertyAnimation destekli akışkan widget
- **Global Hotkey:** `pynput` / `keyboard` (Toggle modu: `Ctrl + Space` veya `Alt + Space` ile bir basışta dinleme başlar, tekrar basışta sonlanır)
- **Audio Capture & Playback:** `sounddevice`, `numpy`, `wave`, `pygame` / `soundfile`
- **Speech-to-Text (STT) & Brain:**
  - *Primary:* Google Gemini API (`google-genai` / `google-generativeai`) — Kullanıcının Google AI Pro avantajıyla doğrudan Türkçe ses/metin multimodal desteği (yüksek kotalar, ultra düşük gecikme)
  - *Fallback / Local LLM:* `ollama` Python client (yerel `qwen2.5:3b` veya `llama3.2:3b`) + hafif yerel STT (`faster-whisper` base/tiny)
- **Text-to-Speech (TTS):**
  - *Primary:* `VoiceStudio API` (`http://localhost:3900`) — Doğal, insansı yerel ses
  - *Fallback:* `edge-tts` (VoiceStudio kapalıysa veya çalışmıyorsa otomatik devreye girer)
- **Configuration & Storage:** `pydantic-settings`, `.env`, JSON/YAML

## Commands
- **Environment Setup:**
  ```bash
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- **Run Assistant:**
  ```bash
  python -m src.main
  ```
- **Run Tests:**
  ```bash
  pytest tests/ -v
  ```
- **Lint / Format:**
  ```bash
  black src/ tests/
  flake8 src/ tests/
  ```

## Project Structure
```
desktop-voice-assistant/
├── docs/
│   └── intent/
│       └── desktop-voice-assistant.md
├── src/
│   ├── __init__.py
│   ├── main.py                     # Uygulama giriş noktası ve yaşam döngüsü
│   ├── config.py                   # Ayarlar, tuş kısayolları, API anahtarları
│   ├── core/
│   │   ├── __init__.py
│   │   ├── assistant.py            # Ana durum makinesi (Idle -> Listening -> Thinking -> Speaking)
│   │   ├── hotkey_listener.py      # Bas-konuş küresel kısayol yakalayıcı
│   │   └── audio_recorder.py       # Mikrofon ses yakalama ve tampon yönetimi
│   ├── brain/
│   │   ├── __init__.py
│   │   ├── provider_base.py        # LLM servis arayüzü (BaseProvider)
│   │   ├── gemini_provider.py      # Google Gemini API entegrasyonu (Primary)
│   │   └── ollama_provider.py      # Ollama yerel model entegrasyonu (Fallback)
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── tts_base.py             # TTS servis arayüzü
│   │   ├── voicestudio_client.py   # VoiceStudio API (localhost:3900) entegrasyonu
│   │   ├── edge_tts_client.py      # Yedek TTS motoru
│   │   └── audio_player.py         # Asenkron ses çalma kuyruğu
│   └── ui/
│       ├── __init__.py
│       ├── widget.py               # Glass-liquid PySide6 widget penceresi
│       ├── styles.py               # QSS / CSS glassmorphism, gradient ve blur stilleri
│       └── animations.py           # Pulse, slide-down, glow animasyon kontrolcüleri
├── tests/
│   ├── test_brain.py
│   ├── test_voice.py
│   └── test_hotkey.py
├── .env.example
├── requirements.txt
├── README.md
└── SPEC.md
```

## Code Style & Architecture
- **Modüler Durum Makinesi:** UI, Ses ve Yapay Zeka servisleri birbirinden tamamen bağımsızdır; `AssistantController` olay tabanlı (Signal/Slot veya async event) haberleşir. UI asla ağır bir işlem yaparken donmaz (Non-blocking worker threads).
- **Tip Güvenliği:** Python Type Hinting (`str`, `Optional`, `dict`) ve Pydantic modelleri.
- **Örnek Kod:**
  ```python
  from enum import Enum
  from typing import Optional
  from pydantic import BaseModel

  class AssistantState(str, Enum):
      IDLE = "idle"
      LISTENING = "listening"
      THINKING = "thinking"
      SPEAKING = "speaking"
      ERROR = "error"

  class AIResponse(BaseModel):
      text: str
      audio_path: Optional[str] = None
      provider: str
  ```

## Testing Strategy
- **Unit Tests:** `pytest` ile provider adaptörlerinin (Gemini, Ollama, VoiceStudio) mock isteklerle doğru payload üretip üretmediğinin testi.
- **Audio Loopback Test:** Mikrofon kaydı ve hoparlör oynatımının donanım seviyesinde takılmadığını doğrulayan izolasyon testleri.
- **UI Render Test:** PySide6 widget'ının çerçevesiz ve şeffaf olarak oluşturulabildiğinin ve durum geçişlerinde doğru sinyallerin tetiklendiğinin testi.

## Boundaries
- **Always do:**
  - Tüm ses ve ağ işlemlerini arka plan thread'lerinde (QThread / Worker) çalıştır, ana UI thread'ini asla bloke etme.
  - Harici servisler (Gemini, VoiceStudio) çevrimdışı veya hatalı olduğunda zarif bir şekilde çökmek yerine kullanıcıya durumu (hata ikonu veya yedek motorla) bildir.
  - Bas-konuş tuşunun serbest bırakılmasını anında algılayıp dinlemeyi kes.
- **Ask first:**
  - Yeni bir harici kütüphane veya sistem servisi eklemeden önce onay al.
  - Varsayılan kısayol tuşu veya widget pozisyonu gibi kullanıcı deneyimini doğrudan etkileyen değişiklikleri doğrula.
- **Never do:**
  - API anahtarlarını kod içerisine hard-code etme (`.env` kullan).
  - Kullanıcı konuşmayı bitirmeden veya izin vermeden arka planda sürekli mikrofonu açık tutma.
  - 1. Aşamada ekran görüntüsü alma veya sistem komutları çalıştırma kodu ekleme (kapsam dışı).

## Success Criteria (Phase 1 MVP)
1. **Glass-Liquid Widget:** Kısayol tuşuna basıldığında ekranın üst ortasında yarı saydam, buzlu cam efektli şık bir kapsül belirmeli; "Dinleniyor", "Düşünülüyor", "Konuşuyor" geçişlerini yumuşak animasyonlarla göstermelidir.
2. **Sesli İletişim Döngüsü:**
   - Kısayola basılı tutup Türkçe konuşulduğunda mikrofon temiz ses yakalamalı.
   - Tuş bırakıldığında Gemini API (veya yerel Ollama) yanıt üretmeli.
   - VoiceStudio API (veya yedek edge-tts) üzerinden akıcı ve doğal Türkçe ses olarak hoparlörden dinletilmeli.
3. **Sıfır Maliyet ve Düşük Tüketim:** Asistan arka planda boşta beklerken CPU kullanımı <%1 ve RAM kullanımı kabul edilebilir (<150MB) seviyede olmalı.

## Kararlaştırılan Tercihler (Decisions)
1. **Tetikleme Yöntemi:** Toggle modu (`Ctrl + Space` / `Alt + Space`). Bir kez basınca dinleme başlar ("Dinleniyor"), tekrar basınca dinleme durur ve yapay zeka işlemeye geçer ("Düşünülüyor").
2. **Yapay Zeka Hesabı:** Kullanıcının mevcut Google AI Pro üyeliği üzerinden Google AI Studio API anahtarı kullanılacak (yüksek kotalar ve Pro hız avantajı). Kurulum adımında kullanıcı ile birlikte `.env` dosyasına eklenecektir.
