"""Deterministic Kubernetes YAML renderer for Kubernetes AgentPod objects."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised in environments without deps
    raise RuntimeError(
        "Missing dependency: PyYAML. Install with `python -m pip install -r requirements-dev.txt`."
    ) from exc

GENERATOR_VERSION = "0.1.0"
PVC_SIZE_BY_VOLUME_CLASS = {
    "agent-models": "120Gi",
    "agent-cache-warm": "80Gi",
    "agent-scratch": "40Gi",
    "agent-evidence": "20Gi",
}
VOLUME_NAME_BY_VOLUME_CLASS = {
    "agent-models": "models",
    "agent-cache-warm": "warm-cache",
    "agent-scratch": "scratch",
    "agent-evidence": "evidence",
}


def require_k8s_agentpod(path: Path, pod: dict[str, Any]) -> None:
    if pod.get("kind") != "AgentPod":
        raise AssertionError(f"{path}: kind must be AgentPod")
    if pod.get("podType") != "kubernetes-pod":
        raise AssertionError(f"{path}: podType must be kubernetes-pod")

    runtime = pod.get("runtime", {})
    if runtime.get("mode") != "kubernetes":
        raise AssertionError(f"{path}: runtime.mode must be kubernetes")
    if not runtime.get("namespace"):
        raise AssertionError(f"{path}: runtime.namespace is required")
    if not runtime.get("serviceAccountName"):
        raise AssertionError(f"{path}: runtime.serviceAccountName is required")
    if runtime.get("networkMode") != "kubernetes-service":
        raise AssertionError(f"{path}: runtime.networkMode must be kubernetes-service")

    policy = pod.get("policy", {})
    for key in ("policyFabricRequired", "agentRegistryRequired", "networkPolicyRequired", "egressPolicyRequired"):
        if policy.get(key) is not True:
            raise AssertionError(f"{path}: policy.{key} must be true")
    if policy.get("allowPrivileged") is not False:
        raise AssertionError(f"{path}: policy.allowPrivileged must be false")
    if policy.get("allowHostNetwork") is not False:
        raise AssertionError(f"{path}: policy.allowHostNetwork must be false")
    if policy.get("allowSecretInSpec") is not False:
        raise AssertionError(f"{path}: policy.allowSecretInSpec must be false")

    receipts = pod.get("receipts", {})
    if receipts.get("required") is not True:
        raise AssertionError(f"{path}: receipts.required must be true")
    if receipts.get("includeRawContent") is not False:
        raise AssertionError(f"{path}: receipts.includeRawContent must be false")

    for item in pod.get("storage", []):
        if item.get("storageClassName") != "topolvm-provisioner":
            raise AssertionError(f"{path}: initial renderer requires topolvm-provisioner storageClassName")
        volume_class = item.get("volumeClass")
        if volume_class not in PVC_SIZE_BY_VOLUME_CLASS:
            raise AssertionError(f"{path}: unsupported volumeClass for initial renderer: {volume_class!r}")
        if not item.get("pvcName"):
            raise AssertionError(f"{path}: storage item {volume_class!r} requires pvcName")


def labels(component: str | None = None) -> dict[str, str]:
    result = {"app.kubernetes.io/name": "agent-machine"}
    if component:
        result["app.kubernetes.io/component"] = component
    return result


def render_namespace(namespace: str) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": namespace,
            "labels": labels("namespace"),
        },
    }


def render_service_account(namespace: str, service_account_name: str) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {
            "name": service_account_name,
            "namespace": namespace,
            "labels": labels("inference-provider"),
        },
    }


def render_pvc(namespace: str, item: dict[str, Any]) -> dict[str, Any]:
    volume_class = str(item["volumeClass"])
    return {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "name": item["pvcName"],
            "namespace": namespace,
            "labels": {
                "app.kubernetes.io/name": "agent-machine",
                "agent-machine.sourceos.dev/volume-class": volume_class,
                "agent-machine.sourceos.dev/storage-profile": "topolvm-k8s",
            },
        },
        "spec": {
            "accessModes": ["ReadWriteOnce"],
            "storageClassName": item["storageClassName"],
            "resources": {
                "requests": {
                    "storage": PVC_SIZE_BY_VOLUME_CLASS[volume_class],
                }
            },
        },
    }


def bytes_to_gib(value: int) -> str:
    if value % (1024**3) != 0:
        raise AssertionError(f"memory byte value must be whole GiB for initial renderer: {value}")
    return f"{value // (1024**3)}Gi"


def render_pod(pod: dict[str, Any]) -> dict[str, Any]:
    runtime = pod["runtime"]
    namespace = runtime["namespace"]
    storage = pod.get("storage", [])
    resources = pod["resources"]
    cpu = resources["cpu"]
    memory = resources["memoryBytes"]
    args = runtime.get("args") or []
    ports = pod.get("ports") or []
    if len(ports) != 1:
        raise AssertionError("initial Kubernetes renderer supports exactly one port")
    port = ports[0]

    volume_mounts = []
    volumes = []
    for item in storage:
        volume_class = item["volumeClass"]
        volume_name = VOLUME_NAME_BY_VOLUME_CLASS[volume_class]
        mount = {
            "name": volume_name,
            "mountPath": item["mountPath"],
        }
        if item.get("accessMode") == "read-only":
            mount["readOnly"] = True
        volume_mounts.append(mount)
        pvc_ref: dict[str, Any] = {"claimName": item["pvcName"]}
        if item.get("accessMode") == "read-only":
            pvc_ref["readOnly"] = True
        volumes.append({"name": volume_name, "persistentVolumeClaim": pvc_ref})

    volume_mounts.append({"name": "tmp", "mountPath": "/tmp"})
    volumes.append({"name": "tmp", "emptyDir": {"medium": "Memory", "sizeLimit": "1Gi"}})

    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "llama-cpp-provider",
            "namespace": namespace,
            "labels": {
                "app.kubernetes.io/name": "agent-machine",
                "app.kubernetes.io/component": "inference-provider",
                "agent-machine.sourceos.dev/provider": "llama.cpp",
                "agent-machine.sourceos.dev/storage-profile": "topolvm-k8s",
            },
            "annotations": {
                "agent-machine.sourceos.dev/agent-pod-id": pod["id"],
                "agent-machine.sourceos.dev/receipts-required": "true",
                "agent-machine.sourceos.dev/raw-content-in-receipts": "false",
            },
        },
        "spec": {
            "serviceAccountName": runtime["serviceAccountName"],
            "restartPolicy": "Always",
            "securityContext": {
                "runAsNonRoot": True,
                "seccompProfile": {"type": "RuntimeDefault"},
            },
            "containers": [
                {
                    "name": "llama-cpp",
                    "image": runtime["imageOrCommand"],
                    "imagePullPolicy": "IfNotPresent",
                    "args": args,
                    "ports": [
                        {
                            "name": "http",
                            "containerPort": port["containerPort"],
                            "protocol": "TCP",
                        }
                    ],
                    "env": [
                        {"name": "AGENT_MACHINE_PROFILE", "value": pod["profile"]},
                        {"name": "AGENT_MACHINE_PROVIDER", "value": "llama.cpp"},
                        {"name": "AGENT_MACHINE_RECEIPTS_REQUIRED", "value": "true"},
                    ],
                    "resources": {
                        "requests": {
                            "cpu": cpu["request"],
                            "memory": bytes_to_gib(memory["request"]),
                        },
                        "limits": {
                            "cpu": cpu["limit"],
                            "memory": bytes_to_gib(memory["limit"]),
                        },
                    },
                    "securityContext": {
                        "allowPrivilegeEscalation": False,
                        "readOnlyRootFilesystem": True,
                        "capabilities": {"drop": ["ALL"]},
                    },
                    "volumeMounts": volume_mounts,
                }
            ],
            "volumes": volumes,
        },
    }


def render_service(namespace: str) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "llama-cpp-provider",
            "namespace": namespace,
            "labels": labels("inference-provider"),
        },
        "spec": {
            "type": "ClusterIP",
            "selector": {
                "app.kubernetes.io/name": "agent-machine",
                "app.kubernetes.io/component": "inference-provider",
                "agent-machine.sourceos.dev/provider": "llama.cpp",
            },
            "ports": [
                {
                    "name": "http",
                    "port": 8080,
                    "targetPort": "http",
                    "protocol": "TCP",
                }
            ],
        },
    }


def render_network_policy(namespace: str) -> dict[str, Any]:
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {
            "name": "llama-cpp-provider-default-deny-egress",
            "namespace": namespace,
            "labels": labels("inference-provider"),
        },
        "spec": {
            "podSelector": {
                "matchLabels": {
                    "app.kubernetes.io/name": "agent-machine",
                    "app.kubernetes.io/component": "inference-provider",
                    "agent-machine.sourceos.dev/provider": "llama.cpp",
                }
            },
            "policyTypes": ["Egress"],
            "egress": [],
        },
    }


def render_documents(pod: dict[str, Any]) -> list[dict[str, Any]]:
    runtime = pod["runtime"]
    namespace = runtime["namespace"]
    docs = [render_namespace(namespace), render_service_account(namespace, runtime["serviceAccountName"])]
    docs.extend(render_pvc(namespace, item) for item in pod.get("storage", []))
    docs.append(render_pod(pod))
    docs.append(render_service(namespace))
    docs.append(render_network_policy(namespace))
    return docs


def dump_documents(docs: list[dict[str, Any]]) -> str:
    rendered_parts = []
    for doc in docs:
        rendered_parts.append(yaml.safe_dump(doc, sort_keys=False).strip())
    return "---\n".join(rendered_parts) + "\n"


def load_yaml_documents(path: Path) -> list[Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return [doc for doc in yaml.safe_load_all(handle) if doc is not None]
    except yaml.YAMLError as exc:
        raise AssertionError(f"{path}: invalid YAML: {exc}") from exc


def compare(expected_path: Path, docs: list[dict[str, Any]]) -> None:
    expected_docs = load_yaml_documents(expected_path)
    if expected_docs != docs:
        expected = json.dumps(expected_docs, sort_keys=True, indent=2).splitlines(keepends=True)
        rendered = json.dumps(docs, sort_keys=True, indent=2).splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(expected, rendered, fromfile=str(expected_path), tofile="rendered-k8s"))
        raise AssertionError(f"rendered Kubernetes YAML does not match expected skeleton:\n{diff}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Kubernetes YAML from a Kubernetes AgentPod JSON object")
    parser.add_argument("agentpod_json", type=Path, help="Path to a Kubernetes AgentPod JSON object")
    parser.add_argument("--compare", type=Path, help="Compare rendered semantic documents to an existing YAML file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pod = load_json(args.agentpod_json)
    require_k8s_agentpod(args.agentpod_json, pod)
    docs = render_documents(pod)
    if args.compare:
        compare(args.compare, docs)
    else:
        print(dump_documents(docs), end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
