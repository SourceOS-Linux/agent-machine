#!/usr/bin/env python3
"""Run deterministic steering harness against a local request fixture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_machine.steering_engine import STATUS_OK, SteeringEngine, build_hook, parse_steering_run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic steering harness")
    parser.add_argument("request_json", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.request_json.read_text(encoding="utf-8"))
    result = SteeringEngine().run(payload)
    run = parse_steering_run(payload)
    hook = build_hook(run)

    print(json.dumps({"result": result, "hook": hook}, indent=2 if args.pretty else None, sort_keys=True))

    if result.get("status") != STATUS_OK:
        print(f"unexpected status: {result.get('status')}", file=sys.stderr)
        return 1
    if result.get("baseline") == result.get("steered"):
        print("expected deterministic baseline and transformed outputs to differ", file=sys.stderr)
        return 1
    if hook.get("hook_name") != "blocks.6.hook_resid_pre":
        print(f"unexpected hook_name: {hook.get('hook_name')}", file=sys.stderr)
        return 1
    if result.get("feature_id") != run.feature_id or result.get("layer") != run.layer or result.get("strength") != run.strength:
        print("result did not preserve request fields", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
