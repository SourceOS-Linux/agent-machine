"""Transitional Python CLI for Agent Machine package-owned commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_machine import __version__
from agent_machine.contracts import load_json
from agent_machine.paths import (
    default_config_path,
    default_evidence_path,
    default_model_cache_path,
    default_runtime_cache_path,
    default_runtime_path,
    default_state_path,
)
from agent_machine.renderers import k8s as k8s_renderer
from agent_machine.renderers import plan as plan_renderer
from agent_machine.renderers import quadlet as quadlet_renderer


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


def cmd_render_plan(args: argparse.Namespace) -> int:
    pod = load_json(args.agentpod_json)
    plan_renderer.validate_agentpod(args.agentpod_json, pod)
    plan = plan_renderer.render_plan(args.agentpod_json, pod)
    plan_renderer.validate_against_schema(plan, plan_renderer.PLAN_SCHEMA_PATH, "AgentPodDeploymentPlan")
    plan_renderer.emit_json(plan, args.pretty)
    return 0


def cmd_render_receipt(args: argparse.Namespace) -> int:
    pod = load_json(args.agentpod_json)
    plan_renderer.validate_agentpod(args.agentpod_json, pod)
    plan = plan_renderer.render_plan(args.agentpod_json, pod)
    plan_renderer.validate_against_schema(plan, plan_renderer.PLAN_SCHEMA_PATH, "AgentPodDeploymentPlan")
    receipt = plan_renderer.render_receipt(args.agentpod_json, pod, plan, args.artifact_path)
    plan_renderer.validate_against_schema(receipt, plan_renderer.RECEIPT_SCHEMA_PATH, "DeploymentReceipt")
    plan_renderer.emit_json(receipt, args.pretty)
    return 0


def cmd_render_quadlet(args: argparse.Namespace) -> int:
    pod = load_json(args.agentpod_json)
    quadlet_renderer.require_local_quadlet(args.agentpod_json, pod)
    rendered = quadlet_renderer.render_quadlet(pod)
    if args.compare:
        quadlet_renderer.compare(args.compare, rendered)
    else:
        print(rendered, end="")
    return 0


def cmd_render_k8s(args: argparse.Namespace) -> int:
    pod = load_json(args.agentpod_json)
    k8s_renderer.require_k8s_agentpod(args.agentpod_json, pod)
    docs = k8s_renderer.render_documents(pod)
    if args.compare:
        k8s_renderer.compare(args.compare, docs)
    else:
        print(k8s_renderer.dump_documents(docs), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent Machine Python CLI")
    subcommands = parser.add_subparsers(dest="command", required=True)

    version = subcommands.add_parser("version", help="Print package version")
    version.set_defaults(func=cmd_version)

    paths = subcommands.add_parser("paths", help="Print default runtime paths")
    paths.add_argument("--format", choices=["text", "json"], default="text")
    paths.set_defaults(func=cmd_paths)

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
