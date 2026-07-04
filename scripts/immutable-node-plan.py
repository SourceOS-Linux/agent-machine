#!/usr/bin/env python3
"""Plan, preflight, and guarded-apply SourceOS immutable-node profiles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_machine.contracts import load_json
from agent_machine.immutable_node import (
    ApplyOptions,
    emit_json,
    load_projection_index,
    preflight_plan,
    render_plan,
    validate_profile,
)

DEFAULT_PROFILE = ROOT / "fixtures" / "sourceos-spec" / "immutablenodeprofile.m2-asahi-agent-node-dev.json"
DEFAULT_FIXTURES_DIR = ROOT / "fixtures" / "sourceos-spec"
DEFAULT_MUTATION_CLASSES = ("state-roots", "staging-artifacts")


def _load_plan(args: argparse.Namespace) -> dict:
    profile_path = args.profile_json
    profile = load_json(profile_path)
    index = load_projection_index(args.fixtures_dir)
    return render_plan(profile_path, profile, index)


def cmd_validate(args: argparse.Namespace) -> int:
    profile = load_json(args.profile_json)
    index = load_projection_index(args.fixtures_dir)
    validate_profile(profile, index)
    emit_json(
        {
            "kind": "ImmutableNodeValidation",
            "specVersion": "0.1.0",
            "profileRef": profile["id"],
            "fixturesDir": str(args.fixtures_dir),
            "verdict": "valid",
        },
        args.pretty,
    )
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    emit_json(_load_plan(args), args.pretty)
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    plan = _load_plan(args)
    emit_json(preflight_plan(plan, args.target_root, tuple(args.mutation_class)), args.pretty)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    from agent_machine.immutable_node import apply_plan

    plan = _load_plan(args)
    evidence = apply_plan(
        plan,
        ApplyOptions(
            target_root=args.target_root,
            execute=args.execute,
            policy_ok=args.policy_ok,
            mutation_classes=tuple(args.mutation_class),
            evidence_out=args.evidence_out,
        ),
    )
    emit_json(evidence, args.pretty)
    return 0


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("profile_json", type=Path, nargs="?", default=DEFAULT_PROFILE)
    parser.add_argument("--fixtures-dir", type=Path, default=DEFAULT_FIXTURES_DIR)
    parser.add_argument("--pretty", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SourceOS immutable-node plan/preflight/apply helper")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="Validate immutable-node profile and referenced projection fixtures")
    add_common_arguments(validate)
    validate.set_defaults(func=cmd_validate)

    plan = subcommands.add_parser("plan", help="Render ImmutableNodePlan JSON")
    add_common_arguments(plan)
    plan.set_defaults(func=cmd_plan)

    preflight = subcommands.add_parser("preflight", help="Preflight state-root and staging-artifact mutation without writing")
    add_common_arguments(preflight)
    preflight.add_argument("--target-root", type=Path, required=True)
    preflight.add_argument("--mutation-class", action="append", choices=sorted(DEFAULT_MUTATION_CLASSES), default=list(DEFAULT_MUTATION_CLASSES))
    preflight.set_defaults(func=cmd_preflight)

    apply = subcommands.add_parser("apply", help="Apply guarded immutable-node mutation")
    add_common_arguments(apply)
    apply.add_argument("--target-root", type=Path, required=True)
    apply.add_argument("--mutation-class", action="append", choices=sorted(DEFAULT_MUTATION_CLASSES), default=list(DEFAULT_MUTATION_CLASSES))
    apply.add_argument("--execute", action="store_true", help="Required to permit mutation")
    apply.add_argument("--policy-ok", action="store_true", help="Required bootstrap policy assertion")
    apply.add_argument("--evidence-out", type=Path)
    apply.set_defaults(func=cmd_apply)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
