"""Configure le fournisseur STT local dans une base Open WebUI existante."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path


def main() -> None:
    database = Path(sys.argv[1])
    if not database.exists():
        # Au premier démarrage, Open WebUI crée la base depuis les variables d'environnement.
        return

    values = {
        "audio.stt.engine": os.getenv("AUDIO_STT_ENGINE", "openai"),
        "audio.stt.openai.api_base_url": os.getenv(
            "AUDIO_STT_OPENAI_API_BASE_URL", "http://stt:8000/v1"
        ),
        "audio.stt.openai.api_key": os.getenv(
            "AUDIO_STT_OPENAI_API_KEY", "maxinus-local-stt"
        ),
        "audio.stt.openai.api_request_format": os.getenv(
            "AUDIO_STT_OPENAI_API_REQUEST_FORMAT", "multipart"
        ),
        "audio.stt.model": os.getenv("AUDIO_STT_MODEL", "base"),
        "audio.tts.engine": os.getenv("AUDIO_TTS_ENGINE", "openai"),
        "audio.tts.openai.api_base_url": os.getenv(
            "AUDIO_TTS_OPENAI_API_BASE_URL", "http://stt:8000/v1"
        ),
        "audio.tts.openai.api_key": os.getenv(
            "AUDIO_TTS_OPENAI_API_KEY", "maxinus-local-tts"
        ),
        "audio.tts.model": os.getenv("AUDIO_TTS_MODEL", "kokoro"),
        "audio.tts.voice": os.getenv("AUDIO_TTS_VOICE", "ff_siwis"),
    }

    with sqlite3.connect(database) as connection:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='config'"
        ).fetchone()
        if not table_exists:
            return
        now = int(time.time())
        connection.executemany(
            """
            INSERT INTO config (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            [(key, json.dumps(value), now) for key, value in values.items()],
        )


if __name__ == "__main__":
    main()
