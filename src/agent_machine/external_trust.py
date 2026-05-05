"""External trust signal adapter validation.

ExternalTrustSignalProvider artifacts are optional verifier inputs for Agent
Registry grant resolution. They are never authorization and must never become
the SourceOS root of trust.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json, schema_by_kind, validate_instance

AUTHORITY = "non-authoritative-verifier-input"
USABLE_STATUS = "available"
UNUSABLE_STATUSES = {"unavailable", "stale", "malformed", "unsigned", "denied", "error"}
SIGNAL_TYPES = {
    "agent-identity",
    "cert-tier",
    "reputation-score",
    "counterparty-check",
    "registry-lookup",
    "other",
}
EXTRA_SAFETY_FLAGS = [
    "apiKeysIncluded",
    "walletPrivateKeysIncluded",
    "rawCredentialsIncluded",
    "rawUserDataIncluded",
]
BASE_SAFETY_FLAGS = [
    "includeRawContent",
    "rawPromptContentIncluded",
    "rawKvCacheContentIncluded",
    "secretValuesIncluded",
    "privateMemoryIncluded",
]


def validate_external_trust_signal_provider_schema(path: Path, root: Path | None = None) -> dict[str, Any]:
    validate_instance(path, schema_by_kind(root)["ExternalTrustSignalProvider"])
    value = load_json(path)
    if not isinstance(value, dict):
        raise AssertionError(f"{path}: ExternalTrustSignalProvider root must be an object")
    return value


def validate_external_trust_signal_provider_semantics(provider: dict[str, Any], source: str = "<external-trust>") -> None:
    request = _require_object(provider.get("request"), f"{source}: request")
    response = _require_object(provider.get("response"), f"{source}: response")
    safety = _require_object(provider.get("receiptSafety"), f"{source}: receiptSafety")

    provider_ref = request.get("providerRef")
    if response.get("providerRef") != provider_ref:
        raise AssertionError(f"{source}: response.providerRef must match request.providerRef")

    requested_signal_types = request.get("requestedSignalTypes")
    if not isinstance(requested_signal_types, list) or not requested_signal_types:
        raise AssertionError(f"{source}: request.requestedSignalTypes must be a non-empty list")
    if len(requested_signal_types) != len(set(requested_signal_types)):
        raise AssertionError(f"{source}: request.requestedSignalTypes must not contain duplicates")
    if not set(requested_signal_types).issubset(SIGNAL_TYPES):
        raise AssertionError(f"{source}: request.requestedSignalTypes contains unsupported values")

    freshness_window = request.get("verificationFreshnessSeconds")
    if not isinstance(freshness_window, int) or freshness_window < 0:
        raise AssertionError(f"{source}: request.verificationFreshnessSeconds must be a non-negative integer")

    status = response.get("status")
    usable = response.get("usableForGrantResolution")
    if status == USABLE_STATUS:
        if usable is not True:
            raise AssertionError(f"{source}: available response requires usableForGrantResolution=true")
        if response.get("failureReason") is not None:
            raise AssertionError(f"{source}: available response must not carry failureReason")
    elif status in UNUSABLE_STATUSES:
        if usable is not False:
            raise AssertionError(f"{source}: response.status={status} requires usableForGrantResolution=false")
        if not response.get("failureReason"):
            raise AssertionError(f"{source}: response.status={status} requires failureReason")
    else:
        raise AssertionError(f"{source}: unsupported external trust status {status!r}")

    if response.get("authority") != AUTHORITY:
        raise AssertionError(f"{source}: response.authority must be {AUTHORITY}")

    response_freshness = _require_object(response.get("freshness"), f"{source}: response.freshness")
    _assert_freshness(response_freshness, f"{source}: response.freshness")
    if usable is True and response_freshness.get("fresh") is not True:
        raise AssertionError(f"{source}: usable external trust response must be fresh")
    if status == "stale" and response_freshness.get("fresh") is not False:
        raise AssertionError(f"{source}: stale response requires freshness.fresh=false")

    signals = response.get("signals")
    if not isinstance(signals, list):
        raise AssertionError(f"{source}: response.signals must be a list")
    if usable is True and not signals:
        raise AssertionError(f"{source}: usable external trust response requires at least one signal")

    signal_types_seen: list[str] = []
    for index, signal in enumerate(signals):
        signal_source = f"{source}: response.signals[{index}]"
        _assert_signal_payload(
            signal,
            signal_source,
            expected_provider_ref=str(provider_ref),
            requested_signal_types=set(requested_signal_types),
            signature_required=bool(request.get("signatureRequired")),
            usable_response=bool(usable),
        )
        signal_types_seen.append(str(signal.get("signalType")))

    if len(signal_types_seen) != len(set(signal_types_seen)):
        raise AssertionError(f"{source}: response.signals must not contain duplicate signalType entries")

    _assert_safety_flags(safety, source)


def external_trust_signal_usable(provider: dict[str, Any]) -> bool:
    """Return true only when an adapter result can be used as local verifier input.

    This result is still not authorization. It can only be considered by a local
    Agent Registry grant resolver.
    """
    response = provider.get("response", {})
    return (
        response.get("status") == USABLE_STATUS
        and response.get("usableForGrantResolution") is True
        and response.get("authority") == AUTHORITY
        and response.get("freshness", {}).get("fresh") is True
    )


def _require_object(value: Any, source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssertionError(f"{source} must be an object")
    return value


def _assert_signal_payload(
    signal: Any,
    source: str,
    *,
    expected_provider_ref: str,
    requested_signal_types: set[str],
    signature_required: bool,
    usable_response: bool,
) -> None:
    signal_doc = _require_object(signal, source)
    if signal_doc.get("providerRef") != expected_provider_ref:
        raise AssertionError(f"{source}.providerRef must match request.providerRef")
    signal_type = signal_doc.get("signalType")
    if signal_type not in requested_signal_types:
        raise AssertionError(f"{source}.signalType must be one of the requested signal types")
    if signal_doc.get("authority") != AUTHORITY:
        raise AssertionError(f"{source}.authority must be {AUTHORITY}")
    if usable_response and signal_doc.get("failureReason") is not None:
        raise AssertionError(f"{source}.failureReason must be null for usable responses")

    freshness = _require_object(signal_doc.get("freshness"), f"{source}.freshness")
    _assert_freshness(freshness, f"{source}.freshness")
    if usable_response and freshness.get("fresh") is not True:
        raise AssertionError(f"{source}: usable response cannot include stale signal")

    signature = _require_object(signal_doc.get("signature"), f"{source}.signature")
    if signature_required:
        if signature.get("required") is not True:
            raise AssertionError(f"{source}.signature.required must be true when request.signatureRequired=true")
        if signature.get("observed") is not True:
            raise AssertionError(f"{source}.signature.observed must be true when signatures are required")
        if not signature.get("signatureRef"):
            raise AssertionError(f"{source}.signature.signatureRef is required when signatures are required")
        if not signature.get("signerRef"):
            raise AssertionError(f"{source}.signature.signerRef is required when signatures are required")


def _assert_freshness(freshness: dict[str, Any], source: str) -> None:
    max_age = freshness.get("maxAgeSeconds")
    observed_age = freshness.get("observedAgeSeconds")
    fresh = freshness.get("fresh")
    if not isinstance(max_age, int) or max_age < 0:
        raise AssertionError(f"{source}.maxAgeSeconds must be a non-negative integer")
    if not isinstance(observed_age, int) or observed_age < 0:
        raise AssertionError(f"{source}.observedAgeSeconds must be a non-negative integer")
    if not isinstance(fresh, bool):
        raise AssertionError(f"{source}.fresh must be a boolean")
    if observed_age > max_age and fresh is True:
        raise AssertionError(f"{source}.fresh cannot be true when observedAgeSeconds exceeds maxAgeSeconds")
    if observed_age <= max_age and fresh is False:
        raise AssertionError(f"{source}.fresh cannot be false when observedAgeSeconds is within maxAgeSeconds")


def _assert_safety_flags(safety: dict[str, Any], source: str) -> None:
    for key in BASE_SAFETY_FLAGS + EXTRA_SAFETY_FLAGS:
        if safety.get(key) is not False:
            raise AssertionError(f"{source}: receiptSafety.{key} must be false")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an ExternalTrustSignalProvider artifact")
    parser.add_argument("external_trust_json", type=Path)
    parser.add_argument("--expect", choices=["usable", "unusable"], required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provider = validate_external_trust_signal_provider_schema(args.external_trust_json)
    validate_external_trust_signal_provider_semantics(provider, str(args.external_trust_json))
    usable = external_trust_signal_usable(provider)
    if args.expect == "usable" and not usable:
        raise AssertionError(f"{args.external_trust_json}: expected usable external trust signal")
    if args.expect == "unusable" and usable:
        raise AssertionError(f"{args.external_trust_json}: expected unusable external trust signal")
    print(f"VALID external trust {args.expect} {args.external_trust_json}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=__import__("sys").stderr)
        raise SystemExit(1) from exc
