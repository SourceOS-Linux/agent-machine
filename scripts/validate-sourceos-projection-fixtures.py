#!/usr/bin/env python3
"""Validate SourceOS projection fixture shape without depending on sourceos-spec checkout."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "sourceos-spec"

EXPECTED = {
    "sourceosmodelcarryref.json": "SourceOSModelCarryRef",
    "inferenceprovider.json": "InferenceProvider",
    "modelresidency.json": "ModelResidency",
    "placementfact.json": "PlacementFact",
    "agentmachinereceipt.json": "AgentMachineReceipt",
}

REQUIRED = {
    "SourceOSModelCarryRef": ["id", "type", "specVersion", "modelRef", "governanceRef", "routerProfileRef", "mutableModelState"],
    "InferenceProvider": ["id", "type", "specVersion", "providerClass", "endpointMode", "executionProfile", "trustPosture"],
    "ModelResidency": ["id", "type", "specVersion", "machineRef", "modelCarryRef", "providerRef", "residencyState", "observedAt"],
    "PlacementFact": ["id", "type", "specVersion", "machineRef", "observedAt", "hardware", "isolation", "trustPosture"],
    "AgentMachineReceipt": ["id", "type", "specVersion", "machineRef", "receiptClass", "issuedAt", "placementFactRefs", "policyDecisionRef", "verdict"],
}


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise AssertionError(f"{path}: root must be a JSON object")
    return data


def main() -> int:
    for filename, expected_type in EXPECTED.items():
        path = FIXTURE_DIR / filename
        if not path.exists():
            raise AssertionError(f"missing fixture: {path.relative_to(ROOT)}")
        data = load(path)
        actual_type = data.get("type")
        if actual_type != expected_type:
            raise AssertionError(f"{path}: expected type {expected_type!r}, got {actual_type!r}")
        for field in REQUIRED[expected_type]:
            if field not in data:
                raise AssertionError(f"{path}: missing required projection field {field!r}")
        if not str(data.get("id", "")).startswith("urn:srcos:"):
            raise AssertionError(f"{path}: id must use urn:srcos prefix")
        print(f"VALID SourceOS projection fixture {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
