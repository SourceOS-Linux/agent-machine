#!/usr/bin/env python3
"""Validate AgentPlane runtime evidence examples."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.contracts import load_json  # noqa: E402
from agent_machine.evidence import validate_runtime_evidence_payload  # noqa: E402

EVIDENCE_EXAMPLES = [
    REPO_ROOT / "examples" / "agentplane-runtime-evidence.local.json",
    REPO_ROOT / "examples" / "agentplane-runtime-evidence.k8s.json",
]


def main() -> int:
    for path in EVIDENCE_EXAMPLES:
        evidence = load_json(path)
        validate_runtime_evidence_payload(evidence, REPO_ROOT)
        print(f"VALID runtime evidence {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
