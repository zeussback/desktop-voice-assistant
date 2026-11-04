# Implementation Plan: Desktop Voice Assistant (Phase 1 MVP)

## Overview
Windows üzerinde toggle kısayolu (`Ctrl + Space`) ile açılıp kapanan; ekranın üstünde modern "glass-liquid" (buzlu cam) tarzında animasyonlu bir widget barındıran; Google Gemini API (kullanıcının Google AI Pro hesabıyla) ve yedek hafif Ollama modeliyle zekasını sağlayan; yerel VoiceStudio (ve yedek edge-tts) ile doğal Türkçe konuşan masaüstü asistanının 1. aşama (MVP) uygulaması.

## Architecture Decisions
- **PySide6 UI Thread Güvenliği:** Arayüz (widget) ana thread'de çalışırken, mikrofon kaydı, LLM API çağrısı ve ses sentezi QThread / Worker havuzunda asenkron olarak çalışır; widget hiçbir zaman donmaz.
- **Modüler Brain Arayüzü:** `BaseBrainProvider` arayüzü sayesinde Gemini API birincil, Ollama yerel modeli ise kota aşımında veya çevrimdışı durumda ikincil (fallback) olarak sorunsuz devreye girer.
- **Akıllı TTS Seçimi:** `VoiceStudioClient` yerel `http://localhost:3900` adresini yoklar; eğer servis ayaktaysa ultra doğal OmniVoice/Kokoro modellerini kullanır, ayakta değilse `edge-tts` ile konuşmayı aksatmadan sürdürür.
- **Kısayol Toggle Modu:** `pynput` ile küresel kısayol (`Ctrl+Space`) dinlenir. İlk basış: `IDLE -> LISTENING`, ikinci basış: `LISTENING -> THINKING -> SPEAKING -> IDLE`.

## Task List Summary
- **Phase 1: Foundation & Brain** (Tasks 1-2)
- **Phase 2: Audio & Voice Engines** (Tasks 3-4)
- **Phase 3: Glass-Liquid Widget & Global Hotkey** (Tasks 5-6)
- **Phase 4: Integration & E2E Verification** (Tasks 7-8)

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| VoiceStudio sunucusunun henüz kurulu veya açık olmaması | Orta | Otomatik `edge-tts` fallback motoru ile ses kesintisini önleme |
| PySide6 şeffaf pencerede Windows DWM blur uyumsuzluğu | Düşük | DWM Acrylic API'si yanında şık CSS semi-transparent gradient alternatifi bulundurma |
| Küresel kısayolun başka bir uygulama tarafından yakalanması | Düşük | Kısayolu `.env` dosyasından kolayca değiştirilebilir (`Ctrl+Space`, `Alt+Space`, `F8`) kılma |
