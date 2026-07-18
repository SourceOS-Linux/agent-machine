#!/usr/bin/env python3
"""Validate AgentPod image/provenance posture."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.contracts import load_json  # noqa: E402
from agent_machine.supply_chain import validate_agentpod_supply_chain  # noqa: E402

BOOTSTRAP_AGENTPODS = [
    REPO_ROOT / "examples" / "local-podman-llama-cpp.agent-pod.json",
    REPO_ROOT / "examples" / "k8s-topolvm.agent-pod.json",
]
STRICT_AGENTPODS = [
    REPO_ROOT / "examples" / "local-podman-llama-cpp.pinned.agent-pod.json",
]


def main() -> int:
    for path in BOOTSTRAP_AGENTPODS:
        warnings = validate_agentpod_supply_chain(load_json(path), strict=False, source=str(path.relative_to(REPO_ROOT)))
        for warning in warnings:
            print(f"WARNING {warning}")
        print(f"VALID supply-chain bootstrap {path.relative_to(REPO_ROOT)}")

    for path in STRICT_AGENTPODS:
        validate_agentpod_supply_chain(load_json(path), strict=True, source=str(path.relative_to(REPO_ROOT)))
        print(f"VALID supply-chain strict {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
