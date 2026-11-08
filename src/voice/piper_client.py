import io
import logging
import os
import subprocess
import wave
from pathlib import Path
from typing import Optional

from src.voice.tts_base import BaseTTSClient

logger = logging.getLogger(__name__)


class PiperTTSClient(BaseTTSClient):
    """Piper TTS yerel ve ultra hızlı (~0.2s) ses sentezi istemcisi."""

    def __init__(
        self,
        model_path: str = "models/piper/tr_TR-dfki-medium.onnx",
        length_scale: float = 0.85,
        pitch_factor: float = 1.05,
    ):
        self.raw_model_path = model_path
        self.model_path = self._resolve_model_path(model_path)
        self.length_scale = length_scale
        self.pitch_factor = pitch_factor
        self._voice = None

    @staticmethod
    def _resolve_model_path(path_str: str) -> str:
        """Model yolunu çözer; relative ise proje kök dizini ile eşleştirir."""
        p = Path(path_str)
        if p.is_file():
            return str(p.resolve())
        # Proje kökünü bularak dene
        project_root = Path(__file__).resolve().parent.parent.parent
        resolved = project_root / path_str
        if resolved.is_file():
            return str(resolved)
        return str(p)

    def is_available(self) -> bool:
        """Model dosyasının mevcut olup olmadığını denetler."""
        if not os.path.isfile(self.model_path):
            self.model_path = self._resolve_model_path(self.raw_model_path)
        return os.path.isfile(self.model_path)

    def _get_piper_voice(self):
        """Python piper kütüphanesini dinamik olarak yükler."""
        if self._voice is None:
            try:
                from piper import PiperVoice

                self._voice = PiperVoice.load(self.model_path)
                logger.info(f"Piper modeli başarıyla yüklendi: {self.model_path}")
            except Exception as e:
                logger.warning(f"Piper python modülü yüklenemedi: {e}")
        return self._voice

    def _synthesize_raw(self, text: str) -> bytes:
        """Metni sese dönüştürür ve WAV baytlarını döner."""
        voice = self._get_piper_voice()
        if voice is not None:
            try:
                from piper.voice import SynthesisConfig

                base_sample_rate = getattr(voice.config, "sample_rate", 22050)
                # Hız ve artikülasyon ayarı
                syn_config = SynthesisConfig(length_scale=self.length_scale)
                chunks = list(voice.synthesize(text, syn_config=syn_config))
                pcm_data = b"".join(chunk.audio_int16_bytes for chunk in chunks)

                # Perde / Tını frekansı (daha canlı ve net ses için)
                target_sample_rate = int(base_sample_rate * self.pitch_factor)

                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(target_sample_rate)
                    wf.writeframes(pcm_data)
                return wav_io.getvalue()
            except Exception as e:
                logger.warning(f"Piper doğrudan sentezde hata verdi: {e}. Subprocess deneniyor.")

        # Yedek yöntem: Piper CLI / Subprocess
        try:
            cmd = ["piper", "--model", self.model_path, "--output-raw"]
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            raw_pcm, err = proc.communicate(input=text.encode("utf-8"))
            if proc.returncode != 0:
                raise RuntimeError(f"Piper CLI hatası: {err.decode('utf-8')}")

            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(22050)
                wf.writeframes(raw_pcm)
            return wav_io.getvalue()

        except Exception as e:
            raise RuntimeError(f"Piper ses sentezinde hata: {e}")

    def synthesize(self, text: str) -> bytes:
        if not self.is_available():
            raise RuntimeError(f"Piper model dosyası bulunamadı: {self.model_path}")
        return self._synthesize_raw(text)
