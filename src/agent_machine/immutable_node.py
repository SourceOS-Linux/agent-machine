"""Functional immutable-node profile planning and guarded apply helpers.

This module consumes SourceOS immutable-node projection fixtures and supports a
real staged host mutation path. Mutation is denied by default and requires both
`--execute` and `--policy-ok` in the CLI wrapper.

Initial supported mutation classes:
- state-roots: create declared /var/lib or /var/cache state roots.
- staging-artifacts: write plan/evidence artifacts under Agent Machine state.

The module intentionally does not start services, pull images, enroll Socios,
change boot entries, or run systemctl in this first tranche.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json

GENERATOR_VERSION = "0.1.0"
PLAN_SPEC_VERSION = "0.1.0"
EVIDENCE_SPEC_VERSION = "0.1.0"
VALID_PROFILE_PLANES = {"node-substrate", "agent-runtime-substrate"}
VALID_STATE_ROOT_PREFIXES = ("/var/lib/", "/var/cache/")
FORBIDDEN_STATE_ROOT_PREFIXES = ("/etc", "/usr")
SUPPORTED_MUTATION_CLASSES = {"state-roots", "staging-artifacts"}
DEFAULT_STAGING_ROOT = "/var/lib/agent-machine/immutable-node"


@dataclass(frozen=True)
class ApplyOptions:
    target_root: Path
    execute: bool
    policy_ok: bool
    mutation_classes: tuple[str, ...]
    evidence_out: Path | None = None


class ProjectionIndex(dict[str, dict[str, Any]]):
    """Simple id-keyed projection index."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def slug_from_urn(value: str) -> str:
    tail = value.rsplit(":", 1)[-1]
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", tail).strip("-") or "immutable-node"


def under_target_root(target_root: Path, absolute_path: str) -> Path:
    if not absolute_path.startswith("/"):
        raise AssertionError(f"expected absolute path, got {absolute_path!r}")
    return target_root / absolute_path.lstrip("/")


def ensure_safe_target_root(target_root: Path, execute: bool) -> None:
    if execute and target_root == Path("/") and hasattr(os, "geteuid") and os.geteuid() != 0:
        raise AssertionError("applying to / requires root privileges")


