import os
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models" / "piper"
BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium"
FILES = [
    "tr_TR-dfki-medium.onnx",
    "tr_TR-dfki-medium.onnx.json",
]


def download_with_progress(url: str, dest_path: Path):
    print(f"İndiriliyor: {dest_path.name}...")

    def _progress(count, block_size, total_size):
        if total_size > 0:
            percent = int(count * block_size * 100 / total_size)
            downloaded_mb = (count * block_size) / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\r  İlerleme: {percent}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)")
            sys.stdout.flush()

    urllib.request.urlretrieve(url, str(dest_path), reporthook=_progress)
    print("\n  Tamamlandı.")


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print("=== Piper TTS Türkçe Ses Modeli İndirici (DFKI Medium - ~60MB) ===")
    print(f"Hedef Klasör: {MODEL_DIR}\n")

    for filename in FILES:
        dest_path = MODEL_DIR / filename
        if dest_path.exists() and dest_path.stat().st_size > 0:
            print(f"Zaten mevcut: {filename}")
            continue

        url = f"{BASE_URL}/{filename}"
        try:
            download_with_progress(url, dest_path)
        except Exception as e:
            print(f"\nHata oluştu ({filename}): {e}")
            sys.exit(1)

    print("\n✓ Piper Türkçe modeli başarıyla kuruldu!")
    print("Artık asistanınız 0.2 saniyede yerel olarak Türkçe konuşabilir.")


if __name__ == "__main__":
    main()
