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
    return f"Agent Machine Python dependency missing: {missing}.\nInstall dependencies with: python3 -m pip install -r {REQUIREMENTS_PATH}"


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
        "host": {"hostname": platform.node() or command_output(["hostname"]), "os": platform.system() or "unknown", "kernel": platform.release() or "unknown", "arch": platform.machine() or "unknown"},
        "runtime": {"systemdAvailable": command_available("systemctl"), "podmanAvailable": command_available("podman"), "dockerAvailable": command_available("docker"), "selinuxMode": selinux_mode(), "cgroupMode": cgroup_mode()},
        "storage": {"lvmAvailable": command_available("lvs"), "modelCache": str(default_model_cache_path()), "runtimeCache": str(default_runtime_cache_path()), "evidencePath": str(default_evidence_path())},
        "accelerators": {"cpuAvailable": True, "vulkanProbeAvailable": command_available("vulkaninfo"), "cudaProbeAvailable": command_available("nvidia-smi"), "rocmProbeAvailable": command_available("rocminfo"), "metalAvailable": False},
        "safety": {"rawPromptContentIncluded": False, "rawKvCacheContentIncluded": False, "secretValuesIncluded": False},
    }


def doctor_payload() -> dict[str, Any]:
    return {
        "specVersion": "0.1.0",
        "kind": "AgentMachineDoctor",
        "install": {"cliVersion": __version__, "homebrewAvailable": command_available("brew"), "bootstrapOnly": True, "runtimeDirectoriesManaged": False},
        "readiness": {"podmanAvailable": command_available("podman"), "lvmAvailable": command_available("lvs"), "probeSecretFree": True},
        "nextActions": ["agent-machine probe --format json", "review docs/install.md before privileged runtime activation"],
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
    paths = {"config": str(default_config_path()), "state": str(default_state_path()), "models": str(default_model_cache_path()), "cache": str(default_runtime_cache_path()), "evidence": str(default_evidence_path()), "runtime": str(default_runtime_path())}
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


def resolve_activation_policy_and_grant(args: argparse.Namespace, agentpod: dict[str, Any], policy_fabric: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve activation policy/grant from explicit files or local policy store."""
    policy_json = args.policy_json
    grant_json = args.grant_json

    # Backward-compatible shorthand:
    # agent-machine activate evaluate <agentpod.json> <grant.json> --policy-dir examples ...
    # argparse first assigns the single optional positional to policy_json, so we
    # reinterpret it as grant_json when a policy store/resolver option is present.
    resolver_requested = bool(args.policy_file or args.policy_dir or args.policy_id or args.expected_status)
    if grant_json is None and policy_json is not None and resolver_requested:
        grant_json = policy_json
        policy_json = None

    if grant_json is None:
        raise AssertionError(
            "grant JSON is required. Use either `<agentpod> <policy.json> <grant.json>` "
            "or `<agentpod> <grant.json> --policy-dir <dir>`"
        )

    if policy_json is not None:
        return load_json(policy_json), load_json(grant_json)

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
    return policy, load_json(grant_json)


def cmd_activate_evaluate(args: argparse.Namespace) -> int:
    activation = import_renderer(lambda: __import__("agent_machine.activation", fromlist=["_unused"]))
    policy_fabric = import_renderer(lambda: __import__("agent_machine.policy_fabric", fromlist=["_unused"]))
    agentpod = load_json(args.agentpod_json)
    policy, grant = resolve_activation_policy_and_grant(args, agentpod, policy_fabric)
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
        grant=grant,
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
    policy = policy_fabric.resolve_policy_admission(policies=policies, agentpod_id=str(agentpod.get("id")), request_type=args.request_type, deployment_receipt_id=args.deployment_receipt_id, agent_machine_id=args.agent_machine_id, provider_id=args.provider_id, policy_id=args.policy_id, expected_status=args.expected_status, allow_missing_stub=not args.no_missing_stub, decided_at=args.decided_at, root=REPO_ROOT)
    print(json.dumps(policy, indent=2 if args.pretty else None, sort_keys=True))
    return 0


def agentpod_workload_default(agentpod: dict[str, Any], key: str) -> str | None:
    value = agentpod.get("workload", {}).get(key)
    return value if isinstance(value, str) and value else None


def resolve_registry_grant_from_args(args: argparse.Namespace, agentpod: dict[str, Any], agent_registry: Any) -> dict[str, Any]:
    requested_agent_identity_ref = args.requested_agent_identity_ref or agentpod_workload_default(agentpod, "agentIdentityRef")
    session_ref = args.session_ref
    if not requested_agent_identity_ref:
        raise AssertionError("requested agent identity ref is required; pass --requested-agent-identity-ref or set workload.agentIdentityRef")
    if not session_ref:
        raise AssertionError("session ref is required when resolving AgentRegistryGrant; pass --session-ref")
    requested_scope = agent_registry.requested_scope_from_inputs(
        provider_id=args.provider_id,
        model_ref=args.model_ref,
        tool_refs=args.tool_ref,
        storage_scope_ref=args.storage_scope_ref,
        evidence_scope_ref=args.evidence_scope_ref,
    )
    grants = agent_registry.load_agent_registry_grants(files=args.grant_file, directories=args.grant_dir, root=REPO_ROOT)
    return agent_registry.resolve_agent_registry_grant(
        grants=grants,
        agentpod_id=str(agentpod.get("id")),
        requested_agent_identity_ref=requested_agent_identity_ref,
        session_ref=session_ref,
        agent_machine_id=args.agent_machine_id,
        workroom_ref=args.workroom_ref or agentpod_workload_default(agentpod, "workroomRef"),
        topic_ref=args.topic_ref or agentpod_workload_default(agentpod, "topicRef"),
        grant_id=args.grant_id,
        expected_status=args.expected_grant_status,
        allow_missing_stub=not args.no_missing_stub,
        issued_at=args.issued_at,
        requested_scope=requested_scope,
        requested_expires_at=args.requested_expires_at,
        root=REPO_ROOT,
    )


def cmd_registry_resolve(args: argparse.Namespace) -> int:
    agent_registry = import_renderer(lambda: __import__("agent_machine.agent_registry", fromlist=["_unused"]))
    agentpod = load_json(args.agentpod_json)
    grant = resolve_registry_grant_from_args(args, agentpod, agent_registry)
    print(json.dumps(grant, indent=2 if args.pretty else None, sort_keys=True))
    return 0


def resolve_activation_policy_and_grant(args: argparse.Namespace, agentpod: dict[str, Any], policy_fabric: Any, agent_registry: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    policy_json = args.policy_json
    grant_json = args.grant_json
    policy_resolver_requested = bool(args.policy_file or args.policy_dir or args.policy_id or args.expected_status)
    grant_resolver_requested = bool(args.grant_file or args.grant_dir or args.grant_id or args.expected_grant_status)
    if grant_json is None and policy_json is not None and policy_resolver_requested and not grant_resolver_requested:
        grant_json = policy_json
        policy_json = None

    if policy_json is not None:
        policy = load_json(policy_json)
    else:
        policies = policy_fabric.load_policy_admissions(files=args.policy_file, directories=args.policy_dir, root=REPO_ROOT)
        policy = policy_fabric.resolve_policy_admission(policies=policies, agentpod_id=str(agentpod.get("id")), request_type="activation", deployment_receipt_id=args.deployment_receipt_id, agent_machine_id=args.agent_machine_id, provider_id=args.provider_id, policy_id=args.policy_id, expected_status=args.expected_status, allow_missing_stub=not args.no_missing_stub, decided_at=args.decided_at, root=REPO_ROOT)

    if grant_json is not None:
        grant = load_json(grant_json)
    elif grant_resolver_requested:
        grant = resolve_registry_grant_from_args(args, agentpod, agent_registry)
    else:
        raise AssertionError("grant JSON is required unless --grant-file/--grant-dir resolver inputs are provided")
    return policy, grant


def cmd_activate_evaluate(args: argparse.Namespace) -> int:
    activation = import_renderer(lambda: __import__("agent_machine.activation", fromlist=["_unused"]))
    policy_fabric = import_renderer(lambda: __import__("agent_machine.policy_fabric", fromlist=["_unused"]))
    agent_registry = import_renderer(lambda: __import__("agent_machine.agent_registry", fromlist=["_unused"]))
    agentpod = load_json(args.agentpod_json)
    policy, grant = resolve_activation_policy_and_grant(args, agentpod, policy_fabric, agent_registry)
    storage_receipts = activation.load_storage_receipts(files=args.storage_receipt_file, directories=args.storage_receipt_dir)
    storage_receipt_refs = list(args.storage_receipt_ref or [])
    if not storage_receipt_refs and storage_receipts:
        storage_receipt_refs = [str(receipt.get("id")) for receipt in storage_receipts]
    decision = activation.evaluate_activation(agentpod=agentpod, policy=policy, grant=grant, deployment_receipt_id=args.deployment_receipt_id, storage_receipt_refs=storage_receipt_refs, storage_receipts=storage_receipts if storage_receipts else None, decided_at=args.decided_at, decision_id=args.decision_id, root=REPO_ROOT)
    activation.validate_activation_decision_payload(decision, REPO_ROOT)
    print(json.dumps(decision, indent=2 if args.pretty else None, sort_keys=True))
    return 0


def cmd_steer_stub_response(args: argparse.Namespace) -> int:
    steering_stub = __import__("agent_machine.steering_stub", fromlist=["_unused"])
    request = steering_stub.load_steer_request(str(args.request_json))
    result = steering_stub.build_stub_steer_result(request, status=args.status)
    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


def cmd_steer_serve_stub(args: argparse.Namespace) -> int:
    steering_stub = __import__("agent_machine.steering_stub", fromlist=["_unused"])
    return int(steering_stub.serve_stub(host=args.host, port=args.port, status=args.status))


def cmd_steer_preflight(args: argparse.Namespace) -> int:
    steering_runtime = __import__("agent_machine.steering_runtime", fromlist=["_unused"])
    result = steering_runtime.runtime_preflight(args.sourceset)
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


def cmd_steer_serve(args: argparse.Namespace) -> int:
    steering_runtime = __import__("agent_machine.steering_runtime", fromlist=["_unused"])
    return int(steering_runtime.serve_sourceset(args.sourceset, host=args.host, port=args.port))


def cmd_steer_resolve_artifacts(args: argparse.Namespace) -> int:
    steering_artifacts = __import__("agent_machine.steering_artifacts", fromlist=["_unused"])
    result = steering_artifacts.resolve_steering_artifacts(args.sourceset, args.local_dir, args.receipt_out, allow_network=args.allow_network, dry_run=args.dry_run, revision=args.revision)
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


def add_registry_resolver_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--grant-file", action="append", type=Path, default=[])
    parser.add_argument("--grant-dir", action="append", type=Path, default=[])
    parser.add_argument("--requested-agent-identity-ref")
    parser.add_argument("--session-ref")
    parser.add_argument("--agent-machine-id")
    parser.add_argument("--workroom-ref")
    parser.add_argument("--topic-ref")
    parser.add_argument("--grant-id")
    parser.add_argument("--expected-grant-status", choices=["missing", "active", "expired", "revoked", "denied", "unknown"])
    parser.add_argument("--no-missing-stub", action="store_true")
    parser.add_argument("--provider-id")
    parser.add_argument("--model-ref")
    parser.add_argument("--tool-ref", action="append", default=[])
    parser.add_argument("--storage-scope-ref")
    parser.add_argument("--evidence-scope-ref")
    parser.add_argument("--requested-expires-at")
    parser.add_argument("--issued-at", default="1970-01-01T00:00:00Z")
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
    registry = subcommands.add_parser("registry", help="Resolve Agent Registry grant artifacts")
    registry_subcommands = registry.add_subparsers(dest="registry_command", required=True)
    registry_resolve = registry_subcommands.add_parser("resolve", help="Resolve an AgentRegistryGrant from local files/stores")
    registry_resolve.add_argument("agentpod_json", type=Path)
    add_registry_resolver_args(registry_resolve)
    registry_resolve.add_argument("--pretty", action="store_true")
    registry_resolve.set_defaults(func=cmd_registry_resolve)
    activate = subcommands.add_parser("activate", help="Evaluate activation readiness")
    activate_subcommands = activate.add_subparsers(dest="activate_command", required=True)
    activate_evaluate = activate_subcommands.add_parser("evaluate", help="Evaluate AgentPod activation decision")
    activate_evaluate.add_argument("agentpod_json", type=Path)
    activate_evaluate.add_argument("policy_json", type=Path, nargs="?")
    activate_evaluate.add_argument("grant_json", type=Path, nargs="?")
    activate_evaluate.add_argument("--deployment-receipt-id", required=True)
    activate_evaluate.add_argument("--policy-file", action="append", type=Path, default=[])
    activate_evaluate.add_argument("--policy-dir", action="append", type=Path, default=[])
    activate_evaluate.add_argument("--policy-id")
    activate_evaluate.add_argument("--expected-status", choices=["missing", "allowed", "denied", "not-required", "unknown"])
    activate_evaluate.add_argument("--no-missing-stub", action="store_true")
    activate_evaluate.add_argument("--agent-machine-id")
    activate_evaluate.add_argument("--provider-id")
    add_registry_resolver_args(activate_evaluate)
    activate_evaluate.add_argument("--storage-receipt-ref", action="append", default=[])
    activate_evaluate.add_argument("--storage-receipt-file", action="append", type=Path, default=[])
    activate_evaluate.add_argument("--storage-receipt-dir", action="append", type=Path, default=[])
    activate_evaluate.add_argument("--decided-at", default="1970-01-01T00:00:00Z")
    activate_evaluate.add_argument("--decision-id")
    activate_evaluate.add_argument("--pretty", action="store_true")
    activate_evaluate.set_defaults(func=cmd_activate_evaluate)

    steer = subcommands.add_parser("steer", help="Inspect or serve local steering endpoint stubs")
    steer_subcommands = steer.add_subparsers(dest="steer_command", required=True)
    steer = subcommands.add_parser("steer", help="Inspect or serve local steering endpoints")
    steer_subcommands = steer.add_subparsers(dest="steer_command", required=True)
    stub_response = steer_subcommands.add_parser("stub-response", help="Render a Noetica-compatible steering stub response")
    stub_response.add_argument("request_json", type=Path)
    stub_response.add_argument("--status", choices=["not_configured", "noop"], default="not_configured")
    stub_response.add_argument("--pretty", action="store_true")
    stub_response.set_defaults(func=cmd_steer_stub_response)

    serve_stub = steer_subcommands.add_parser("serve-stub", help="Serve local POST /steer contract stub")
    serve_stub.add_argument("--host", default="127.0.0.1")
    serve_stub.add_argument("--port", type=int, default=8080)
    serve_stub.add_argument("--status", choices=["not_configured", "noop"], default="not_configured")
    serve_stub.set_defaults(func=cmd_steer_serve_stub)
    preflight = steer_subcommands.add_parser("preflight", help="Inspect readiness for a registered steering sourceset")
    preflight.add_argument("--sourceset", required=True)
    preflight.add_argument("--pretty", action="store_true")
    preflight.set_defaults(func=cmd_steer_preflight)
    serve = steer_subcommands.add_parser("serve", help="Serve sourceset-aware local /steer endpoint in fail-closed mode")
    serve.add_argument("--sourceset", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.set_defaults(func=cmd_steer_serve)
    resolve_artifacts = steer_subcommands.add_parser("resolve-artifacts", help="Resolve steering artifacts and emit a receipt")
    resolve_artifacts.add_argument("--sourceset", required=True)
    resolve_artifacts.add_argument("--local-dir", type=Path, required=True)
    resolve_artifacts.add_argument("--receipt-out", type=Path, required=True)
    resolve_artifacts.add_argument("--revision", default="main")
    resolve_artifacts.add_argument("--allow-network", action="store_true")
    resolve_artifacts.add_argument("--dry-run", action="store_true")
    resolve_artifacts.add_argument("--pretty", action="store_true")
    resolve_artifacts.set_defaults(func=cmd_steer_resolve_artifacts)
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
