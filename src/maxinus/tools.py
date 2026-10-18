from __future__ import annotations

import ast
import json
import operator
import os
import platform
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable

from .memory import Memory


def _schema(name: str, description: str, properties: dict, required: list[str] | None = None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


class ToolBox:
    def __init__(self, memory: Memory, workspace: Path, confirm: Callable[[str], bool]):
        self.memory = memory
        self.workspace = workspace
        self.confirm = confirm
        self.schemas = [
            _schema("get_datetime", "Donne la date et l'heure locales", {}),
            _schema("system_info", "Informations non sensibles sur cet ordinateur", {}),
            _schema("list_directory", "Liste un dossier local", {"path": {"type": "string"}}),
            _schema("read_text_file", "Lit un petit fichier texte local", {"path": {"type": "string"}}, ["path"]),
            _schema("search_files", "Recherche du texte dans les fichiers avec ripgrep", {
                "query": {"type": "string"}, "path": {"type": "string"}
            }, ["query"]),
            _schema("write_note", "Ajoute une note dans le carnet local Maxinus", {
                "title": {"type": "string"}, "content": {"type": "string"}
            }, ["title", "content"]),
            _schema("remember", "Mémorise durablement une préférence ou un fait donné par l'utilisateur", {
                "content": {"type": "string"}
            }, ["content"]),
            _schema("search_memory", "Recherche dans la mémoire personnelle locale", {
                "query": {"type": "string"}
            }, ["query"]),
            _schema("calculate", "Calcule une expression arithmétique", {
                "expression": {"type": "string"}
            }, ["expression"]),
            _schema("open_application", "Ouvre une application macOS après confirmation", {
                "name": {"type": "string"}
            }, ["name"]),
            _schema("run_terminal_command", "Exécute une commande terminal locale après confirmation", {
                "command": {"type": "string"}
            }, ["command"]),
        ]

    def _path(self, raw: str | None) -> Path:
        path = Path(raw or self.workspace).expanduser()
        if not path.is_absolute():
            path = self.workspace / path
        return path.resolve()

    def execute(self, name: str, args: dict) -> str:
        try:
            method = getattr(self, f"tool_{name}", None)
            if method is None:
                return f"Outil inconnu: {name}"
            return str(method(**args))[:12000]
        except Exception as exc:
            return f"Erreur de l'outil {name}: {type(exc).__name__}: {exc}"

    def tool_get_datetime(self) -> str:
        return datetime.now().astimezone().strftime("%A %d %B %Y, %H:%M:%S (%Z)")

    def tool_system_info(self) -> str:
        return json.dumps({
            "system": platform.system(), "version": platform.mac_ver()[0],
            "machine": platform.machine(), "python": platform.python_version(),
            "hostname": platform.node(),
        }, ensure_ascii=False)

    def tool_list_directory(self, path: str = "") -> str:
        target = self._path(path)
        entries = []
        for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:200]:
            entries.append(("📁 " if item.is_dir() else "📄 ") + item.name)
        return "\n".join(entries) or "Dossier vide"

    def tool_read_text_file(self, path: str) -> str:
        target = self._path(path)
        if target.stat().st_size > 1_000_000:
            return "Fichier trop volumineux (limite: 1 Mo)."
        return target.read_text(encoding="utf-8", errors="replace")

    def tool_search_files(self, query: str, path: str = "") -> str:
        target = self._path(path)
        result = subprocess.run(
            ["rg", "-n", "--max-count", "50", "--", query, str(target)],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout or "Aucun résultat."

    def tool_write_note(self, title: str, content: str) -> str:
        safe = re.sub(r"[^\w .-]", "_", title, flags=re.UNICODE).strip()[:80] or "note"
        notes = self.memory.db_path.parent / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        path = notes / f"{datetime.now():%Y-%m-%d_%H%M}-{safe}.md"
        path.write_text(f"# {title}\n\n{content.strip()}\n", encoding="utf-8")
        return f"Note enregistrée localement: {path}"

    def tool_remember(self, content: str) -> str:
        return self.memory.remember(content)

    def tool_search_memory(self, query: str) -> str:
        found = self.memory.search(query)
        return "\n".join(f"- {x}" for x in found) or "Aucun souvenir correspondant."

    def tool_calculate(self, expression: str) -> str:
        allowed = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                   ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
                   ast.Mod: operator.mod, ast.Pow: operator.pow, ast.USub: operator.neg,
                   ast.UAdd: operator.pos}
        def evaluate(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in allowed:
                return allowed[type(node.op)](evaluate(node.left), evaluate(node.right))
            if isinstance(node, ast.UnaryOp) and type(node.op) in allowed:
                return allowed[type(node.op)](evaluate(node.operand))
            raise ValueError("Expression non autorisée")
        if len(expression) > 200:
            raise ValueError("Expression trop longue")
        return str(evaluate(ast.parse(expression, mode="eval").body))

    def tool_open_application(self, name: str) -> str:
        if not re.fullmatch(r"[\w .+-]{1,80}", name):
            return "Nom d'application invalide."
        if not self.confirm(f"Ouvrir l'application « {name} » ?"):
            return "Action refusée par l'utilisateur."
        result = subprocess.run(["open", "-a", name], capture_output=True, text=True, timeout=10)
        return "Application ouverte." if result.returncode == 0 else result.stderr

    def tool_run_terminal_command(self, command: str) -> str:
        if len(command) > 1000 or "\n" in command:
            return "Commande refusée: format invalide."
        destructive = re.compile(r"(^|\s)(rm|rmdir|shutdown|reboot|kill|pkill|diskutil|dd|sudo)(\s|$)", re.I)
        if destructive.search(command):
            return "Commande destructive ou privilégiée refusée par la politique de Maxinus."
        if not self.confirm(f"Exécuter dans le terminal : {command}"):
            return "Action refusée par l'utilisateur."
        argv = shlex.split(command)
        if not argv:
            return "Commande vide."
        result = subprocess.run(
            argv, cwd=self.workspace, capture_output=True, text=True, timeout=60,
            env={**os.environ, "PAGER": "cat"},
        )
        return f"code={result.returncode}\n{result.stdout}\n{result.stderr}".strip()
