from __future__ import annotations

import queue
import platform
import subprocess
import sys
import tempfile
import time
from collections import deque
from collections.abc import Callable
from threading import Event

import numpy as np
import sounddevice as sd


class AudioRecorder:
    """Enregistre une phrase et s'arrête après un silence."""

    def __init__(self, sample_rate: int = 16000, device: str | int | None = None):
        self.sample_rate = sample_rate
        self.device = device
        self._silero_model = None

    def prepare(self) -> None:
        """Charge le détecteur en avance pour ne pas perdre les premiers mots."""
        if self._silero_model is None:
            from silero_vad import load_silero_vad

            self._silero_model = load_silero_vad(onnx=True)

    def record_utterance(
        self,
        max_seconds: float = 30,
        silence_seconds: float = 1.15,
        start_timeout: float = 8,
        on_speech_start: Callable[[], None] | None = None,
        stop_event: Event | None = None,
    ) -> np.ndarray | None:
        """Détection de tour de parole neuronale, avec replis locaux."""
        try:
            return self._record_with_silero(
                max_seconds, silence_seconds, start_timeout, on_speech_start, stop_event
            )
        except (ImportError, ModuleNotFoundError, RuntimeError):
            pass
        try:
            return self._record_with_vad(max_seconds, silence_seconds, start_timeout)
        except (ImportError, ModuleNotFoundError):
            return self._record_with_energy(max_seconds, silence_seconds, start_timeout)

    def _record_with_silero(
        self,
        max_seconds: float,
        silence_seconds: float,
        start_timeout: float,
        on_speech_start: Callable[[], None] | None = None,
        stop_event: Event | None = None,
    ) -> np.ndarray | None:
        import torch
        from silero_vad import load_silero_vad

        # Silero travaille par fenêtres exactes de 512 échantillons à 16 kHz.
        blocksize = 512
        frame_seconds = blocksize / self.sample_rate
        chunks: queue.Queue[bytes] = queue.Queue()
        self.prepare()
        model = self._silero_model
        model.reset_states()

        def callback(indata, frames, time_info, status):
            if status:
                print(f"[audio] {status}", file=sys.stderr)
            chunks.put(bytes(indata))

        pre_roll: deque[bytes] = deque(maxlen=12)
        decisions: deque[bool] = deque(maxlen=5)
        recorded: list[bytes] = []
        started = False
        silence_frames = 0
        max_silence_frames = max(10, int(silence_seconds / frame_seconds))
        began = time.monotonic()

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=blocksize,
            callback=callback,
            device=self.device,
        ):
            while time.monotonic() - began < max_seconds:
                if stop_event and stop_event.is_set():
                    return None
                try:
                    frame = chunks.get(timeout=0.1)
                except queue.Empty:
                    continue
                samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
                probability = float(model(torch.from_numpy(samples), self.sample_rate).item())
                voiced = probability >= (0.38 if started else 0.55)
                if not started:
                    pre_roll.append(frame)
                    decisions.append(voiced)
                    if len(decisions) == decisions.maxlen and sum(decisions) >= 3:
                        started = True
                        recorded.extend(pre_roll)
                        if on_speech_start:
                            on_speech_start()
                    elif time.monotonic() - began >= start_timeout:
                        return None
                else:
                    recorded.append(frame)
                    silence_frames = 0 if voiced else silence_frames + 1
                    duration = len(recorded) * frame_seconds
                    if duration >= 0.45 and silence_frames >= max_silence_frames:
                        break

        if not recorded:
            return None
        pcm = b"".join(recorded)
        return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

    def _record_with_vad(
        self, max_seconds: float, silence_seconds: float, start_timeout: float
    ) -> np.ndarray | None:
        import webrtcvad

        frame_ms = 30
        blocksize = self.sample_rate * frame_ms // 1000
        chunks: queue.Queue[bytes] = queue.Queue()
        vad = webrtcvad.Vad(2)

        def callback(indata, frames, time_info, status):
            if status:
                print(f"[audio] {status}", file=sys.stderr)
            chunks.put(bytes(indata))

        pre_roll: deque[bytes] = deque(maxlen=10)
        decisions: deque[bool] = deque(maxlen=5)
        calibration: list[float] = []
        recorded: list[bytes] = []
        started = False
        silence_frames = 0
        max_silence_frames = max(12, int(silence_seconds * 1000 / frame_ms))
        began = time.monotonic()

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=blocksize,
            callback=callback,
            device=self.device,
        ):
            while time.monotonic() - began < max_seconds:
                try:
                    frame = chunks.get(timeout=1)
                except queue.Empty:
                    continue
                samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(samples * samples) + 1e-12))
                # Les 450 premières ms servent à mesurer le bruit de la pièce.
                if len(calibration) < 15:
                    calibration.append(rms)
                    pre_roll.append(frame)
                    continue
                noise_floor = float(np.median(calibration))
                start_level = max(0.009, noise_floor * 3.2)
                continue_level = max(0.0055, noise_floor * 1.8)
                vad_voice = vad.is_speech(frame, self.sample_rate)
                voiced = vad_voice and rms >= (continue_level if started else start_level)
                if not started:
                    pre_roll.append(frame)
                    decisions.append(voiced)
                    if len(decisions) == decisions.maxlen and sum(decisions) >= 3:
                        started = True
                        recorded.extend(pre_roll)
                    elif time.monotonic() - began >= start_timeout:
                        return None
                else:
                    recorded.append(frame)
                    silence_frames = 0 if voiced else silence_frames + 1
                    duration = len(recorded) * frame_ms / 1000
                    if duration >= 0.45 and silence_frames >= max_silence_frames:
                        break

        if not recorded:
            return None
        pcm = b"".join(recorded)
        return (np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0)

    def _record_with_energy(
        self, max_seconds: float, silence_seconds: float, start_timeout: float
    ) -> np.ndarray | None:
        chunks: queue.Queue[np.ndarray] = queue.Queue()
        block_seconds = 0.1
        blocksize = int(self.sample_rate * block_seconds)

        def callback(indata, frames, time_info, status):
            if status:
                print(f"[audio] {status}", file=sys.stderr)
            chunks.put(indata[:, 0].copy())

        frames: list[np.ndarray] = []
        pre_roll: list[np.ndarray] = []
        started = False
        silent_for = 0.0
        began = time.monotonic()
        noise_floor = 0.004
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=blocksize,
            callback=callback,
            device=self.device,
        ):
            while time.monotonic() - began < max_seconds:
                try:
                    block = chunks.get(timeout=1)
                except queue.Empty:
                    continue
                rms = float(np.sqrt(np.mean(block * block) + 1e-12))
                if not started:
                    pre_roll.append(block)
                    pre_roll = pre_roll[-3:]
                    noise_floor = 0.97 * noise_floor + 0.03 * min(rms, 0.03)
                    threshold = max(0.006, noise_floor * 2.4)
                    if rms > threshold:
                        started = True
                        frames.extend(pre_roll)
                    elif time.monotonic() - began > start_timeout:
                        return None
                else:
                    frames.append(block)
                    threshold = max(0.005, noise_floor * 1.9)
                    silent_for = silent_for + block_seconds if rms < threshold else 0.0
                    if silent_for >= silence_seconds:
                        break
        if not frames:
            return None
        audio = np.concatenate(frames)
        peak = float(np.max(np.abs(audio)))
        if peak > 1.0:
            audio = audio / peak
        return audio.astype(np.float32)


