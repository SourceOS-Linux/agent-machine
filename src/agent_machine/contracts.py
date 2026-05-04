"""Contract and schema helpers for Agent Machine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_machine.paths import repo_root_from_file


def jsonschema_validator_for() -> Any:
    """Import jsonschema lazily so non-validation commands stay dependency-light."""
    try:
        from jsonschema.validators import validator_for
    except ImportError as exc:  # pragma: no cover - exercised in environments without deps
        raise RuntimeError(
            "Missing dependency: jsonschema. Install with `python -m pip install -r requirements-dev.txt`."
        ) from exc
    return validator_for


def repo_root() -> Path:
    """Return the repository root for the current checkout/package context."""
    return repo_root_from_file(__file__)


def contracts_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "contracts"


def examples_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "examples"


def load_json(path: Path) -> Any:
    """Load a JSON file with a consistent error surface."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path}: invalid JSON: {exc}") from exc


def schema_by_kind(root: Path | None = None) -> dict[str, Path]:
    base = contracts_dir(root)
    return {
        "ActivationDecision": base / "activation-decision.schema.json",
        "AgentMachine": base / "agent-machine.schema.json",
        "AgentPlaneRuntimeEvidence": base / "agentplane-runtime-evidence.schema.json",
        "AgentPod": base / "agent-pod.schema.json",
        "AgentPodDeploymentPlan": base / "agentpod-deployment-plan.schema.json",
        "AgentRegistryGrant": base / "agent-registry-grant.schema.json",
        "CacheTier": base / "cache-tier.schema.json",
        "DeploymentReceipt": base / "deployment-receipt.schema.json",
        "ExternalTrustSignalProvider": base / "external-trust-signal-provider.schema.json",
        "InferenceProvider": base / "inference-provider.schema.json",
        "PolicyAdmission": base / "policy-admission.schema.json",
        "ReleaseEvidenceBundle": base / "release-evidence-bundle.schema.json",
        "StorageReceipt": base / "storage-receipt.schema.json",
    }


def iter_json_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.rglob("*.json") if path.is_file())


def check_schema(path: Path) -> dict[str, Any]:
    schema = load_json(path)
    validator_cls = jsonschema_validator_for()(schema)
    validator_cls.check_schema(schema)
    return schema


def validate_instance(instance_path: Path, schema_path: Path) -> None:
    schema = load_json(schema_path)
    instance = load_json(instance_path)
    validator_cls = jsonschema_validator_for()(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    if errors:
        rendered = []
        for err in errors:
            location = "/".join(str(part) for part in err.path) or "<root>"
            rendered.append(f"  - {instance_path}: {location}: {err.message}")
        raise AssertionError("Schema validation failed:\n" + "\n".join(rendered))


def validate_by_kind(instance_path: Path, root: Path | None = None) -> Path:
    instance = load_json(instance_path)
    if not isinstance(instance, dict):
        raise AssertionError(f"{instance_path}: example root must be a JSON object")
    kind = instance.get("kind")
    if not isinstance(kind, str):
        raise AssertionError(f"{instance_path}: missing string `kind` field")
    mapping = schema_by_kind(root)
    schema_path = mapping.get(kind)
    if schema_path is None:
        known = ", ".join(sorted(mapping))
        raise AssertionError(f"{instance_path}: no schema mapping for kind {kind!r}; known: {known}")
    if not schema_path.exists():
        raise AssertionError(f"{instance_path}: mapped schema is missing: {schema_path}")
    validate_instance(instance_path, schema_path)
    return schema_path