def require_object(path: Path, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssertionError(f"{path}: root must be a JSON object")
    return value


def load_projection_index(fixtures_dir: Path) -> ProjectionIndex:
    if not fixtures_dir.exists():
        raise AssertionError(f"fixtures directory does not exist: {fixtures_dir}")
    index: ProjectionIndex = ProjectionIndex()
    for path in sorted(fixtures_dir.glob("*.json")):
        data = require_object(path, load_json(path))
        identifier = data.get("id")
        if not isinstance(identifier, str) or not identifier.startswith("urn:srcos:"):
            raise AssertionError(f"{path}: id must be a urn:srcos string")
        if identifier in index:
            raise AssertionError(f"duplicate projection id: {identifier}")
        index[identifier] = data
    return index


def validate_host_capability(capability: dict[str, Any]) -> None:
    if capability.get("type") != "HostCapabilityPlacement":
        raise AssertionError(f"{capability.get('id')}: expected HostCapabilityPlacement")
    if capability.get("mandatoryForBaseNode") is True and capability.get("requiresEnrollment") is True:
        raise AssertionError(f"{capability.get('id')}: mandatory base node capability must not require enrollment")
    if capability.get("mandatoryForBaseNode") is True and capability.get("primaryPlane") == "desktop-consumer":
        raise AssertionError(f"{capability.get('id')}: desktop cannot own mandatory base node capability")
    if capability.get("authority") == "socios-optional-pack" and capability.get("mandatoryForBaseNode") is True:
        raise AssertionError(f"{capability.get('id')}: Socios optional pack cannot be mandatory for base node")


def validate_state_root(state_root: dict[str, Any]) -> None:
    if state_root.get("type") != "NodeStateSchema":
        raise AssertionError(f"{state_root.get('id')}: expected NodeStateSchema")
    root_path = state_root.get("rootPath")
    if not isinstance(root_path, str):
        raise AssertionError(f"{state_root.get('id')}: rootPath must be a string")
    if root_path.startswith(FORBIDDEN_STATE_ROOT_PREFIXES):
        raise AssertionError(f"{state_root.get('id')}: rootPath must not live under /etc or /usr")
    if not root_path.startswith(VALID_STATE_ROOT_PREFIXES):
        raise AssertionError(f"{state_root.get('id')}: rootPath must live under /var/lib or /var/cache")


def validate_profile(profile: dict[str, Any], index: ProjectionIndex) -> None:
    if profile.get("type") != "ImmutableNodeProfile":
        raise AssertionError("profile type must be ImmutableNodeProfile")
    primary_plane = profile.get("primaryPlane")
    if primary_plane not in VALID_PROFILE_PLANES:
        raise AssertionError("ImmutableNodeProfile.primaryPlane must be node-substrate or agent-runtime-substrate")
    substrate = profile.get("substrate")
    if not isinstance(substrate, dict):
        raise AssertionError("ImmutableNodeProfile.substrate must be an object")
    if substrate.get("sociosRequired") is not False:
        raise AssertionError("Base SourceOS immutable nodes must not require Socios enrollment")
    for ref in profile.get("hostCapabilityPlacementRefs", []):
        capability = index.get(ref)
        if capability is None:
            raise AssertionError(f"missing HostCapabilityPlacement projection: {ref}")
        validate_host_capability(capability)
    for ref in profile.get("nodeStateSchemaRefs", []):
        state_root = index.get(ref)
        if state_root is None:
            raise AssertionError(f"missing NodeStateSchema projection: {ref}")
        validate_state_root(state_root)


def render_capability(capability: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": capability.get("id"),
        "name": capability.get("name"),
        "placementClass": capability.get("placementClass"),
        "authority": capability.get("authority"),
        "primaryPlane": capability.get("primaryPlane"),
        "mandatoryForBaseNode": capability.get("mandatoryForBaseNode", False),
        "requiresEnrollment": capability.get("requiresEnrollment", False),
        "lifecycleCoupling": capability.get("lifecycleCoupling"),
        "pathHints": capability.get("pathHints", []),
        "policyRef": capability.get("policyRef"),
        "evidenceRefs": capability.get("evidenceRefs", []),
    }


def render_state_root(state_root: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": state_root.get("id"),
        "name": state_root.get("name"),
        "rootPath": state_root.get("rootPath"),
        "stateClass": state_root.get("stateClass"),
        "primaryPlane": state_root.get("primaryPlane"),
        "rollbackCompatibility": state_root.get("rollbackCompatibility"),
        "mutability": state_root.get("mutability"),
        "owner": state_root.get("owner"),
        "evidenceRequired": state_root.get("evidenceRequired", False),
        "desktopVisible": state_root.get("desktopVisible", False),
        "schemaRef": state_root.get("schemaRef"),
    }


def render_plan(profile_path: Path, profile: dict[str, Any], index: ProjectionIndex) -> dict[str, Any]:
    validate_profile(profile, index)
    capabilities = [render_capability(index[ref]) for ref in profile.get("hostCapabilityPlacementRefs", [])]
    state_roots = [render_state_root(index[ref]) for ref in profile.get("nodeStateSchemaRefs", [])]
    substrate = profile.get("substrate", {})
    return {
        "kind": "ImmutableNodePlan",
        "specVersion": PLAN_SPEC_VERSION,
        "generator": {"name": "agent-machine immutable-node", "version": GENERATOR_VERSION},
        "profile": {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "channel": profile.get("channel"),
            "primaryPlane": profile.get("primaryPlane"),
            "sourcePath": str(profile_path),
        },
        "substrate": {
            "strategy": substrate.get("strategy"),
            "hostMutationPosture": substrate.get("hostMutationPosture"),
            "sociosRequired": substrate.get("sociosRequired"),
        },
        "releaseRefs": {"bootReleaseSetRef": profile.get("bootReleaseSetRef"), "releaseSetRef": profile.get("releaseSetRef")},
        "runtimeRefs": {"agentMachineProfileRef": profile.get("agentMachineProfileRef"), "agentPlaneRuntimeRef": profile.get("agentPlaneRuntimeRef")},
        "desktopConsumers": {"workstationProfileRef": profile.get("workstationProfileRef"), "desktopConsumerRefs": profile.get("desktopConsumerRefs", []), "desktopOwnsSubstrate": False},
        "capabilityPlacements": capabilities,
        "stateRoots": state_roots,
        "optionalSociosCapabilityPackRefs": profile.get("optionalSociosCapabilityPackRefs", []),
        "policyRefs": profile.get("policyRefs", []),
        "evidenceRefs": profile.get("evidenceRefs", []),
        "mutationPlan": {
            "supportedMutationClasses": sorted(SUPPORTED_MUTATION_CLASSES),
            "defaultMutationClasses": ["state-roots", "staging-artifacts"],
            "requiresExecuteFlag": True,
            "requiresPolicyOkFlag": True,
        },
        "safety": {
            "hostMutationPerformed": False,
            "sociosEnrollmentPerformed": False,
            "sociosRequired": False,
            "desktopOwnsSubstrate": False,
            "rawSecretsIncluded": False,
        },
        "verdict": "planned",
    }


def preflight_plan(plan: dict[str, Any], target_root: Path, mutation_classes: tuple[str, ...]) -> dict[str, Any]:
    unsupported = sorted(set(mutation_classes) - SUPPORTED_MUTATION_CLASSES)
    if unsupported:
        raise AssertionError(f"unsupported mutation classes: {unsupported}")
    state_root_checks = []
    for root in plan.get("stateRoots", []):
        root_path = str(root.get("rootPath"))
        validate_state_root({"type": "NodeStateSchema", "id": root.get("id"), "rootPath": root_path})
        target_path = under_target_root(target_root, root_path)
        state_root_checks.append({"rootPath": root_path, "targetPath": str(target_path), "exists": target_path.exists(), "willCreate": "state-roots" in mutation_classes and not target_path.exists()})
    return {
        "kind": "ImmutableNodePreflight",
        "specVersion": EVIDENCE_SPEC_VERSION,
        "profileRef": plan["profile"]["id"],
        "targetRoot": str(target_root),
        "mutationClasses": list(mutation_classes),
        "stateRootChecks": state_root_checks,
        "hostMutationPerformed": False,
        "verdict": "preflight-passed",
    }


def apply_plan(plan: dict[str, Any], options: ApplyOptions) -> dict[str, Any]:
    if not options.execute or not options.policy_ok:
        raise AssertionError("apply requires both --execute and --policy-ok")
    ensure_safe_target_root(options.target_root, options.execute)
    preflight = preflight_plan(plan, options.target_root, options.mutation_classes)
    profile_slug = slug_from_urn(str(plan["profile"]["id"]))
    touched: list[dict[str, str]] = []

    if "state-roots" in options.mutation_classes:
        for check in preflight["stateRootChecks"]:
            target_path = Path(check["targetPath"])
            target_path.mkdir(parents=True, exist_ok=True)
            os.chmod(target_path, 0o750)
            touched.append({"action": "ensure-directory", "path": str(target_path)})

    staging_dir = under_target_root(options.target_root, f"{DEFAULT_STAGING_ROOT}/{profile_slug}")
    if "staging-artifacts" in options.mutation_classes:
        staging_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(staging_dir, 0o750)
        plan_path = staging_dir / "immutable-node-plan.json"
        plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        touched.append({"action": "write-plan", "path": str(plan_path)})

    evidence = {
        "kind": "ImmutableNodeApplyEvidence",
        "specVersion": EVIDENCE_SPEC_VERSION,
        "issuedAt": utc_now(),
        "profileRef": plan["profile"]["id"],
        "profileChannel": plan["profile"].get("channel"),
        "targetRoot": str(options.target_root),
        "mutationClasses": list(options.mutation_classes),
        "planDigestSha256": sha256_json(plan),
        "hostMutationPerformed": True,
        "sociosEnrollmentPerformed": False,
        "sociosRequired": False,
        "desktopOwnsSubstrate": False,
        "rawSecretsIncluded": False,
        "touched": touched,
        "verdict": "applied",
    }

    evidence_out = options.evidence_out
    if evidence_out is None and "staging-artifacts" in options.mutation_classes:
        evidence_out = staging_dir / "immutable-node-apply-evidence.json"
    if evidence_out is not None:
        evidence_out.parent.mkdir(parents=True, exist_ok=True)
        evidence_out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def emit_json(payload: dict[str, Any], pretty: bool) -> None:
    if pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
