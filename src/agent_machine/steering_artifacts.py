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
    consent_record: Path | str | None = None,
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
        # A dry run fetches nothing, so an unsatisfiable pin requirement is
        # reported rather than raised — this is the cheap way to discover a
        # sourceset cannot be verified before anyone tries to fetch it.
        receipt = build_pending_receipt(sourceset_id, sourceset)
    else:
        if not allow_network:
            raise SteeringRuntimeError("real artifact resolution requires --allow-network")
        # --allow-network is an OPERATOR affordance: it says this box has connectivity.
        # It has never said a person agreed to these bytes landing on their disk, and
        # treating it as though it did is what makes staging silently unconsented.
        consent = load_json(Path(consent_record)) if consent_record else None
        assert_consent_permits_download(
            consent,
            sourceset,
            repos=[require_repo(sourceset, "model"), require_repo(sourceset, "sae")],
        )
        # Fail closed BEFORE the first network call: a sourceset that requires
        # digest pinning but carries no pins can never be verified, so it must
        # not be fetched at all. Adjudicating this after the bytes have landed
        # is the ordering error this resolver exists to avoid.
        for section in ("model", "sae"):
            pinned_digests(sourceset, section)
        receipt = resolve_gpt2_small_res_jb(sourceset, local_dir, revision=revision, consent=consent)

    receipt_out.parent.mkdir(parents=True, exist_ok=True)
    receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validate_by_kind(receipt_out, REPO_ROOT)
    return receipt


def resolve_gpt2_small_res_jb(sourceset: dict[str, Any], local_dir: Path, *, revision: str, consent: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError as exc:
        raise SteeringRuntimeError(
            "missing optional dependency: huggingface_hub. Install requirements-steering.txt on the operator machine."
        ) from exc

    api = HfApi()
    generated_at = utc_now()
    artifact_records: list[dict[str, Any]] = []

    model_pins = pinned_digests(sourceset, "model")
    sae_pins = pinned_digests(sourceset, "sae")

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
                expected_sha256=model_pins.get(filename),
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
                expected_sha256=sae_pins.get(filename),
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
        "consent": assert_consent_permits_download(
            consent, sourceset, repos=[model_repo, sae_repo]
        ),
        "outstandingPolicyRequirements": outstanding_policy_requirements(sourceset),
        "receiptSafety": {
            "includeRawArtifacts": False,
            "includeAuthMaterial": False,
        },
        "notes": [
            "This receipt records resolved artifact metadata only.",
            "It does not load the model, load the SAE, run inference, or perform activation injection.",
            "A separate storage receipt, policy admission, and grant record are still required before applied steering can be accepted.",
            "consent.checkedBefore records WHEN the decision was adjudicated relative to the fetch; 'download' means no bytes were requested until it passed.",
        ],
    }


def build_pending_receipt(sourceset_id: str, sourceset: dict[str, Any] | None = None) -> dict[str, Any]:
    generated_at = utc_now()
    unpinned: list[str] = []
    if sourceset is not None:
        for section in ("model", "sae"):
            block = sourceset.get(section, {})
            if isinstance(block, dict) and not block.get("expectedDigests", {}).get("files"):
                requirement = "required" if block.get("digestRequired") else "not required"
                unpinned.append(
                    f"{section}.expectedDigests absent (digestRequired {requirement}): "
                    f"{section} artifacts could only be recorded trust-on-first-use"
                )
        if consent_required(sourceset):
            unpinned.append(
                "consent.requiresUserConsent is true: a granted ArtifactConsentRecord must be "
                "supplied via --consent-record before any remote is contacted"
            )
        for requirement in outstanding_policy_requirements(sourceset):
            unpinned.append(f"{requirement} still required before activation (not discharged by resolution)")
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
        ]
        + unpinned,
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


def consent_required(sourceset: dict[str, Any]) -> bool:
    block = sourceset.get("consent")
    return bool(isinstance(block, dict) and block.get("requiresUserConsent"))


