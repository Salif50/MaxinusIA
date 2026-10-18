from __future__ import annotations

import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}


_last_percent = -1


def progress(blocks: int, block_size: int, total: int):
    global _last_percent
    done = blocks * block_size
    pct = min(100, int(done * 100 / total)) if total > 0 else 0
    if pct != _last_percent and (pct % 5 == 0 or pct == 100):
        print(f"\r  {pct:3d}%  {done / 1_048_576:.1f} Mo", end="", flush=True)
        _last_percent = pct


def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        global _last_percent
        _last_percent = -1
        target = MODELS / name
        if target.exists() and target.stat().st_size > 1_000_000:
            print(f"✓ {name} déjà présent")
            continue
        partial = target.with_suffix(target.suffix + ".part")
        print(f"Téléchargement de {name}")
        try:
            urllib.request.urlretrieve(url, partial, progress)
            print()
            partial.replace(target)
        except Exception:
            partial.unlink(missing_ok=True)
            raise

    print("Préchargement de Whisper (peut prendre quelques minutes)…")
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download

    whisper_target = MODELS / "faster-whisper-small"
    if not whisper_target.exists():
        snapshot_download("Systran/faster-whisper-small", local_dir=whisper_target)
    WhisperModel(str(whisper_target), device="cpu", compute_type="int8")
    print("✓ Tous les modèles vocaux sont disponibles hors ligne.")


if __name__ == "__main__":
    main()
