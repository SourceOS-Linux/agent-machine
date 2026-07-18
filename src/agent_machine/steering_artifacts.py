"""Artifact resolution for local SAE steering.

This module resolves model/tokenizer/SAE files into an operator-controlled local
artifact directory and emits a SteeringArtifactReceipt. It does not load models,
load SAEs, run inference, or perform activation injection.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, validate_by_kind
from agent_machine.paths import repo_root_from_file
from agent_machine.steering_runtime import SteeringRuntimeError, load_sourceset

REPO_ROOT = repo_root_from_file(__file__)

GPT2_MODEL_FILES = [
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
]

GPT2_RES_JB_SAE_FILES = [
    "blocks.6.hook_resid_pre/cfg.json",
    "blocks.6.hook_resid_pre/sae_weights.safetensors",
    "blocks.6.hook_resid_pre/sparsity.safetensors",
]


def resolve_steering_artifacts(
    sourceset_id: str,
    local_dir: Path,
    receipt_out: Path,
    *,
    allow_network: bool = False,
    dry_run: bool = False,
    revision: str = "main",
) -> dict[str, Any]:
    """Resolve registered steering artifacts and emit a receipt.

    `dry_run=True` emits a pending receipt shape without contacting external
    services. `allow_network=True` is required for real Hugging Face resolution
    and download.
    """
    sourceset = load_sourceset(sourceset_id)
    if sourceset_id != "gpt2-small.res-jb":
        raise SteeringRuntimeError("artifact resolution currently supports only gpt2-small.res-jb")

    local_dir = Path(local_dir)
    receipt_out = Path(receipt_out)

    if dry_run:
        receipt = build_pending_receipt(sourceset_id)
    else:
        if not allow_network:
            raise SteeringRuntimeError("real artifact resolution requires --allow-network")
        receipt = resolve_gpt2_small_res_jb(sourceset, local_dir, revision=revision)

    receipt_out.parent.mkdir(parents=True, exist_ok=True)
    receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validate_by_kind(receipt_out, REPO_ROOT)
    return receipt


def resolve_gpt2_small_res_jb(sourceset: dict[str, Any], local_dir: Path, *, revision: str) -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError as exc:
        raise SteeringRuntimeError(
            "missing optional dependency: huggingface_hub. Install requirements-steering.txt on the operator machine."
        ) from exc

    api = HfApi()
    generated_at = utc_now()
    artifact_records: list[dict[str, Any]] = []

    model_repo = require_repo(sourceset, "model")
    model_revision = resolved_revision(api, model_repo, revision)
    model_root = local_dir / sourceset["sourcesetId"] / safe_repo_name(model_repo)
    for filename in GPT2_MODEL_FILES:
        path = Path(
            hf_hub_download(
                repo_id=model_repo,
                filename=filename,
                revision=model_revision,
                local_dir=str(model_root),
            )
        )
        artifact_records.append(
            artifact_record(
                role=role_for_model_file(filename),
                repo=model_repo,
                file_path=filename,
                resolved_revision_value=model_revision,
                local_path=path,
            )
        )

    sae_repo = require_repo(sourceset, "sae")
    sae_revision = resolved_revision(api, sae_repo, revision)
    sae_root = local_dir / sourceset["sourcesetId"] / safe_repo_name(sae_repo)
    for filename in GPT2_RES_JB_SAE_FILES:
        path = Path(
            hf_hub_download(
                repo_id=sae_repo,
                filename=filename,
                revision=sae_revision,
                local_dir=str(sae_root),
            )
        )
        artifact_records.append(
            artifact_record(
                role="sae-config" if filename.endswith("cfg.json") else "sae-artifact",
                repo=sae_repo,
                file_path=filename,
                resolved_revision_value=sae_revision,
                local_path=path,
            )
        )

    return {
        "specVersion": "0.1.0",
        "id": f"urn:srcos:agent-machine:steering-artifact-receipt:{sourceset['sourcesetId']}.{receipt_stamp(generated_at)}",
        "kind": "SteeringArtifactReceipt",
        "sourcesetId": sourceset["sourcesetId"],
        "status": "complete",
        "generatedAt": generated_at,
        "activationIssue": "active-steering-work",
        "artifactRecords": artifact_records,
        "missing": [],
        "storageReceiptRefs": [],
        "policyRefs": [],
        "agentRegistryGrantRefs": [],
        "receiptSafety": {
            "includeRawArtifacts": False,
            "includeAuthMaterial": False,
        },
        "notes": [
            "This receipt records resolved artifact metadata only.",
            "It does not load the model, load the SAE, run inference, or perform activation injection.",
            "A separate storage receipt, policy admission, and grant record are still required before applied steering can be accepted.",
        ],
    }


def build_pending_receipt(sourceset_id: str) -> dict[str, Any]:
    generated_at = utc_now()
    return {
        "specVersion": "0.1.0",
        "id": f"urn:srcos:agent-machine:steering-artifact-receipt:{sourceset_id}.{receipt_stamp(generated_at)}.dryrun",
        "kind": "SteeringArtifactReceipt",
        "sourcesetId": sourceset_id,
        "status": "pending",
        "generatedAt": generated_at,
        "activationIssue": "active-steering-work",
        "artifactRecords": [],
        "missing": [
            "network resolution not performed",
            "artifact files not downloaded",
            "artifact revisions not resolved",
            "artifact sha256 digests not computed",
            "storage receipts not emitted",
        ],
        "storageReceiptRefs": [],
        "policyRefs": [],
        "agentRegistryGrantRefs": [],
        "receiptSafety": {
            "includeRawArtifacts": False,
            "includeAuthMaterial": False,
        },
        "notes": [
            "Dry run receipt for validation only.",
            "Run with --allow-network on an operator machine to produce a complete receipt.",
        ],
    }


def artifact_record(
    *,
    role: str,
    repo: str,
    file_path: str,
    resolved_revision_value: str,
    local_path: Path,
) -> dict[str, Any]:
    return {
        "role": role,
        "source": {
            "type": "huggingface",
            "repo": repo,
            "filePath": file_path,
            "resolvedRevision": resolved_revision_value,
            "url": f"https://huggingface.co/{repo}/blob/{resolved_revision_value}/{file_path}",
        },
        "storage": {
            "localPath": str(local_path),
            "sizeBytes": local_path.stat().st_size,
            "storageReceiptRef": None,
        },
        "digest": {
            "algorithm": "sha256",
            "sha256": sha256_file(local_path),
            "verified": True,
        },
    }


def resolved_revision(api: Any, repo: str, revision: str) -> str:
    info = api.model_info(repo_id=repo, revision=revision)
    sha = getattr(info, "sha", None)
    if not isinstance(sha, str) or not sha:
        raise SteeringRuntimeError(f"could not resolve immutable revision for {repo}@{revision}")
    return sha


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def require_repo(sourceset: dict[str, Any], section: str) -> str:
    value = sourceset.get(section, {}).get("source", {}).get("repo")
    if not isinstance(value, str) or not value:
        raise SteeringRuntimeError(f"sourceset missing {section}.source.repo")
    return value


def role_for_model_file(filename: str) -> str:
    if filename in {"config.json", "generation_config.json"}:
        return "model-config"
    if filename in {"tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"}:
        return "tokenizer"
    if filename.endswith(".safetensors"):
        return "model-weight"
    return "other"


def safe_repo_name(repo: str) -> str:
    return repo.replace("/", "__")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def receipt_stamp(timestamp: str) -> str:
    return timestamp.lower().replace("-", "").replace(":", "").replace("+", "").replace(".", "").replace("z", "z")
