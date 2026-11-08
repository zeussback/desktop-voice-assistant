# Spec: Phase 3 — Vision (Ekran Görme & İnceleme)

## Objective
Jarvis masaüstü sesli asistanına, kullanıcının sesli talebi doğrultusunda bilgisayar ekranını görüp analiz edebilmesini sağlayan **Ekran İnceleme Aracı (`ScreenInspectionTool` / `inspect_screen`)** kazandırmak.

Kullanıcı *"Ekranda ne görüyorsun?"*, *"Buradaki hatayı açıkla"*, *"Şu tablodaki toplam nedir?"* veya *"Ekrandaki açık olan pencereye bak"* dediğinde:
1. Google Gemini modeli kullanıcının isteğini anlayarak Araç Motoru (`ToolRegistry`) üzerindeki `inspect_screen` aracını çağıracaktır.
2. `ScreenInspectionTool`, kullanıcının birincil ekranının anlık görüntüsünü tamamen RAM bellekte (`io.BytesIO`) yakalayacak; asla diske dosya (`.jpg`, `.png`) olarak kaydetmeyecektir.
3. Yakalanan görüntü yüksek çözünürlüklü ise (2K, 4K vb.) ağ bant genişliğini, token maliyetini ve yanıt süresini minimumda tutmak için maksimum 1920x1080 boyutlarına orantılı olarak ölçeklendirilecek ve optimize edilmiş JPEG formatında Gemini Multimodal Vision API'sine aktarılacaktır.
4. Gemini Multimodal modeli kullanıcının odak sorusuna göre ekranı analiz edecek ve Piper TTS'in doğal seslendirmesine uygun, maddesiz ve akıcı **1-3 cümlelik** bir özet üretecektir.
5. Yanıt, Jarvis persona kurallarına uygun olarak (*"efendim"*) kullanıcıya seslendirilecektir.

---

## Tech Stack
- **Language / Runtime:** Python 3.11+
- **Screen Capture & Image Processing:** `Pillow` (`PIL.ImageGrab`, `PIL.Image`)
  - Windows yerel GDI `BitBlt` entegrasyonu sayesinde ~20-40 ms içinde ekran yakalama.
  - Bellek içi (`io.BytesIO`) JPEG sıkıştırma ve otomatik çözünürlük ölçekleme (`Image.thumbnail`).
  - Sıfır geçici dosya, sıfır disk I/O.
- **Multimodal LLM:** `google-genai` (Gemini 2.5 / 3.5 Flash Multimodal Vision API).
  - Mevcut 9 modelli fallback havuzu (`gemini-3.5-flash`, `gemini-2.5-flash`, `gemini-flash-latest` vb.) kota (429) veya sunucu yoğunluğunda kesintisiz çalışmayı garanti eder.
- **Tool Engine:** Mevcut `BaseTool` ve `ToolRegistry` altyapısı (`src/tools/base.py`, `src/tools/registry.py`).
- **TTS Engine:** Piper TTS (`tr_TR-fahrettin-medium`) - 1-3 cümlelik sesli çıktı.
- **Test Çatısı:** `pytest`, `pytest-mock`, `unittest.mock`.

---

## Commands
- **Bağımlılıkları Yükleme:**
  ```powershell
  .\.venv\Scripts\pip install Pillow
  ```
- **Vision Testlerini Çalıştırma:**
  ```powershell
  .\.venv\Scripts\pytest tests/test_vision.py -v
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
│       ├── phase2-os-control.md
│       └── phase3-vision.md         # Onaylanan Intent dokümanı
├── src/
│   ├── tools/
│   │   ├── __init__.py              # create_default_tool_registry() içine ScreenInspectionTool eklenir
│   │   ├── base.py                  # BaseTool, ToolResult, ToolParameter, ConfirmationPolicy
│   │   ├── registry.py              # ToolRegistry
│   │   ├── screen_inspection.py     # YENİ: ScreenInspectionTool (ekran yakalama + Gemini Vision analizi)
│   │   └── ...                      # Mevcut ses, parlaklık, medya, uygulama araçları
│   ├── brain/
│   │   ├── provider_base.py         # BaseBrainProvider
│   │   ├── gemini_provider.py       # GeminiProvider (multimodal ve fallback desteği)
│   │   └── ...
│   └── ...
├── tests/
│   ├── test_vision.py               # YENİ: ScreenInspectionTool birim ve entegrasyon testleri
│   ├── test_tools.py                # Araç motoru testleri
│   ├── test_os_control.py           # İşletim sistemi kontrol testleri
│   └── test_assistant_tools.py      # Asistan araç entegrasyon testleri
├── SPEC.md                          # 1. Aşama spesifikasyonu
├── SPEC-PHASE2.md                   # 2. Aşama spesifikasyonu
├── SPEC-PHASE3.md                   # Bu doküman (3. Aşama teknik şartnamesi)
└── README.md
```

