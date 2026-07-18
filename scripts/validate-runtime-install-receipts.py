#!/usr/bin/env python3
"""Validate RuntimeInstallReceipt examples and semantic consistency."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.runtime_install_receipt import (  # noqa: E402
    build_receipt,
    emit_compact_log,
    validate_receipt,
    validate_receipt_file,
)

EXAMPLE_FILES = [
    REPO_ROOT / "examples" / "runtime-install-receipt.installed.json",
    REPO_ROOT / "examples" / "runtime-install-receipt.failed.json",
    REPO_ROOT / "examples" / "runtime-install-receipt.denied.json",
    REPO_ROOT / "examples" / "runtime-install-receipt.partial.json",
    REPO_ROOT / "examples" / "runtime-install-receipt.rolled_back.json",
    REPO_ROOT / "examples" / "runtime-install-receipt.deferred.json",
]


def validate_examples() -> None:
    for path in EXAMPLE_FILES:
        validate_receipt_file(path, REPO_ROOT)
        print(f"VALID RuntimeInstallReceipt example {path.relative_to(REPO_ROOT)}")


def validate_compact_log_output() -> None:
    """Confirm emit_compact_log produces a single-line compact reference string."""
    receipt = build_receipt(
        receipt_id="urn:srcos:receipt:runtime-install:smoke-test-0001",
        session_ref="urn:srcos:session:smoke-0001",
        capability_ledger_ref="urn:srcos:capability-ledger:smoke-0001",
        runtime_ref="urn:srcos:runtime:smoke-runtime@0.0.1",
        target_ref="urn:srcos:target:smoke-target-0001",
        platform="linux-x64",
        install_state="installed",
        manifest_ref="urn:srcos:artifact:smoke-manifest",
        manifest_digest="sha256:1111111111111111111111111111111111111111111111111111111111111111",
        manifest_resolved_at="2026-05-06T10:00:00Z",
        artifacts=[
            {
                "artifactRef": "urn:srcos:artifact:smoke-runtime-bin",
                "digest": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
                "sizeBytes": 4096,
                "verificationState": "verified",
            }
        ],
        policy_decision_ref="urn:srcos:decision:smoke-policy-0001",
        evidence_refs=["urn:srcos:evidence:smoke-evidence-0001"],
        started_at="2026-05-06T10:00:00Z",
        captured_at="2026-05-06T10:00:05Z",
        finished_at="2026-05-06T10:00:04Z",
    )
    validate_receipt(receipt, source="<smoke-test>", root=REPO_ROOT)
    log_line = emit_compact_log(receipt)
    if "\n" in log_line:
        raise AssertionError("emit_compact_log must produce a single-line string")
    if "urn:srcos:receipt:runtime-install:smoke-test-0001" not in log_line:
        raise AssertionError(f"compact log must include receipt id, got: {log_line!r}")
    if "installed" not in log_line:
        raise AssertionError(f"compact log must include installState, got: {log_line!r}")
    print(f"VALID compact log output: {log_line}")


def validate_failure_states() -> None:
    """Confirm that failure states require failureReason and missing states are rejected."""
    base = dict(
        receipt_id="urn:srcos:receipt:runtime-install:semantics-test-0001",
        session_ref="urn:srcos:session:semantics-0001",
        capability_ledger_ref="urn:srcos:capability-ledger:semantics-0001",
        runtime_ref="urn:srcos:runtime:semantics-runtime@0.0.1",
        target_ref="urn:srcos:target:semantics-target-0001",
        platform="linux-x64",
        manifest_ref="urn:srcos:artifact:semantics-manifest",
        manifest_digest="sha256:1111111111111111111111111111111111111111111111111111111111111111",
        manifest_resolved_at="2026-05-06T10:00:00Z",
        artifacts=[
            {
                "artifactRef": "urn:srcos:artifact:semantics-runtime-bin",
                "digest": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
                "verificationState": "not_checked",
            }
        ],
        policy_decision_ref="urn:srcos:decision:semantics-policy-0001",
        evidence_refs=["urn:srcos:evidence:semantics-evidence-0001"],
        started_at="2026-05-06T10:00:00Z",
        captured_at="2026-05-06T10:00:05Z",
    )

    # failure states must have failureReason
    for bad_state in ("failed", "partial", "denied", "deferred"):
        receipt = build_receipt(**base, install_state=bad_state, failure_reason=None)
        try:
            validate_receipt(receipt, root=REPO_ROOT)
            raise AssertionError(f"Expected semantic error for installState={bad_state!r} without failureReason")
        except AssertionError as exc:
            if "failureReason" not in str(exc):
                raise
        print(f"VALID semantic rejection: installState={bad_state!r} without failureReason")

    # rolled_back must have rollbackRef
    receipt = build_receipt(**base, install_state="rolled_back", failure_reason="health_check_failed", rollback_ref=None)
    try:
        validate_receipt(receipt, root=REPO_ROOT)
        raise AssertionError("Expected semantic error for installState=rolled_back without rollbackRef")
    except AssertionError as exc:
        if "rollbackRef" not in str(exc):
            raise
    print("VALID semantic rejection: installState=rolled_back without rollbackRef")

    # installed must not carry failureReason
    receipt = build_receipt(**base, install_state="installed", failure_reason="should_not_be_here")
    try:
        validate_receipt(receipt, root=REPO_ROOT)
        raise AssertionError("Expected semantic error for installState=installed with failureReason")
    except AssertionError as exc:
        if "failureReason" not in str(exc):
            raise
    print("VALID semantic rejection: installState=installed with failureReason")

    # empty evidenceRefs must be rejected
    bad_receipt = build_receipt(**{**base, "evidence_refs": []}, install_state="installed")
    try:
        validate_receipt(bad_receipt, root=REPO_ROOT)
        raise AssertionError("Expected schema/semantic error for empty evidenceRefs")
    except AssertionError:
        pass
    print("VALID semantic rejection: empty evidenceRefs")


def main() -> int:
    validate_examples()
    validate_compact_log_output()
    validate_failure_states()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
