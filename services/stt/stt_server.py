"""API de transcription OpenAI-compatible, locale et privée."""

from __future__ import annotations

import asyncio
import io
import hmac
import os
import tempfile
import threading
import wave
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from faster_whisper import WhisperModel
import numpy as np
from kokoro_onnx import Kokoro
from pydantic import BaseModel
from fastapi.responses import Response


app = FastAPI(title="Maxinus Local STT", docs_url=None, redoc_url=None)
_model: WhisperModel | None = None
_model_lock = threading.Lock()
_inference_lock = threading.Lock()
_kokoro: Kokoro | None = None
_kokoro_lock = threading.Lock()


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = WhisperModel(
                    os.getenv("WHISPER_MODEL", "base"),
                    device="cpu",
                    compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
                    download_root=os.getenv(
                        "WHISPER_MODEL_DIR", "/data/cache/whisper/models"
                    ),
                )
    return _model


def transcribe_file(path: str, language: str | None) -> str:
    with _inference_lock:
        segments, _ = get_model().transcribe(
            path,
            language=language or os.getenv("WHISPER_LANGUAGE", "fr"),
            beam_size=3,
            vad_filter=os.getenv("WHISPER_VAD_FILTER", "true").lower() == "true",
        )
        return "".join(segment.text for segment in segments).strip()


def get_kokoro() -> Kokoro:
    global _kokoro
    if _kokoro is None:
        with _kokoro_lock:
            if _kokoro is None:
                _kokoro = Kokoro(
                    os.getenv("KOKORO_MODEL_PATH", "/models/kokoro-v1.0.onnx"),
                    os.getenv("KOKORO_VOICES_PATH", "/models/voices-v1.0.bin"),
                )
    return _kokoro


def synthesize(text: str, voice: str, speed: float) -> tuple[bytes, int]:
    with _inference_lock:
        audio, sample_rate = get_kokoro().create(
            text=text,
            voice=voice or os.getenv("KOKORO_DEFAULT_VOICE", "ff_siwis"),
            speed=max(0.75, min(speed, 1.2)),
            lang="fr-fr",
        )
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return buffer.getvalue(), sample_rate


def authorize(value: str | None) -> None:
    expected = os.getenv("STT_API_KEY", "maxinus-local-stt")
    received = (value or "").removeprefix("Bearer ")
    if not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="Invalid local STT key")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
async def models(authorization: str | None = Header(default=None)) -> dict:
    authorize(authorization)
    model = os.getenv("WHISPER_MODEL", "base")
    return {"object": "list", "data": [{"id": model, "object": "model"}]}


class SpeechRequest(BaseModel):
    model: str = "kokoro"
    input: str
    voice: str = "ff_siwis"
    response_format: str = "wav"
    speed: float = 1.0


@app.post("/v1/audio/speech")
async def speech(
    payload: SpeechRequest,
    authorization: str | None = Header(default=None),
) -> Response:
    expected = os.getenv("TTS_API_KEY", "maxinus-local-tts")
    received = (authorization or "").removeprefix("Bearer ")
    if not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="Invalid local TTS key")
    text = payload.input.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")
    if len(text) > 4000:
        raise HTTPException(status_code=413, detail="Text is too long for one speech request")
    if payload.response_format.lower() not in {"wav", "mp3", "opus", "aac", "flac", "pcm"}:
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    try:
        audio_bytes, _ = await asyncio.to_thread(
            synthesize, text, payload.voice, payload.speed
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Kokoro synthesis failed: {exc}") from exc
    return Response(content=audio_bytes, media_type="audio/wav")


@app.post("/v1/audio/transcriptions")
async def transcription(
    file: UploadFile = File(...),
    model: str = Form(default="base"),
    language: str | None = Form(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    del model  # Le serveur n'autorise que le modèle fixé par l'administrateur.
    authorize(authorization)
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    temporary_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary_path = temporary.name
            while chunk := await file.read(1024 * 1024):
                temporary.write(chunk)
        text = await asyncio.to_thread(transcribe_file, temporary_path, language)
        return {"text": text}
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
