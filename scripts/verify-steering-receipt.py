#!/usr/bin/env python3
"""Verify steering artifact receipt file paths and SHA-256 digests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_machine.steering_loader import verify_receipt_files  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify steering artifact receipt paths and digests")
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--expect-status", choices=["available", "not_configured"])
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = verify_receipt_files(args.receipt)
    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))

    if args.expect_status and result.get("status") != args.expect_status:
        print(f"expected status {args.expect_status}, got {result.get('status')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
