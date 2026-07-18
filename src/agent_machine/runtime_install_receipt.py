"""RuntimeInstallReceipt emission and validation for Agent Machine install/update flows.

This module builds, validates, and logs compact RuntimeInstallReceipt records for
runtime installation lifecycle transitions.  Full manifests and detailed artifact
payloads must be stored in evidence bundles; ordinary logs emit only compact
receipt ids and evidence references (logMode: compact_receipt_ref).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, schema_by_kind, validate_instance

INSTALL_STATES = {
    "requested",
    "manifest_resolved",
    "artifact_verified",
    "installing",
    "installed",
    "failed",
    "rolled_back",
    "partial",
    "denied",
    "deferred",
}

VERIFICATION_STATES = {"not_checked", "verified", "failed", "skipped"}

PLATFORMS = {"darwin-arm64", "darwin-x64", "linux-x64", "linux-arm64", "win32-x64"}

LOG_MODES = {"compact_receipt_ref", "full_debug_redacted"}

_TERMINAL_STATES = {"installed", "failed", "rolled_back", "partial", "denied", "deferred"}
_FAILURE_STATES = {"failed", "partial", "denied", "deferred"}


def receipt_schema_path(root: Path | None = None) -> Path:
    return schema_by_kind(root)["RuntimeInstallReceipt"]


def validate_receipt_schema(receipt: dict[str, Any], root: Path | None = None) -> None:
    """Validate a RuntimeInstallReceipt dict against the JSON Schema."""
    schema = load_json(receipt_schema_path(root))
    try:
        from jsonschema.validators import validator_for
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: jsonschema. Install with `python -m pip install -r requirements-dev.txt`."
        ) from exc
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(receipt), key=lambda err: list(err.path))
    if errors:
        rendered = []
        for err in errors:
            location = "/".join(str(part) for part in err.path) or "<root>"
            rendered.append(f"  - {location}: {err.message}")
        raise AssertionError("RuntimeInstallReceipt failed schema validation:\n" + "\n".join(rendered))


def validate_receipt_semantics(receipt: dict[str, Any], source: str = "<receipt>") -> None:
    """Validate cross-field semantic invariants for a RuntimeInstallReceipt."""
    install_state = receipt.get("installState")

    # failure_reason must be present for failure/denial/deferral/partial states
    failure_reason = receipt.get("failureReason")
    if install_state in _FAILURE_STATES and not failure_reason:
        raise AssertionError(
            f"{source}: installState={install_state!r} requires a non-empty failureReason"
        )
    if install_state == "installed" and failure_reason is not None:
        raise AssertionError(
            f"{source}: installState=installed must not carry failureReason"
        )

    # rollback_ref should be present when rolled_back
    rollback_ref = receipt.get("rollbackRef")
    if install_state == "rolled_back" and not rollback_ref:
        raise AssertionError(
            f"{source}: installState=rolled_back requires a non-null rollbackRef"
        )

    # logMode default is compact_receipt_ref
    log_mode = receipt.get("logMode")
    if log_mode not in LOG_MODES:
        raise AssertionError(f"{source}: logMode must be one of {sorted(LOG_MODES)!r}, got {log_mode!r}")

    # evidenceRefs must be non-empty
    evidence_refs = receipt.get("evidenceRefs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise AssertionError(f"{source}: evidenceRefs must be a non-empty list")


def validate_receipt(receipt: dict[str, Any], source: str = "<receipt>", root: Path | None = None) -> None:
    """Run both schema and semantic validation on a RuntimeInstallReceipt dict."""
    validate_receipt_schema(receipt, root)
    validate_receipt_semantics(receipt, source)


def build_receipt(
    *,
    receipt_id: str,
    session_ref: str,
    capability_ledger_ref: str,
    runtime_ref: str,
    target_ref: str,
    platform: str,
    install_state: str,
    manifest_ref: str,
    manifest_digest: str,
    manifest_resolved_at: str,
    artifacts: list[dict[str, Any]],
    policy_decision_ref: str,
    evidence_refs: list[str],
    started_at: str,
    captured_at: str,
    spec_version: str = "0.1.0",
    agent_machine_receipt_ref: str | None = None,
    runtime_name: str | None = None,
    runtime_version: str | None = None,
    manifest_bundle_format_version: str | int | None = None,
    rollback_ref: str | None = None,
    failure_reason: str | None = None,
    log_mode: str = "compact_receipt_ref",
    causal_refs: list[str] | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    """Construct a RuntimeInstallReceipt record.

    All full manifests and artifact payloads belong in evidence bundles; this
    record carries only compact receipt ids, digests, and evidence references.
    """
    if install_state not in INSTALL_STATES:
        raise ValueError(f"Unknown installState {install_state!r}; must be one of {sorted(INSTALL_STATES)}")
    if platform not in PLATFORMS:
        raise ValueError(f"Unknown platform {platform!r}; must be one of {sorted(PLATFORMS)}")
    if log_mode not in LOG_MODES:
        raise ValueError(f"Unknown logMode {log_mode!r}; must be one of {sorted(LOG_MODES)}")

    manifest: dict[str, Any] = {
        "manifestRef": manifest_ref,
        "manifestDigest": manifest_digest,
        "resolvedAt": manifest_resolved_at,
    }
    if manifest_bundle_format_version is not None:
        manifest["bundleFormatVersion"] = manifest_bundle_format_version

    receipt: dict[str, Any] = {
        "id": receipt_id,
        "type": "RuntimeInstallReceipt",
        "specVersion": spec_version,
        "sessionRef": session_ref,
        "capabilityLedgerRef": capability_ledger_ref,
        "agentMachineReceiptRef": agent_machine_receipt_ref,
        "runtimeRef": runtime_ref,
        "runtimeName": runtime_name,
        "runtimeVersion": runtime_version,
        "targetRef": target_ref,
        "platform": platform,
        "installState": install_state,
        "manifest": manifest,
        "artifacts": artifacts,
        "rollbackRef": rollback_ref,
        "failureReason": failure_reason,
        "logMode": log_mode,
        "causalRefs": causal_refs or [],
        "policyDecisionRef": policy_decision_ref,
        "evidenceRefs": evidence_refs,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "capturedAt": captured_at,
    }
    return receipt


def emit_compact_log(receipt: dict[str, Any]) -> str:
    """Return a compact one-line log string for operational logs.

    Full manifests and artifact payloads remain in evidence bundles.
    """
    receipt_id = receipt.get("id", "<unknown>")
    install_state = receipt.get("installState", "<unknown>")
    evidence_refs = receipt.get("evidenceRefs") or []
    evidence_summary = evidence_refs[0] if evidence_refs else "<none>"
    return (
        f"RuntimeInstallReceipt id={receipt_id} state={install_state} evidence[0]={evidence_summary}"
    )


def validate_receipt_file(path: Path, root: Path | None = None) -> None:
    """Load and validate a RuntimeInstallReceipt JSON file."""
    receipt = load_json(path)
    if not isinstance(receipt, dict):
        raise AssertionError(f"{path}: root must be a JSON object")
    source = str(path)
    validate_receipt(receipt, source=source, root=root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate or emit RuntimeInstallReceipt records")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="Validate a RuntimeInstallReceipt JSON file")
    validate.add_argument("receipt_json", type=Path)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "validate":
        validate_receipt_file(args.receipt_json)
        print(f"VALID RuntimeInstallReceipt {args.receipt_json}")
        return 0
    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
