from __future__ import annotations

import json
from collections.abc import Iterator

from .config import Config
from .memory import Memory
from .ollama import OllamaClient
from .tools import ToolBox


SYSTEM_PROMPT = """Tu es Maxinus, un assistant vocal personnel local, fiable et chaleureux.
Tu réponds principalement en français, de façon naturelle et concise car tes réponses sont lues à voix haute.
Tu fonctionnes entièrement sur l'ordinateur de l'utilisateur. N'affirme jamais avoir exécuté une action sans outil.
Utilise les outils quand ils améliorent la fiabilité. Pour une préférence personnelle durable explicitement donnée,
utilise remember. Ne mémorise jamais de secret, mot de passe, clé ou donnée bancaire.
Avant une action sensible, l'outil demandera lui-même confirmation. Ne tente pas de contourner cette confirmation.
Pour les chemins relatifs, ils sont résolus depuis l'espace de travail configuré.
"""


class Agent:
    def __init__(self, config: Config, memory: Memory, toolbox: ToolBox):
        self.config = config
        self.memory = memory
        self.toolbox = toolbox
        self.client = OllamaClient(config.ollama_url, config.ollama_model)

    def ask(self, text: str) -> str:
        self.memory.add_message("user", text)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.memory.recent_messages(self.config.context_messages))

        for _ in range(6):
            message = self.client.chat(messages, self.toolbox.schemas, self.config.temperature)
            messages.append(message)
            calls = message.get("tool_calls") or []
            if not calls:
                answer = (message.get("content") or "Je n'ai pas de réponse.").strip()
                self.memory.add_message("assistant", answer)
                return answer
            for call in calls:
                function = call.get("function", {})
                name = function.get("name", "")
                args = function.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                result = self.toolbox.execute(name, args)
                messages.append({"role": "tool", "tool_name": name, "content": result})
        answer = "Je me suis arrêté car trop d'actions successives étaient demandées."
        self.memory.add_message("assistant", answer)
        return answer

    def ask_stream(self, text: str) -> Iterator[str]:
        """Diffuse le texte dès sa génération, tout en conservant les outils."""
        self.memory.add_message("user", text)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.memory.recent_messages(self.config.context_messages))
        full_answer = ""

        for _ in range(6):
            content_parts: list[str] = []
            calls: list[dict] = []
            for message in self.client.chat_stream(
                messages, self.toolbox.schemas, self.config.temperature
            ):
                piece = message.get("content") or ""
                if piece:
                    content_parts.append(piece)
                    full_answer += piece
                    yield piece
                calls.extend(message.get("tool_calls") or [])
            assistant_message: dict = {
                "role": "assistant", "content": "".join(content_parts)
            }
            if calls:
                assistant_message["tool_calls"] = calls
            messages.append(assistant_message)
            if not calls:
                answer = full_answer.strip() or "Je n'ai pas de réponse."
                self.memory.add_message("assistant", answer)
                return
            for call in calls:
                function = call.get("function", {})
                name = function.get("name", "")
                args = function.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                result = self.toolbox.execute(name, args)
                messages.append({"role": "tool", "tool_name": name, "content": result})
        fallback = "Je me suis arrêté car trop d'actions successives étaient demandées."
        if not full_answer:
            yield fallback
            self.memory.add_message("assistant", fallback)
