# Spec: Phase 2 — OS Control & Tool Engine

## Objective
Jarvis masaüstü sesli asistanına, kullanıcının sesli komutlarıyla Windows işletim sistemini kontrol etmesini sağlayan modüler bir **Araç Motoru (Tool Engine / Function Calling)** kazandırmak. 

Kullanıcı *"Spotify'ı aç"*, *"Sesi %40 yap"*, *"Ekran parlaklığını artır"*, *"Müziği durdur"*, *"Chrome'u kapat"* veya *"Google'da Python yeniliklerini ara"* dediğinde; Google Gemini modeli isteği bir fonksiyon çağrısına (`function_call`) dönüştürecek, Jarvis ilgili yerel aracı güvenle çalıştıracak ve kullanıcıya Jarvis kimliğine uygun olarak (*"efendim"*) kısa ve doğal bir sesli teyit dönecektir. Bilgisayarı kapatma veya yeniden başlatma gibi kritik işlemlerde ise kullanıcıdan sesli onay istenecektir.

Bu araç motoru, 3. Aşamada eklenecek olan Ekran Görme (*Vision / inspect_screen*) ve ilerideki karmaşık otomasyon görevlerine de temel teşkil edecek şekilde genişletilebilir olacaktır.

---

## Tech Stack
- **Language / Runtime:** Python 3.11+
- **LLM Tool Engine:** `google-genai` (Gemini 2.5 / 1.5 Flash Function Calling / Tool Calling API)
- **Windows Ses Kontrolü:** `pycaw` (Windows Core Audio API wrapper, ses seviyesi okuma/yazma ve sessize alma)
- **Ekran Parlaklığı:** `screen_brightness_control` (Windows WMI/VCP monitör parlaklık kontrolü)
- **Uygulama & Süreç Yönetimi:** `psutil` (çalışan süreçleri bulma, düzgün kapatma veya sonlandırma) + `subprocess` & `os.startfile` (uygulamaları başlatma)
- **Medya Tuşları Kontrolü:** `ctypes.windll.user32.keybd_event` (Oynat/Duraklat, Sonraki Parça, Önceki Parça sanal tuşları — sıfır harici bağımlılık)
- **Tarayıcı & Web Arama:** Python yerleşik `webbrowser` & `urllib.parse`
- **Veri Doğrulama:** Pydantic v2
- **Test Çatısı:** `pytest`, `pytest-mock`

---

## Commands
- **Bağımlılıkları Yükleme:**
  ```powershell
  .\.venv\Scripts\pip install pycaw screen_brightness_control psutil
  ```
- **Testleri Çalıştırma:**
  ```powershell
  .\.venv\Scripts\pytest tests/test_tools.py tests/test_os_control.py tests/test_assistant_tools.py -v
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
├── docs/
│   └── intent/
│       ├── desktop-voice-assistant.md
│       └── phase2-os-control.md
├── src/
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseTool, ToolResult, ToolParameter, ConfirmationPolicy
│   │   ├── registry.py             # ToolRegistry (araç kayıt, şema üretimi, çalıştırma)
│   │   ├── system_audio.py         # SystemAudioTool (ses düzeyi ayarla, artır/azalt, sustur)
│   │   ├── system_brightness.py    # SystemBrightnessTool (parlaklık ayarla, artır/azalt)
│   │   ├── media_control.py        # MediaControlTool (oynat/duraklat, sonraki/önceki)
│   │   ├── app_control.py          # AppControlTool (uygulama aç, uygulama kapat)
│   │   ├── web_browser.py          # WebBrowserTool (URL aç, Google'da ara)
│   │   └── system_power.py         # SystemPowerTool (bilgisayarı kapat, yeniden başlat, uyku - teyitli)
│   ├── brain/
│   │   ├── provider_base.py        # BaseBrainProvider (tools desteğiyle güncellenir)
│   │   ├── gemini_provider.py      # Gemini Tool/FunctionDeclaration entegrasyonu
│   │   └── ...
│   ├── core/
│   │   ├── assistant.py            # ToolRegistry ve sesli teyit (confirmation) durum makinesi
│   │   └── ...
│   ├── config.py                   # Özel uygulama takma adları (app aliases) konfigürasyonu
│   └── ...
├── tests/
│   ├── test_tools.py               # ToolRegistry ve şema üretim testleri
│   ├── test_os_control.py          # Ses, parlaklık, medya ve uygulama araçları birim testleri
│   └── test_assistant_tools.py     # AssistantController uçtan uca araç çalıştırma ve teyit testleri
├── SPEC.md                         # 1. Aşama spesifikasyonu
├── SPEC-PHASE2.md                  # Bu doküman (2. Aşama teknik şartnamesi)
└── README.md
```

---

## Code Style & Architecture

### 1. Araç Soyutlaması (`BaseTool`)
Tüm araçlar `BaseTool` sınıfından türetilir. Gemini'a gönderilecek fonksiyon şeması (`types.FunctionDeclaration`) bu sınıftan otomatik üretilir:

```python
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ConfirmationPolicy(str, Enum):
    IMMEDIATE = "immediate"               # Onay gerektirmeden anında çalıştır
    REQUIRE_CONFIRMATION = "confirmation"  # Çalıştırmadan önce kullanıcıdan sesli onay iste

class ToolResult(BaseModel):
    success: bool
    message: str                          # Jarvis'in kullanıcıya söyleyeceği veya özetleyeceği yanıt
    data: Optional[Dict[str, Any]] = None
    needs_confirmation: bool = False
    confirmation_prompt: Optional[str] = None

class BaseTool:
    name: str
    description: str
    confirmation_policy: ConfirmationPolicy = ConfirmationPolicy.IMMEDIATE

    def get_declaration(self) -> Dict[str, Any]:
        """Gemini FunctionDeclaration için JSON Schema döndürür."""
        raise NotImplementedError

    def execute(self, **kwargs) -> ToolResult:
        """Aracı çalıştırır ve sonucu döndürür."""
        raise NotImplementedError
```