def assert_consent_permits_download(
    consent: dict[str, Any] | None,
    sourceset: dict[str, Any],
    *,
    repos: list[str],
    now: str | None = None,
) -> dict[str, Any]:
    """Adjudicate consent BEFORE the first byte is fetched.

    Every check here is deliberately positioned ahead of the download rather than
    ahead of activation. A grant adjudicated after the bytes land governs whether
    the artifacts may be USED; it cannot govern whether they may ARRIVE, and by the
    time it is consulted the disk, the bandwidth and the exposure have already been
    spent. That ordering — fetch first, adjudicate later — is the pattern this
    function exists to invert.
    """
    sourceset_id = str(sourceset.get("sourcesetId", ""))
    if not consent_required(sourceset):
        return {"required": False, "checkedBefore": "download", "consentRef": None}

    if consent is None:
        raise SteeringRuntimeError(
            f"{sourceset_id}: consent.requiresUserConsent is true but no ArtifactConsentRecord "
            "was supplied; refusing to fetch"
        )

    if str(consent.get("kind")) != "ArtifactConsentRecord":
        raise SteeringRuntimeError("consent record is not an ArtifactConsentRecord")

    if str(consent.get("sourcesetId", "")) != sourceset_id:
        raise SteeringRuntimeError(
            f"consent record covers {consent.get('sourcesetId')!r}, not {sourceset_id!r}; "
            "consent does not generalise across sourcesets"
        )

    if str(consent.get("decision")) != "granted":
        raise SteeringRuntimeError(
            f"{sourceset_id}: consent was {consent.get('decision')!r}; refusing to fetch"
        )

    # Agreeing that something may run if present is not agreeing that it may be put there.
    if str(consent.get("scope")) not in {"download", "download-and-activation"}:
        raise SteeringRuntimeError(
            f"{sourceset_id}: consent scope is {consent.get('scope')!r}, which does not "
            "authorise a download; refusing to fetch"
        )

    if consent.get("revokedAt"):
        raise SteeringRuntimeError(
            f"{sourceset_id}: consent was revoked at {consent['revokedAt']}; refusing to fetch"
        )

    stamp = now or utc_now()
    expires = consent.get("expiresAt")
    if expires and str(expires) <= stamp:
        raise SteeringRuntimeError(
            f"{sourceset_id}: consent expired at {expires}; refusing to fetch"
        )

    # Consent to an undisclosed remote is not consent to that remote.
    disclosed = set(consent.get("disclosure", {}).get("artifactRepos", []))
    undisclosed = [r for r in repos if r not in disclosed]
    if undisclosed:
        raise SteeringRuntimeError(
            f"{sourceset_id}: would fetch from undisclosed repo(s) {', '.join(sorted(undisclosed))}; "
            f"consent disclosed only {', '.join(sorted(disclosed)) or '(none)'}; refusing to fetch"
        )

    return {
        "required": True,
        "checkedBefore": "download",
        "consentRef": str(consent.get("id", "")),
        "scope": str(consent.get("scope")),
        "decidedAt": str(consent.get("decidedAt", "")),
        "subjectRef": str(consent.get("subject", {}).get("principalRef", "")),
        "attestation": str(consent.get("subject", {}).get("attestation", "")),
        "declaredBytes": consent.get("disclosure", {}).get("declaredBytes"),
    }


def outstanding_policy_requirements(sourceset: dict[str, Any]) -> list[str]:
    """Policy requirements the sourceset declares that resolution does not satisfy.

    The sourceset has always declared requiresGrant, requiresPolicyAdmission,
    requiresStorageReceipt and requiresEvidence, and resolve_steering_artifacts read
    none of them. They gate activation rather than fetching, so resolution cannot
    discharge them — but it can stop pretending they are not there, and name them in
    the receipt so a reader sees what still has to happen before use.
    """
    policy = sourceset.get("policy", {})
    if not isinstance(policy, dict):
        return []
    labels = {
        "requiresGrant": "agent-registry grant",
        "requiresPolicyAdmission": "policy admission",
        "requiresStorageReceipt": "storage receipt",
        "requiresEvidence": "evidence record",
    }
    return [label for key, label in labels.items() if policy.get(key)]


def pinned_digests(sourceset: dict[str, Any], section: str) -> dict[str, str]:
    """Return the pinned filePath -> sha256 map for a sourceset section.

    Enforces the precondition the schema can declare but not check: when a
    section sets `digestRequired`, an `expectedDigests` block must exist.
    Without pins there is nothing to compare downloaded bytes against, so
    resolution fails closed rather than recording an unearned `verified: true`.
    """
    block = sourceset.get(section, {})
    if not isinstance(block, dict):
        raise SteeringRuntimeError(f"sourceset section {section} is not an object")
    pins = block.get("expectedDigests", {}).get("files", {})
    if block.get("digestRequired") and not pins:
        raise SteeringRuntimeError(
            f"{section}.digestRequired is true but {section}.expectedDigests is absent: "
            "downloaded artifacts could not be verified against a pinned expectation, "
            "refusing to resolve"
        )
    return pins


def artifact_record(
    *,
    role: str,
    repo: str,
    file_path: str,
    resolved_revision_value: str,
    local_path: Path,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    observed = sha256_file(local_path)
    if expected_sha256 is None:
        # Nothing was pinned for this file. The digest records what arrived;
        # it is not evidence that what arrived was correct.
        digest: dict[str, Any] = {
            "algorithm": "sha256",
            "sha256": observed,
            "verified": False,
            "verificationMethod": "trust-on-first-use",
        }
    elif observed != expected_sha256:
        raise SteeringRuntimeError(
            f"digest mismatch for {repo}/{file_path} at {resolved_revision_value}: "
            f"expected {expected_sha256}, observed {observed}"
        )
    else:
        digest = {
            "algorithm": "sha256",
            "sha256": observed,
            "expectedSha256": expected_sha256,
            "verified": True,
            "verificationMethod": "pinned-digest",
        }
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
        "digest": digest,
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
