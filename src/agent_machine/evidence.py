"""Runtime evidence helpers for Agent Machine.

These helpers intentionally generate and validate secret-free evidence stubs.
They do not submit evidence to AgentPlane yet and do not authorize execution.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, schema_by_kind, validate_instance

DEFAULT_RUNTIME_VERSION = "0.1.0-dev"
DEFAULT_PROBE_VERSION = "0.1.0-dev"


def evidence_schema_path(root: Path | None = None) -> Path:
    return schema_by_kind(root)["AgentPlaneRuntimeEvidence"]


def validate_runtime_evidence(path: Path, root: Path | None = None) -> None:
    """Validate an AgentPlaneRuntimeEvidence JSON file against its schema."""
    validate_instance(path, evidence_schema_path(root))


def assert_secret_free(evidence: dict[str, Any]) -> None:
    """Enforce the secret-free evidence safety invariants."""
    safety = evidence.get("receiptSafety")
    if not isinstance(safety, dict):
        raise AssertionError("receiptSafety must be present and must be an object")
    required_false = [
        "includeRawContent",
        "rawPromptContentIncluded",
        "rawKvCacheContentIncluded",
        "secretValuesIncluded",
        "privateMemoryIncluded",
    ]
    for key in required_false:
        if safety.get(key) is not False:
            raise AssertionError(f"receiptSafety.{key} must be false")


def assert_fail_closed_when_required(evidence: dict[str, Any]) -> None:
    """Ensure required policy/registry gates do not look active when missing."""
    policy = evidence.get("policyFabric", {})
    registry = evidence.get("agentRegistry", {})
    runtime = evidence.get("runtime", {})

    policy_required = policy.get("required") is True
    registry_required = registry.get("required") is True
    policy_missing = policy.get("admissionStatus") == "missing"
    registry_missing = registry.get("grantStatus") == "missing"

    if (policy_required and policy_missing) or (registry_required and registry_missing):
        status = runtime.get("status")
        if status in {"running", "completed"}:
            raise AssertionError(
                "runtime.status cannot be running/completed when required policy or registry gates are missing"
            )


def validate_runtime_evidence_payload(evidence: dict[str, Any], root: Path | None = None) -> None:
    """Validate runtime evidence payload content and schema by writing through schema validator logic."""
    assert_secret_free(evidence)
    assert_fail_closed_when_required(evidence)

    # Use jsonschema directly on the in-memory object without forcing callers to write temp files.
    schema = load_json(evidence_schema_path(root))
    try:
        from jsonschema.validators import validator_for
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: jsonschema. Install with `python -m pip install -r requirements-dev.txt`."
        ) from exc
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(evidence), key=lambda err: list(err.path))
    if errors:
        rendered = []
        for err in errors:
            location = "/".join(str(part) for part in err.path) or "<root>"
            rendered.append(f"  - {location}: {err.message}")
        raise AssertionError("AgentPlaneRuntimeEvidence failed schema validation:\n" + "\n".join(rendered))


def render_activation_missing_gates_stub(
    *,
    evidence_id: str,
    agent_machine_id: str,
    agent_pod_id: str,
    provider_id: str,
    deployment_receipt_id: str,
    storage_receipt_refs: list[str],
    observed_at: str,
    node_name: str | None = None,
    namespace: str | None = None,
    service_account_name: str | None = None,
) -> dict[str, Any]:
    """Render a fail-closed activation evidence stub for missing policy/registry gates."""
    return {
        "specVersion": "0.1.0",
        "id": evidence_id,
        "kind": "AgentPlaneRuntimeEvidence",
        "evidenceType": "activation",
        "agentMachineId": agent_machine_id,
        "agentPodId": agent_pod_id,
        "providerId": provider_id,
        "deploymentReceiptId": deployment_receipt_id,
        "policyFabric": {
            "required": True,
            "decisionRef": None,
            "decisionDigest": None,
            "admissionStatus": "missing",
            "obligationsRef": None,
            "expiresAt": None,
        },
        "agentRegistry": {
            "required": True,
            "grantRef": None,
            "grantDigest": None,
            "grantStatus": "missing",
            "revocationRef": None,
            "expiresAt": None,
        },
        "artifacts": {
            "imageRef": None,
            "imageDigest": None,
            "modelDigest": None,
            "tokenizerDigest": None,
            "manifestDigest": None,
            "sbomRef": None,
            "provenanceRef": None,
        },
        "storageReceiptRefs": storage_receipt_refs,
        "cache": {
            "cacheReuseRequested": False,
            "cacheReuseAllowed": False,
            "cachePolicyRef": None,
            "cacheReceiptRefs": [],
            "cacheReuseDecisionRef": None,
        },
        "runtime": {
            "status": "activating",
            "runtimeVersion": DEFAULT_RUNTIME_VERSION,
            "probeVersion": DEFAULT_PROBE_VERSION,
            "nodeName": node_name,
            "namespace": namespace,
            "serviceAccountName": service_account_name,
            "pid": None,
            "containerIdDigest": None,
            "startedAt": observed_at,
            "completedAt": None,
            "failureReason": "policy_fabric_admission_missing_and_agent_registry_grant_missing",
        },
        "receiptSafety": {
            "includeRawContent": False,
            "rawPromptContentIncluded": False,
            "rawKvCacheContentIncluded": False,
            "secretValuesIncluded": False,
            "privateMemoryIncluded": False,
        },
        "observedAt": observed_at,
        "labels": {
            "sourceos.evidence.prototype": "true",
            "sourceos.activation.fail-closed": "true",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate or render AgentPlane runtime evidence stubs")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="Validate an AgentPlaneRuntimeEvidence file")
    validate.add_argument("evidence_json", type=Path)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "validate":
        evidence = load_json(args.evidence_json)
        validate_runtime_evidence_payload(evidence)
        print(f"VALID runtime evidence {args.evidence_json}")
        return 0
    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
