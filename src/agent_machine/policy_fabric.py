"""Local Policy Fabric admission resolver for Agent Machine.

This module is a bootstrap stand-in for a real Policy Fabric client. It resolves
secret-free PolicyAdmission artifacts from explicit files or local stores and can
produce a fail-closed missing-admission stub when no policy decision is present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, schema_by_kind
from agent_machine.governance import validate_policy_admission_semantics

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


def validate_policy_admission_payload(policy: dict[str, Any], root: Path | None = None, source: str = "<policy>") -> None:
    validate_payload_against_kind(policy, "PolicyAdmission", root)
    validate_policy_admission_semantics(policy, source=source)


def iter_json_files(directory: Path) -> list[Path]:
    if not directory.exists():
        raise AssertionError(f"policy store directory does not exist: {directory}")
    if not directory.is_dir():
        raise AssertionError(f"policy store path is not a directory: {directory}")
    return sorted(path for path in directory.rglob("*.json") if path.is_file())


def load_policy_admissions(
    *,
    files: list[Path] | None = None,
    directories: list[Path] | None = None,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """Load PolicyAdmission objects from files and/or local store directories."""
    policies: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()

    for path in files or []:
        resolved = path.resolve()
        seen_paths.add(resolved)
        value = load_json(path)
        if not isinstance(value, dict):
            raise AssertionError(f"{path}: policy admission file root must be an object")
        if value.get("kind") != "PolicyAdmission":
            raise AssertionError(f"{path}: expected kind=PolicyAdmission")
        validate_policy_admission_payload(value, root, source=str(path))
        policies.append(value)

    for directory in directories or []:
        for path in iter_json_files(directory):
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            value = load_json(path)
            if isinstance(value, dict) and value.get("kind") == "PolicyAdmission":
                validate_policy_admission_payload(value, root, source=str(path))
                policies.append(value)
                seen_paths.add(resolved)

    policy_ids: dict[str, dict[str, Any]] = {}
    for policy in policies:
        policy_id = policy.get("id")
        if not isinstance(policy_id, str):
            raise AssertionError("PolicyAdmission loaded without string id")
        if policy_id in policy_ids:
            raise AssertionError(f"duplicate PolicyAdmission id loaded: {policy_id}")
        policy_ids[policy_id] = policy
    return policies


def request_matches(
    policy: dict[str, Any],
    *,
    agentpod_id: str,
    request_type: str,
    deployment_receipt_id: str,
    agent_machine_id: str | None = None,
    provider_id: str | None = None,
) -> bool:
    request = policy.get("request", {})
    if request.get("agentPodId") != agentpod_id:
        return False
    if request.get("requestType") != request_type:
        return False
    if request.get("deploymentReceiptId") != deployment_receipt_id:
        return False
    if agent_machine_id and request.get("agentMachineId") != agent_machine_id:
        return False
    if provider_id and request.get("providerId") != provider_id:
        return False
    return True


def missing_policy_admission_stub(
    *,
    agentpod_id: str,
    request_type: str,
    deployment_receipt_id: str,
    decided_at: str,
    agent_machine_id: str | None = None,
    provider_id: str | None = None,
) -> dict[str, Any]:
    suffix = agentpod_id.split(":")[-1]
    return {
        "specVersion": "0.1.0",
        "id": f"urn:srcos:agent-machine:policy-admission:missing-{suffix}-{request_type}",
        "kind": "PolicyAdmission",
        "request": {
            "requestId": f"urn:srcos:agent-machine:policy-request:missing-{suffix}-{request_type}",
            "requestType": request_type,
            "agentMachineId": agent_machine_id or "urn:srcos:agent-machine:unknown",
            "agentPodId": agentpod_id,
            "providerId": provider_id,
            "deploymentReceiptId": deployment_receipt_id,
            "planDigest": None,
            "manifestDigest": None,
        },
        "decision": {
            "status": "missing",
            "authorizationGranted": False,
            "decisionRef": None,
            "decisionDigest": None,
            "reason": "No matching PolicyAdmission was resolved; activation must fail closed.",
            "policyBundleRef": None,
            "policyBundleDigest": None,
        },
        "scope": {
            "allowed": {
                "networkExposure": [],
                "storageClasses": [],
                "volumeClasses": [],
                "providerIds": [],
                "cacheReuse": False,
                "sideEffects": [],
            },
            "denied": {
                "networkExposure": ["loopback", "host", "cluster", "ingress"],
                "storageClasses": ["filesystem", "local-lvm", "topolvm-k8s", "tmpfs", "object-store", "remote-volume"],
                "volumeClasses": ["agent-models", "agent-cache-hot", "agent-cache-warm", "agent-cache-cold", "agent-scratch", "agent-evidence", "agent-artifacts"],
                "providerIds": [provider_id] if provider_id else [],
                "cacheReuse": True,
                "sideEffects": ["start-provider", "mount-cache", "reuse-cache", "public-ingress"],
            },
        },
        "obligations": {
            "requiredReceipts": ["deployment", "storage", "runtime"],
            "expiresAt": None,
            "revocationRef": None,
            "constraints": ["fail-closed-until-policy-decision-present"],
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
            "sourceos.policy.resolver": "local-store",
            "sourceos.activation.fail-closed": "true",
        },
    }


def resolve_policy_admission(
    *,
    policies: list[dict[str, Any]],
    agentpod_id: str,
    request_type: str,
    deployment_receipt_id: str,
    agent_machine_id: str | None = None,
    provider_id: str | None = None,
    policy_id: str | None = None,
    expected_status: str | None = None,
    allow_missing_stub: bool = True,
    decided_at: str = DEFAULT_DECIDED_AT,
    root: Path | None = None,
) -> dict[str, Any]:
    """Resolve one PolicyAdmission or return a fail-closed missing stub.

    Ambiguity is a hard failure. A caller may disambiguate by policy_id or expected_status.
    """
    if policy_id:
        matches = [policy for policy in policies if policy.get("id") == policy_id]
    else:
        matches = [
            policy
            for policy in policies
            if request_matches(
                policy,
                agentpod_id=agentpod_id,
                request_type=request_type,
                deployment_receipt_id=deployment_receipt_id,
                agent_machine_id=agent_machine_id,
                provider_id=provider_id,
            )
        ]
        if expected_status:
            matches = [policy for policy in matches if policy.get("decision", {}).get("status") == expected_status]

    if len(matches) == 1:
        validate_policy_admission_payload(matches[0], root, source=str(matches[0].get("id")))
        return matches[0]
    if not matches:
        if not allow_missing_stub:
            raise AssertionError("no matching PolicyAdmission found")
        stub = missing_policy_admission_stub(
            agentpod_id=agentpod_id,
            request_type=request_type,
            deployment_receipt_id=deployment_receipt_id,
            agent_machine_id=agent_machine_id,
            provider_id=provider_id,
            decided_at=decided_at,
        )
        validate_policy_admission_payload(stub, root, source="missing-policy-stub")
        return stub

    ids = ", ".join(sorted(str(policy.get("id")) for policy in matches))
    raise AssertionError(f"ambiguous PolicyAdmission match; disambiguate with policy_id or expected_status: {ids}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve PolicyAdmission from local Policy Fabric files/stores")
    parser.add_argument("agentpod_json", type=Path)
    parser.add_argument("--policy-file", action="append", type=Path, default=[])
    parser.add_argument("--policy-dir", action="append", type=Path, default=[])
    parser.add_argument("--request-type", default="activation")
    parser.add_argument("--deployment-receipt-id", required=True)
    parser.add_argument("--agent-machine-id")
    parser.add_argument("--provider-id")
    parser.add_argument("--policy-id")
    parser.add_argument("--expected-status", choices=["missing", "allowed", "denied", "not-required", "unknown"])
    parser.add_argument("--no-missing-stub", action="store_true")
    parser.add_argument("--decided-at", default=DEFAULT_DECIDED_AT)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    agentpod = load_json(args.agentpod_json)
    if not isinstance(agentpod, dict) or agentpod.get("kind") != "AgentPod":
        raise AssertionError(f"{args.agentpod_json}: expected kind=AgentPod")
    policies = load_policy_admissions(files=args.policy_file, directories=args.policy_dir)
    policy = resolve_policy_admission(
        policies=policies,
        agentpod_id=str(agentpod.get("id")),
        request_type=args.request_type,
        deployment_receipt_id=args.deployment_receipt_id,
        agent_machine_id=args.agent_machine_id,
        provider_id=args.provider_id,
        policy_id=args.policy_id,
        expected_status=args.expected_status,
        allow_missing_stub=not args.no_missing_stub,
        decided_at=args.decided_at,
    )
    if args.pretty:
        print(json.dumps(policy, indent=2, sort_keys=True))
    else:
        print(json.dumps(policy, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
