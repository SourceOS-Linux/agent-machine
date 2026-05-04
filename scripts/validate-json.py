#!/usr/bin/env python3
"""Validate Agent Machine JSON schemas and examples.

This script intentionally keeps validation local to the repository. It parses every
JSON document under contracts/ and examples/, checks each schema with the
jsonschema library, and validates examples by their `kind` field.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema.validators import validator_for
except ImportError as exc:  # pragma: no cover - exercised in environments without deps
    raise SystemExit(
        "Missing dependency: jsonschema. Install with `python -m pip install -r requirements-dev.txt`."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = REPO_ROOT / "contracts"
EXAMPLES_DIR = REPO_ROOT / "examples"

SCHEMA_BY_KIND = {
    "AgentMachine": CONTRACTS_DIR / "agent-machine.schema.json",
    "AgentPod": CONTRACTS_DIR / "agent-pod.schema.json",
    "CacheTier": CONTRACTS_DIR / "cache-tier.schema.json",
    "InferenceProvider": CONTRACTS_DIR / "inference-provider.schema.json",
}


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path}: invalid JSON: {exc}") from exc


def iter_json_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.rglob("*.json") if path.is_file())


def check_schema(path: Path) -> dict[str, Any]:
    schema = load_json(path)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    return schema


def validate_instance(instance_path: Path, schema_path: Path) -> None:
    schema = load_json(schema_path)
    instance = load_json(instance_path)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    if errors:
        rendered = []
        for err in errors:
            location = "/".join(str(part) for part in err.path) or "<root>"
            rendered.append(f"  - {instance_path}: {location}: {err.message}")
        raise AssertionError("Schema validation failed:\n" + "\n".join(rendered))


def validate_examples() -> None:
    for example_path in iter_json_files(EXAMPLES_DIR):
        instance = load_json(example_path)
        if not isinstance(instance, dict):
            raise AssertionError(f"{example_path}: example root must be a JSON object")
        kind = instance.get("kind")
        if not isinstance(kind, str):
            raise AssertionError(f"{example_path}: missing string `kind` field")
        schema_path = SCHEMA_BY_KIND.get(kind)
        if schema_path is None:
            known = ", ".join(sorted(SCHEMA_BY_KIND))
            raise AssertionError(f"{example_path}: no schema mapping for kind {kind!r}; known: {known}")
        if not schema_path.exists():
            raise AssertionError(f"{example_path}: mapped schema is missing: {schema_path}")
        validate_instance(example_path, schema_path)
        print(f"VALID example {example_path.relative_to(REPO_ROOT)} -> {schema_path.relative_to(REPO_ROOT)}")


def main() -> int:
    schema_files = iter_json_files(CONTRACTS_DIR)
    if not schema_files:
        raise AssertionError("No JSON schemas found under contracts/")

    for schema_path in schema_files:
        check_schema(schema_path)
        print(f"VALID schema {schema_path.relative_to(REPO_ROOT)}")

    validate_examples()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
