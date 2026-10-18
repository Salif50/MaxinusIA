from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


# src/maxinus/config.py -> racine du projet
ROOT = Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class Config:
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:14b"
    whisper_model: str = "small"
    language: str = "fr"
    tts_voice: str = "ff_siwis"
    tts_speed: float = 1.05
    input_device: str | int | None = None
    output_device: str | int | None = None
    wake_word: str = "maxinus"
    temperature: float = 0.35
    context_messages: int = 20
    workspace: str = "~"

    @property
    def model_dir(self) -> Path:
        return ROOT / "models"

    @property
    def data_dir(self) -> Path:
        path = ROOT / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def workspace_path(self) -> Path:
        return Path(self.workspace).expanduser().resolve()

    @classmethod
    def load(cls) -> "Config":
        values: dict = {}
        path = ROOT / "config.json"
        if path.exists():
            values.update(json.loads(path.read_text(encoding="utf-8")))
        env_map = {
            "MAXINUS_MODEL": "ollama_model",
            "MAXINUS_OLLAMA_URL": "ollama_url",
            "MAXINUS_WHISPER_MODEL": "whisper_model",
            "MAXINUS_VOICE": "tts_voice",
            "MAXINUS_WORKSPACE": "workspace",
            "MAXINUS_INPUT_DEVICE": "input_device",
            "MAXINUS_OUTPUT_DEVICE": "output_device",
        }
        for env, key in env_map.items():
            if os.getenv(env):
                values[key] = os.environ[env]
        known = set(asdict(cls()))
        return cls(**{k: v for k, v in values.items() if k in known})
