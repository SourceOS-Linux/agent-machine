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

from agent_machine.contracts import load_json, schema_by_kind
from agent_machine.governance import (
    activation_ready,
    grant_allows_activation,
    policy_allows_activation,
    validate_agent_registry_grant_semantics,
    validate_policy_admission_semantics,
)

DEFAULT_DECIDED_AT = "1970-01-01T00:00:00Z"


def validate_payload_against_kind(value: dict[str, Any], kind: str, root: Path | None = None) -> None:
    schema_path = schema_by_kind(root)[kind]
    schema_payload = load_json(schema_path)
    try:
        from jsonschema.validators import validator_for
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: jsonschema. Install with `python -m pip install -r requirements-dev.txt`."
        ) from exc
    validator_cls = validator_for(schema_payload)
    validator_cls.check_schema(schema_payload)
    validator = validator_cls(schema_payload)
    errors = sorted(validator.iter_errors(value), key=lambda err: list(err.path))
    if errors:
        rendered = []
        for err in errors:
            location = "/".join(str(part) for part in err.path) or "<root>"
            rendered.append(f"  - {location}: {err.message}")
        raise AssertionError(f"{kind} failed schema validation:\n" + "\n".join(rendered))


def validate_activation_decision_payload(decision: dict[str, Any], root: Path | None = None) -> None:
    validate_payload_against_kind(decision, "ActivationDecision", root)


def validate_storage_receipt_payload(receipt: dict[str, Any], root: Path | None = None) -> None:
    validate_payload_against_kind(receipt, "StorageReceipt", root)
    safety = receipt.get("receiptSafety", {})
    for key in ["includeRawContent", "rawPromptContentIncluded", "rawKvCacheContentIncluded", "secretValuesIncluded"]:
        if safety.get(key) is not False:
            raise AssertionError(f"StorageReceipt {receipt.get('id')}: receiptSafety.{key} must be false")
    filesystem = receipt.get("filesystem", {})
    if filesystem.get("worldWritable") is not False:
        raise AssertionError(f"StorageReceipt {receipt.get('id')}: worldWritable must be false")
    if filesystem.get("symlinkTraversalObserved") is not False:
        raise AssertionError(f"StorageReceipt {receipt.get('id')}: symlinkTraversalObserved must be false")


def iter_json_files(directory: Path) -> list[Path]:
    if not directory.exists():
        raise AssertionError(f"storage receipt directory does not exist: {directory}")
    if not directory.is_dir():
        raise AssertionError(f"storage receipt path is not a directory: {directory}")
    return sorted(path for path in directory.rglob("*.json") if path.is_file())


def load_storage_receipts(
    *,
    files: list[Path] | None = None,
    directories: list[Path] | None = None,
) -> list[dict[str, Any]]:
    """Load StorageReceipt objects from explicit files and/or receipt directories."""
    receipts: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()

    for path in files or []:
        resolved = path.resolve()
        seen_paths.add(resolved)
        value = load_json(path)
        if not isinstance(value, dict):
            raise AssertionError(f"{path}: storage receipt file root must be an object")
        if value.get("kind") != "StorageReceipt":
            raise AssertionError(f"{path}: expected kind=StorageReceipt")
        receipts.append(value)

    for directory in directories or []:
        for path in iter_json_files(directory):
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            value = load_json(path)
            if isinstance(value, dict) and value.get("kind") == "StorageReceipt":
                receipts.append(value)
                seen_paths.add(resolved)

    receipt_ids: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        receipt_id = receipt.get("id")
        if not isinstance(receipt_id, str):
            raise AssertionError("StorageReceipt loaded without string id")
        if receipt_id in receipt_ids:
            raise AssertionError(f"duplicate StorageReceipt id loaded: {receipt_id}")
        receipt_ids[receipt_id] = receipt
    return receipts


