# Implementation Plan: Phase 2 — OS Control & Tool Engine

## Overview
Jarvis kişisel asistanına sesli komutlarla Windows işletim sistemini yönetme kabiliyeti kazandıracak modüler bir **Araç Motoru (Tool Engine / Function Calling)** entegrasyonu. Google Gemini modeli sesli komutları algılayarak uygun araçları (`SystemAudioTool`, `SystemBrightnessTool`, `MediaControlTool`, `AppControlTool`, `WebBrowserTool`, `SystemPowerTool`) tetikleyecek, Jarvis eylemi gerçekleştirip doğal Türkçe geri bildirim dönecektir.

## Architecture Decisions
- **Modüler Araç Mimarisi (`BaseTool` & `ToolRegistry`):** Her yetenek bağımsız bir sınıf olarak tanımlanır. Gemini Function Calling JSON şemaları `BaseTool` üzerinden otomatik üretilir. Aşama 3'teki Vision (*inspect_screen*) yeteneği de bu motora tek bir araç olarak takılabilecektir.
- **Hafif ve Sıfır Maliyetli Kütüphaneler:**
  - Ses kontrolü için `pycaw` (Windows Core Audio API, pure Python/ctypes).
  - Ekran parlaklığı için `screen_brightness_control`.
  - Süreç ve uygulama yönetimi için `psutil` ve yerel Windows komutları.
  - Medya tuşları için harici paket yüklemeden doğrudan `ctypes.windll.user32.keybd_event` (VK_MEDIA_PLAY_PAUSE vb.).
- **Çift Kademeli Güvenlik ve Teyit:**
  - *Immediate:* Normal eylemler (ses ayarı, uygulama açma/kapama, web arama) kullanıcıya sormadan anında icra edilir ve kısa sesli teyit verilir (*"Spotify açıldı efendim"*).
  - *Require Confirmation:* Kritik eylemler (sistemi kapatma/yeniden başlatma) öncesi asistan `AWAITING_CONFIRMATION` durumuna geçerek sesli onay ister; bir sonraki konuşmada onay gelirse çalıştırır.
- **Asenkron UI Güvenliği:** Tüm araç çalıştırma ve Windows API işlemleri arka plan QThread / Worker havuzunda yürütülür; PySide6 widget'ı hiçbir zaman donmaz.

## Task List Summary

### Phase 2: OS Control & Tool Engine
- **Task 1: Tool Engine Core (`BaseTool`, `ToolResult`, `ToolRegistry`)** (Foundation)
- **Task 2: System Audio & Media Control Tools** (Core Tool)
- **Task 3: Display Brightness & Web Browser Tools** (Core Tool)
- **Task 4: Application Control & Power Management Tools** (Core Tool)
- **Task 5: Gemini Provider Tool Calling Loop & Function Execution** (Brain Integration)
- **Task 6: Assistant Controller Confirmation State Machine & End-to-End Orchestration** (Orchestration & Verification)

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Bazı harici monitörlerin WMI/DDC-CI parlaklık kontrolünü desteklememesi | Düşük | `screen_brightness_control` hata verdiğinde zarifçe yakalayıp kullanıcıya ekranın donanımsal parlaklık ayarına izin vermediğini sesli bildirme |
| Uygulama adlarının farklı yollar altında olması (AppData vs Program Files) | Orta | Windows Başlat Menüsü (.lnk) kısayollarını, App Paths kayıt defterini ve yaygın sistem dizinlerini tarayan toleranslı arama mekanizması kurma |
| Gemini API'nin bazen tool çağırmak yerine salt metin yanıt vermesi | Orta | `SYSTEM_PROMPT` içine net tool yönlendirmeleri ekleme ve fallback metin işleme |
| Kritik sistem komutunda kullanıcının teyidi yanlışlıkla tetiklemesi | Yüksek | Kesin teyit kelimeleri ("evet", "kapat", "onaylıyorum") haricinde işlemi otomatik iptal etme |

## Verification Checkpoints
1. **Checkpoint 1 (Foundation):** `ToolRegistry` ve şema üretim birim testleri hatasız geçer (`pytest tests/test_tools.py`).
2. **Checkpoint 2 (OS Tools):** Tüm sistem araçları (`pycaw`, `psutil`, `media`, `brightness`, `browser`) mock'larla ve yerel çağrılarla test edilir (`pytest tests/test_os_control.py`).
3. **Checkpoint 3 (Brain & Confirmation):** Gemini tool calling döngüsü ve sesli onay durum makinesi test edilir (`pytest tests/test_assistant_tools.py`).
4. **Final Checkpoint:** Tüm 34 mevcut test + yeni araç testleri (toplam ~50+ test) yeşil olarak tamamlanır ve canlı sesli deneme yapılır.
