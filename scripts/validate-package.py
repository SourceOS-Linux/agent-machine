#!/usr/bin/env python3
"""Validate the transitional Agent Machine Python package surface."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def main() -> int:
    import agent_machine
    import agent_machine.activation
    import agent_machine.cli
    import agent_machine.evidence
    import agent_machine.external_trust
    import agent_machine.governance
    import agent_machine.release_bundle
    import agent_machine.supply_chain
    import agent_machine.renderers.k8s
    import agent_machine.renderers.plan
    import agent_machine.renderers.quadlet
    from agent_machine.contracts import contracts_dir, examples_dir, schema_by_kind
    from agent_machine.digest import stable_digest, stable_text_digest
    from agent_machine.paths import default_evidence_path, default_model_cache_path, repo_root_from_file

    root = repo_root_from_file(__file__)
    if contracts_dir(root) != REPO_ROOT / "contracts":
        raise AssertionError("contracts_dir(root) did not resolve to repository contracts/")
    if examples_dir(root) != REPO_ROOT / "examples":
        raise AssertionError("examples_dir(root) did not resolve to repository examples/")
    mapping = schema_by_kind(root)
    required_kinds = {
        "ActivationDecision",
        "AgentPod",
        "AgentPlaneRuntimeEvidence",
        "AgentRegistryGrant",
        "ExternalTrustSignalProvider",
        "PolicyAdmission",
        "ReleaseEvidenceBundle",
        "StorageReceipt",
    }
    missing = sorted(required_kinds - set(mapping))
    if missing:
        raise AssertionError(f"schema_by_kind(root) missing: {', '.join(missing)}")
    if stable_digest({"b": 2, "a": 1}) != stable_digest({"a": 1, "b": 2}):
        raise AssertionError("stable_digest must be key-order independent")
    if not stable_text_digest("agent-machine").startswith("sha256:"):
        raise AssertionError("stable_text_digest must return sha256: prefixed digest")
    if not agent_machine.supply_chain.is_sha256_digest("sha256:" + "a" * 64):
        raise AssertionError("supply_chain.is_sha256_digest rejected valid digest")
    if agent_machine.release_bundle.DEFAULT_REPOSITORY != "SourceOS-Linux/agent-machine":
        raise AssertionError("unexpected release_bundle default repository")
    if agent_machine.external_trust.AUTHORITY != "non-authoritative-verifier-input":
        raise AssertionError("unexpected external trust authority")
    if str(default_model_cache_path()) != "/var/lib/agent-machine/models":
        raise AssertionError("unexpected default model cache path")
    if str(default_evidence_path()) != "/var/lib/agent-machine/evidence":
        raise AssertionError("unexpected default evidence path")

    print(f"VALID package agent_machine {agent_machine.__version__}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