---

## Code Style & Architecture

### 1. `ScreenInspectionTool` Sınıfı Tasarımı
Tüm araçlar gibi `BaseTool` sınıfından türetilir. Okuma amaçlı ve güvenli bir işlem olduğundan `ConfirmationPolicy.IMMEDIATE` kullanır:

```python
import io
import logging
from typing import Any, Dict, Optional
from PIL import Image, ImageGrab
from src.tools.base import BaseTool, ConfirmationPolicy, ToolParameter, ToolResult

logger = logging.getLogger(__name__)

class ScreenInspectionTool(BaseTool):
    """Kullanıcının bilgisayar ekranını yakalayıp Gemini Multimodal ile analiz eden araç."""

    def __init__(self, api_key: Optional[str] = None, vision_client: Optional[Any] = None):
        super().__init__(
            name="inspect_screen",
            description=(
                "Kullanıcı bilgisayar ekranında ne olduğunu sorduğunda, ekrandaki bir hatayı, "
                "kodu, metni, tabloyu, resmi, videoyu, açık pencereyi veya uygulamaları incelemesini "
                "istediğinde bu aracı çağır. 'Ekranda ne var?', 'Buradaki hataya bak', "
                "'Ekranda ne görüyorsun?' gibi sorular için zorunludur."
            ),
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Kullanıcının ekranla ilgili sorduğu spesifik soru veya odaklanılması istenen konu.",
                    required=False,
                    default="Ekranda ne olduğunu genel olarak açıkla.",
                )
            ],
            confirmation_policy=ConfirmationPolicy.IMMEDIATE,
        )
        self.api_key = api_key
        self._client = vision_client

    def _capture_screen_bytes(self, max_width: int = 1920, max_height: int = 1080) -> bytes:
        """Birincil ekranı yakalar, gerekiyorsa ölçeklendirir ve RAM içinde JPEG baytları olarak döner."""
        img = ImageGrab.grab(all_screens=False)
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # RGBA modundaysa JPEG için RGB'ye çevir
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        return buffer.getvalue()

    def execute(self, query: str = "Ekranda ne olduğunu genel olarak açıkla.") -> ToolResult:
        """Ekranı yakalar ve Gemini Vision modeli ile analiz eder."""
        try:
            image_bytes = self._capture_screen_bytes()
            analysis_text = self._analyze_with_gemini(image_bytes, query)
            return ToolResult(
                success=True,
                message=analysis_text,
                data={"query": query, "image_size_bytes": len(image_bytes)}
            )
        except Exception as e:
            logger.error(f"Ekran inceleme hatası: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message="Ekran görüntüsü alınamadı veya analiz edilemedi efendim.",
                data={"error": str(e)}
            )
```

### 2. Vision Prompt & Persona Kuralları
Gemini Vision modeline gönderilen sistem talimatı:
- Asistanın adı Jarvis'tir.
- Kullanıcının sorusuna (`query`) doğrudan ve net yanıt verir.
- Yanıt, **sesli olarak okunacağından** (Piper TTS) markdown işaretleri (`*`, `#`, bullet point), liste numaraları veya kod blokları içermemelidir.
- Yanıt uzunluğu **en fazla 1-3 cümle** olmalıdır.
- Cümle doğal bir dille ve mutlaka **tek bir "efendim"** ile bitmelidir (örn: *"Ekranda açık olan VS Code penceresinde bir sözdizimi hatası görünüyor efendim."*).

---

