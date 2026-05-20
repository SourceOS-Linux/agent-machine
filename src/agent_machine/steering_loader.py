"""Receipt-backed local artifact verification for steering runtime.

This module verifies a SteeringArtifactReceipt before any runtime may use the
referenced files. It is deliberately fail-closed: absent files or digest mismatch
produce a not_configured result rather than a runtime claim.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, validate_by_kind
from agent_machine.paths import repo_root_from_file

REPO_ROOT = repo_root_from_file(__file__)


def verify_receipt_files(receipt_path: Path) -> dict[str, Any]:
    """Verify receipt local paths and SHA-256 digests without loading artifacts."""
    receipt_path = Path(receipt_path)
    validate_by_kind(receipt_path, REPO_ROOT)
    receipt = load_json(receipt_path)
    records = receipt.get("artifactRecords", [])
    checks = [verify_artifact_record(record) for record in records if isinstance(record, dict)]
    missing = [item for check in checks for item in check.get("missing", [])]
    digest_mismatches = [item for check in checks for item in check.get("digestMismatches", [])]
    verified = [check for check in checks if check.get("verified")]
    ready = bool(records) and len(verified) == len(records) and not missing and not digest_mismatches
    return {
        "ok": True,
        "status": "available" if ready else "not_configured",
        "receiptPath": str(receipt_path),
        "sourcesetId": receipt.get("sourcesetId"),
        "receiptStatus": receipt.get("status"),
        "artifactCount": len(records),
        "verifiedArtifactCount": len(verified),
        "readyForRuntimeUse": ready,
        "missing": missing,
        "digestMismatches": digest_mismatches,
        "checks": checks,
    }


def verify_artifact_record(record: dict[str, Any]) -> dict[str, Any]:
    source = record.get("source", {}) if isinstance(record.get("source"), dict) else {}
    storage = record.get("storage", {}) if isinstance(record.get("storage"), dict) else {}
    digest = record.get("digest", {}) if isinstance(record.get("digest"), dict) else {}
    local_path = Path(str(storage.get("localPath", "")))
    expected_sha = str(digest.get("sha256", ""))
    result: dict[str, Any] = {
        "role": record.get("role"),
        "repo": source.get("repo"),
        "filePath": source.get("filePath"),
        "resolvedRevision": source.get("resolvedRevision"),
        "localPath": str(local_path),
        "expectedSha256": expected_sha,
        "actualSha256": None,
        "exists": local_path.exists(),
        "verified": False,
        "missing": [],
        "digestMismatches": [],
    }
    if not local_path.exists():
        result["missing"].append(f"artifact file missing: {local_path}")
        return result
    if not local_path.is_file():
        result["missing"].append(f"artifact path is not a file: {local_path}")
        return result
    actual_sha = sha256_file(local_path)
    result["actualSha256"] = actual_sha
    if actual_sha != expected_sha:
        result["digestMismatches"].append(f"sha256 mismatch for {local_path}: expected {expected_sha}, got {actual_sha}")
        return result
    result["verified"] = True
    return result


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
