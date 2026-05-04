"""Activation decision evaluator for Agent Machine.

ActivationDecision is the final local decision artifact before an AgentPod can
be activated. It combines AgentPod intent, PolicyAdmission, AgentRegistryGrant,
DeploymentReceipt reference, and StorageReceipt references. It remains evidence
and control-plane evaluation, not runtime execution.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, schema_by_kind, validate_instance
from agent_machine.governance import (
    activation_ready,
    grant_allows_activation,
    policy_allows_activation,
    validate_agent_registry_grant_semantics,
    validate_policy_admission_semantics,
)

DEFAULT_DECIDED_AT = "1970-01-01T00:00:00Z"


def validate_activation_decision_payload(decision: dict[str, Any], root: Path | None = None) -> None:
    schema = schema_by_kind(root)["ActivationDecision"]
    # Validate in-memory payload through a temporary jsonschema path without writing a file.
    schema_payload = load_json(schema)
    try:
        from jsonschema.validators import validator_for
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: jsonschema. Install with `python -m pip install -r requirements-dev.txt`."
        ) from exc
    validator_cls = validator_for(schema_payload)
    validator_cls.check_schema(schema_payload)
    validator = validator_cls(schema_payload)
    errors = sorted(validator.iter_errors(decision), key=lambda err: list(err.path))
    if errors:
        rendered = []
        for err in errors:
            location = "/".join(str(part) for part in err.path) or "<root>"
            rendered.append(f"  - {location}: {err.message}")
        raise AssertionError("ActivationDecision failed schema validation:\n" + "\n".join(rendered))


def evaluate_activation(
    *,
    agentpod: dict[str, Any],
    policy: dict[str, Any],
    grant: dict[str, Any],
    deployment_receipt_id: str,
    storage_receipt_refs: list[str],
    decided_at: str,
    decision_id: str | None = None,
) -> dict[str, Any]:
    validate_policy_admission_semantics(policy, source="activation:policy")
    validate_agent_registry_grant_semantics(grant, source="activation:grant")

    agent_pod_id = str(agentpod.get("id"))
    agent_machine_id = policy.get("request", {}).get("agentMachineId") or grant.get("request", {}).get("agentMachineId")
    provider_id = policy.get("request", {}).get("providerId")
    policy_id = str(policy.get("id"))
    grant_id = str(grant.get("id"))
    runtime_mode = agentpod.get("runtime", {}).get("mode")

    failure_reasons: list[str] = []
    required_before_activation: list[str] = []

    if agentpod.get("kind") != "AgentPod":
        failure_reasons.append("agentpod_kind_invalid")
    if agentpod.get("workload", {}).get("agentIdentityRequired") is not True:
        failure_reasons.append("agent_identity_not_required_by_agentpod")
    if not policy_allows_activation(policy):
        failure_reasons.append("policy_does_not_allow_activation_scope")
        required_before_activation.append("policy_admission_allowed_activation")
    if not grant_allows_activation(grant, provider_id=provider_id):
        failure_reasons.append("agent_registry_grant_does_not_allow_activation_scope")
        required_before_activation.append("agent_registry_grant_active_activation")
    if not storage_receipt_refs:
        failure_reasons.append("storage_receipts_missing")
        required_before_activation.append("storage_receipts")
    if not deployment_receipt_id:
        failure_reasons.append("deployment_receipt_missing")
        required_before_activation.append("deployment_receipt")

    allowed = not failure_reasons and activation_ready(policy, grant)
    status = "allowed" if allowed else "fail-closed"
    reason = "activation allowed" if allowed else "activation failed closed"

    policy_allowed_scope = policy.get("scope", {}).get("allowed", {})
    grant_allowed_scope = grant.get("scope", {}).get("allowed", {})
    obligations = policy.get("obligations", {})
    grant_payload = grant.get("grant", {})
    policy_decision = policy.get("decision", {})

    return {
        "specVersion": "0.1.0",
        "id": decision_id or f"urn:srcos:agent-machine:activation-decision:{agent_pod_id.split(':')[-1]}",
        "kind": "ActivationDecision",
        "decision": {
            "status": status,
            "activationAllowed": allowed,
            "reason": reason,
            "failureReasons": sorted(set(failure_reasons)),
            "requiredBeforeActivation": sorted(set(required_before_activation)),
        },
        "inputs": {
            "agentPodId": agent_pod_id,
            "agentMachineId": agent_machine_id,
            "providerId": provider_id,
            "policyAdmissionId": policy_id,
            "agentRegistryGrantId": grant_id,
            "deploymentReceiptId": deployment_receipt_id,
            "storageReceiptRefs": storage_receipt_refs,
        },
        "scope": {
            "runtimeMode": runtime_mode,
            "networkExposure": policy_allowed_scope.get("networkExposure") or [],
            "sideEffects": policy_allowed_scope.get("sideEffects") or [],
            "toolRefs": grant_allowed_scope.get("toolRefs") or [],
            "storageScopeRefs": grant_allowed_scope.get("storageScopeRefs") or [],
            "cacheReuseAllowed": bool(policy_allowed_scope.get("cacheReuse")) and bool(grant_allowed_scope.get("cacheScopeRefs")),
        },
        "obligations": {
            "requiredReceipts": obligations.get("requiredReceipts") or [],
            "policyDecisionRef": policy_decision.get("decisionRef"),
            "agentRegistryGrantRef": grant_payload.get("grantRef"),
            "expiresAt": obligations.get("expiresAt") or grant_payload.get("expiresAt"),
            "revocationRefs": [
                ref for ref in [obligations.get("revocationRef"), grant_payload.get("revocationRef")] if ref
            ],
        },
        "receiptSafety": {
            "includeRawContent": False,
            "rawPromptContentIncluded": False,
            "rawKvCacheContentIncluded": False,
            "secretValuesIncluded": False,
            "privateMemoryIncluded": False,
        },
        "decidedAt": decided_at,
        "labels": {
            "sourceos.activation.prototype": "true",
            "sourceos.activation.allowed": str(allowed).lower(),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Agent Machine activation decision")
    parser.add_argument("agentpod_json", type=Path)
    parser.add_argument("policy_json", type=Path)
    parser.add_argument("grant_json", type=Path)
    parser.add_argument("--deployment-receipt-id", required=True)
    parser.add_argument("--storage-receipt-ref", action="append", default=[])
    parser.add_argument("--decided-at", default=DEFAULT_DECIDED_AT)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    decision = evaluate_activation(
        agentpod=load_json(args.agentpod_json),
        policy=load_json(args.policy_json),
        grant=load_json(args.grant_json),
        deployment_receipt_id=args.deployment_receipt_id,
        storage_receipt_refs=args.storage_receipt_ref,
        decided_at=args.decided_at,
    )
    validate_activation_decision_payload(decision)
    if args.pretty:
        print(json.dumps(decision, indent=2, sort_keys=True))
    else:
        print(json.dumps(decision, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