## Testing Strategy
- **Framework:** `pytest`, `unittest.mock`
- **Konum:** `tests/test_vision.py`
- **Kapsam & Senaryolar:**
  1. `test_screen_capture_bytes_in_memory`: Ekran görüntüsünün diske dokunmadan bellek içinde (`bytes`) JPEG formatında oluşturulduğunu ve boyut sınırlarına (örn: 1920x1080) uyduğunu doğrular.
  2. `test_screen_inspection_tool_declaration`: `inspect_screen` aracının `ToolRegistry`'ye başarıyla kaydedildiğini ve geçerli Gemini `FunctionDeclaration` ürettiğini doğrular.
  3. `test_screen_inspection_execute_success`: Mock Gemini Vision yanıtı ile aracın `ToolResult(success=True, message=...)` ürettiğini doğrular.
  4. `test_screen_inspection_execute_capture_failure`: Ekran yakalama başarısız olduğunda (örneğin kilitli ekran / yetki sorunu) asistanın çökmeyip nazik bir hata mesajı döndüğünü doğrular.
  5. `test_screen_inspection_execute_gemini_failure`: Gemini API hatasında graceful fallback ve hata mesajı döndüğünü doğrular.
  6. `test_gemini_provider_integration`: `GeminiProvider`'ın `inspect_screen` araç çağrısını başarıyla çalıştırıp yanıtı sesli metin olarak döndüğünü doğrular.
  7. **Regresyon:** Mevcut tüm 90 testin (`test_tools.py`, `test_os_control.py`, `test_assistant_tools.py`, vb.) bozulmadan yeşil kalması.

---

## Boundaries
- **Always do:**
  - Ekran görüntülerini sadece RAM bellekte (`io.BytesIO`) işle; diske ASLA kaydetme.
  - Büyük ekranlarda (2K/4K) performansı ve hızı korumak için görüntüyü 1920x1080 sınırına ölçeklendir.
  - Yanıtı TTS için 1-3 cümle ile sınırla ve tek bir "efendim" kuralını koru.
  - Her değişiklik sonrası `pytest tests/` ile regresyon kontrolü yap.
- **Ask first:**
  - Ekran görüntüsünü diske kaydetme veya kullanıcıya dosya olarak sunma talepleri.
  - Sürekli (live background stream) ekran kaydı veya video streaming özellikleri.
- **Never do:**
  - Kullanıcı ekrana dair bir şey sormadığı sürece arka planda habersiz ekran görüntüsü almak (On-Demand prensibini çiğnemek).
  - Ekran görüntüsü baytlarını log dosyalarına veya konsola dökmek (bellek ve güvenlik).
  - Başarısız testleri silmek veya devre dışı bırakmak.

---

## Success Criteria
- [ ] `tests/test_vision.py` içindeki tüm testler başarıyla geçer.
- [ ] Toplam test sayısı en az 96+ olur ve 0 hata ile çalışır.
- [ ] Kullanıcı *"Ekranda ne var?"* dediğinde `inspect_screen` aracı tetiklenir ve 1-3 cümlelik net sesli yanıt döner.
- [ ] Diskte hiçbir geçici ekran görüntüsü dosyası (`.png`, `.jpg`) oluşmaz.
- [ ] `requirements.txt` güncellenir (`Pillow`).

---

## Assumptions & Open Questions
### Varsayımlarımız (Assumptions):
1. **Birincil Monitör Odaklılığı:** Aşama 3 kapsamında varsayılan olarak birincil monitör (`all_screens=False`) yakalanacaktır. Kullanıcının birden fazla monitörü varsa birincil monitör veya odaklı pencere temel alınır.
2. **Pillow Tercihi:** `Pillow`, Windows GDI `BitBlt` entegrasyonu, bellek içi JPEG encode (`io.BytesIO`) ve en-boy oranını bozmadan küçültme (`thumbnail`) yeteneklerini ek bir C derleyicisine ihtiyaç duymadan sunduğu için seçilmiştir.
3. **1080p Ölçekleme Sınırı:** 2K/4K ekranlarda çözünürlüğü 1920x1080'e küçültmek, modelin ekrandaki kod, metin ve pencereleri okumasına engel olmazken; ağ aktarım süresini ve API yanıt gecikmesini yarı yarıya düşürür.

### Açık Sorular (Open Questions):
1. *Çoklu monitörünüz varsa:* Ekran yakalamada her zaman birincil monitörün (ana ekranın) yakalanması sizin için uygun mu, yoksa tüm monitörleri yan yana tek bir görüntüde birleştirmesini (panoramik) mi tercih edersiniz? (Tavsiyemiz: Hız ve okunabilirlik için ana ekran).
2. Spesifikasyonda değiştirmek veya eklemek istediğiniz başka bir detay var mı?
