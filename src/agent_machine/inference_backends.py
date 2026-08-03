"""Serving backends for the local InferenceGateway adapter.

A backend is the callable the gateway invokes once a call is admitted:
`backend(request) -> {"output": str, "usage": dict}`. The Ollama backend runs a model
on the local Ollama daemon — no egress, fully sovereign (privacy_profile sovereign-local).
The HTTP transport is injectable so the backend is testable without a live daemon, and a
failure (daemon down, bad response) raises — which the gateway turns into an audited
denial, never a silent success.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Callable, Dict, List, Optional

DEFAULT_HOST = "http://127.0.0.1:11434"
Transport = Callable[[str, Dict[str, Any]], Dict[str, Any]]


def _urllib_transport(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (local daemon)
        return json.loads(resp.read().decode("utf-8"))


def _to_prompt(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):  # chat-style messages → flattened prompt
        parts: List[str] = []
        for m in value:
            if isinstance(m, dict):
                parts.append(f"{m.get('role', 'user')}: {m.get('content', '')}")
            else:
                parts.append(str(m))
        return "\n".join(parts)
    return str(value)


def ollama_backend(*, model: Optional[str] = None, host: Optional[str] = None,
                   transport: Optional[Transport] = None) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Return a gateway backend that serves via the local Ollama daemon (no egress)."""
    host = (host or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/")
    xport = transport or _urllib_transport

    def _call(request: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "model": request.get("model") or model or "llama3.3",
            "prompt": _to_prompt(request.get("input", "")),
            "stream": False,
        }
        data = xport(f"{host}/api/generate", payload)
        if not isinstance(data, dict) or "response" not in data:
            raise ValueError("ollama: response missing 'response' field")
        return {
            "output": data["response"],
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
        }

    return _call
