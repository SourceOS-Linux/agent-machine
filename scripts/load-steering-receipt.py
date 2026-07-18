#!/usr/bin/env python3
"""Run receipt-backed steering loader preflight or synthetic load."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_machine.steering_loader import SteeringLoader  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Load or preflight a steering artifact receipt")
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--attempt-load", action="store_true")
    parser.add_argument("--allow-runtime-imports", action="store_true")
    parser.add_argument("--expect-status", choices=["available", "not_configured"])
    parser.add_argument("--expect-model-loaded", choices=["true", "false"])
    parser.add_argument("--expect-sae-loaded", choices=["true", "false"])
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    if not args.attempt_load and args.allow_runtime_imports:
        print("--allow-runtime-imports requires --attempt-load", file=sys.stderr)
        return 2

    if args.attempt_load:
        result = SteeringLoader().load(args.receipt, allow_runtime_imports=args.allow_runtime_imports)
    else:
        from agent_machine.steering_loader import verify_receipt_files

        result = verify_receipt_files(args.receipt)

    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))

    if args.expect_status and result.get("status") != args.expect_status:
        print(f"expected status {args.expect_status}, got {result.get('status')}", file=sys.stderr)
        return 1
    if args.expect_model_loaded is not None:
        expected = args.expect_model_loaded == "true"
        if bool(result.get("modelLoaded")) is not expected:
            print(f"expected modelLoaded={expected}, got {result.get('modelLoaded')}", file=sys.stderr)
            return 1
    if args.expect_sae_loaded is not None:
        expected = args.expect_sae_loaded == "true"
        if bool(result.get("saeLoaded")) is not expected:
            print(f"expected saeLoaded={expected}, got {result.get('saeLoaded')}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
