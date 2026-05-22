"""Local Agent Registry grant resolver for Agent Machine.

This module is a bootstrap stand-in for a real Agent Registry client. It resolves
secret-free AgentRegistryGrant artifacts from explicit files or local stores and
can produce a fail-closed missing-grant stub when no grant is present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, schema_by_kind
from agent_machine.governance import GRANT_SCOPE_KEYS, validate_agent_registry_grant_semantics

DEFAULT_ISSUED_AT = "1970-01-01T00:00:00Z"
EMPTY_SCOPE = {
    "providerIds": [],
    "modelRefs": [],
    "toolRefs": [],
    "cacheScopeRefs": [],
    "memoryScopeRefs": [],
    "storageScopeRefs": [],
    "evidenceScopeRefs": [],
}


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


def validate_agent_registry_grant_payload(grant: dict[str, Any], root: Path | None = None, source: str = "<grant>") -> None:
    validate_payload_against_kind(grant, "AgentRegistryGrant", root)
    validate_agent_registry_grant_semantics(grant, source=source)


def iter_json_files(directory: Path) -> list[Path]:
    if not directory.exists():
        raise AssertionError(f"grant store directory does not exist: {directory}")
    if not directory.is_dir():
        raise AssertionError(f"grant store path is not a directory: {directory}")
    return sorted(path for path in directory.rglob("*.json") if path.is_file())


def load_agent_registry_grants(
    *,
    files: list[Path] | None = None,
    directories: list[Path] | None = None,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """Load AgentRegistryGrant objects from files and/or local store directories."""
    grants: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()

    for path in files or []:
        resolved = path.resolve()
        seen_paths.add(resolved)
        value = load_json(path)
        if not isinstance(value, dict):
            raise AssertionError(f"{path}: agent registry grant file root must be an object")
        if value.get("kind") != "AgentRegistryGrant":
            raise AssertionError(f"{path}: expected kind=AgentRegistryGrant")
        validate_agent_registry_grant_payload(value, root, source=str(path))
        grants.append(value)

    for directory in directories or []:
        for path in iter_json_files(directory):
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            value = load_json(path)
            if isinstance(value, dict) and value.get("kind") == "AgentRegistryGrant":
                validate_agent_registry_grant_payload(value, root, source=str(path))
                grants.append(value)
                seen_paths.add(resolved)

    grant_ids: dict[str, dict[str, Any]] = {}
    for grant in grants:
        grant_id = grant.get("id")
        if not isinstance(grant_id, str):
            raise AssertionError("AgentRegistryGrant loaded without string id")
        if grant_id in grant_ids:
            raise AssertionError(f"duplicate AgentRegistryGrant id loaded: {grant_id}")
        grant_ids[grant_id] = grant
    return grants


def request_matches(
    grant: dict[str, Any],
    *,
    agentpod_id: str,
    requested_agent_identity_ref: str,
    session_ref: str,
    agent_machine_id: str | None = None,
    workroom_ref: str | None = None,
    topic_ref: str | None = None,
) -> bool:
    request = grant.get("request", {})
    if request.get("agentPodId") != agentpod_id:
        return False
    if request.get("requestedAgentIdentityRef") != requested_agent_identity_ref:
        return False
    if request.get("sessionRef") != session_ref:
        return False
    if agent_machine_id and request.get("agentMachineId") != agent_machine_id:
        return False
    if workroom_ref and request.get("workroomRef") != workroom_ref:
        return False
    if topic_ref and request.get("topicRef") != topic_ref:
        return False
    return True


def requested_scope_from_inputs(
    *,
    provider_id: str | None = None,
    model_ref: str | None = None,
    tool_refs: list[str] | None = None,
    storage_scope_ref: str | None = None,
    evidence_scope_ref: str | None = None,
) -> dict[str, list[str]]:
    scope = {key: [] for key in GRANT_SCOPE_KEYS}
    if provider_id:
        scope["providerIds"].append(provider_id)
    if model_ref:
        scope["modelRefs"].append(model_ref)
    for tool_ref in tool_refs or []:
        if tool_ref not in scope["toolRefs"]:
            scope["toolRefs"].append(tool_ref)
    if storage_scope_ref:
        scope["storageScopeRefs"].append(storage_scope_ref)
    if evidence_scope_ref:
        scope["evidenceScopeRefs"].append(evidence_scope_ref)
    return scope


def missing_agent_registry_grant_stub(
    *,
    agentpod_id: str,
    requested_agent_identity_ref: str,
    session_ref: str,
    issued_at: str,
    agent_machine_id: str | None = None,
    workroom_ref: str | None = None,
    topic_ref: str | None = None,
    requested_scope: dict[str, list[str]] | None = None,
    requested_expires_at: str | None = None,
) -> dict[str, Any]:
    suffix = agentpod_id.split(":")[-1]
    scope = {key: list((requested_scope or EMPTY_SCOPE).get(key) or []) for key in GRANT_SCOPE_KEYS}
    return {
        "specVersion": "0.1.0",
        "id": f"urn:srcos:agent-machine:agent-registry-grant:missing-{suffix}",
        "kind": "AgentRegistryGrant",
        "request": {
            "requestId": f"urn:srcos:agent-machine:grant-request:missing-{suffix}",
            "agentMachineId": agent_machine_id,
            "agentPodId": agentpod_id,
            "requestedAgentIdentityRef": requested_agent_identity_ref,
            "sessionRef": session_ref,
            "workroomRef": workroom_ref,
            "topicRef": topic_ref,
            "requestedScope": scope,
            "requestedExpiresAt": requested_expires_at,
        },
        "grant": {
            "status": "missing",
            "authorizationGranted": False,
            "grantRef": None,
            "grantDigest": None,
            "reason": "No matching AgentRegistryGrant was resolved; activation must fail closed.",
            "expiresAt": None,
            "revocationStatus": "unavailable",
            "revocationRef": None,
            "revocationHookRef": None,
            "externalTrustSignals": [],
        },
        "scope": {
            "allowed": {key: [] for key in GRANT_SCOPE_KEYS},
            "denied": scope,
        },
        "receiptSafety": {
            "includeRawContent": False,
            "rawPromptContentIncluded": False,
            "rawKvCacheContentIncluded": False,
            "secretValuesIncluded": False,
            "privateMemoryIncluded": False,
        },
        "issuedAt": issued_at,
        "labels": {
            "sourceos.registry.resolver": "local-store",
            "sourceos.activation.fail-closed": "true",
        },
    }


def resolve_agent_registry_grant(
    *,
    grants: list[dict[str, Any]],
    agentpod_id: str,
    requested_agent_identity_ref: str,
    session_ref: str,
    agent_machine_id: str | None = None,
    workroom_ref: str | None = None,
    topic_ref: str | None = None,
    grant_id: str | None = None,
    expected_status: str | None = None,
    allow_missing_stub: bool = True,
    issued_at: str = DEFAULT_ISSUED_AT,
    requested_scope: dict[str, list[str]] | None = None,
    requested_expires_at: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Resolve one AgentRegistryGrant or return a fail-closed missing stub.

    Ambiguity is a hard failure. A caller may disambiguate by grant_id or expected_status.
    """
    if grant_id:
        matches = [grant for grant in grants if grant.get("id") == grant_id]
    else:
        matches = [
            grant
            for grant in grants
            if request_matches(
                grant,
                agentpod_id=agentpod_id,
                requested_agent_identity_ref=requested_agent_identity_ref,
                session_ref=session_ref,
                agent_machine_id=agent_machine_id,
                workroom_ref=workroom_ref,
                topic_ref=topic_ref,
            )
        ]
        if expected_status:
            matches = [grant for grant in matches if grant.get("grant", {}).get("status") == expected_status]

    if len(matches) == 1:
        validate_agent_registry_grant_payload(matches[0], root, source=str(matches[0].get("id")))
        return matches[0]
    if not matches:
        if not allow_missing_stub:
            raise AssertionError("no matching AgentRegistryGrant found")
        stub = missing_agent_registry_grant_stub(
            agentpod_id=agentpod_id,
            requested_agent_identity_ref=requested_agent_identity_ref,
            session_ref=session_ref,
            agent_machine_id=agent_machine_id,
            workroom_ref=workroom_ref,
            topic_ref=topic_ref,
            requested_scope=requested_scope,
            requested_expires_at=requested_expires_at,
            issued_at=issued_at,
        )
        validate_agent_registry_grant_payload(stub, root, source="missing-grant-stub")
        return stub

    ids = ", ".join(sorted(str(grant.get("id")) for grant in matches))
    raise AssertionError(f"ambiguous AgentRegistryGrant match; disambiguate with grant_id or expected_status: {ids}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve AgentRegistryGrant from local Agent Registry files/stores")
    parser.add_argument("agentpod_json", type=Path)
    parser.add_argument("--grant-file", action="append", type=Path, default=[])
    parser.add_argument("--grant-dir", action="append", type=Path, default=[])
    parser.add_argument("--requested-agent-identity-ref", required=True)
    parser.add_argument("--session-ref", required=True)
    parser.add_argument("--agent-machine-id")
    parser.add_argument("--workroom-ref")
    parser.add_argument("--topic-ref")
    parser.add_argument("--grant-id")
    parser.add_argument("--expected-status", choices=["missing", "active", "expired", "revoked", "denied", "unknown"])
    parser.add_argument("--no-missing-stub", action="store_true")
    parser.add_argument("--provider-id")
    parser.add_argument("--model-ref")
    parser.add_argument("--tool-ref", action="append", default=[])
    parser.add_argument("--storage-scope-ref")
    parser.add_argument("--evidence-scope-ref")
    parser.add_argument("--requested-expires-at")
    parser.add_argument("--issued-at", default=DEFAULT_ISSUED_AT)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    agentpod = load_json(args.agentpod_json)
    if not isinstance(agentpod, dict) or agentpod.get("kind") != "AgentPod":
        raise AssertionError(f"{args.agentpod_json}: expected kind=AgentPod")
    grants = load_agent_registry_grants(files=args.grant_file, directories=args.grant_dir)
    grant = resolve_agent_registry_grant(
        grants=grants,
        agentpod_id=str(agentpod.get("id")),
        requested_agent_identity_ref=args.requested_agent_identity_ref,
        session_ref=args.session_ref,
        agent_machine_id=args.agent_machine_id,
        workroom_ref=args.workroom_ref,
        topic_ref=args.topic_ref,
        grant_id=args.grant_id,
        expected_status=args.expected_status,
        allow_missing_stub=not args.no_missing_stub,
        requested_scope=requested_scope_from_inputs(
            provider_id=args.provider_id,
            model_ref=args.model_ref,
            tool_refs=args.tool_ref,
            storage_scope_ref=args.storage_scope_ref,
            evidence_scope_ref=args.evidence_scope_ref,
        ),
        requested_expires_at=args.requested_expires_at,
        issued_at=args.issued_at,
    )
    if args.pretty:
        print(json.dumps(grant, indent=2, sort_keys=True))
    else:
        print(json.dumps(grant, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
