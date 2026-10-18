from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _request(self, path: str, payload: dict | None = None, timeout: int = 300) -> dict:
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaError(f"Ollama inaccessible: {exc}") from exc

    def models(self) -> list[str]:
        return [m["name"] for m in self._request("/api/tags", timeout=10).get("models", [])]

    def chat(self, messages: list[dict], tools: list[dict], temperature: float) -> dict:
        result = self._request(
            "/api/chat",
            {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "stream": False,
                "keep_alive": "15m",
                "options": {"temperature": temperature, "num_ctx": 8192},
            },
        )
        return result.get("message", {})

    def chat_stream(
        self, messages: list[dict], tools: list[dict], temperature: float
    ) -> Iterator[dict]:
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": True,
            "keep_alive": "15m",
            "options": {"temperature": temperature, "num_ctx": 8192},
        }).encode()
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                for raw in response:
                    if not raw.strip():
                        continue
                    chunk = json.loads(raw)
                    if chunk.get("error"):
                        raise OllamaError(chunk["error"])
                    yield chunk.get("message", {})
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaError(f"Ollama inaccessible: {exc}") from exc
