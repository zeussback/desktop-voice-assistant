"""Screen Inspection and Multimodal Vision Tool for Jarvis."""

import io
import logging
import re
from typing import Any, Callable, Dict, List, Optional
from PIL import Image, ImageGrab

from src.config import settings
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult

logger = logging.getLogger(__name__)


def _capture_with_qscreen(max_width: int = 1920, max_height: int = 1080, quality: int = 85) -> bytes:
    """PySide6 QScreen ile ekran görüntüsü yakalar (Windows DWM / Qt yerel köprüsü)."""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtCore import QBuffer, QIODevice, Qt

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    screen = QGuiApplication.primaryScreen()
    if not screen:
        raise RuntimeError("Birincil ekran aygıtı bulunamadı.")

    pixmap = screen.grabWindow(0)
    if pixmap.isNull() or pixmap.width() == 0:
        raise RuntimeError("Ekran görüntüsü yakalanamadı (boş pixmap).")

    if pixmap.width() > max_width or pixmap.height() > max_height:
        pixmap = pixmap.scaled(
            max_width,
            max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not pixmap.save(buffer, "JPEG", quality=quality):
        raise RuntimeError("Ekran görüntüsü JPEG formatına dönüştürülemedi.")

    return bytes(buffer.data())


def capture_screen_bytes(max_width: int = 1920, max_height: int = 1080, quality: int = 85) -> bytes:
    """Birincil ekran görüntüsünü yakalar, gerekiyorsa ölçeklendirir ve RAM içinde JPEG baytları olarak döner.
    
    Önce Pillow ImageGrab'i dener; Windows oturum sınırlamalarında PySide6 QScreen yedeğine geçer.
    Hiçbir dosya diske yazılmaz; tamamen bellek içi (io.BytesIO / QBuffer) çalışır.
    """
    try:
        img = ImageGrab.grab(all_screens=False)
        # En-boy oranını koruyarak maksimum boyutlara sığacak şekilde ölçekle
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # JPEG için RGB moduna dönüştür
        if img.mode != "RGB":
            img = img.convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()
    except Exception as pil_err:
        logger.debug(f"Pillow ekran yakalama başarısız ({pil_err}), PySide6 yerel ekran yakalaması deneniyor...")
        return _capture_with_qscreen(max_width=max_width, max_height=max_height, quality=quality)


def clean_vision_text_for_tts(text: str) -> str:
    """Piper TTS için metni temizler: markdown sembollerini kaldırır ve tek 'efendim.' ile bitirir."""
    if not text:
        return "Ekranda belirgin bir içerik göremedim efendim."

    # Markdown formatlama işaretlerini temizle
    cleaned = re.sub(r'[*_#`~]', '', text)
    # Madde işaretlerini ve liste numaralarını temizle (örn: "* ", "- ", "1. ")
    cleaned = re.sub(r'^\s*[-*•]\s+', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)

    # Cümle içerisindeki tüm 'efendim' kelimelerini temizle
    cleaned = re.sub(r'\befendim\b', '', cleaned, flags=re.IGNORECASE)

    # Fazla boşlukları ve satır sonlarını tek boşluğa indir
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = cleaned.strip(" .,;!?")

    if not cleaned:
        return "Ekranda belirgin bir içerik göremedim efendim."

    return f"{cleaned} efendim."


class ScreenInspectionTool(BaseTool):
    """Kullanıcının bilgisayar ekranını yakalayıp Gemini Multimodal Vision ile analiz eden araç."""

    name = "inspect_screen"
    description = (
        "Kullanıcı bilgisayar ekranında ne olduğunu sorduğunda, ekrandaki bir hatayı, "
        "kodu, metni, tabloyu, resmi, videoyu, açık pencereyi veya uygulamaları incelemesini "
        "istediğinde bu aracı çağır. 'Ekranda ne var?', 'Buradaki hataya bak', "
        "'Ekranda ne görüyorsun?' gibi sorular için zorunludur."
    )
    confirmation_policy = ConfirmationPolicy.IMMEDIATE

    FALLBACK_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[Any] = None,
        model: str = "gemini-3.5-flash",
        fallback_models: Optional[List[str]] = None,
        timeout_ms: int = 15000,
        capture_fn: Optional[Callable[[], bytes]] = None,
    ):
        self.api_key = api_key
        self._client = client
        self.model = model
        self.fallback_models = fallback_models or list(self.FALLBACK_MODELS)
        self.timeout_ms = timeout_ms
        self._capture_fn = capture_fn or capture_screen_bytes

    def get_declaration(self) -> Dict[str, Any]:
        """Gemini Tool calling için JSON fonksiyon bildirim şemasını döner."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "Kullanıcının ekranla ilgili sorduğu spesifik soru veya odaklanılması istenen konu.",
                    }
                },
                "required": [],
            },
        }

    def _get_client(self):
        if self._client is not None:
            return self._client

        effective_key = self.api_key or settings.GEMINI_API_KEY
        if not effective_key:
            return None

        from google import genai
        from google.genai import types

        self._client = genai.Client(
            api_key=effective_key,
            http_options=types.HttpOptions(timeout=self.timeout_ms),
        )
        return self._client

    def execute(self, query: str = "Ekranda ne olduğunu genel olarak açıkla.") -> ToolResult:
        """Ekranı yakalar ve Gemini Vision modeli ile analiz eder."""
        try:
            image_bytes = self._capture_fn()
        except Exception as e:
            logger.error(f"Ekran görüntüsü yakalama hatası: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message="Ekran görüntüsü alınamadı efendim.",
                data={"error": str(e)},
            )

        client = self._get_client()
        if client is None:
            return ToolResult(
                success=False,
                message="Gemini API anahtarı tanımlanmadığı için ekran analiz edilemedi efendim.",
            )

        from google.genai import types

        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            f"Kullanıcı sorusu: {query}",
        ]

        config = types.GenerateContentConfig(
            system_instruction=(
                "Sen Jarvis adında akıllı ve saygılı bir masaüstü kişisel asistansın. "
                "Kullanıcının bilgisayar ekranının anlık görüntüsünü görüyorsun. "
                "Kullanıcının sorusuna veya odaklanmak istediği konuya doğrudan odaklanarak yanıt ver.\n"
                "YANIT KURALLARI:\n"
                "1. Yanıtın Piper TTS ses motoru ile seslendirilecektir. Bu nedenle ASLA markdown sembolleri "
                "(*, #, `), liste numaraları, madde işaretleri veya kod blokları kullanma.\n"
                "2. Yanıtın en fazla 1-3 cümle uzunluğunda, doğrudan seslendirilebilir, doğal ve akıcı Türkçe olsun.\n"
                "3. Yanıtını tek bir 'efendim' kelimesi ile bitir."
            ),
            temperature=0.2,
        )

        models_to_try = [self.model]
        for m in self.fallback_models:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        for candidate_model in models_to_try:
            try:
                logger.info(f"Gemini Vision modeli deneniyor: {candidate_model}")
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=contents,
                    config=config,
                )
                raw_text = getattr(response, "text", "") or ""
                speech_text = clean_vision_text_for_tts(raw_text)
                return ToolResult(
                    success=True,
                    message=speech_text,
                    data={"query": query, "model": candidate_model, "image_size_bytes": len(image_bytes)},
                )
            except Exception as e:
                err_str = str(e).lower()
                last_error = e
                is_transient = any(
                    code in err_str
                    for code in [
                        "503", "504", "429", "timeout", "deadline", "unavailable",
                        "high demand", "temporary", "overloaded", "resource has been exhausted"
                    ]
                )
                if is_transient:
                    logger.warning(
                        f"Vision modeli ({candidate_model}) yanıt vermedi ({e}). Sonraki modele geçiliyor..."
                    )
                    continue
                else:
                    logger.error(f"Vision API çağrısı sırasında hata ({candidate_model}): {e}")
                    return ToolResult(
                        success=False,
                        message="Ekran analiz edilirken bir bağlantı hatası oluştu efendim.",
                        data={"error": str(e)},
                    )

        logger.error(f"Tüm Gemini Vision modelleri tükendi: {last_error}")
        return ToolResult(
            success=False,
            message="Ekran analiz edilirken bir bağlantı hatası oluştu efendim.",
            data={"error": str(last_error)},
        )
