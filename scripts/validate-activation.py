#!/usr/bin/env python3
"""Validate ActivationDecision examples and evaluator behavior."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.activation import evaluate_activation, validate_activation_decision_payload  # noqa: E402
from agent_machine.contracts import load_json  # noqa: E402

LOCAL_AGENTPOD = REPO_ROOT / "examples" / "local-podman-llama-cpp.agent-pod.json"
FAIL_POLICY = REPO_ROOT / "examples" / "policy-admission.missing.json"
FAIL_GRANT = REPO_ROOT / "examples" / "agent-registry-grant.missing.json"
READY_POLICY = REPO_ROOT / "examples" / "policy-admission.allowed-activation.json"
READY_GRANT = REPO_ROOT / "examples" / "agent-registry-grant.active-activation.json"
FAIL_DECISION = REPO_ROOT / "examples" / "activation-decision.fail-closed.json"
READY_DECISION = REPO_ROOT / "examples" / "activation-decision.allowed.json"
DEPLOYMENT_RECEIPT_ID = "urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
STORAGE_RECEIPT_REFS = ["urn:srcos:agent-machine:storage-receipt:local-lvm-warm-cache"]
DECIDED_AT = "2026-05-04T12:51:00Z"


def assert_decision_shape(path: Path, expected_allowed: bool) -> None:
    decision = load_json(path)
    validate_activation_decision_payload(decision, REPO_ROOT)
    observed = decision["decision"]["activationAllowed"]
    if observed is not expected_allowed:
        raise AssertionError(f"{path}: expected activationAllowed={expected_allowed}, observed {observed}")
    print(f"VALID activation decision example {path.relative_to(REPO_ROOT)}")


def assert_evaluator(policy_path: Path, grant_path: Path, expected_allowed: bool, label: str) -> None:
    decision = evaluate_activation(
        agentpod=load_json(LOCAL_AGENTPOD),
        policy=load_json(policy_path),
        grant=load_json(grant_path),
        deployment_receipt_id=DEPLOYMENT_RECEIPT_ID,
        storage_receipt_refs=STORAGE_RECEIPT_REFS,
        decided_at=DECIDED_AT,
    )
    validate_activation_decision_payload(decision, REPO_ROOT)
    observed = decision["decision"]["activationAllowed"]
    if observed is not expected_allowed:
        raise AssertionError(f"{label}: expected activationAllowed={expected_allowed}, observed {observed}")
    print(f"VALID activation evaluator {label}")


def main() -> int:
    assert_decision_shape(FAIL_DECISION, expected_allowed=False)
    assert_decision_shape(READY_DECISION, expected_allowed=True)
    assert_evaluator(FAIL_POLICY, FAIL_GRANT, expected_allowed=False, label="fail-closed")
    assert_evaluator(READY_POLICY, READY_GRANT, expected_allowed=True, label="allowed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
