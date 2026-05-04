#!/usr/bin/env python3
"""Render a deterministic Quadlet .container file from a local AgentPod JSON object.

This renderer is intentionally narrow. It supports the first local
`local-podman-quadlet` inference-provider shape and can compare its output to a
hand-written skeleton so drift is visible in CI.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "0.1.0"


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AssertionError(f"{path}: root must be a JSON object")
    return value


def require_local_quadlet(path: Path, pod: dict[str, Any]) -> None:
    if pod.get("kind") != "AgentPod":
        raise AssertionError(f"{path}: kind must be AgentPod")
    if pod.get("podType") != "local-podman-quadlet":
        raise AssertionError(f"{path}: podType must be local-podman-quadlet")

    policy = pod.get("policy", {})
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

    runtime = pod.get("runtime", {})
    if runtime.get("networkMode") != "loopback":
        raise AssertionError(f"{path}: runtime.networkMode must be loopback for this renderer")

    for port in pod.get("ports", []):
        if not isinstance(port, dict):
            raise AssertionError(f"{path}: port entries must be objects")
        if port.get("exposure") != "loopback":
            raise AssertionError(f"{path}: ports must use loopback exposure for this renderer")


def render_exec(runtime: dict[str, Any]) -> str:
    entrypoint = str(runtime.get("entrypoint") or "")
    args = runtime.get("args") or []
    if not entrypoint:
        raise AssertionError("runtime.entrypoint is required for Quadlet rendering")
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise AssertionError("runtime.args must be a string array")
    return " ".join([entrypoint] + args)


def render_publish_port(pod: dict[str, Any]) -> str:
    ports = pod.get("ports") or []
    if len(ports) != 1:
        raise AssertionError("exactly one port is supported by the initial Quadlet renderer")
    port = ports[0]
    host_port = port.get("hostPort")
    container_port = port.get("containerPort")
    if not isinstance(host_port, int) or not isinstance(container_port, int):
        raise AssertionError("hostPort and containerPort are required integer fields")
    return f"127.0.0.1:{host_port}:{container_port}"


def render_volume(storage_item: dict[str, Any]) -> str:
    host_path = storage_item.get("hostPath")
    mount_path = storage_item.get("mountPath")
    access_mode = storage_item.get("accessMode")
    if not isinstance(host_path, str) or not host_path:
        raise AssertionError("local Quadlet storage entries require hostPath")
    if not isinstance(mount_path, str) or not mount_path:
        raise AssertionError("local Quadlet storage entries require mountPath")

    if access_mode == "read-only":
        mode = "ro"
    elif access_mode in {"read-write", "runtime-managed"}:
        mode = "rw"
    else:
        raise AssertionError(f"unsupported accessMode for Quadlet volume: {access_mode!r}")
    return f"{host_path}:{mount_path}:{mode},Z"


def render_quadlet(pod: dict[str, Any]) -> str:
    runtime = pod.get("runtime", {})
    workload = pod.get("workload", {})
    profile = str(pod.get("profile"))
    provider = str((pod.get("labels") or {}).get("sourceos.provider", "unknown"))
    image = str(runtime.get("imageOrCommand") or "")
    if not image:
        raise AssertionError("runtime.imageOrCommand is required")

    volumes = [render_volume(item) for item in pod.get("storage", [])]
    if not any(":/models:ro" in volume for volume in volumes):
        raise AssertionError("rendered Quadlet must include a read-only /models mount")

    lines = [
        "# Agent Machine local llama.cpp provider",
        "#",
        "# This is the first local AgentPod deployment template. It mirrors",
        "# examples/local-podman-llama-cpp.agent-pod.json and keeps exposure on loopback.",
        "# Runtime activation remains explicit: install this into the appropriate systemd",
        "# user or system Quadlet directory only after Policy Fabric / Agent Registry",
        "# admission has approved the workload.",
        "",
        "[Unit]",
        "Description=Agent Machine llama.cpp local inference provider",
        "Documentation=https://github.com/SourceOS-Linux/agent-machine",
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Container]",
        f"Image={image}",
        "ContainerName=agent-machine-llama-cpp",
        f"Exec={render_exec(runtime)}",
        f"PublishPort={render_publish_port(pod)}",
        "ReadOnly=true",
        "NoNewPrivileges=true",
        "SecurityLabelDisable=false",
        "DropCapability=all",
        "AddCapability=CHOWN DAC_OVERRIDE FOWNER SETGID SETUID",
        f"Environment=AGENT_MACHINE_PROFILE={profile}",
        f"Environment=AGENT_MACHINE_PROVIDER={provider}",
        "Environment=AGENT_MACHINE_RECEIPTS_REQUIRED=true",
    ]
    for volume in volumes:
        lines.append(f"Volume={volume}")
    lines.extend(
        [
            "Tmpfs=/tmp:rw,nodev,nosuid,size=1g",
            "",
            "[Service]",
            "Restart=on-failure",
            "RestartSec=5s",
            "TimeoutStartSec=120s",
            "TimeoutStopSec=30s",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )
    return "\n".join(lines)


def compare(expected_path: Path, rendered: str) -> None:
    expected = expected_path.read_text(encoding="utf-8")
    if expected != rendered:
        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                rendered.splitlines(keepends=True),
                fromfile=str(expected_path),
                tofile="rendered-quadlet",
            )
        )
        raise AssertionError(f"rendered Quadlet does not match expected skeleton:\n{diff}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a local AgentPod Quadlet .container file")
    parser.add_argument("agentpod_json", type=Path, help="Path to a local AgentPod JSON object")
    parser.add_argument("--compare", type=Path, help="Compare rendered output to an existing .container file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pod = load_json(args.agentpod_json)
    require_local_quadlet(args.agentpod_json, pod)
    rendered = render_quadlet(pod)
    if args.compare:
        compare(args.compare, rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
