"""Receipt-backed local artifact verification and loading gate.

This module verifies a SteeringArtifactReceipt immediately before any runtime use
of the referenced files. It is deliberately fail-closed: absent files or digest
mismatch produce a not_configured result rather than a runtime claim.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, validate_by_kind
from agent_machine.paths import repo_root_from_file

REPO_ROOT = repo_root_from_file(__file__)


@dataclass(frozen=True)
class SteeringLoadedArtifacts:
    """Minimal loaded-artifact envelope consumed by future steering engines."""

    sourceset_id: str
    model_artifacts: list[Path]
    sae_artifacts: list[Path]
    receipt_path: Path
    synthetic: bool = False
    runtime_model: Any | None = None
    runtime_tokenizer: Any | None = None
    runtime_sae: Any | None = None


class SteeringLoader:
    """Fail-closed loader that re-verifies receipt digests before loading."""

    def load(self, receipt_path: Path, *, allow_runtime_imports: bool = False) -> dict[str, Any]:
        verified = verify_receipt_files(receipt_path)
        if verified["status"] != "available":
            return {
                **verified,
                "loadAttempted": False,
                "modelLoaded": False,
                "saeLoaded": False,
                "loadStatus": "not_configured",
                "loadError": "receipt files must exist and match SHA-256 before loading",
            }

        receipt = load_json(Path(receipt_path))
        records = receipt.get("artifactRecords", [])
        model_files = files_for_roles(records, {"model-config", "model-weight", "tokenizer"})
        sae_files = files_for_roles(records, {"sae-config", "sae-artifact"})
        synthetic = is_synthetic_receipt(records)

        if synthetic:
            loaded = SteeringLoadedArtifacts(
                sourceset_id=str(receipt.get("sourcesetId")),
                model_artifacts=model_files,
                sae_artifacts=sae_files,
                receipt_path=Path(receipt_path),
                synthetic=True,
            )
            return {
                **verified,
                "loadAttempted": True,
                "modelLoaded": True,
                "saeLoaded": True,
                "loadStatus": "available",
                "synthetic": True,
                "loadedArtifactCount": len(loaded.model_artifacts) + len(loaded.sae_artifacts),
            }

        if not allow_runtime_imports:
            return {
                **verified,
                "loadAttempted": False,
                "modelLoaded": False,
                "saeLoaded": False,
                "loadStatus": "not_configured",
                "loadError": "runtime imports disabled; pass allow_runtime_imports on an operator machine after artifact verification",
            }

        return load_runtime_artifacts(receipt, model_files, sae_files, Path(receipt_path), verified)


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


def load_runtime_artifacts(
    receipt: dict[str, Any],
    model_files: list[Path],
    sae_files: list[Path],
    receipt_path: Path,
    verified: dict[str, Any],
) -> dict[str, Any]:
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        return {**verified, "loadAttempted": True, "modelLoaded": False, "saeLoaded": False, "loadStatus": "not_configured", "loadError": f"missing optional dependency: transformers: {exc}"}
    try:
        from safetensors.torch import load_file as load_safetensors
    except ImportError as exc:
        return {**verified, "loadAttempted": True, "modelLoaded": False, "saeLoaded": False, "loadStatus": "not_configured", "loadError": f"missing optional dependency: safetensors: {exc}"}

    model_dir = common_parent(model_files)
    if model_dir is None:
        return {**verified, "loadAttempted": True, "modelLoaded": False, "saeLoaded": False, "loadStatus": "not_configured", "loadError": "could not determine local model directory from receipt"}
    if not sae_files:
        return {**verified, "loadAttempted": True, "modelLoaded": False, "saeLoaded": False, "loadStatus": "not_configured", "loadError": "receipt does not contain SAE files"}

    model = AutoModelForCausalLM.from_pretrained(str(model_dir), local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    sae_payloads: list[Any] = []
    for path in sae_files:
        if path.name.endswith(".safetensors"):
            sae_payloads.append(load_safetensors(str(path)))
        elif path.name == "cfg.json":
            sae_payloads.append(json.loads(path.read_text(encoding="utf-8")))

    loaded = SteeringLoadedArtifacts(
        sourceset_id=str(receipt.get("sourcesetId")),
        model_artifacts=model_files,
        sae_artifacts=sae_files,
        receipt_path=receipt_path,
        runtime_model=model,
        runtime_tokenizer=tokenizer,
        runtime_sae=sae_payloads,
    )
    return {**verified, "loadAttempted": True, "modelLoaded": loaded.runtime_model is not None and loaded.runtime_tokenizer is not None, "saeLoaded": bool(loaded.runtime_sae), "loadStatus": "available" if loaded.runtime_model is not None and loaded.runtime_tokenizer is not None and loaded.runtime_sae else "not_configured", "synthetic": False}


def files_for_roles(records: list[dict[str, Any]], roles: set[str]) -> list[Path]:
    return [Path(str(record.get("storage", {}).get("localPath"))) for record in records if record.get("role") in roles]


def is_synthetic_receipt(records: list[dict[str, Any]]) -> bool:
    repos = {str(record.get("source", {}).get("repo", "")) for record in records if isinstance(record.get("source"), dict)}
    return bool(repos) and all(repo.startswith("synthetic/") for repo in repos)


def common_parent(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    common = paths[0].parent
    for path in paths[1:]:
        parent = path.parent
        while common != parent and common not in parent.parents:
            if common.parent == common:
                return None
            common = common.parent
    return common


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
