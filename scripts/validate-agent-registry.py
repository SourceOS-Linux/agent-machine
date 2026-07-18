#!/usr/bin/env python3
"""Validate local Agent Registry grant resolution behavior."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.agent_registry import (  # noqa: E402
    load_agent_registry_grants,
    requested_scope_from_inputs,
    resolve_agent_registry_grant,
    validate_agent_registry_grant_payload,
)

AGENTPOD_ID = "urn:srcos:agent-machine:agent-pod:local-podman-llama-cpp"
AGENT_MACHINE_ID = "urn:srcos:agent-machine:m2-asahi-local"
IDENTITY_REF = "urn:srcos:agent:local-inference-provider"
SESSION_REF = "urn:srcos:session:local-bootstrap"
WORKROOM_REF = "urn:srcos:workroom:local-default"
TOPIC_REF = "urn:srcos:topic:agent-machine"
PROVIDER_ID = "urn:srcos:agent-machine:inference-provider:asahi-llama-cpp"
ISSUED_AT = "2026-05-04T12:51:00Z"


def expect_status(grant: dict, expected: str, label: str) -> None:
    observed = grant.get("grant", {}).get("status")
    if observed != expected:
        raise AssertionError(f"{label}: expected status={expected}, observed {observed}")
    validate_agent_registry_grant_payload(grant, REPO_ROOT, source=label)
    print(f"VALID registry resolve {label} status={expected}")


def expect_ambiguous(grants: list[dict]) -> None:
    try:
        resolve_agent_registry_grant(
            grants=grants,
            agentpod_id=AGENTPOD_ID,
            requested_agent_identity_ref=IDENTITY_REF,
            session_ref=SESSION_REF,
            agent_machine_id=AGENT_MACHINE_ID,
            workroom_ref=WORKROOM_REF,
            topic_ref=TOPIC_REF,
            allow_missing_stub=False,
            root=REPO_ROOT,
        )
    except AssertionError as exc:
        if "ambiguous AgentRegistryGrant" not in str(exc):
            raise
        print("VALID registry resolve ambiguous grant requires disambiguation")
        return
    raise AssertionError("expected ambiguous AgentRegistryGrant resolution to fail")


def main() -> int:
    grants = load_agent_registry_grants(directories=[REPO_ROOT / "examples"], root=REPO_ROOT)
    if len(grants) < 4:
        raise AssertionError("expected at least four AgentRegistryGrant examples")

    expect_ambiguous(grants)

    active_activation = resolve_agent_registry_grant(
        grants=grants,
        agentpod_id=AGENTPOD_ID,
        requested_agent_identity_ref=IDENTITY_REF,
        session_ref=SESSION_REF,
        agent_machine_id=AGENT_MACHINE_ID,
        workroom_ref=WORKROOM_REF,
        topic_ref=TOPIC_REF,
        grant_id="urn:srcos:agent-machine:agent-registry-grant:active-loopback-activation",
        root=REPO_ROOT,
    )
    expect_status(active_activation, "active", "active-activation")

    revoked = resolve_agent_registry_grant(
        grants=grants,
        agentpod_id=AGENTPOD_ID,
        requested_agent_identity_ref=IDENTITY_REF,
        session_ref=SESSION_REF,
        agent_machine_id=AGENT_MACHINE_ID,
        workroom_ref=WORKROOM_REF,
        topic_ref=TOPIC_REF,
        expected_status="revoked",
        root=REPO_ROOT,
    )
    expect_status(revoked, "revoked", "revoked")

    missing = resolve_agent_registry_grant(
        grants=grants,
        agentpod_id=AGENTPOD_ID,
        requested_agent_identity_ref="urn:srcos:agent:unresolved-provider",
        session_ref=SESSION_REF,
        agent_machine_id=AGENT_MACHINE_ID,
        workroom_ref=WORKROOM_REF,
        topic_ref=TOPIC_REF,
        allow_missing_stub=True,
        requested_scope=requested_scope_from_inputs(
            provider_id=PROVIDER_ID,
            tool_refs=["urn:srcos:tool:start-provider", "urn:srcos:tool:mount-cache"],
        ),
        issued_at=ISSUED_AT,
        root=REPO_ROOT,
    )
    expect_status(missing, "missing", "generated-missing-stub")

    by_id = resolve_agent_registry_grant(
        grants=grants,
        agentpod_id=AGENTPOD_ID,
        requested_agent_identity_ref=IDENTITY_REF,
        session_ref=SESSION_REF,
        grant_id="urn:srcos:agent-machine:agent-registry-grant:active-render-only",
        root=REPO_ROOT,
    )
    expect_status(by_id, "active", "grant-id")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
