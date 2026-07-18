#!/usr/bin/env python3
"""Validate local Policy Fabric admission resolution behavior."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.policy_fabric import (  # noqa: E402
    load_policy_admissions,
    resolve_policy_admission,
    validate_policy_admission_payload,
)

AGENTPOD_ID = "urn:srcos:agent-machine:agent-pod:local-podman-llama-cpp"
AGENT_MACHINE_ID = "urn:srcos:agent-machine:m2-asahi-local"
PROVIDER_ID = "urn:srcos:agent-machine:inference-provider:asahi-llama-cpp"
DEPLOYMENT_RECEIPT_ID = "urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
DECIDED_AT = "2026-05-04T12:51:00Z"


def expect_status(policy: dict, expected: str, label: str) -> None:
    observed = policy.get("decision", {}).get("status")
    if observed != expected:
        raise AssertionError(f"{label}: expected status={expected}, observed {observed}")
    validate_policy_admission_payload(policy, REPO_ROOT, source=label)
    print(f"VALID policy resolve {label} status={expected}")


def expect_ambiguous(policies: list[dict]) -> None:
    try:
        resolve_policy_admission(
            policies=policies,
            agentpod_id=AGENTPOD_ID,
            request_type="activation",
            deployment_receipt_id=DEPLOYMENT_RECEIPT_ID,
            agent_machine_id=AGENT_MACHINE_ID,
            provider_id=PROVIDER_ID,
            allow_missing_stub=False,
            root=REPO_ROOT,
        )
    except AssertionError as exc:
        if "ambiguous PolicyAdmission" not in str(exc):
            raise
        print("VALID policy resolve ambiguous activation requires disambiguation")
        return
    raise AssertionError("expected ambiguous PolicyAdmission resolution to fail")


def main() -> int:
    policies = load_policy_admissions(directories=[REPO_ROOT / "examples"], root=REPO_ROOT)
    if len(policies) < 4:
        raise AssertionError("expected at least four PolicyAdmission examples")

    expect_ambiguous(policies)

    allowed = resolve_policy_admission(
        policies=policies,
        agentpod_id=AGENTPOD_ID,
        request_type="activation",
        deployment_receipt_id=DEPLOYMENT_RECEIPT_ID,
        agent_machine_id=AGENT_MACHINE_ID,
        provider_id=PROVIDER_ID,
        expected_status="allowed",
        root=REPO_ROOT,
    )
    expect_status(allowed, "allowed", "allowed-activation")

    denied = resolve_policy_admission(
        policies=policies,
        agentpod_id=AGENTPOD_ID,
        request_type="activation",
        deployment_receipt_id=DEPLOYMENT_RECEIPT_ID,
        agent_machine_id=AGENT_MACHINE_ID,
        provider_id=PROVIDER_ID,
        expected_status="denied",
        root=REPO_ROOT,
    )
    expect_status(denied, "denied", "denied-activation")

    missing = resolve_policy_admission(
        policies=policies,
        agentpod_id=AGENTPOD_ID,
        request_type="activation",
        deployment_receipt_id=DEPLOYMENT_RECEIPT_ID,
        agent_machine_id=AGENT_MACHINE_ID,
        provider_id="urn:srcos:agent-machine:inference-provider:unresolved-provider",
        allow_missing_stub=True,
        decided_at=DECIDED_AT,
        root=REPO_ROOT,
    )
    expect_status(missing, "missing", "generated-missing-stub")

    by_id = resolve_policy_admission(
        policies=policies,
        agentpod_id=AGENTPOD_ID,
        request_type="activation",
        deployment_receipt_id=DEPLOYMENT_RECEIPT_ID,
        policy_id="urn:srcos:agent-machine:policy-admission:allowed-loopback-activation",
        root=REPO_ROOT,
    )
    expect_status(by_id, "allowed", "policy-id")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