def play_audio_interruptible(
    audio: np.ndarray,
    sample_rate: int,
    device: str | int | None = None,
    stop_event: Event | None = None,
) -> bool:
    """Lit un signal sans utiliser l'état global PortAudio.

    Retourne True si la lecture a été interrompue.
    """
    signal = np.asarray(audio, dtype=np.float32)
    if signal.ndim == 1:
        signal = signal[:, None]
    blocksize = 1024
    with sd.OutputStream(
        samplerate=sample_rate,
        channels=signal.shape[1],
        dtype="float32",
        blocksize=blocksize,
        device=device,
    ) as stream:
        for start in range(0, len(signal), blocksize):
            if stop_event and stop_event.is_set():
                return True
            block = signal[start : start + blocksize]
            if len(block) < blocksize:
                block = np.pad(block, ((0, blocksize - len(block)), (0, 0)))
            stream.write(block)
    return False


def play_audio(audio: np.ndarray, sample_rate: int, device: str | int | None = None) -> None:
    play_audio_interruptible(audio, sample_rate, device=device)


class AudioPlayer:
    """Sortie persistante, nécessaire pour certains pilotes CoreAudio/Bluetooth."""

    def __init__(self, device: str | int | None = None, sample_rate: int = 24000):
        self.device = device
        self.sample_rate = sample_rate
        self.blocksize = 1024
        self.stream = None
        self.process: subprocess.Popen | None = None
        self.use_system_player = platform.system() == "Darwin"
        if not self.use_system_player:
            self.stream = sd.OutputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.blocksize,
                device=device,
            )
            self.stream.start()

    def play(self, audio: np.ndarray, sample_rate: int, stop_event: Event | None = None) -> bool:
        signal = np.asarray(audio, dtype=np.float32).reshape(-1)
        if stop_event and stop_event.is_set():
            return True
        if self.use_system_player:
            import soundfile as sf

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                path = handle.name
            try:
                sf.write(path, signal, sample_rate, subtype="PCM_16")
                self.process = subprocess.Popen(
                    ["/usr/bin/afplay", path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                while self.process.poll() is None:
                    if stop_event and stop_event.is_set():
                        self.process.terminate()
                        self.process.wait(timeout=2)
                        return True
                    time.sleep(0.02)
                return False
            finally:
                self.process = None
                try:
                    import os
                    os.unlink(path)
                except OSError:
                    pass
        if sample_rate != self.sample_rate and len(signal):
            size = int(len(signal) * self.sample_rate / sample_rate)
            signal = np.interp(
                np.arange(size) * sample_rate / self.sample_rate,
                np.arange(len(signal)),
                signal,
            ).astype(np.float32)
        signal = signal[:, None]
        for start in range(0, len(signal), self.blocksize):
            if stop_event and stop_event.is_set():
                return True
            block = signal[start : start + self.blocksize]
            if len(block) < self.blocksize:
                block = np.pad(block, ((0, self.blocksize - len(block)), (0, 0)))
            assert self.stream is not None
            self.stream.write(block)
        return False

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
        if self.stream is not None and not self.stream.closed:
            self.stream.stop()
            self.stream.close()
