#!/usr/bin/env python3
"""Render a non-mutating deployment plan from an AgentPod JSON object.

This is deliberately a plan renderer, not a manifest writer. It proves that the
AgentPod contract has enough information to derive local Quadlet and Kubernetes
execution intent without treating a manifest as authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

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


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render an AgentPod deployment plan")
    parser.add_argument("agentpod_json", type=Path, help="Path to an AgentPod JSON object")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pod = load_json(args.agentpod_json)
    validate_agentpod(args.agentpod_json, pod)
    plan = render_plan(args.agentpod_json, pod)
    if args.pretty:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(json.dumps(plan, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
