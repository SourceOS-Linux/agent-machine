#!/usr/bin/env python3
"""Validate Agent Machine JSON schemas and examples."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.contracts import (  # noqa: E402
    check_schema,
    contracts_dir,
    examples_dir,
    iter_json_files,
    load_json,
    schema_by_kind,
    validate_instance,
)


def schema_mapping(root: Path) -> dict[str, Path]:
    """Return schema mappings, including upstream-style receipt examples that use type."""
    mapping = dict(schema_by_kind(root))
    mapping.setdefault("RuntimeInstallReceipt", contracts_dir(root) / "runtime-install-receipt.schema.json")
    return mapping


def validate_example_by_kind_or_type(example_path: Path, root: Path) -> Path:
    instance = load_json(example_path)
    if not isinstance(instance, dict):
        raise AssertionError(f"{example_path}: example root must be a JSON object")
    kind = instance.get("kind") or instance.get("type")
    if not isinstance(kind, str):
        raise AssertionError(f"{example_path}: missing string `kind` or `type` field")
    mapping = schema_mapping(root)
    schema_path = mapping.get(kind)
    if schema_path is None:
        known = ", ".join(sorted(mapping))
        raise AssertionError(f"{example_path}: no schema mapping for kind {kind!r}; known: {known}")
    if not schema_path.exists():
        raise AssertionError(f"{example_path}: mapped schema is missing: {schema_path}")
    validate_instance(example_path, schema_path)
    return schema_path


def is_documentation_bundle(instance: object) -> bool:
    """A narrative bundle of illustrative fragments, not a single typed artifact.

    Shape: no top-level `kind`/`type`, plus an `examples` array. The fragments it
    carries are untyped, so there is no schema to check them against without
    guessing. Recognised here so it can be REPORTED as unvalidated rather than
    silently walked past — an unchecked file that nothing mentions is how a
    contract quietly stops being enforced.
    """
    return (
        isinstance(instance, dict)
        and not isinstance(instance.get("kind") or instance.get("type"), str)
        and isinstance(instance.get("examples"), list)
    )


def validate_examples(root: Path) -> None:
    unvalidated: list[Path] = []
    for example_path in iter_json_files(examples_dir(root)):
        if is_documentation_bundle(load_json(example_path)):
            unvalidated.append(example_path)
            print(f"DOC BUNDLE (not schema-validated) {example_path.relative_to(root)}")
            continue
        schema_path = validate_example_by_kind_or_type(example_path, root)
        print(f"VALID example {example_path.relative_to(root)} -> {schema_path.relative_to(root)}")
    if unvalidated:
        print(f"\nNOTE: {len(unvalidated)} documentation bundle(s) carry untyped fragments and were not")
        print("      schema-checked. Give a fragment a `kind` and a contract to bring it under validation.")


def main() -> int:
    root = REPO_ROOT
    schema_files = iter_json_files(contracts_dir(root))
    if not schema_files:
        raise AssertionError("No JSON schemas found under contracts/")

    for schema_path in schema_files:
        check_schema(schema_path)
        print(f"VALID schema {schema_path.relative_to(root)}")

    validate_examples(root)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
