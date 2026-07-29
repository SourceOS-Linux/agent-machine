#!/usr/bin/env python3
"""Validate that artifacts cannot be fetched before consent is adjudicated.

The ordering IS the guarantee. A grant checked after the bytes land governs whether
the artifacts may be USED; it cannot govern whether they may ARRIVE, and by then the
disk, the bandwidth and the exposure have already been spent. Every gate in this
resolver used to sit between *staged* and *activated*; none sat between *consented*
and *staged*.

The checks below are overwhelmingly negative controls, because the property being
asserted is a refusal. A consent gate that has never been observed refusing anything
is indistinguishable from no gate at all — which is precisely how a policy block can
sit in a schema, fully declared, and be read by nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.contracts import jsonschema_validator_for, load_json  # noqa: E402
from agent_machine.steering_artifacts import (  # noqa: E402
    assert_consent_permits_download,
    build_pending_receipt,
    consent_required,
    outstanding_policy_requirements,
)
from agent_machine.steering_runtime import SteeringRuntimeError  # noqa: E402

CONSENT_DIR = REPO_ROOT / "examples" / "artifact-consent-records"
SOURCESET = REPO_ROOT / "examples" / "steering-sourcesets" / "gpt2-small-res-jb.steering-sourceset.json"
REPOS = ["openai-community/gpt2", "jbloom/GPT2-Small-SAEs-Reformatted"]

failures: list[str] = []


def record(name: str) -> dict:
    return load_json(CONSENT_DIR / f"gpt2-small-res-jb.{name}.artifact-consent-record.json")


def expect_refusal(label: str, consent, sourceset, *, repos=None, needle: str, now: str | None = None) -> None:
    try:
        assert_consent_permits_download(consent, sourceset, repos=repos or REPOS, now=now)
    except SteeringRuntimeError as exc:
        if needle not in str(exc):
            failures.append(f"{label}: refused, but for the wrong reason: {exc}")
        else:
            print(f"  REFUSED  {label}")
    else:
        failures.append(f"{label}: FETCH WAS PERMITTED — the gate did not hold")


def expect_allowed(label: str, consent, sourceset, *, repos=None) -> dict:
    try:
        out = assert_consent_permits_download(consent, sourceset, repos=repos or REPOS)
    except SteeringRuntimeError as exc:
        failures.append(f"{label}: expected to be permitted, refused with: {exc}")
        return {}
    print(f"  ALLOWED  {label}")
    return out


def main() -> int:
    sourceset = load_json(SOURCESET)

    # The examples must themselves conform, or the controls below prove nothing.
    schema = load_json(REPO_ROOT / "contracts" / "artifact-consent-record.schema.json")
    validator = jsonschema_validator_for()(schema)(schema)
    for path in sorted(CONSENT_DIR.glob("*.json")):
        errs = sorted(validator.iter_errors(load_json(path)), key=lambda e: list(e.path))
        if errs:
            failures.append(f"{path.name}: example does not conform: {errs[0].message}")

    if not consent_required(sourceset):
        failures.append("fixture sourceset must set consent.requiresUserConsent for these controls to mean anything")

    # ── The permitted path ────────────────────────────────────────────────────
    granted = expect_allowed("granted, in scope, unexpired, all repos disclosed", record("granted"), sourceset)
    if granted.get("checkedBefore") != "download":
        failures.append(f"consent evidence must record checkedBefore='download', got {granted.get('checkedBefore')!r}")
    if not granted.get("consentRef"):
        failures.append("permitted fetch must carry the consent record it relied on")

    # ── Negative controls: each is a way the fetch must NOT happen ────────────
    expect_refusal("no consent record supplied at all", None, sourceset,
                   needle="no ArtifactConsentRecord")
    expect_refusal("consent explicitly declined", record("declined"), sourceset,
                   needle="was 'declined'")
    expect_refusal("scope is activation-only — may run, may not arrive", record("activation-only"), sourceset,
                   needle="does not authorise a download")
    expect_refusal("consent revoked after being granted", record("revoked"), sourceset,
                   needle="revoked")
    expect_refusal("consent expired", dict(record("granted"), expiresAt="2026-07-01T00:00:00Z"), sourceset,
                   needle="expired", now="2026-07-29T00:00:00Z")
    expect_refusal("consent for a different sourceset", dict(record("granted"), sourcesetId="some-other-set"), sourceset,
                   needle="does not generalise")
    expect_refusal("would fetch from an undisclosed remote", record("granted"), sourceset,
                   repos=REPOS + ["attacker/exfil"], needle="undisclosed repo")
    expect_refusal("not an ArtifactConsentRecord", dict(record("granted"), kind="AgentRegistryGrant"), sourceset,
                   needle="not an ArtifactConsentRecord")

    # ── A sourceset that does not require consent is unaffected ───────────────
    open_sourceset = dict(sourceset, consent={"requiresUserConsent": False})
    out = expect_allowed("sourceset not requiring consent proceeds without a record", None, open_sourceset)
    if out.get("required") is not False:
        failures.append("a sourceset not requiring consent must record required=False, not fabricate a decision")

    # ── The declared-but-unread policy block is now named, not ignored ────────
    outstanding = outstanding_policy_requirements(sourceset)
    for expected in ("agent-registry grant", "policy admission", "storage receipt", "evidence record"):
        if expected not in outstanding:
            failures.append(f"declared policy requirement {expected!r} is not surfaced by resolution")
    if outstanding:
        print(f"  NAMED    {len(outstanding)} declared policy requirement(s) resolution does not discharge")

    # ── A dry run must disclose the gap rather than appear healthy ────────────
    missing = build_pending_receipt("gpt2-small.res-jb", sourceset)["missing"]
    if not any("consent.requiresUserConsent" in m for m in missing):
        failures.append("dry run must report that a consent record will be required")
    else:
        print("  REPORTED dry run names the consent requirement before anyone attempts a fetch")

    # ── The ordering claim itself, proved rather than inferred ────────────────
    # Everything above tests the adjudicator in isolation. This drives the real entry
    # point with --allow-network set and no consent record, and fails if execution
    # reaches the point where a remote would be contacted. Without this, the gate
    # could be correct and still be called too late to matter.
    import tempfile
    import agent_machine.steering_artifacts as sa

    reached_network = []
    original = sa.resolve_gpt2_small_res_jb

    def tripwire(*args, **kwargs):  # pragma: no cover - must never run
        reached_network.append(True)
        raise AssertionError("network path entered")

    sa.resolve_gpt2_small_res_jb = tripwire
    try:
        with tempfile.TemporaryDirectory() as tmp:
            sa.resolve_steering_artifacts(
                "gpt2-small.res-jb",
                Path(tmp) / "artifacts",
                Path(tmp) / "receipt.json",
                allow_network=True,          # connectivity granted...
                consent_record=None,         # ...but nobody agreed
            )
    except SteeringRuntimeError as exc:
        if "no ArtifactConsentRecord" not in str(exc):
            failures.append(f"refused before fetch, but for the wrong reason: {exc}")
        else:
            print("  BLOCKED  --allow-network without consent never reaches the fetch path")
    except AssertionError:
        failures.append("THE FETCH PATH WAS ENTERED WITHOUT CONSENT — the gate is after the download")
    else:
        failures.append("resolution completed without consent")
    finally:
        sa.resolve_steering_artifacts.__globals__["resolve_gpt2_small_res_jb"] = original
        sa.resolve_gpt2_small_res_jb = original
    if reached_network:
        failures.append("a remote would have been contacted before consent was adjudicated")

    if failures:
        print(f"\n{len(failures)} failure(s):\n", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print("\nOK consent is adjudicated BEFORE the fetch, and refuses in every way it must")
    return 0


if __name__ == "__main__":
    sys.exit(main())
