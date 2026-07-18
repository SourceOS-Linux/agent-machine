#!/usr/bin/env python3
"""Validate SourceOS immutable-node projection fixtures and safety boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_machine.contracts import load_json
from agent_machine.immutable_node import load_projection_index, validate_profile

FIXTURE_DIR = ROOT / "fixtures" / "sourceos-spec"
PROFILE = FIXTURE_DIR / "immutablenodeprofile.m2-asahi-agent-node-dev.json"


def main() -> int:
    index = load_projection_index(FIXTURE_DIR)
    profile = load_json(PROFILE)
    validate_profile(profile, index)

    if profile.get("primaryPlane") == "desktop-consumer":
        raise AssertionError("ImmutableNodeProfile must not be desktop-owned")
    if profile.get("substrate", {}).get("sociosRequired") is not False:
        raise AssertionError("ImmutableNodeProfile must keep Socios optional for base SourceOS nodes")

    for ref in profile.get("hostCapabilityPlacementRefs", []):
        capability = index[ref]
        if capability.get("mandatoryForBaseNode") is True and capability.get("requiresEnrollment") is True:
            raise AssertionError(f"{ref}: mandatory base capability must not require enrollment")
        if capability.get("authority") == "socios-optional-pack" and capability.get("mandatoryForBaseNode") is True:
            raise AssertionError(f"{ref}: Socios optional pack cannot be mandatory")

    for ref in profile.get("nodeStateSchemaRefs", []):
        state_root = index[ref]
        root_path = state_root.get("rootPath", "")
        if not str(root_path).startswith(("/var/lib/", "/var/cache/")):
            raise AssertionError(f"{ref}: state root must live under /var/lib or /var/cache")
        if str(root_path).startswith(("/etc", "/usr")):
            raise AssertionError(f"{ref}: state root must not live under /etc or /usr")

    print(f"VALID immutable-node profile {PROFILE.relative_to(ROOT)}")
    print("VALID immutable-node safety boundary: Socios optional, desktop consumer-only, /var-only state roots")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
