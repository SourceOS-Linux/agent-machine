"""Governance semantic validators for Agent Machine.

JSON Schema validates structure. This module validates cross-field semantics for
PolicyAdmission, AgentRegistryGrant, and activation readiness. These checks are
release-gate material: they prevent contradictory artifacts from looking valid.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, schema_by_kind, validate_instance

POLICY_ALLOWED_STATUSES = {"allowed", "not-required"}
POLICY_DENIED_STATUSES = {"missing", "denied", "unknown"}
GRANT_ACTIVE_STATUSES = {"active", "not-required"}
GRANT_INACTIVE_STATUSES = {"missing", "expired", "revoked", "denied", "unknown"}
ACTIVATION_SIDE_EFFECTS = {"start-provider", "mount-cache"}
ACTIVATION_TOOL_REFS = {"urn:srcos:tool:start-provider", "urn:srcos:tool:mount-cache"}


def validate_policy_admission_schema(path: Path, root: Path | None = None) -> dict[str, Any]:
    validate_instance(path, schema_by_kind(root)["PolicyAdmission"])
    value = load_json(path)
    if not isinstance(value, dict):
        raise AssertionError(f"{path}: PolicyAdmission root must be an object")
    return value


def validate_agent_registry_grant_schema(path: Path, root: Path | None = None) -> dict[str, Any]:
    validate_instance(path, schema_by_kind(root)["AgentRegistryGrant"])
    value = load_json(path)
    if not isinstance(value, dict):
        raise AssertionError(f"{path}: AgentRegistryGrant root must be an object")
    return value


def validate_policy_admission_semantics(policy: dict[str, Any], source: str = "<policy>") -> None:
    decision = policy.get("decision")
    scope = policy.get("scope")
    obligations = policy.get("obligations")
    safety = policy.get("receiptSafety")

    if not isinstance(decision, dict):
        raise AssertionError(f"{source}: decision must be an object")
    if not isinstance(scope, dict):
        raise AssertionError(f"{source}: scope must be an object")
    if not isinstance(obligations, dict):
        raise AssertionError(f"{source}: obligations must be an object")
    if not isinstance(safety, dict):
        raise AssertionError(f"{source}: receiptSafety must be an object")

    status = decision.get("status")
    granted = decision.get("authorizationGranted")

    if status == "allowed" and granted is not True:
        raise AssertionError(f"{source}: decision.status=allowed requires authorizationGranted=true")
    if status in {"missing", "denied", "unknown"} and granted is not False:
        raise AssertionError(f"{source}: decision.status={status} requires authorizationGranted=false")
    if status == "not-required" and granted is not True:
        raise AssertionError(f"{source}: decision.status=not-required requires authorizationGranted=true for this stub")

    decision_ref = decision.get("decisionRef")
    decision_digest = decision.get("decisionDigest")
    if status in {"allowed", "denied"}:
        if not decision_ref:
            raise AssertionError(f"{source}: decision.status={status} requires decisionRef")
        if not decision_digest:
            raise AssertionError(f"{source}: decision.status={status} requires decisionDigest")
    if status == "missing":
        if decision_ref is not None or decision_digest is not None:
            raise AssertionError(f"{source}: missing policy decision must not carry decisionRef or decisionDigest")

    allowed = scope.get("allowed")
    denied = scope.get("denied")
    if not isinstance(allowed, dict) or not isinstance(denied, dict):
        raise AssertionError(f"{source}: scope.allowed and scope.denied must be objects")

    if granted is False:
        if status == "missing":
            for key, value in allowed.items():
                if value not in (False, [], None):
                    raise AssertionError(f"{source}: missing policy admission cannot allow scope {key}={value!r}")

    if status == "allowed":
        required_receipts = obligations.get("requiredReceipts")
        if not isinstance(required_receipts, list) or not required_receipts:
            raise AssertionError(f"{source}: allowed policy admission requires at least one required receipt")

    _assert_secret_free_safety(safety, source)


def validate_agent_registry_grant_semantics(grant_doc: dict[str, Any], source: str = "<grant>") -> None:
    grant = grant_doc.get("grant")
    scope = grant_doc.get("scope")
    safety = grant_doc.get("receiptSafety")

    if not isinstance(grant, dict):
        raise AssertionError(f"{source}: grant must be an object")
    if not isinstance(scope, dict):
        raise AssertionError(f"{source}: scope must be an object")
    if not isinstance(safety, dict):
        raise AssertionError(f"{source}: receiptSafety must be an object")

    status = grant.get("status")
    granted = grant.get("authorizationGranted")

    if status == "active" and granted is not True:
        raise AssertionError(f"{source}: grant.status=active requires authorizationGranted=true")
    if status in {"missing", "expired", "revoked", "denied", "unknown"} and granted is not False:
        raise AssertionError(f"{source}: grant.status={status} requires authorizationGranted=false")

    grant_ref = grant.get("grantRef")
    grant_digest = grant.get("grantDigest")
    if status == "active":
        if not grant_ref:
            raise AssertionError(f"{source}: active grant requires grantRef")
        if not grant_digest:
            raise AssertionError(f"{source}: active grant requires grantDigest")
    if status == "missing":
        if grant_ref is not None or grant_digest is not None:
            raise AssertionError(f"{source}: missing grant must not carry grantRef or grantDigest")
    if status in {"revoked", "expired"} and not grant_ref:
        raise AssertionError(f"{source}: {status} grant should identify the stale grantRef")

    allowed = scope.get("allowed")
    denied = scope.get("denied")
    if not isinstance(allowed, dict) or not isinstance(denied, dict):
        raise AssertionError(f"{source}: scope.allowed and scope.denied must be objects")

    if status == "missing":
        for key, value in allowed.items():
            if value not in (False, [], None):
                raise AssertionError(f"{source}: missing grant cannot allow scope {key}={value!r}")
    if status == "active":
        if not any(value for value in allowed.values()):
            raise AssertionError(f"{source}: active grant should allow at least one explicit scope")

    _assert_secret_free_safety(safety, source)


def policy_allows_activation(policy: dict[str, Any]) -> bool:
    decision = policy.get("decision", {})
    if decision.get("status") != "allowed" or decision.get("authorizationGranted") is not True:
        return False
    request = policy.get("request", {})
    if request.get("requestType") != "activation":
        return False
    allowed = policy.get("scope", {}).get("allowed", {})
    side_effects = set(allowed.get("sideEffects") or [])
    provider_ids = set(allowed.get("providerIds") or [])
    provider_id = request.get("providerId")
    if not ACTIVATION_SIDE_EFFECTS.issubset(side_effects):
        return False
    if provider_id and provider_id not in provider_ids:
        return False
    return True


def grant_allows_activation(grant_doc: dict[str, Any], provider_id: str | None = None) -> bool:
    grant = grant_doc.get("grant", {})
    if grant.get("status") != "active" or grant.get("authorizationGranted") is not True:
        return False
    allowed = grant_doc.get("scope", {}).get("allowed", {})
    tool_refs = set(allowed.get("toolRefs") or [])
    provider_ids = set(allowed.get("providerIds") or [])
    if not ACTIVATION_TOOL_REFS.issubset(tool_refs):
        return False
    if provider_id and provider_id not in provider_ids:
        return False
    return True


def activation_ready(policy: dict[str, Any], grant: dict[str, Any]) -> bool:
    """Return true only when policy+grant authorize the activation operation, not merely render-only work."""
    provider_id = policy.get("request", {}).get("providerId")
    return policy_allows_activation(policy) and grant_allows_activation(grant, provider_id=provider_id)


def assert_activation_ready(policy: dict[str, Any], grant: dict[str, Any], source: str = "<activation>") -> None:
    validate_policy_admission_semantics(policy, source=f"{source}:policy")
    validate_agent_registry_grant_semantics(grant, source=f"{source}:grant")
    if not activation_ready(policy, grant):
        raise AssertionError(f"{source}: activation is not allowed without activation-scoped PolicyAdmission and AgentRegistryGrant")


def assert_activation_fails_closed(policy: dict[str, Any], grant: dict[str, Any], source: str = "<activation>") -> None:
    validate_policy_admission_semantics(policy, source=f"{source}:policy")
    validate_agent_registry_grant_semantics(grant, source=f"{source}:grant")
    if activation_ready(policy, grant):
        raise AssertionError(f"{source}: expected fail-closed state but policy+grant are activation-ready")


def _assert_secret_free_safety(safety: dict[str, Any], source: str) -> None:
    required_false = [
        "includeRawContent",
        "rawPromptContentIncluded",
        "rawKvCacheContentIncluded",
        "secretValuesIncluded",
        "privateMemoryIncluded",
    ]
    for key in required_false:
        if safety.get(key) is not False:
            raise AssertionError(f"{source}: receiptSafety.{key} must be false")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate governance semantics")
    subcommands = parser.add_subparsers(dest="command", required=True)

    policy = subcommands.add_parser("policy", help="Validate a PolicyAdmission file")
    policy.add_argument("policy_json", type=Path)

    grant = subcommands.add_parser("grant", help="Validate an AgentRegistryGrant file")
    grant.add_argument("grant_json", type=Path)

    activation = subcommands.add_parser("activation", help="Validate activation readiness/fail-closed semantics")
    activation.add_argument("policy_json", type=Path)
    activation.add_argument("grant_json", type=Path)
    activation.add_argument("--expect", choices=["ready", "fail-closed"], required=True)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "policy":
        policy = validate_policy_admission_schema(args.policy_json)
        validate_policy_admission_semantics(policy, str(args.policy_json))
        print(f"VALID policy admission {args.policy_json}")
        return 0
    if args.command == "grant":
        grant = validate_agent_registry_grant_schema(args.grant_json)
        validate_agent_registry_grant_semantics(grant, str(args.grant_json))
        print(f"VALID agent registry grant {args.grant_json}")
        return 0
    if args.command == "activation":
        policy = validate_policy_admission_schema(args.policy_json)
        grant = validate_agent_registry_grant_schema(args.grant_json)
        if args.expect == "ready":
            assert_activation_ready(policy, grant)
        else:
            assert_activation_fails_closed(policy, grant)
        print(f"VALID activation {args.expect} {args.policy_json} {args.grant_json}")
        return 0
    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
