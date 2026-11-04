import io
import wave
import numpy as np
import pytest

from src.core.audio_recorder import AudioRecorder


def test_audio_recorder_init():
    """AudioRecorder başlatma ve varsayılan parametrelerini test eder."""
    recorder = AudioRecorder(sample_rate=16000, channels=1)
    assert recorder.sample_rate == 16000
    assert recorder.channels == 1
    assert not recorder.is_recording


def test_audio_recorder_buffer_to_wav():
    """Tampona eklenen ses verisinin geçerli bir WAV bayt dizisine dönüştüğünü test eder."""
    recorder = AudioRecorder(sample_rate=16000, channels=1)

    # Simüle edilmiş 1 saniyelik sessiz/sinüs dalga verisi
    fake_data = np.zeros((16000, 1), dtype=np.int16)
    recorder._frames.append(fake_data)

    wav_bytes = recorder._export_wav_bytes()
    assert len(wav_bytes) > 44  # WAV başlığından büyük olmalı

    # WAV başlığını doğrula
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2  # 16-bit
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 16000


def test_audio_recorder_rms_calculation():
    """RMS (ses şiddeti) hesaplamasını test eder."""
    recorder = AudioRecorder()
    assert recorder.get_current_rms() == 0.0

    # Yüksek genlikli ses verisi
    loud_data = np.full((1000, 1), 10000, dtype=np.int16)
    recorder._update_rms(loud_data)
    assert recorder.get_current_rms() > 0.1
