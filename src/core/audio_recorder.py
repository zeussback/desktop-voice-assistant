import io
import logging
import threading
import wave
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Mikrofon sesini asenkron olarak kaydeden ve WAV tamponu üreten modül."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._is_recording = False
        self._frames: List[np.ndarray] = []
        self._stream = None
        self._lock = threading.Lock()
        self._current_rms: float = 0.0

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def get_current_rms(self) -> float:
        """Anlık ses genliğini (0.0 - 1.0 aralığında) döner."""
        return self._current_rms

    def _update_rms(self, indata: np.ndarray) -> None:
        """Gelen ses bloğunun RMS değerini hesaplar."""
        try:
            if indata.size > 0:
                data_float = indata.astype(np.float32)
                rms = np.sqrt(np.mean(data_float**2))
                # 16-bit PCM (max 32768) için normalize et
                self._current_rms = float(np.clip(rms / 32768.0, 0.0, 1.0))
        except Exception:
            self._current_rms = 0.0

    def _audio_callback(self, indata, frames, time_info, status):
        """sounddevice akış geri çağrım fonksiyonu."""
        if status:
            logger.debug(f"Ses akış durumu: {status}")
        with self._lock:
            if self._is_recording:
                self._frames.append(indata.copy())
                self._update_rms(indata)

    def start_recording(self) -> bool:
        """Kayıt akışını başlatır."""
        with self._lock:
            if self._is_recording:
                return True
            self._frames.clear()
            self._current_rms = 0.0
            self._is_recording = True

        try:
            import sounddevice as sd

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info("Mikrofon kaydı başlatıldı.")
            return True
        except Exception as e:
            logger.error(f"Mikrofon başlatılamadı: {e}")
            self._is_recording = False
            return False

    def stop_recording(self) -> bytes:
        """Kayıt akışını durdurur ve WAV formatında bayt dizisi döndürür."""
        with self._lock:
            self._is_recording = False
            self._current_rms = 0.0

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Ses akışı kapatılırken hata: {e}")
            finally:
                self._stream = None

        logger.info("Mikrofon kaydı tamamlandı.")
        return self._export_wav_bytes()

    def _export_wav_bytes(self) -> bytes:
        """Tampondaki veriyi WAV bayt dizisine çevirir."""
        with self._lock:
            if not self._frames:
                return b""
            audio_data = np.concatenate(self._frames, axis=0)

        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        return wav_io.getvalue()