### 2. Araç Motoru (`ToolRegistry`)
Araçların kaydedildiği, Gemini FunctionDeclaration nesnelerine dönüştürüldüğü ve isimle çağrıldığı merkezi motor:

```python
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_declarations(self) -> list:
        return [tool.get_declaration() for tool in self._tools.values()]

    def execute(self, name: str, args: Dict[str, Any]) -> ToolResult:
        if name not in self._tools:
            return ToolResult(success=False, message=f"'{name}' adında bir araç bulunamadı efendim.")
        return self._tools[name].execute(**args)
```

### 3. Örnek Sistem Aracı (`SystemAudioTool`)
```python
class SystemAudioTool(BaseTool):
    name = "control_system_audio"
    description = "Bilgisayarın ana ses düzeyini ayarlar, artırır/azaltır veya sesi açıp kapatır (mute/unmute)."

    def execute(self, action: str, level: Optional[int] = None) -> ToolResult:
        # pycaw ile ses seviyesi yönetimi (0-100)
        ...
        return ToolResult(success=True, message=f"Ses düzeyi %{level} olarak ayarlandı efendim.")
```

---

## Testing Strategy
- **Birim Testleri (`pytest`):**
  - Tüm araçların argüman doğrulama (örneğin ses için `0 <= level <= 100`) kontrolleri.
  - `pycaw`, `screen_brightness_control` ve `psutil` çağrılarının mock'lanarak donanım bağımsız test edilmesi.
  - Uygulama açma/kapama senaryolarında bulunamayan uygulamalara karşı dönen zarif hata mesajlarının testi.
- **Entegrasyon Testleri:**
  - `GeminiProvider`'ın `function_call` içeren yanıtları parse etmesi ve `ToolRegistry` ile yürütmesi.
  - `AssistantController`'ın `ConfirmationPolicy.REQUIRE_CONFIRMATION` durumunda kullanıcıya teyit sorusu yöneltip bir sonraki yanıtta onay verildiğinde işlemi icra etmesi.
- **Regresyon:**
  - 1. Aşamada oluşturulan 34 adet birim testin kırılmadan yeşil kalması.

---

## Boundaries
- **Always do:**
  - Tüm araç çalıştırmalarını ve donanım işlemlerini arka plan thread'inde yürüt, UI döngüsünü asla bloke etme.
  - Hata oluştuğunda (uygulama bulunamadı, yetki yetersiz, monitör desteklemiyor) çökmek yerine kullanıcıya anlaşılır Türkçe açıklama dön (*"Efendim, Spotify uygulamasını bilgisayarınızda bulamadım"*).
  - Sistem kapatma/yeniden başlatma gibi geri dönüşsüz eylemlerde mutlak surette teyit al.
  - Ses seviyesini 0 ile 100 arasında sınırla.
- **Ask first:**
  - Ağır veya ek C-derlemeli harici paketler eklemeden önce onay al.
  - Kullanıcı onay politikalarını değiştirirken danış.
- **Never do:**
  - Kullanıcı teyidi olmadan `shutdown` veya `restart` komutunu doğrudan çalıştırma.
  - Güvenlik kontrolü olmadan harici shell betiği (`cmd.exe /c` veya keyfi PowerShell) çalıştırma.
  - Birincil Gemini API anahtarını kod içine gömme (`config.py` ve `.env` kullan).

---

## Success Criteria
1. **Araç Kayıt ve Şema Entegrasyonu:** `ToolRegistry` tüm sistem araçlarını (`audio`, `brightness`, `media`, `app`, `web`, `power`) tek noktada toplar ve Gemini API'ye standart FunctionDeclaration formatında sunar.
2. **Ses ve Medya Yönetimi:**
   - *"Sesi yüzde 30 yap"* -> Ses seviyesi %30 olur, sesli teyit verilir.
   - *"Sesi kapat"* -> Master mute aktifleşir.
   - *"Müziği durdur / devam ettir"* -> Medya oynat/duraklat tuş olayı tetiklenir.
3. **Ekran Parlaklığı:**
   - *"Parlaklığı %70 yap"* -> Monitör parlaklığı %70 olur.
4. **Uygulama & Web Kontrolü:**
   - *"Spotify'ı aç"* veya *"Chrome'u aç"* -> Uygulama başlatılır.
   - *"Chrome'u kapat"* -> Süreç düzgünce sonlandırılır.
   - *"YouTube'u aç"* -> Varsayılan tarayıcıda `https://www.youtube.com` açılır.
   - *"Google'da yapay zeka haberlerini ara"* -> Tarayıcıda arama sonuçları açılır.
5. **Güvenli Teyit Döngüsü:**
   - *"Bilgisayarı kapat"* -> Asistan *"Bilgisayarı kapatmak istediğinizden emin misiniz efendim?"* der; kullanıcı *"Evet"* derse eylem gerçekleşir.

---

## Open Questions
1. **Uygulama Kısayolları (App Aliases):** Kullanıcının özel olarak tanımlamak isteyebileceği özel takma adlar (örneğin *"kod"* -> *"code.exe"*, *"stüdyo"* -> *"FL64.exe"*) için `config.py` ve `.env` üzerinden basit bir JSON/sözlük yapılandırması sunulmalı mı? (Varsayılan olarak popüler uygulamalar ve Windows Başlat Menüsü dizinleri otomatik taranacaktır).
