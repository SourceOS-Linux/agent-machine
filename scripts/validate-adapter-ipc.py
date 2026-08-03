#!/usr/bin/env python3
"""Validate the M2 Adapter IPC v0.1 contract with teeth.

The M2 Adapter IPC protocol is JSON-over-stdio (NDJSON) between the
contract-runner and a backend adapter subprocess. This validator proves the
contract enforces its own invariants:

  * every accept fixture under fixtures/protocol/*.ndjson MUST validate
    against contracts/adapter-ipc.schema.json AND satisfy the semantic
    invariants (id correlation, ok/errors coupling, canonical error codes,
    hello handshake rules);
  * every reject fixture under fixtures/protocol/_reject/*.ndjson MUST FAIL
    at least one of those checks (a reject that passes is a hole in the
    contract and fails this validator).

Provenance: 'M2 Adapter IPC Spec v0.1 (JSON-over-stdio, Subprocess Plugins)'
+ 'M2 Protocol Versioning & Compatibility Spec v0.1', SourceOS Spec intake
2026-07-31. Hashes are SHA-256 (FIPS 180-4).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "adapter-ipc.schema.json"
ACCEPT_DIR = ROOT / "fixtures" / "protocol"
REJECT_DIR = ACCEPT_DIR / "_reject"

PROTOCOL_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+$")

CANONICAL_ERROR_CODES = {
    "E_PROTOCOL_INCOMPATIBLE", "E_HELLO_REQUIRED", "E_CAPABILITY_MISSING",
    "E_LOCK_MISSING", "E_LOCK_INVALID", "E_LOCK_HASH_FAILED", "E_LOCK_UPDATE_DENIED",
    "E_ENV_REALIZE_FAILED", "E_ENV_FLOATING_DISALLOWED", "E_ENV_NOT_FOUND",
    "E_TASK_UNKNOWN", "E_TASK_FAILED", "E_TASK_TIMEOUT", "E_CMD_FAILED",
    "E_PATH_ESCAPE", "E_WRITE_DENIED", "E_DEPS_INVENTORY_FAILED",
    "E_LICENSE_EVIDENCE_MISSING", "E_UNSUPPORTED", "E_INTERNAL",
}


class ContractError(Exception):
    """Raised when a message violates the schema or a semantic invariant."""


def load_schema() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def read_messages(path: Path) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{path.name}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ContractError(f"{path.name}:{lineno}: message must be a JSON object")
        messages.append(obj)
    return messages


def check_message(validator: Draft202012Validator, msg: dict[str, Any]) -> None:
    """Schema + semantic invariants for a single message. Raises on violation."""
    errors = sorted(validator.iter_errors(msg), key=lambda e: list(e.path))
    if errors:
        loc = "/".join(str(p) for p in errors[0].path) or "<root>"
        raise ContractError(f"schema: {loc}: {errors[0].message}")

    if not isinstance(msg.get("id"), str) or not msg["id"]:
        raise ContractError("every message must carry a non-empty string id")

    is_request = "op" in msg
    is_response = "ok" in msg
    if is_request == is_response:
        raise ContractError("message must be exactly one of request (op) or response (ok)")

    if is_request and msg["op"] == "hello":
        pv = msg.get("protocol_version")
        if not isinstance(pv, str) or not PROTOCOL_VERSION_RE.match(pv):
            raise ContractError("hello request needs MAJOR.MINOR protocol_version")

    if is_response:
        errs = msg.get("errors")
        if not isinstance(errs, list):
            raise ContractError("response.errors must be an array")
        if msg["ok"] is False and len(errs) == 0:
            raise ContractError("ok=false must carry a non-empty errors array")
        if msg["ok"] is True and len(errs) != 0:
            raise ContractError("ok=true must carry an empty errors array")
        for e in errs:
            if e.get("code") not in CANONICAL_ERROR_CODES:
                raise ContractError(f"error code {e.get('code')!r} not in canonical registry")


def check_correlation(messages: list[dict[str, Any]]) -> None:
    """Consecutive request/response pairs must share the same id."""
    for i in range(0, len(messages) - 1, 2):
        req, resp = messages[i], messages[i + 1]
        if "op" in req and "ok" in resp and req.get("id") != resp.get("id"):
            raise ContractError(
                f"correlation: request id {req.get('id')!r} != response id {resp.get('id')!r}"
            )


def main() -> int:
    if not SCHEMA_PATH.exists():
        print(f"ERROR: missing schema {SCHEMA_PATH}", file=sys.stderr)
        return 1
    validator = load_schema()

    accepted = 0
    for path in sorted(ACCEPT_DIR.glob("*.ndjson")):
        try:
            messages = read_messages(path)
            if not messages:
                raise ContractError("accept fixture has no messages")
            for msg in messages:
                check_message(validator, msg)
            check_correlation(messages)
        except ContractError as exc:
            print(f"FAIL(accept): {path.name}: {exc}", file=sys.stderr)
            return 1
        accepted += 1
        print(f"OK(accept): {path.name} ({len(messages)} message(s))")

    rejected = 0
    for path in sorted(REJECT_DIR.glob("*.ndjson")):
        try:
            messages = read_messages(path)
            for msg in messages:
                check_message(validator, msg)
            check_correlation(messages)
        except ContractError:
            rejected += 1
            print(f"OK(reject fired): {path.name}")
            continue
        print(f"FAIL(reject): {path.name}: expected a contract violation but it passed", file=sys.stderr)
        return 1

    if accepted == 0 or rejected == 0:
        print("ERROR: expected at least one accept and one reject fixture", file=sys.stderr)
        return 1

    print(f"OK: adapter-ipc contract — {accepted} accepted, {rejected} rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
