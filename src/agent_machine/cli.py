"""Transitional Python CLI for Agent Machine package-owned commands."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from agent_machine import __version__
from agent_machine.paths import (
    default_config_path,
    default_evidence_path,
    default_model_cache_path,
    default_runtime_cache_path,
    default_runtime_path,
    default_state_path,
    repo_root_from_file,
)

REPO_ROOT = repo_root_from_file(__file__)
REQUIREMENTS_PATH = REPO_ROOT / "requirements-dev.txt"


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object without importing optional validation dependencies."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AssertionError(f"{path}: root must be a JSON object")
    return value


def dependency_hint(error: BaseException) -> str:
    message = str(error)
    lower = message.lower()
    if "pyyaml" in lower or "yaml" in lower:
        missing = "PyYAML"
    elif "jsonschema" in lower:
        missing = "jsonschema"
    else:
        missing = "a required Python dependency"
    return (
        f"Agent Machine Python dependency missing: {missing}.\n"
        f"Install dependencies with: python3 -m pip install -r {REQUIREMENTS_PATH}"
    )


def import_renderer(importer: Callable[[], Any]) -> Any:
    try:
        return importer()
    except (ImportError, ModuleNotFoundError, RuntimeError) as exc:
        raise RuntimeError(dependency_hint(exc)) from exc


def command_available(command: str) -> bool:
    return shutil.which(command) is not None


def command_output(command: list[str], fallback: str = "unknown") -> str:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return fallback
    if result.returncode != 0:
        return fallback
    value = result.stdout.strip()
    return value if value else fallback


def selinux_mode() -> str:
    if command_available("getenforce"):
        return command_output(["getenforce"])
    return "unknown"


def cgroup_mode() -> str:
    if Path("/sys/fs/cgroup/cgroup.controllers").is_file():
        return "v2"
    if Path("/sys/fs/cgroup").is_dir():
        return "v1"
    return "unknown"


def probe_payload() -> dict[str, Any]:
    return {
        "specVersion": "0.1.0",
        "kind": "AgentMachineProbe",
        "host": {
            "hostname": platform.node() or command_output(["hostname"]),
            "os": platform.system() or "unknown",
            "kernel": platform.release() or "unknown",
            "arch": platform.machine() or "unknown",
        },
        "runtime": {
            "systemdAvailable": command_available("systemctl"),
            "podmanAvailable": command_available("podman"),
            "dockerAvailable": command_available("docker"),
            "selinuxMode": selinux_mode(),
            "cgroupMode": cgroup_mode(),
        },
        "storage": {
            "lvmAvailable": command_available("lvs"),
            "modelCache": str(default_model_cache_path()),
            "runtimeCache": str(default_runtime_cache_path()),
            "evidencePath": str(default_evidence_path()),
        },
        "accelerators": {
            "cpuAvailable": True,
            "vulkanProbeAvailable": command_available("vulkaninfo"),
            "cudaProbeAvailable": command_available("nvidia-smi"),
            "rocmProbeAvailable": command_available("rocminfo"),
            "metalAvailable": False,
        },
        "safety": {
            "rawPromptContentIncluded": False,
            "rawKvCacheContentIncluded": False,
            "secretValuesIncluded": False,
        },
    }


def doctor_payload() -> dict[str, Any]:
    return {
        "specVersion": "0.1.0",
        "kind": "AgentMachineDoctor",
        "install": {
            "cliVersion": __version__,
            "homebrewAvailable": command_available("brew"),
            "bootstrapOnly": True,
            "runtimeDirectoriesManaged": False,
        },
        "readiness": {
            "podmanAvailable": command_available("podman"),
            "lvmAvailable": command_available("lvs"),
            "probeSecretFree": True,
        },
        "nextActions": [
            "agent-machine probe --format json",
            "review docs/install.md before privileged runtime activation",
        ],
    }


def print_json_or_text(payload: dict[str, Any], output_format: str, text_renderer: Any) -> None:
    if output_format == "json":
        print(json.dumps(payload, sort_keys=True))
    else:
        text_renderer(payload)


def print_doctor_text(payload: dict[str, Any]) -> None:
    print("Agent Machine doctor")
    print(f"  agent-machine {payload['install']['cliVersion']}")
    print(f"  homebrew: {'available' if payload['install']['homebrewAvailable'] else 'unavailable'}")
    print(f"  podman: {'available' if payload['readiness']['podmanAvailable'] else 'unavailable'}")
    print(f"  lvm: {'available' if payload['readiness']['lvmAvailable'] else 'unavailable'}")
    print(f"  bootstrap-only install: {str(payload['install']['bootstrapOnly']).lower()}")
    print(f"  runtime directories managed automatically: {str(payload['install']['runtimeDirectoriesManaged']).lower()}")
    print("  next: agent-machine probe --format json")


def print_probe_text(payload: dict[str, Any]) -> None:
    host = payload["host"]
    runtime = payload["runtime"]
    storage = payload["storage"]
    accelerators = payload["accelerators"]
    print("Agent Machine probe summary")
    print(f"  host: {host['os']} {host['kernel']} {host['arch']}")
    print(f"  podman: {'available' if runtime['podmanAvailable'] else 'unavailable'}")
    print(f"  docker: {'available' if runtime['dockerAvailable'] else 'unavailable'}")
    print(f"  lvm: {'available' if storage['lvmAvailable'] else 'unavailable'}")
    print(f"  vulkan probe: {'available' if accelerators['vulkanProbeAvailable'] else 'unavailable'}")
    print("  metal: unavailable on Linux profiles")


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"agent-machine {__version__}")
    return 0


def cmd_paths(args: argparse.Namespace) -> int:
    paths = {
        "config": str(default_config_path()),
        "state": str(default_state_path()),
        "models": str(default_model_cache_path()),
        "cache": str(default_runtime_cache_path()),
        "evidence": str(default_evidence_path()),
        "runtime": str(default_runtime_path()),
    }
    if args.format == "json":
        print(json.dumps(paths, sort_keys=True))
    else:
        print("Agent Machine default paths:")
        for key, value in paths.items():
            print(f"  {key}: {value}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    print_json_or_text(doctor_payload(), args.format, print_doctor_text)
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    # --fail-closed is accepted now so shell and Python CLIs remain compatible.
    print_json_or_text(probe_payload(), args.format, print_probe_text)
    return 0


def cmd_render_plan(args: argparse.Namespace) -> int:
    plan_renderer = import_renderer(lambda: __import__("agent_machine.renderers.plan", fromlist=["_unused"]))
    pod = load_json(args.agentpod_json)
    plan_renderer.validate_agentpod(args.agentpod_json, pod)
    plan = plan_renderer.render_plan(args.agentpod_json, pod)
    plan_renderer.validate_against_schema(plan, plan_renderer.PLAN_SCHEMA_PATH, "AgentPodDeploymentPlan")
    plan_renderer.emit_json(plan, args.pretty)
    return 0


def cmd_render_receipt(args: argparse.Namespace) -> int:
    plan_renderer = import_renderer(lambda: __import__("agent_machine.renderers.plan", fromlist=["_unused"]))
    pod = load_json(args.agentpod_json)
    plan_renderer.validate_agentpod(args.agentpod_json, pod)
    plan = plan_renderer.render_plan(args.agentpod_json, pod)
    plan_renderer.validate_against_schema(plan, plan_renderer.PLAN_SCHEMA_PATH, "AgentPodDeploymentPlan")
    receipt = plan_renderer.render_receipt(args.agentpod_json, pod, plan, args.artifact_path)
    plan_renderer.validate_against_schema(receipt, plan_renderer.RECEIPT_SCHEMA_PATH, "DeploymentReceipt")
    plan_renderer.emit_json(receipt, args.pretty)
    return 0


def cmd_render_quadlet(args: argparse.Namespace) -> int:
    quadlet_renderer = import_renderer(lambda: __import__("agent_machine.renderers.quadlet", fromlist=["_unused"]))
    pod = load_json(args.agentpod_json)
    quadlet_renderer.require_local_quadlet(args.agentpod_json, pod)
    rendered = quadlet_renderer.render_quadlet(pod)
    if args.compare:
        quadlet_renderer.compare(args.compare, rendered)
    else:
        print(rendered, end="")
    return 0


def cmd_render_k8s(args: argparse.Namespace) -> int:
    k8s_renderer = import_renderer(lambda: __import__("agent_machine.renderers.k8s", fromlist=["_unused"]))
    pod = load_json(args.agentpod_json)
    k8s_renderer.require_k8s_agentpod(args.agentpod_json, pod)
    docs = k8s_renderer.render_documents(pod)
    if args.compare:
        k8s_renderer.compare(args.compare, docs)
    else:
        print(k8s_renderer.dump_documents(docs), end="")
    return 0


def cmd_policy_resolve(args: argparse.Namespace) -> int:
    policy_fabric = import_renderer(lambda: __import__("agent_machine.policy_fabric", fromlist=["_unused"]))
    agentpod = load_json(args.agentpod_json)
    policies = policy_fabric.load_policy_admissions(files=args.policy_file, directories=args.policy_dir, root=REPO_ROOT)
    policy = policy_fabric.resolve_policy_admission(
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
        root=REPO_ROOT,
    )
    if args.pretty:
        print(json.dumps(policy, indent=2, sort_keys=True))
    else:
        print(json.dumps(policy, sort_keys=True, separators=(",", ":")))
    return 0


def cmd_activate_evaluate(args: argparse.Namespace) -> int:
    activation = import_renderer(lambda: __import__("agent_machine.activation", fromlist=["_unused"]))
    policy_fabric = import_renderer(lambda: __import__("agent_machine.policy_fabric", fromlist=["_unused"]))
    agentpod = load_json(args.agentpod_json)
    if args.policy_json:
        policy = load_json(args.policy_json)
    else:
        policies = policy_fabric.load_policy_admissions(
            files=args.policy_file,
            directories=args.policy_dir,
            root=REPO_ROOT,
        )
        policy = policy_fabric.resolve_policy_admission(
            policies=policies,
            agentpod_id=str(agentpod.get("id")),
            request_type="activation",
            deployment_receipt_id=args.deployment_receipt_id,
            agent_machine_id=args.agent_machine_id,
            provider_id=args.provider_id,
            policy_id=args.policy_id,
            expected_status=args.expected_status,
            allow_missing_stub=not args.no_missing_stub,
            decided_at=args.decided_at,
            root=REPO_ROOT,
        )
    storage_receipts = activation.load_storage_receipts(
        files=args.storage_receipt_file,
        directories=args.storage_receipt_dir,
    )
    storage_receipt_refs = list(args.storage_receipt_ref or [])
    if not storage_receipt_refs and storage_receipts:
        storage_receipt_refs = [str(receipt.get("id")) for receipt in storage_receipts]
    decision = activation.evaluate_activation(
        agentpod=agentpod,
        policy=policy,
        grant=load_json(args.grant_json),
        deployment_receipt_id=args.deployment_receipt_id,
        storage_receipt_refs=storage_receipt_refs,
        storage_receipts=storage_receipts if storage_receipts else None,
        decided_at=args.decided_at,
        decision_id=args.decision_id,
        root=REPO_ROOT,
    )
    activation.validate_activation_decision_payload(decision, REPO_ROOT)
    if args.pretty:
        print(json.dumps(decision, indent=2, sort_keys=True))
    else:
        print(json.dumps(decision, sort_keys=True, separators=(",", ":")))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent Machine Python CLI")
    subcommands = parser.add_subparsers(dest="command", required=True)

    version = subcommands.add_parser("version", help="Print package version")
    version.set_defaults(func=cmd_version)

    paths = subcommands.add_parser("paths", help="Print default runtime paths")
    paths.add_argument("--format", choices=["text", "json"], default="text")
    paths.set_defaults(func=cmd_paths)

    doctor = subcommands.add_parser("doctor", help="Run conservative install/readiness diagnostics")
    doctor.add_argument("--format", choices=["text", "json"], default="text")
    doctor.set_defaults(func=cmd_doctor)

    probe = subcommands.add_parser("probe", help="Run conservative host/runtime probe")
    probe.add_argument("--format", choices=["text", "json"], default="text")
    probe.add_argument("--fail-closed", action="store_true")
    probe.set_defaults(func=cmd_probe)

    render = subcommands.add_parser("render", help="Render AgentPod-derived artifacts")
    render_subcommands = render.add_subparsers(dest="render_command", required=True)

    render_plan = render_subcommands.add_parser("plan", help="Render AgentPodDeploymentPlan JSON")
    render_plan.add_argument("agentpod_json", type=Path)
    render_plan.add_argument("--pretty", action="store_true")
    render_plan.set_defaults(func=cmd_render_plan)

    render_receipt = render_subcommands.add_parser("receipt", help="Render DeploymentReceipt JSON")
    render_receipt.add_argument("agentpod_json", type=Path)
    render_receipt.add_argument("--pretty", action="store_true")
    render_receipt.add_argument("--artifact-path", default="stdout:AgentPodDeploymentPlan")
    render_receipt.set_defaults(func=cmd_render_receipt)

    render_quadlet = render_subcommands.add_parser("quadlet", help="Render local Quadlet .container")
    render_quadlet.add_argument("agentpod_json", type=Path)
    render_quadlet.add_argument("--compare", type=Path)
    render_quadlet.set_defaults(func=cmd_render_quadlet)

    render_k8s = render_subcommands.add_parser("k8s", help="Render Kubernetes YAML")
    render_k8s.add_argument("agentpod_json", type=Path)
    render_k8s.add_argument("--compare", type=Path)
    render_k8s.set_defaults(func=cmd_render_k8s)

    policy = subcommands.add_parser("policy", help="Resolve Policy Fabric admission artifacts")
    policy_subcommands = policy.add_subparsers(dest="policy_command", required=True)
    policy_resolve = policy_subcommands.add_parser("resolve", help="Resolve a PolicyAdmission from local files/stores")
    policy_resolve.add_argument("agentpod_json", type=Path)
    policy_resolve.add_argument("--policy-file", action="append", type=Path, default=[])
    policy_resolve.add_argument("--policy-dir", action="append", type=Path, default=[])
    policy_resolve.add_argument("--request-type", default="activation")
    policy_resolve.add_argument("--deployment-receipt-id", required=True)
    policy_resolve.add_argument("--agent-machine-id")
    policy_resolve.add_argument("--provider-id")
    policy_resolve.add_argument("--policy-id")
    policy_resolve.add_argument("--expected-status", choices=["missing", "allowed", "denied", "not-required", "unknown"])
    policy_resolve.add_argument("--no-missing-stub", action="store_true")
    policy_resolve.add_argument("--decided-at", default="1970-01-01T00:00:00Z")
    policy_resolve.add_argument("--pretty", action="store_true")
    policy_resolve.set_defaults(func=cmd_policy_resolve)

    activate = subcommands.add_parser("activate", help="Evaluate activation readiness")
    activate_subcommands = activate.add_subparsers(dest="activate_command", required=True)
    activate_evaluate = activate_subcommands.add_parser("evaluate", help="Evaluate AgentPod activation decision")
    activate_evaluate.add_argument("agentpod_json", type=Path)
    activate_evaluate.add_argument("policy_json", type=Path, nargs="?")
    activate_evaluate.add_argument("grant_json", type=Path)
    activate_evaluate.add_argument("--deployment-receipt-id", required=True)
    activate_evaluate.add_argument("--policy-file", action="append", type=Path, default=[])
    activate_evaluate.add_argument("--policy-dir", action="append", type=Path, default=[])
    activate_evaluate.add_argument("--policy-id")
    activate_evaluate.add_argument("--expected-status", choices=["missing", "allowed", "denied", "not-required", "unknown"])
    activate_evaluate.add_argument("--no-missing-stub", action="store_true")
    activate_evaluate.add_argument("--agent-machine-id")
    activate_evaluate.add_argument("--provider-id")
    activate_evaluate.add_argument("--storage-receipt-ref", action="append", default=[])
    activate_evaluate.add_argument("--storage-receipt-file", action="append", type=Path, default=[])
    activate_evaluate.add_argument("--storage-receipt-dir", action="append", type=Path, default=[])
    activate_evaluate.add_argument("--decided-at", default="1970-01-01T00:00:00Z")
    activate_evaluate.add_argument("--decision-id")
    activate_evaluate.add_argument("--pretty", action="store_true")
    activate_evaluate.set_defaults(func=cmd_activate_evaluate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
