#!/usr/bin/env python3
"""Validate ReleaseEvidenceBundle examples and generated output."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.contracts import load_json  # noqa: E402
from agent_machine.release_bundle import (  # noqa: E402
    DEFAULT_COMMIT_SHA,
    DEFAULT_GENERATED_AT,
    DEFAULT_REPOSITORY,
    generate_release_bundle,
    validate_release_bundle,
)

EXAMPLE = REPO_ROOT / "examples" / "release-evidence-bundle.bootstrap.json"


def main() -> int:
    example = load_json(EXAMPLE)
    validate_release_bundle(example, REPO_ROOT)
    print(f"VALID release bundle example {EXAMPLE.relative_to(REPO_ROOT)}")

    generated = generate_release_bundle(
        root=REPO_ROOT,
        repository=DEFAULT_REPOSITORY,
        branch="main",
        commit_sha=DEFAULT_COMMIT_SHA,
        pull_request=None,
        workflow_run_id=None,
        validation_status="unknown",
        workflow_job_name="Validate contracts, examples, CLI, formula, and docs",
        generated_at=DEFAULT_GENERATED_AT,
        validated_at=None,
    )
    validate_release_bundle(generated, REPO_ROOT)
    if generated["kind"] != "ReleaseEvidenceBundle":
        raise AssertionError("generated bundle kind mismatch")
    if generated["receiptSafety"]["secretValuesIncluded"] is not False:
        raise AssertionError("generated bundle must be secret-free")
    if not generated["inventories"]["schemas"]:
        raise AssertionError("generated bundle missing schema inventory")
    if not generated["renderedArtifacts"]:
        raise AssertionError("generated bundle missing rendered artifacts")
    print("VALID generated release evidence bundle")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
