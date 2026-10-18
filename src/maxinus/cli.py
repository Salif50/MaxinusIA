from __future__ import annotations

import argparse
import re
import shutil
import sys
import threading
import time
from pathlib import Path

import sounddevice as sd

from .agent import Agent
from .audio import AudioPlayer, AudioRecorder
from .config import Config
from .memory import Memory
from .ollama import OllamaClient, OllamaError
from .speech import SpeechEngine
from .tools import ToolBox


CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def confirm(question: str) -> bool:
    try:
        value = input(f"\n{YELLOW}⚠ {question} [o/N] {RESET}").strip().lower()
        return value in {"o", "oui", "y", "yes"}
    except (EOFError, KeyboardInterrupt):
        return False


def build():
    config = Config.load()
    memory = Memory(config.data_dir / "maxinus.db")
    toolbox = ToolBox(memory, config.workspace_path, confirm)
    return config, memory, Agent(config, memory, toolbox)


def banner(config: Config) -> None:
    print(f"{CYAN}╭──────────────────────────────────────╮")
    print("│  M A X I N U S  •  IA locale        │")
    print(f"╰──────────────────────────────────────╯{RESET}")
    print(f"Modèle: {config.ollama_model}  •  aucune donnée envoyée au cloud\n")


def text_mode(agent: Agent, config: Config) -> None:
    banner(config)
    print("Commandes: /effacer, /quitter\n")
    while True:
        try:
            text = input(f"{GREEN}Vous › {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            continue
        if text in {"/quitter", "/exit", "/q"}:
            return
        if text == "/effacer":
            agent.memory.clear_conversation()
            print("Conversation effacée.\n")
            continue
        try:
            answer = agent.ask(text)
            print(f"{CYAN}Maxinus ›{RESET} {answer}\n")
        except OllamaError as exc:
            print(f"Erreur: {exc}\nLancez Ollama puis réessayez.")


def voice_mode(agent: Agent, config: Config, wake: bool = False, live: bool = False) -> None:
    banner(config)
    speech = SpeechEngine(config)
    recorder = AudioRecorder(device=config.input_device)
    player: AudioPlayer | None = None
    if live:
        print("Conversation live active. Parlez naturellement, Ctrl+C pour quitter.\n")
        greeting = (
            "Salut ! Je suis Maxinus, votre assistant local. Que puis-je faire pour vous ?"
        )
        print(f"{CYAN}Maxinus ›{RESET} {greeting}\n")
        welcome_cache = config.data_dir / "audio-cache" / "welcome-v2.wav"

        def warm_up_live_models():
            recorder.prepare()
            speech._load_stt()
            if welcome_cache.exists():
                speech._load_tts()

        warmup = threading.Thread(target=warm_up_live_models, daemon=True)
        warmup.start()
        player = AudioPlayer(device=config.output_device)
        welcome_audio, welcome_rate = speech.cached_audio("welcome-v2", greeting)
        player.play(welcome_audio, welcome_rate)
        warmup.join()
    elif wake:
        print(f"Mode veille actif. Dites « {config.wake_word} », Ctrl+C pour quitter.")
    else:
        print("Appuyez sur Entrée, puis parlez. Tapez q pour quitter.")
    pending_text: str | None = None

    def speak_interruptibly(chunk: str):
        """Parle tout en écoutant une éventuelle interruption utilisateur."""
        stop_monitor = threading.Event()
        user_started = threading.Event()
        captured: dict[str, object] = {"audio": None}

        def on_start():
            user_started.set()

        def monitor():
            try:
                captured["audio"] = recorder.record_utterance(
                    max_seconds=45,
                    start_timeout=45,
                    silence_seconds=0.75,
                    on_speech_start=on_start,
                    stop_event=stop_monitor,
                )
            except sd.PortAudioError as exc:
                captured["error"] = exc

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        audio_out, rate = speech.synthesize(chunk)
        if not user_started.is_set() and len(audio_out):
            assert player is not None
            player.play(audio_out, rate, stop_event=user_started)
        if user_started.is_set():
            thread.join(timeout=12)
            return captured["audio"]
        stop_monitor.set()
        thread.join(timeout=1)
        return None

    try:
        while True:
            if not wake and not live:
                if input().strip().lower() == "q":
                    return
            if pending_text is not None:
                text, pending_text = pending_text, None
            else:
                if live:
                    # Laisse disparaître la fin acoustique de la réponse précédente.
                    time.sleep(0.45)
                print("🎙  À vous…", flush=True)
                audio = recorder.record_utterance(
                    start_timeout=3600 if live else (12 if not wake else 8),
                    silence_seconds=0.9 if live else 1.15,
                )
                if audio is None:
                    if not wake and not live:
                        print("Aucune parole détectée.")
                    continue
                print("… transcription", flush=True)
                text = speech.transcribe(audio)
            if not text:
                continue
            if wake:
                lowered = text.lower()
                if config.wake_word.lower() not in lowered:
                    continue
                text = lowered.split(config.wake_word.lower(), 1)[1].strip(" ,.!?")
                if not text:
                    speech.speak("Oui, je vous écoute.")
                    print("🎙  Votre demande…", flush=True)
                    audio = recorder.record_utterance(start_timeout=8)
                    if audio is None:
                        continue
                    text = speech.transcribe(audio)
            print(f"{GREEN}Vous ›{RESET} {text}")
            if live:
                print(f"{CYAN}Maxinus ›{RESET} ", end="", flush=True)
                spoken_buffer = ""
                full_answer = ""
                interrupted = False
                response_stream = agent.ask_stream(text)
                for piece in response_stream:
                    full_answer += piece
                    spoken_buffer += piece
                    print(piece, end="", flush=True)
                    # Parle dès qu'une phrase complète arrive, pendant que la suite est générée.
                    matches = list(re.finditer(r"[.!?…](?:\s|$)", spoken_buffer))
                    if matches:
                        cut = matches[-1].end()
                        ready, spoken_buffer = spoken_buffer[:cut], spoken_buffer[cut:]
                        interruption = speak_interruptibly(ready)
                        if interruption is not None:
                            response_stream.close()
                            print("  [interrompu]")
                            pending_text = speech.transcribe(interruption)
                            interrupted = True
                            break
                if not interrupted and spoken_buffer.strip():
                    interruption = speak_interruptibly(spoken_buffer)
                    if interruption is not None:
                        pending_text = speech.transcribe(interruption)
                print("\n")
            else:
                answer = agent.ask(text)
                print(f"{CYAN}Maxinus ›{RESET} {answer}\n")
                speech.speak(answer)
    except KeyboardInterrupt:
        print("\nÀ bientôt.")
    except sd.PortAudioError:
        print(
            "\nCoreAudio est bloqué par le pilote ZW-PG02. "
            "Fermez Maxinus puis lancez scripts/macos/fix_audio.command."
        )
    finally:
        if player is not None:
            player.close()


def doctor(config: Config) -> int:
    checks = []
    checks.append(("Python 3.11–3.13", (3, 11) <= sys.version_info[:2] < (3, 14), sys.version.split()[0]))
    checks.append(("Ollama installé", shutil.which("ollama") is not None, shutil.which("ollama") or "absent"))
    try:
        models = OllamaClient(config.ollama_url, config.ollama_model).models()
        checks.append(("Serveur Ollama", True, ", ".join(models) or "aucun modèle"))
        checks.append((f"Modèle {config.ollama_model}", config.ollama_model in models, "présent" if config.ollama_model in models else "absent"))
    except Exception as exc:
        checks.append(("Serveur Ollama", False, str(exc)))
    for filename in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        path = config.model_dir / filename
        checks.append((filename, path.exists(), str(path)))
    try:
        import sounddevice as sd
        inputs = [d["name"] for d in sd.query_devices() if d["max_input_channels"] > 0]
        outputs = [d["name"] for d in sd.query_devices() if d["max_output_channels"] > 0]
        selected_in = config.input_device or (
            sd.query_devices(sd.default.device[0])["name"] if sd.default.device[0] >= 0 else None
        )
        selected_out = config.output_device or (
            sd.query_devices(sd.default.device[1])["name"] if sd.default.device[1] >= 0 else None
        )
        checks.append(("Microphone", selected_in in inputs, str(selected_in or "aucun")))
        checks.append(("Sortie audio", selected_out in outputs, str(selected_out or "aucune")))
    except Exception as exc:
        checks.append(("Audio", False, str(exc)))
    for label, ok, detail in checks:
        print(f"{'✓' if ok else '✗'} {label}: {detail}")
    return 0 if all(x[1] for x in checks) else 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="maxinus", description="Assistant vocal IA 100 % local")
    parser.add_argument("mode", nargs="?", choices=["live", "voice", "wake", "text", "doctor"], default="live")
    args = parser.parse_args()
    config, memory, agent = build()
    if args.mode == "doctor":
        raise SystemExit(doctor(config))
    if args.mode == "text":
        text_mode(agent, config)
    else:
        voice_mode(agent, config, wake=args.mode == "wake", live=args.mode == "live")


if __name__ == "__main__":
    main()
