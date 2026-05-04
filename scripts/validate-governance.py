#!/usr/bin/env python3
"""Validate PolicyAdmission and AgentRegistryGrant semantic consistency."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.contracts import load_json  # noqa: E402
from agent_machine.governance import (  # noqa: E402
    assert_activation_fails_closed,
    assert_activation_ready,
    validate_agent_registry_grant_semantics,
    validate_policy_admission_semantics,
)

POLICY_EXAMPLES = {
    "missing": REPO_ROOT / "examples" / "policy-admission.missing.json",
    "denied": REPO_ROOT / "examples" / "policy-admission.denied.json",
    "allowed": REPO_ROOT / "examples" / "policy-admission.allowed.json",
}

GRANT_EXAMPLES = {
    "missing": REPO_ROOT / "examples" / "agent-registry-grant.missing.json",
    "revoked": REPO_ROOT / "examples" / "agent-registry-grant.revoked.json",
    "active": REPO_ROOT / "examples" / "agent-registry-grant.active.json",
}


def validate_policy_examples() -> dict[str, dict]:
    values = {}
    for name, path in POLICY_EXAMPLES.items():
        value = load_json(path)
        validate_policy_admission_semantics(value, str(path.relative_to(REPO_ROOT)))
        values[name] = value
        print(f"VALID policy semantics {path.relative_to(REPO_ROOT)}")
    return values


def validate_grant_examples() -> dict[str, dict]:
    values = {}
    for name, path in GRANT_EXAMPLES.items():
        value = load_json(path)
        validate_agent_registry_grant_semantics(value, str(path.relative_to(REPO_ROOT)))
        values[name] = value
        print(f"VALID grant semantics {path.relative_to(REPO_ROOT)}")
    return values


def validate_activation_matrix(policies: dict[str, dict], grants: dict[str, dict]) -> None:
    # Missing/denied policy or missing/revoked grant must fail closed.
    fail_closed_cases = [
        ("missing", "missing"),
        ("denied", "missing"),
        ("denied", "revoked"),
        ("allowed", "missing"),
        ("allowed", "revoked"),
    ]
    for policy_name, grant_name in fail_closed_cases:
        assert_activation_fails_closed(
            policies[policy_name],
            grants[grant_name],
            source=f"activation:{policy_name}:{grant_name}",
        )
        print(f"VALID activation fail-closed policy={policy_name} grant={grant_name}")

    # Current active grant + allowed policy is render-only in examples but semantically
    # activation-ready at the primitive gate level. Higher-level activation policy will
    # still restrict actual side effects by scope. This validates the primitive AND gate.
    assert_activation_ready(policies["allowed"], grants["active"], source="activation:allowed:active")
    print("VALID activation primitive-ready policy=allowed grant=active")


def main() -> int:
    policies = validate_policy_examples()
    grants = validate_grant_examples()
    validate_activation_matrix(policies, grants)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
