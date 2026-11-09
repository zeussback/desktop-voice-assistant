"""Live end-to-end verification script for Jarvis Phase 3 Vision & Tool Engine."""

import sys
import os
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import settings
from src.tools.screen_inspection import capture_screen_bytes, ScreenInspectionTool
from src.tools import create_default_tool_registry
from src.brain.gemini_provider import GeminiProvider

def run_live_verification():
    print("=" * 60)
    print("🚀 JARVIS PHASE 3 CANLI DOĞRULAMA (LIVE VERIFICATION)")
    print("=" * 60)

    # 1. Test: Ekran Yakalama (Pillow ImageGrab)
    print("\n[1/4] Canlı Ekran Görüntüsü Yakalama Test Ediliyor...")
    t0 = time.time()
    try:
        image_bytes = capture_screen_bytes()
        t_capture = (time.time() - t0) * 1000
        print(f"  ✅ Ekran başarıyla yakalandı!")
        print(f"  ⏱️ Süre: {t_capture:.1f} ms")
        print(f"  📦 Boyut: {len(image_bytes) / 1024:.1f} KB (RAM bellekte JPEG)")
        assert image_bytes.startswith(b"\xff\xd8"), "JPEG SOI marker bulunamadı!"
    except Exception as e:
        print(f"  ❌ Ekran yakalama hatası: {e}")
        return False

    # 2. Test: ScreenInspectionTool Doğrudan Çağrı (Gemini Multimodal Vision)
    print("\n[2/4] ScreenInspectionTool ile Canlı Gemini Multimodal Çağrısı...")
    t0 = time.time()
    try:
        tool = ScreenInspectionTool(api_key=settings.GEMINI_API_KEY)
        query = "Ekranda şu an hangi pencere veya metinler görünüyor?"
        result = tool.execute(query=query)
        t_tool = time.time() - t0
        print(f"  ✅ Tool Sonucu: success={result.success}")
        print(f"  ⏱️ API Yanıt Süresi: {t_tool:.2f} saniye")
        print(f"  🗣️ Jarvis Spoken Text:\n    \"{result.message}\"")
        if not result.success:
            print(f"  ❌ Hata detayı: {result.data}")
            return False
    except Exception as e:
        print(f"  ❌ ScreenInspectionTool hatası: {e}")
        return False

    # 3. Test: GeminiProvider Uçtan Uca Doğal Dil Tool Use ("Ekranda ne görüyorsun?")
    print("\n[3/4] GeminiProvider Otonom Tool Calling Test Ediliyor...")
    t0 = time.time()
    try:
        registry = create_default_tool_registry()
        provider = GeminiProvider(api_key=settings.GEMINI_API_KEY, tool_registry=registry)
        user_prompt = "Jarvis, ekranda ne görüyorsun?"
        print(f"  👤 Kullanıcı Sorusu: \"{user_prompt}\"")
        resp = provider.generate_response(user_prompt)
        t_provider = time.time() - t0
        print(f"  🤖 Çağrılan Araç (Tool): {resp.tool_called}")
        print(f"  ⏱️ Toplam Uçtan Uca Süre: {t_provider:.2f} saniye")
        print(f"  🗣️ Jarvis Yanıtı:\n    \"{resp.text}\"")
        assert "inspect_screen" in resp.tool_called, f"inspect_screen çağrılmadı! ({resp.tool_called})"
    except Exception as e:
        print(f"  ❌ GeminiProvider otonom araç çağırma hatası: {e}")
        return False

    # 4. Test: Piper TTS ile Ses Sentezleme (Ses Motoru Uyum Doğrulaması)
    print("\n[4/4] Üretilen Metnin Piper TTS ile Seslendirilebilirliği Test Ediliyor...")
    try:
        from src.voice.piper_client import PiperTTSClient
        from src.voice.edge_tts_client import EdgeTTSClient
        from src.voice.hybrid_tts import HybridTTS

        piper_tts = PiperTTSClient(
            model_path=settings.PIPER_MODEL_PATH,
            length_scale=settings.PIPER_LENGTH_SCALE,
            pitch_factor=settings.PIPER_PITCH_FACTOR,
        )
        edge_tts = EdgeTTSClient(voice=settings.FALLBACK_TTS_VOICE)
        tts = HybridTTS(providers=[piper_tts, edge_tts])

        sample_text = resp.text
        wav_data = tts.synthesize(sample_text)
        print(f"  ✅ Ses sentezleme başarılı!")
        print(f"  📦 Üretilen WAV Bayt: {len(wav_data) if wav_data else 0} bytes")
    except Exception as e:
        print(f"  ❌ TTS sentezleme hatası: {e}")
        return False

    print("\n" + "=" * 60)
    print("🎉 TÜM CANLI TESTLER BAŞARIYLA TAMAMLANDI! (ALL CHECKS PASSED)")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_live_verification()
    sys.exit(0 if success else 1)
