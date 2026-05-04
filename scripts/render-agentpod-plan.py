#!/usr/bin/env python3
"""Render a non-mutating deployment plan from an AgentPod JSON object.

This is deliberately a plan renderer, not a manifest writer. It proves that the
AgentPod contract has enough information to derive local Quadlet and Kubernetes
execution intent without treating a manifest as authorization. It can also emit a
secret-free DeploymentReceipt for the rendered plan artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema.validators import validator_for
except ImportError as exc:  # pragma: no cover - exercised in environments without deps
    raise SystemExit(
        "Missing dependency: jsonschema. Install with `python -m pip install -r requirements-dev.txt`."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.digest import stable_digest  # noqa: E402

PLAN_SCHEMA_PATH = REPO_ROOT / "contracts" / "agentpod-deployment-plan.schema.json"
RECEIPT_SCHEMA_PATH = REPO_ROOT / "contracts" / "deployment-receipt.schema.json"

GENERATOR_NAME = "agentpod-plan-renderer"
GENERATOR_VERSION = "0.1.0"

LOCAL_TARGETS = {"local-systemd", "local-podman", "local-podman-quadlet", "local-docker-compat", "local-bubblewrap"}
K8S_TARGETS = {"kubernetes-pod", "kubernetes-crd"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AssertionError(f"{path}: root must be a JSON object")
    return value


def validate_against_schema(value: dict[str, Any], schema_path: Path, label: str) -> None:
    schema = load_json(schema_path)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(value), key=lambda err: list(err.path))
    if errors:
        rendered = []
        for err in errors:
            location = "/".join(str(part) for part in err.path) or "<root>"
            rendered.append(f"  - {location}: {err.message}")
        raise AssertionError(f"Rendered {label} failed schema validation:\n" + "\n".join(rendered))


def require_bool_false(obj: dict[str, Any], key: str, path: Path) -> None:
    if obj.get(key) is not False:
        raise AssertionError(f"{path}: {key} must be false")


def require_bool_true(obj: dict[str, Any], key: str, path: Path) -> None:
    if obj.get(key) is not True:
        raise AssertionError(f"{path}: {key} must be true")


def validate_agentpod(source_path: Path, pod: dict[str, Any]) -> None:
    if pod.get("kind") != "AgentPod":
        raise AssertionError(f"{source_path}: kind must be AgentPod")
    pod_type = pod.get("podType")
    if pod_type not in LOCAL_TARGETS | K8S_TARGETS:
        raise AssertionError(f"{source_path}: unsupported podType {pod_type!r}")

    policy = pod.get("policy")
    if not isinstance(policy, dict):
        raise AssertionError(f"{source_path}: policy must be an object")
    require_bool_false(policy, "allowPrivileged", source_path)
    require_bool_false(policy, "allowSecretInSpec", source_path)
    require_bool_true(policy, "policyFabricRequired", source_path)
    require_bool_true(policy, "agentRegistryRequired", source_path)

    receipts = pod.get("receipts")
    if not isinstance(receipts, dict):
        raise AssertionError(f"{source_path}: receipts must be an object")
    require_bool_true(receipts, "required", source_path)
    require_bool_false(receipts, "includeRawContent", source_path)

    if pod_type in LOCAL_TARGETS:
        for port in pod.get("ports", []):
            if not isinstance(port, dict):
                raise AssertionError(f"{source_path}: port entries must be objects")
            if port.get("exposure") not in {"none", "loopback", "policy-managed"}:
                raise AssertionError(f"{source_path}: local AgentPod ports must stay loopback/none/policy-managed")
        runtime = pod.get("runtime", {})
        if runtime.get("networkMode") not in {"none", "loopback", "slirp4netns", "policy-managed"}:
            raise AssertionError(f"{source_path}: local AgentPod networkMode is too broad")

    if pod_type in K8S_TARGETS:
        runtime = pod.get("runtime", {})
        if not runtime.get("namespace"):
            raise AssertionError(f"{source_path}: Kubernetes AgentPod requires runtime.namespace")
        if not runtime.get("serviceAccountName"):
            raise AssertionError(f"{source_path}: Kubernetes AgentPod requires runtime.serviceAccountName")


def target_surface(pod_type: str) -> str:
    if pod_type == "local-podman-quadlet":
        return "quadlet-container"
    if pod_type in LOCAL_TARGETS:
        return "local-runtime-plan"
    if pod_type == "kubernetes-pod":
        return "kubernetes-yaml"
    if pod_type == "kubernetes-crd":
        return "agentpod-crd"
    return "unknown"


def render_plan(source_path: Path, pod: dict[str, Any]) -> dict[str, Any]:
    pod_type = str(pod["podType"])
    runtime = pod.get("runtime", {})
    workload = pod.get("workload", {})
    resources = pod.get("resources", {})
    storage = pod.get("storage", [])
    ports = pod.get("ports", [])
    policy = pod.get("policy", {})
    receipts = pod.get("receipts", {})

    storage_resolution = []
    for item in storage:
        storage_resolution.append(
            {
                "cacheTierId": item.get("cacheTierId"),
                "volumeClass": item.get("volumeClass"),
                "mountPath": item.get("mountPath"),
                "hostPath": item.get("hostPath"),
                "pvcName": item.get("pvcName"),
                "storageClassName": item.get("storageClassName"),
                "accessMode": item.get("accessMode"),
                "sensitive": item.get("sensitive"),
            }
        )

    return {
        "specVersion": "0.1.0",
        "kind": "AgentPodDeploymentPlan",
        "generator": {
            "name": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
        },
        "source": {
            "path": str(source_path),
            "agentPodId": pod.get("id"),
            "digest": stable_digest(pod),
        },
        "target": {
            "podType": pod_type,
            "surface": target_surface(pod_type),
            "profile": pod.get("profile"),
        },
        "workload": {
            "name": workload.get("name"),
            "purpose": workload.get("purpose"),
            "agentIdentityRequired": workload.get("agentIdentityRequired"),
            "agentIdentityRef": workload.get("agentIdentityRef"),
            "workroomRef": workload.get("workroomRef"),
            "topicRef": workload.get("topicRef"),
        },
        "runtime": {
            "mode": runtime.get("mode"),
            "imageOrCommand": runtime.get("imageOrCommand"),
            "networkMode": runtime.get("networkMode"),
            "restartPolicy": runtime.get("restartPolicy"),
            "namespace": runtime.get("namespace"),
            "serviceAccountName": runtime.get("serviceAccountName"),
        },
        "resources": resources,
        "storageResolution": storage_resolution,
        "ports": ports,
        "policy": {
            "policyFabricRequired": policy.get("policyFabricRequired"),
            "agentRegistryRequired": policy.get("agentRegistryRequired"),
            "networkPolicyRequired": policy.get("networkPolicyRequired"),
            "egressPolicyRequired": policy.get("egressPolicyRequired"),
            "allowPrivileged": policy.get("allowPrivileged"),
            "allowHostNetwork": policy.get("allowHostNetwork"),
            "allowSecretInSpec": policy.get("allowSecretInSpec"),
        },
        "receipts": {
            "required": receipts.get("required"),
            "emitPlacement": receipts.get("emitPlacement"),
            "emitStorage": receipts.get("emitStorage"),
            "emitRuntime": receipts.get("emitRuntime"),
            "includeRawContent": receipts.get("includeRawContent"),
        },
        "notes": [
            "This is a non-mutating plan, not authorization.",
            "Production rendering requires Policy Fabric admission, Agent Registry grants, image digest pinning, and receipt emission.",
        ],
    }


def render_receipt(source_path: Path, pod: dict[str, Any], plan: dict[str, Any], artifact_path: str) -> dict[str, Any]:
    plan_digest = stable_digest(plan)
    receipt_seed = f"{pod.get('id')}:{plan_digest}:{GENERATOR_NAME}:{GENERATOR_VERSION}"
    receipt_suffix = hashlib.sha256(receipt_seed.encode("utf-8")).hexdigest()[:32]
    policy = plan["policy"]
    return {
        "specVersion": "0.1.0",
        "kind": "DeploymentReceipt",
        "receiptId": f"urn:srcos:agent-machine:deployment-receipt:{receipt_suffix}",
        "generator": {
            "name": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
        },
        "source": {
            "sourceKind": "AgentPod",
            "path": str(source_path),
            "id": pod.get("id"),
            "digest": stable_digest(pod),
        },
        "artifact": {
            "artifactKind": "AgentPodDeploymentPlan",
            "path": artifact_path,
            "digest": plan_digest,
        },
        "target": {
            "surface": plan["target"]["surface"],
            "profile": plan["target"]["profile"],
        },
        "policy": {
            "authorizationGranted": False,
            "policyFabricRequired": policy["policyFabricRequired"],
            "policyDecisionRef": None,
            "agentRegistryRequired": policy["agentRegistryRequired"],
            "agentRegistryGrantRef": None,
        },
        "receiptSafety": {
            "includeRawContent": False,
            "rawPromptContentIncluded": False,
            "rawKvCacheContentIncluded": False,
            "secretValuesIncluded": False,
        },
        "notes": [
            "This receipt proves deterministic derivation only; it does not authorize execution.",
            "Policy Fabric admission and Agent Registry grants are required before activation.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render an AgentPod deployment plan or receipt")
    parser.add_argument("agentpod_json", type=Path, help="Path to an AgentPod JSON object")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--receipt", action="store_true", help="Emit DeploymentReceipt for the rendered plan instead of the plan")
    parser.add_argument(
        "--artifact-path",
        default="stdout:AgentPodDeploymentPlan",
        help="Artifact path/reference to record in DeploymentReceipt output",
    )
    return parser.parse_args()


def emit_json(value: dict[str, Any], pretty: bool) -> None:
    if pretty:
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main() -> int:
    args = parse_args()
    pod = load_json(args.agentpod_json)
    validate_agentpod(args.agentpod_json, pod)
    plan = render_plan(args.agentpod_json, pod)
    validate_against_schema(plan, PLAN_SCHEMA_PATH, "AgentPodDeploymentPlan")

    if args.receipt:
        receipt = render_receipt(args.agentpod_json, pod, plan, args.artifact_path)
        validate_against_schema(receipt, RECEIPT_SCHEMA_PATH, "DeploymentReceipt")
        emit_json(receipt, args.pretty)
    else:
        emit_json(plan, args.pretty)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