def validate_storage_receipts(
    *,
    storage_receipt_refs: list[str],
    storage_receipts: list[dict[str, Any]] | None,
    root: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Validate storage receipt files and return (valid_refs, failure_reasons)."""
    requested_refs = sorted(set(storage_receipt_refs))
    if not requested_refs:
        return [], ["storage_receipts_missing"]
    if storage_receipts is None:
        return requested_refs, ["storage_receipt_files_missing"]

    seen: set[str] = set()
    failures: list[str] = []
    for receipt in storage_receipts:
        try:
            validate_storage_receipt_payload(receipt, root)
        except AssertionError as exc:
            failures.append(f"storage_receipt_invalid:{receipt.get('id', 'unknown')}:{exc}")
            continue
        receipt_id = receipt.get("id")
        if not isinstance(receipt_id, str):
            failures.append("storage_receipt_id_missing")
            continue
        seen.add(receipt_id)
        encryption = receipt.get("encryption", {})
        if encryption.get("required") is True and encryption.get("observed") is not True:
            failures.append(f"storage_receipt_encryption_required_not_observed:{receipt_id}")
        quota = receipt.get("quota", {})
        if quota.get("required") is True and quota.get("observed") is not True:
            failures.append(f"storage_receipt_quota_required_not_observed:{receipt_id}")

    missing = sorted(set(requested_refs) - seen)
    for missing_ref in missing:
        failures.append(f"storage_receipt_ref_unresolved:{missing_ref}")
    return requested_refs, sorted(set(failures))


def sorted_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return sorted(value, key=lambda item: json.dumps(item, sort_keys=True))


def evaluate_activation(
    *,
    agentpod: dict[str, Any],
    policy: dict[str, Any],
    grant: dict[str, Any],
    deployment_receipt_id: str,
    storage_receipt_refs: list[str],
    decided_at: str,
    decision_id: str | None = None,
    storage_receipts: list[dict[str, Any]] | None = None,
    root: Path | None = None,
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

    resolved_storage_refs, storage_failures = validate_storage_receipts(
        storage_receipt_refs=storage_receipt_refs,
        storage_receipts=storage_receipts,
        root=root,
    )
    failure_reasons.extend(storage_failures)
    if storage_failures:
        required_before_activation.append("valid_storage_receipts")

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
            "storageReceiptRefs": resolved_storage_refs,
        },
        "scope": {
            "runtimeMode": runtime_mode,
            "networkExposure": sorted_list(policy_allowed_scope.get("networkExposure")),
            "sideEffects": sorted_list(policy_allowed_scope.get("sideEffects")),
            "toolRefs": sorted_list(grant_allowed_scope.get("toolRefs")),
            "storageScopeRefs": sorted_list(grant_allowed_scope.get("storageScopeRefs")),
            "cacheReuseAllowed": bool(policy_allowed_scope.get("cacheReuse")) and bool(grant_allowed_scope.get("cacheScopeRefs")),
        },
        "obligations": {
            "requiredReceipts": sorted_list(obligations.get("requiredReceipts")),
            "policyDecisionRef": policy_decision.get("decisionRef"),
            "agentRegistryGrantRef": grant_payload.get("grantRef"),
            "expiresAt": obligations.get("expiresAt") or grant_payload.get("expiresAt"),
            "revocationRefs": sorted(ref for ref in [obligations.get("revocationRef"), grant_payload.get("revocationRef")] if ref),
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
            "sourceos.activation.fail-closed": str(not allowed).lower(),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Agent Machine activation decision")
    parser.add_argument("agentpod_json", type=Path)
    parser.add_argument("policy_json", type=Path)
    parser.add_argument("grant_json", type=Path)
    parser.add_argument("--deployment-receipt-id", required=True)
    parser.add_argument("--storage-receipt-ref", action="append", default=[])
    parser.add_argument("--storage-receipt-file", action="append", type=Path, default=[])
    parser.add_argument("--storage-receipt-dir", action="append", type=Path, default=[])
    parser.add_argument("--decided-at", default=DEFAULT_DECIDED_AT)
    parser.add_argument("--decision-id")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    storage_receipts = load_storage_receipts(files=args.storage_receipt_file, directories=args.storage_receipt_dir)
    if not args.storage_receipt_ref and storage_receipts:
        args.storage_receipt_ref = [str(receipt.get("id")) for receipt in storage_receipts]
    decision = evaluate_activation(
        agentpod=load_json(args.agentpod_json),
        policy=load_json(args.policy_json),
        grant=load_json(args.grant_json),
        deployment_receipt_id=args.deployment_receipt_id,
        storage_receipt_refs=args.storage_receipt_ref,
        storage_receipts=storage_receipts if storage_receipts else None,
        decided_at=args.decided_at,
        decision_id=args.decision_id,
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
