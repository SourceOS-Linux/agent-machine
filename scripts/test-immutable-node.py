#!/usr/bin/env python3
"""Executable safety tests for immutable-node planning and guarded apply."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_machine.contracts import load_json
from agent_machine.immutable_node import (
    ApplyOptions,
    load_projection_index,
    preflight_plan,
    render_plan,
    sha256_json,
    apply_plan,
    validate_host_capability,
    validate_profile,
    validate_state_root,
)

FIXTURE_DIR = ROOT / "fixtures" / "sourceos-spec"
PROFILE = FIXTURE_DIR / "immutablenodeprofile.m2-asahi-agent-node-dev.json"


def expect_failure(label: str, fn) -> None:
    try:
        fn()
    except AssertionError:
        return
    raise AssertionError(f"expected failure did not occur: {label}")


def main() -> int:
    index = load_projection_index(FIXTURE_DIR)
    profile = load_json(PROFILE)
    validate_profile(profile, index)

    plan = render_plan(PROFILE, profile, index)
    assert plan["kind"] == "ImmutableNodePlan"
    assert plan["safety"]["hostMutationPerformed"] is False
    assert plan["safety"]["sociosRequired"] is False
    assert plan["desktopConsumers"]["desktopOwnsSubstrate"] is False
    assert sha256_json(plan) == sha256_json(copy.deepcopy(plan))

    with tempfile.TemporaryDirectory(prefix="agent-machine-immutable-node-") as tmp:
        target_root = Path(tmp)
        preflight = preflight_plan(plan, target_root, ("state-roots", "staging-artifacts"))
        assert preflight["kind"] == "ImmutableNodePreflight"
        assert preflight["hostMutationPerformed"] is False
        assert preflight["stateRootChecks"][0]["willCreate"] is True
        assert not (target_root / "var/lib/sourceos/evidence").exists()

        expect_failure(
            "apply requires --execute and --policy-ok",
            lambda: apply_plan(
                plan,
                ApplyOptions(
                    target_root=target_root,
                    execute=False,
                    policy_ok=False,
                    mutation_classes=("state-roots", "staging-artifacts"),
                ),
            ),
        )

        evidence = apply_plan(
            plan,
            ApplyOptions(
                target_root=target_root,
                execute=True,
                policy_ok=True,
                mutation_classes=("state-roots", "staging-artifacts"),
            ),
        )
        assert evidence["kind"] == "ImmutableNodeApplyEvidence"
        assert evidence["hostMutationPerformed"] is True
        assert evidence["sociosEnrollmentPerformed"] is False
        assert evidence["rawSecretsIncluded"] is False
        assert evidence["planDigestSha256"] == sha256_json(plan)
        assert (target_root / "var/lib/sourceos/evidence").is_dir()
        assert (target_root / "var/lib/agent-machine/immutable-node/m2-asahi-agent-node-dev/immutable-node-plan.json").is_file()
        assert (target_root / "var/lib/agent-machine/immutable-node/m2-asahi-agent-node-dev/immutable-node-apply-evidence.json").is_file()

    bad_profile = copy.deepcopy(profile)
    bad_profile["substrate"]["sociosRequired"] = True
    expect_failure("sociosRequired must be false", lambda: validate_profile(bad_profile, index))

    bad_profile = copy.deepcopy(profile)
    bad_profile["primaryPlane"] = "desktop-consumer"
    expect_failure("desktop cannot own immutable node profile", lambda: validate_profile(bad_profile, index))

    bad_state = copy.deepcopy(index["urn:srcos:node-state-schema:sourceos-evidence-root"])
    bad_state["rootPath"] = "/etc/sourceos/evidence"
    expect_failure("state root under /etc rejected", lambda: validate_state_root(bad_state))

    bad_state = copy.deepcopy(index["urn:srcos:node-state-schema:sourceos-evidence-root"])
    bad_state["rootPath"] = "/usr/lib/sourceos/evidence"
    expect_failure("state root under /usr rejected", lambda: validate_state_root(bad_state))

    bad_capability = copy.deepcopy(index["urn:srcos:host-capability-placement:sourceos-supervisor"])
    bad_capability["requiresEnrollment"] = True
    expect_failure("mandatory capability cannot require enrollment", lambda: validate_host_capability(bad_capability))

    print(json.dumps({"kind": "ImmutableNodeSafetyTest", "verdict": "passed"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
