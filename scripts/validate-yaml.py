#!/usr/bin/env python3
"""Validate Agent Machine YAML deployment manifests.

The current YAML lane is intentionally narrow. We parse every YAML document under
deploy/ and apply structural safety checks that are useful before we add a full
Kubernetes policy engine or kubeconform lane.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised in environments without deps
    raise SystemExit(
        "Missing dependency: PyYAML. Install with `python -m pip install -r requirements-dev.txt`."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = REPO_ROOT / "deploy"

K8S_REQUIRED_TOP_LEVEL = {"apiVersion", "kind", "metadata"}


def iter_yaml_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}
    )


def load_yaml_documents(path: Path) -> list[Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            docs = list(yaml.safe_load_all(handle))
    except yaml.YAMLError as exc:
        raise AssertionError(f"{path}: invalid YAML: {exc}") from exc
    return [doc for doc in docs if doc is not None]


def require_mapping(path: Path, index: int, doc: Any) -> dict[str, Any]:
    if not isinstance(doc, dict):
        raise AssertionError(f"{path}: document {index}: expected mapping/object root")
    return doc


def validate_k8s_doc(path: Path, index: int, doc: dict[str, Any]) -> None:
    missing = sorted(K8S_REQUIRED_TOP_LEVEL - set(doc))
    if missing:
        raise AssertionError(f"{path}: document {index}: missing top-level keys: {', '.join(missing)}")

    metadata = doc.get("metadata")
    if not isinstance(metadata, dict):
        raise AssertionError(f"{path}: document {index}: metadata must be an object")
    name = metadata.get("name")
    if not isinstance(name, str) or not name:
        raise AssertionError(f"{path}: document {index}: metadata.name is required")

    kind = doc.get("kind")
    if kind == "Pod":
        validate_pod(path, index, doc)
    if kind == "Service":
        validate_service(path, index, doc)
    if kind == "PersistentVolumeClaim":
        validate_pvc(path, index, doc)
    if kind == "NetworkPolicy":
        validate_network_policy(path, index, doc)


def validate_pod(path: Path, index: int, doc: dict[str, Any]) -> None:
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise AssertionError(f"{path}: document {index}: Pod spec must be an object")
    containers = spec.get("containers")
    if not isinstance(containers, list) or not containers:
        raise AssertionError(f"{path}: document {index}: Pod spec.containers must be a non-empty list")
    for container_index, container in enumerate(containers):
        if not isinstance(container, dict):
            raise AssertionError(f"{path}: document {index}: container {container_index} must be an object")
        image = container.get("image")
        if not isinstance(image, str) or not image:
            raise AssertionError(f"{path}: document {index}: container {container_index} image is required")
        security_context = container.get("securityContext")
        if not isinstance(security_context, dict):
            raise AssertionError(f"{path}: document {index}: container {container_index} securityContext is required")
        if security_context.get("allowPrivilegeEscalation") is not False:
            raise AssertionError(
                f"{path}: document {index}: container {container_index} must set allowPrivilegeEscalation: false"
            )
        if security_context.get("readOnlyRootFilesystem") is not True:
            raise AssertionError(
                f"{path}: document {index}: container {container_index} must set readOnlyRootFilesystem: true"
            )


def validate_service(path: Path, index: int, doc: dict[str, Any]) -> None:
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise AssertionError(f"{path}: document {index}: Service spec must be an object")
    if spec.get("type") not in {None, "ClusterIP"}:
        raise AssertionError(f"{path}: document {index}: Service type must stay ClusterIP for skeleton manifests")


def validate_pvc(path: Path, index: int, doc: dict[str, Any]) -> None:
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise AssertionError(f"{path}: document {index}: PVC spec must be an object")
    if not spec.get("storageClassName"):
        raise AssertionError(f"{path}: document {index}: PVC storageClassName is required")
    resources = spec.get("resources")
    if not isinstance(resources, dict) or not isinstance(resources.get("requests"), dict):
        raise AssertionError(f"{path}: document {index}: PVC resources.requests is required")
    if not resources["requests"].get("storage"):
        raise AssertionError(f"{path}: document {index}: PVC resources.requests.storage is required")


def validate_network_policy(path: Path, index: int, doc: dict[str, Any]) -> None:
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise AssertionError(f"{path}: document {index}: NetworkPolicy spec must be an object")
    policy_types = spec.get("policyTypes")
    if not isinstance(policy_types, list) or not policy_types:
        raise AssertionError(f"{path}: document {index}: NetworkPolicy policyTypes must be non-empty")


def main() -> int:
    yaml_files = iter_yaml_files(DEPLOY_DIR)
    if not yaml_files:
        print("No YAML files found under deploy/")
        return 0

    for path in yaml_files:
        docs = load_yaml_documents(path)
        if not docs:
            raise AssertionError(f"{path}: no YAML documents found")
        for index, raw_doc in enumerate(docs, start=1):
            doc = require_mapping(path, index, raw_doc)
            # For now every YAML file under deploy/ is treated as Kubernetes YAML.
            validate_k8s_doc(path, index, doc)
        print(f"VALID yaml {path.relative_to(REPO_ROOT)} ({len(docs)} document(s))")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
