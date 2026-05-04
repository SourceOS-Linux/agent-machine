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
    validate_by_kind,
)


def validate_examples(root: Path) -> None:
    for example_path in iter_json_files(examples_dir(root)):
        schema_path = validate_by_kind(example_path, root)
        print(f"VALID example {example_path.relative_to(root)} -> {schema_path.relative_to(root)}")


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
