#!/usr/bin/env python3
"""Validate AttestationDecision contract + examples (T2-1, T2-4/5).

Asserts the fail-closed activation rule by construction:
  * every example validates against contracts/attestation-decision.schema.json;
  * all eight required BLOCKING checks are present;
  * activation_permitted is true IFF every blocking check passed — a single
    blocking failure must deny activation;
  * overall_status is consistent (pass = all checks pass; fail = a blocking
    check failed; partial otherwise);
  * the passed/failed-sip/failed-mdm fixtures carry the expected verdicts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("ERR: jsonschema not installed", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "attestation-decision.schema.json"
EXAMPLES = {
    "passed": True,
    "failed-sip": False,
    "failed-mdm": False,
}
REQUIRED_BLOCKING = {
    "SIP_STATUS", "NVRAM_INTEGRITY", "MDM_PROFILE_AUDIT", "SEP_PARTICIPATION",
    "SECURITY_DB_SCHEMA", "DNS_INTEGRITY", "TLS_CIPHER_AUDIT", "EFI_SIGNATURE",
}


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    schema = load(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)

    for name, expect_permitted in EXAMPLES.items():
        path = ROOT / "examples" / f"attestation-decision.{name}.json"
        doc = load(path)
        errs = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        if errs:
            fail(f"{path.name} schema-invalid: {errs[0].message}")

        checks = doc["check_results"]
        blocking = [c for c in checks if c["blocking"]]
        blocking_ids = {c["check_id"] for c in blocking}
        missing = REQUIRED_BLOCKING - blocking_ids
        if missing:
            fail(f"{path.name}: missing required blocking checks: {sorted(missing)}")

        all_blocking_pass = all(c["status"] == "pass" for c in blocking)
        any_blocking_fail = any(c["status"] == "fail" for c in blocking)
        all_pass = all(c["status"] == "pass" for c in checks)

        # activation_permitted IFF all blocking checks pass.
        if doc["activation_permitted"] != all_blocking_pass:
            fail(
                f"{path.name}: activation_permitted={doc['activation_permitted']} but "
                f"all_blocking_pass={all_blocking_pass} (fail-closed rule violated)"
            )
        # overall_status consistency.
        expected_overall = "fail" if any_blocking_fail else ("pass" if all_pass else "partial")
        if doc["overall_status"] != expected_overall:
            fail(f"{path.name}: overall_status={doc['overall_status']} but expected {expected_overall}")
        # fixture-level expectation.
        if doc["activation_permitted"] != expect_permitted:
            fail(f"{path.name}: expected activation_permitted={expect_permitted}")

    print(
        f"OK: AttestationDecision schema + {len(EXAMPLES)} examples valid; "
        f"fail-closed activation rule and 8 blocking checks enforced"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
