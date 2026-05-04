"""Supply-chain validation helpers for Agent Machine.

Bootstrap examples may use mutable tags so operators can iterate quickly.
Release-candidate and production artifacts must be digest-pinned and carry
provenance/SBOM references where available.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json

SHA256_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
IMAGE_WITH_DIGEST_RE = re.compile(r"@sha256:[a-f0-9]{64}$")


def is_sha256_digest(value: str | None) -> bool:
    return isinstance(value, str) and bool(SHA256_DIGEST_RE.match(value))


def image_reference_is_pinned(image_ref: str | None) -> bool:
    return isinstance(image_ref, str) and bool(IMAGE_WITH_DIGEST_RE.search(image_ref))


def runtime_image_digest(runtime: dict[str, Any]) -> str | None:
    image_digest = runtime.get("imageDigest")
    if isinstance(image_digest, str):
        return image_digest
    image_ref = runtime.get("imageOrCommand")
    if image_reference_is_pinned(image_ref):
        return "sha256:" + str(image_ref).rsplit("@sha256:", 1)[1]
    return None


def validate_runtime_supply_chain(
    runtime: dict[str, Any],
    *,
    strict: bool,
    source: str = "<runtime>",
) -> list[str]:
    """Validate runtime image/provenance metadata and return warnings.

    Strict mode fails on mutable image references or missing provenance metadata.
    Bootstrap mode allows tags only when explicitly marked `tag-allowed-bootstrap`.
    """
    warnings: list[str] = []
    image_ref = runtime.get("imageOrCommand")
    image_policy = runtime.get("imageReferencePolicy")
    digest = runtime_image_digest(runtime)
    sbom_ref = runtime.get("sbomRef")
    provenance_ref = runtime.get("provenanceRef")

    if not isinstance(image_ref, str) or not image_ref:
        raise AssertionError(f"{source}: runtime.imageOrCommand is required")

    has_container_image_shape = "/" in image_ref or ":" in image_ref or image_reference_is_pinned(image_ref)
    if not has_container_image_shape:
        warnings.append(f"{source}: runtime.imageOrCommand does not look like a container image; strict digest checks may not apply")

    if strict:
        if not digest or not is_sha256_digest(digest):
            raise AssertionError(f"{source}: strict mode requires image digest via imageOrCommand @sha256 or runtime.imageDigest")
        if image_policy not in {"digest-required", "digest-pinned"}:
            raise AssertionError(f"{source}: strict mode requires imageReferencePolicy=digest-required or digest-pinned")
        if not sbom_ref:
            raise AssertionError(f"{source}: strict mode requires runtime.sbomRef")
        if not provenance_ref:
            raise AssertionError(f"{source}: strict mode requires runtime.provenanceRef")
        if image_reference_is_pinned(image_ref) and runtime.get("imageDigest") and digest != runtime.get("imageDigest"):
            raise AssertionError(f"{source}: imageOrCommand digest and runtime.imageDigest disagree")
        return warnings

    if digest and not is_sha256_digest(digest):
        raise AssertionError(f"{source}: runtime.imageDigest must be sha256:<64 hex chars>")
    if image_reference_is_pinned(image_ref) and image_policy == "tag-allowed-bootstrap":
        warnings.append(f"{source}: image is digest-pinned but policy still says tag-allowed-bootstrap")
    if not image_reference_is_pinned(image_ref) and image_policy is None:
        warnings.append(f"{source}: mutable image reference without explicit imageReferencePolicy")
    if not image_reference_is_pinned(image_ref) and image_policy not in {None, "tag-allowed-bootstrap"}:
        raise AssertionError(f"{source}: mutable image reference conflicts with imageReferencePolicy={image_policy!r}")
    return warnings


def validate_agentpod_supply_chain(agentpod: dict[str, Any], *, strict: bool, source: str = "<agentpod>") -> list[str]:
    if agentpod.get("kind") != "AgentPod":
        raise AssertionError(f"{source}: expected kind=AgentPod")
    runtime = agentpod.get("runtime")
    if not isinstance(runtime, dict):
        raise AssertionError(f"{source}: runtime must be an object")
    return validate_runtime_supply_chain(runtime, strict=strict, source=f"{source}:runtime")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate AgentPod supply-chain image/provenance posture")
    parser.add_argument("agentpod_json", type=Path)
    parser.add_argument("--strict", action="store_true", help="Require digest-pinned image and provenance/SBOM refs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    agentpod = load_json(args.agentpod_json)
    warnings = validate_agentpod_supply_chain(agentpod, strict=args.strict, source=str(args.agentpod_json))
    for warning in warnings:
        print(f"WARNING {warning}")
    mode = "strict" if args.strict else "bootstrap"
    print(f"VALID supply-chain {mode} {args.agentpod_json}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
