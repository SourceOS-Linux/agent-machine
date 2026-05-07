#!/usr/bin/env python3
"""Validate Superconscious runtime-plan fixture for Agent Machine.

The M1 runtime plan is intentionally no-activation: it must not start a runtime,
load a model, open a socket, mutate host state, or require network access.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "superconscious" / "reasoning-runtime-plan.json"


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(doc: dict[str, Any]) -> int:
    if doc.get("apiVersion") != "agentmachine.sourceos.dev/v1":
        return fail("apiVersion invalid")
    if doc.get("kind") != "SuperconsciousReasoningRuntimePlan":
        return fail("kind must be SuperconsciousReasoningRuntimePlan")
    spec = doc.get("spec") or {}
    for key in [
        "reasoningRunRef",
        "agentPodRef",
        "runtimeProfileRef",
        "activationMode",
        "providerClass",
        "modelResidencyRequired",
        "cachePosture",
        "networkRequired",
        "hostMutationRequired",
        "toolExecutionRequired",
        "storage",
        "activationDecision",
    ]:
        if key not in spec:
            return fail(f"missing spec.{key}")
    if not str(spec["reasoningRunRef"]).startswith("urn:srcos:reasoning-run:"):
        return fail("reasoningRunRef must be a SourceOS reasoning-run URN")
    if spec["activationMode"] != "no-activation":
        return fail("activationMode must be no-activation for M1")
    if spec["providerClass"] != "none":
        return fail("providerClass must be none for M1")
    for key in ["modelResidencyRequired", "networkRequired", "hostMutationRequired", "toolExecutionRequired"]:
        if spec[key] is not False:
            return fail(f"{key} must be false for M1")
    storage = spec["storage"]
    if storage.get("memory") != "proposal-only":
        return fail("storage.memory must be proposal-only")
    decision = spec["activationDecision"]
    expected_false = ["startsRuntime", "loadsModel", "opensSocket", "changesHostState"]
    for key in expected_false:
        if decision.get(key) is not False:
            return fail(f"activationDecision.{key} must be false")
    if decision.get("decision") != "allowed-dry-run-plan":
        return fail("activationDecision.decision must be allowed-dry-run-plan")
    if not str(decision.get("evidenceRef", "")).startswith("urn:srcos:reasoning-event:"):
        return fail("activationDecision.evidenceRef must reference a SourceOS reasoning event")
    print("OK: Superconscious runtime plan fixture validated")
    return 0


def main() -> int:
    return validate(load(FIXTURE))


if __name__ == "__main__":
    raise SystemExit(main())
