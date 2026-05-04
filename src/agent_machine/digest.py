"""Stable digest helpers for Agent Machine artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_bytes(value: Any) -> bytes:
    """Return canonical JSON bytes for deterministic hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def stable_digest(value: Any) -> str:
    """Return a sha256 digest string for a JSON-serializable value."""
    return "sha256:" + hashlib.sha256(stable_json_bytes(value)).hexdigest()


def stable_text_digest(value: str) -> str:
    """Return a sha256 digest string for UTF-8 text."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
