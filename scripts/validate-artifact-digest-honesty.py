#!/usr/bin/env python3
"""Validate that artifact receipts cannot claim verification they did not perform.

A receipt that records `verified: true` for a digest it computed from the bytes
it just downloaded asserts nothing: with no pinned expectation there is nothing
to compare against. This validator holds the line in both directions — it
asserts the honest shapes are accepted AND that the dishonest ones are rejected.

The negative controls are the point. A constraint with no negative control is
indistinguishable from a constraint that is not enforced.
"""

from __future__ import annotations

import copy
import hashlib
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.contracts import jsonschema_validator_for, load_json  # noqa: E402
from agent_machine.steering_artifacts import (  # noqa: E402
    artifact_record,
    build_pending_receipt,
    pinned_digests,
)
from agent_machine.steering_runtime import SteeringRuntimeError  # noqa: E402

RECEIPT_SCHEMA = REPO_ROOT / "contracts" / "steering-artifact-receipt.schema.json"
PINNED_EXAMPLE = REPO_ROOT / "examples" / "steering-artifact-receipts" / "synthetic.available.steering-artifact-receipt.json"
UNPINNED_EXAMPLE = REPO_ROOT / "examples" / "steering-artifact-receipts" / "gpt2-small-res-jb.missing.steering-artifact-receipt.json"

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def receipt_validator():
    schema = load_json(RECEIPT_SCHEMA)
    return jsonschema_validator_for()(schema)(schema)


def with_digest(base: dict, digest: dict) -> dict:
    receipt = copy.deepcopy(base)
    receipt["artifactRecords"] = [copy.deepcopy(receipt["artifactRecords"][0])]
    receipt["artifactRecords"][0]["digest"] = digest
    return receipt


def expect_valid(validator, payload: dict, label: str) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        raise AssertionError(f"{label}: expected VALID, rejected with: {errors[0].message}")
    print(f"ACCEPTED {label}")


def expect_invalid(validator, payload: dict, label: str) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if not errors:
        raise AssertionError(f"{label}: expected REJECTED, but the schema accepted it")
    print(f"REJECTED {label}")


def check_schema_constraints() -> None:
    validator = receipt_validator()
    base = load_json(PINNED_EXAMPLE)

    expect_valid(
        validator,
        with_digest(base, {
            "algorithm": "sha256", "sha256": DIGEST_A, "expectedSha256": DIGEST_A,
            "verified": True, "verificationMethod": "pinned-digest",
        }),
        "pinned digest, compared equal, verified true",
    )
    expect_valid(
        validator,
        with_digest(base, {
            "algorithm": "sha256", "sha256": DIGEST_A,
            "verified": False, "verificationMethod": "trust-on-first-use",
        }),
        "unpinned digest, verified false",
    )

    # The three shapes this change exists to make unrepresentable.
    expect_invalid(
        validator,
        with_digest(base, {"algorithm": "sha256", "sha256": DIGEST_A, "verified": True}),
        "verified true with no verificationMethod (the pre-change shape)",
    )
    expect_invalid(
        validator,
        with_digest(base, {
            "algorithm": "sha256", "sha256": DIGEST_A,
            "verified": True, "verificationMethod": "trust-on-first-use",
        }),
        "verified true while admitting nothing was compared",
    )
    expect_invalid(
        validator,
        with_digest(base, {
            "algorithm": "sha256", "sha256": DIGEST_A,
            "verified": True, "verificationMethod": "pinned-digest",
        }),
        "verified true claiming a pin but carrying no expectedSha256",
    )


def check_fail_closed_before_fetch() -> None:
    """digestRequired with no pins must refuse, not download-then-shrug."""
    try:
        pinned_digests({"model": {"digestRequired": True}}, "model")
    except SteeringRuntimeError as exc:
        if "refusing to resolve" not in str(exc):
            raise AssertionError(f"unexpected refusal message: {exc}") from exc
        print("REFUSED  digestRequired:true with no expectedDigests block")
    else:
        raise AssertionError("digestRequired:true with no pins must fail closed")

    pins = pinned_digests(
        {"model": {"digestRequired": True, "expectedDigests": {"algorithm": "sha256", "files": {"config.json": DIGEST_A}}}},
        "model",
    )
    if pins != {"config.json": DIGEST_A}:
        raise AssertionError(f"expected pins to be returned, got {pins}")
    print("ALLOWED  digestRequired:true with pins present")

    if pinned_digests({"sae": {}}, "sae") != {}:
        raise AssertionError("absent digestRequired must not raise")
    print("ALLOWED  digestRequired absent, no pins")


def check_record_records_what_happened() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.safetensors"
        path.write_bytes(b"steering artifact bytes")
        real = hashlib.sha256(path.read_bytes()).hexdigest()
        common = dict(role="model-weight", repo="openai-community/gpt2",
                      file_path="model.safetensors", resolved_revision_value="deadbeef",
                      local_path=path)

        unpinned = artifact_record(**common)["digest"]
        if unpinned["verified"] is not False or unpinned["verificationMethod"] != "trust-on-first-use":
            raise AssertionError(f"unpinned record must not claim verification: {unpinned}")
        print("RECORDED unpinned download as trust-on-first-use, verified false")

        pinned = artifact_record(**common, expected_sha256=real)["digest"]
        if pinned["verified"] is not True or pinned["verificationMethod"] != "pinned-digest":
            raise AssertionError(f"matching pin must verify: {pinned}")
        if pinned["expectedSha256"] != real:
            raise AssertionError("verified record must carry the value it compared against")
        print("RECORDED matching pin as pinned-digest, verified true")

        try:
            artifact_record(**common, expected_sha256=DIGEST_B)
        except SteeringRuntimeError as exc:
            if "digest mismatch" not in str(exc):
                raise AssertionError(f"unexpected mismatch message: {exc}") from exc
            print("RAISED   on digest mismatch")
        else:
            raise AssertionError("a digest mismatch must raise, not be recorded")


def check_dry_run_reports_gap() -> None:
    sourceset = load_json(REPO_ROOT / "examples" / "steering-sourcesets" / "gpt2-small-res-jb.steering-sourceset.json")
    missing = build_pending_receipt("gpt2-small.res-jb", sourceset)["missing"]
    if not any("expectedDigests absent" in item for item in missing):
        raise AssertionError(f"dry run must report the unsatisfiable pin requirement, got: {missing}")
    print("REPORTED dry run names the missing pin block instead of raising")


def main() -> int:
    check_schema_constraints()
    check_fail_closed_before_fetch()
    check_record_records_what_happened()
    check_dry_run_reports_gap()
    print("\nOK artifact digest honesty: verification cannot be claimed without a comparison")
    return 0


if __name__ == "__main__":
    sys.exit(main())
