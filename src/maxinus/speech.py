from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .audio import play_audio
from .config import Config


class SpeechEngine:
    def __init__(self, config: Config):
        self.config = config
        self._stt = None
        self._tts = None

    def _load_stt(self):
        if self._stt is None:
            from faster_whisper import WhisperModel

            local = self.config.model_dir / f"faster-whisper-{self.config.whisper_model}"
            source = str(local) if local.exists() else self.config.whisper_model
            self._stt = WhisperModel(source, device="cpu", compute_type="int8")
        return self._stt

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self._load_stt().transcribe(
            audio,
            language=self.config.language,
            beam_size=3,
            vad_filter=True,
            condition_on_previous_text=False,
            temperature=0.0,
            no_speech_threshold=0.55,
            log_prob_threshold=-0.9,
            compression_ratio_threshold=2.2,
        )
        reliable = []
        for segment in segments:
            if segment.no_speech_prob > 0.55 or segment.avg_logprob < -0.9:
                continue
            reliable.append(segment.text.strip())
        text = " ".join(reliable).strip()
        hallucinations = (
            "sous-titres réalisés par",
            "merci d'avoir regardé",
            "amara.org",
        )
        if any(phrase in text.lower() for phrase in hallucinations):
            return ""
        return text

    def _load_tts(self):
        if self._tts is None:
            from kokoro_onnx import Kokoro

            model = self.config.model_dir / "kokoro-v1.0.onnx"
            voices = self.config.model_dir / "voices-v1.0.bin"
            if not model.exists() or not voices.exists():
                raise FileNotFoundError(
                    "Modèles Kokoro absents. Lancez ./setup.sh pour les télécharger."
                )
            self._tts = Kokoro(str(model), str(voices))
        return self._tts

    @staticmethod
    def _spoken_text(text: str) -> str:
        text = re.sub(r"```.*?```", " bloc de code omis ", text, flags=re.S)
        text = re.sub(r"https?://\S+", "lien", text)
        text = re.sub(r"[*_#`>|]", "", text)
        return re.sub(r"\s+", " ", text).strip()[:1800]

    def speak(self, text: str) -> None:
        audio, sample_rate = self.synthesize(text)
        if len(audio):
            play_audio(audio, sample_rate, device=self.config.output_device)

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        spoken = self._spoken_text(text)
        if not spoken:
            return np.empty(0, dtype=np.float32), 24000
        audio, sample_rate = self._load_tts().create(
            spoken,
            voice=self.config.tts_voice,
            speed=self.config.tts_speed,
            lang="fr-fr",
        )
        return audio, sample_rate

    def speak_cached(self, key: str, text: str) -> None:
        """Génère une phrase fixe une seule fois, puis la relit immédiatement."""
        audio, sample_rate = self.cached_audio(key, text)
        play_audio(audio, sample_rate, device=self.config.output_device)

    def cached_audio(self, key: str, text: str) -> tuple[np.ndarray, int]:
        import soundfile as sf

        cache = self.config.data_dir / "audio-cache"
        cache.mkdir(parents=True, exist_ok=True)
        path = cache / f"{key}.wav"
        if path.exists():
            audio, sample_rate = sf.read(path, dtype="float32")
        else:
            audio, sample_rate = self._load_tts().create(
                self._spoken_text(text),
                voice=self.config.tts_voice,
                speed=self.config.tts_speed,
                lang="fr-fr",
            )
            sf.write(path, audio, sample_rate, subtype="PCM_16")
        return audio, sample_rate
