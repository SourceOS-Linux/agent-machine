"""Release evidence bundle generator for Agent Machine.

The release evidence bundle is a deterministic, secret-free summary of the
bootstrap/runtime-control substrate: validation proof, source identity,
contract/example/doc inventories, rendered artifact digests, supply-chain
posture, readiness, and known blockers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_machine.activation import evaluate_activation
from agent_machine.contracts import load_json, schema_by_kind
from agent_machine.digest import stable_digest, stable_text_digest
from agent_machine.paths import repo_root_from_file
from agent_machine.renderers import k8s as k8s_renderer
from agent_machine.renderers import plan as plan_renderer
from agent_machine.renderers import quadlet as quadlet_renderer

DEFAULT_GENERATED_AT = "1970-01-01T00:00:00Z"
DEFAULT_COMMIT_SHA = "0000000000000000000000000000000000000000"
DEFAULT_REPOSITORY = "SourceOS-Linux/agent-machine"


def digest_file(path: Path) -> str:
    return stable_text_digest(path.read_text(encoding="utf-8"))


def digested_files(root: Path, directory: str, pattern: str = "*") -> list[dict[str, str]]:
    base = root / directory
    if not base.exists():
        return []
    items: list[dict[str, str]] = []
    for path in sorted(base.rglob(pattern)):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        # Avoid circularity: checked-in bundle examples should not define the
        # inventory digest of the generated release bundle itself.
        if rel.startswith("examples/release-evidence-bundle"):
            continue
        items.append({"path": rel, "digest": digest_file(path)})
    return items


def artifact_digest(value: Any) -> str:
    if isinstance(value, str):
        return stable_text_digest(value)
    return stable_digest(value)


def rendered_artifacts(root: Path) -> list[dict[str, str | None]]:
    local_agentpod_path = root / "examples" / "local-podman-llama-cpp.agent-pod.json"
    k8s_agentpod_path = root / "examples" / "k8s-topolvm.agent-pod.json"
    local_agentpod = load_json(local_agentpod_path)
    k8s_agentpod = load_json(k8s_agentpod_path)

    local_plan = plan_renderer.render_plan(local_agentpod_path, local_agentpod)
    k8s_plan = plan_renderer.render_plan(k8s_agentpod_path, k8s_agentpod)
    local_receipt = plan_renderer.render_receipt(
        local_agentpod_path,
        local_agentpod,
        local_plan,
        "/tmp/agent-machine-local-agentpod-plan.json",
    )
    local_quadlet = quadlet_renderer.render_quadlet(local_agentpod)
    k8s_yaml = k8s_renderer.dump_documents(k8s_renderer.render_documents(k8s_agentpod))

    activation_decision = evaluate_activation(
        agentpod=local_agentpod,
        policy=load_json(root / "examples" / "policy-admission.allowed-activation.json"),
        grant=load_json(root / "examples" / "agent-registry-grant.active-activation.json"),
        deployment_receipt_id="urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        storage_receipt_refs=["urn:srcos:agent-machine:storage-receipt:local-lvm-warm-cache"],
        storage_receipts=[load_json(root / "examples" / "local-lvm-warm-cache.storage-receipt.json")],
        decided_at="2026-05-04T12:51:00Z",
        decision_id="urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed",
        root=root,
    )

    return [
        {"name": "local-agentpod-plan", "artifactKind": "AgentPodDeploymentPlan", "path": None, "digest": artifact_digest(local_plan)},
        {"name": "k8s-agentpod-plan", "artifactKind": "AgentPodDeploymentPlan", "path": None, "digest": artifact_digest(k8s_plan)},
        {"name": "local-deployment-receipt", "artifactKind": "DeploymentReceipt", "path": None, "digest": artifact_digest(local_receipt)},
        {"name": "local-quadlet", "artifactKind": "QuadletContainer", "path": "deploy/quadlet/agent-machine-llama-cpp.container", "digest": artifact_digest(local_quadlet)},
        {"name": "k8s-yaml", "artifactKind": "KubernetesYaml", "path": "deploy/k8s/llama-cpp-topolvm-pod.yaml", "digest": artifact_digest(k8s_yaml)},
        {"name": "local-activation-decision", "artifactKind": "ActivationDecision", "path": "examples/activation-decision.allowed.json", "digest": artifact_digest(activation_decision)},
    ]


def known_production_blockers() -> list[str]:
    return sorted(
        [
            "main-branch-ci-visibility-and-branch-protection-policy",
            "real-image-signature-and-provenance-verification",
            "real-policy-fabric-client-or-endpoint",
            "real-agent-registry-grant-resolver",
            "real-agentplane-evidence-submission-or-staging-client",
            "local-lvm-provisioning-and-probe-implementation",
            "topolvm-runtime-integration-beyond-skeleton-manifests",
            "provider-discovery-and-controlled-provider-activation",
            "m2-asahi-host-measurement-and-provider-readiness-data",
            "signed-release-evidence-bundle",
            "rollback-teardown-and-wipe-workflows",
        ]
    )


def generate_release_bundle(
    *,
    root: Path,
    repository: str,
    branch: str,
    commit_sha: str,
    pull_request: int | None,
    workflow_run_id: int | None,
    validation_status: str,
    workflow_job_name: str | None,
    generated_at: str,
    validated_at: str | None,
) -> dict[str, Any]:
    return {
        "specVersion": "0.1.0",
        "id": "urn:srcos:agent-machine:release-evidence-bundle:bootstrap-v0",
        "kind": "ReleaseEvidenceBundle",
        "release": {
            "name": "agent-machine-bootstrap-v0",
            "maturity": "bootstrap-ready",
            "productionReady": False,
            "notes": [
                "Bootstrap dry-run runtime-control substrate only.",
                "Does not start providers or mutate privileged runtime directories.",
            ],
        },
        "source": {
            "repository": repository,
            "branch": branch,
            "commitSha": commit_sha,
            "pullRequest": pull_request,
        },
        "validation": {
            "canonicalCommand": "make validate",
            "status": validation_status,
            "workflowRunId": workflow_run_id,
            "workflowJobName": workflow_job_name,
            "validatedAt": validated_at,
        },
        "inventories": {
            "schemas": digested_files(root, "contracts", "*.json"),
            "examples": digested_files(root, "examples", "*.json"),
            "docs": digested_files(root, "docs", "*.md"),
        },
        "renderedArtifacts": rendered_artifacts(root),
        "supplyChain": {
            "strictModeAvailable": True,
            "strictExamples": [
                {
                    "path": "examples/local-podman-llama-cpp.pinned.agent-pod.json",
                    "digest": digest_file(root / "examples" / "local-podman-llama-cpp.pinned.agent-pod.json"),
                }
            ],
            "mutableBootstrapExamples": [
                {
                    "path": "examples/local-podman-llama-cpp.agent-pod.json",
                    "digest": digest_file(root / "examples" / "local-podman-llama-cpp.agent-pod.json"),
                },
                {
                    "path": "examples/k8s-topolvm.agent-pod.json",
                    "digest": digest_file(root / "examples" / "k8s-topolvm.agent-pod.json"),
                },
            ],
        },
        "readiness": {
            "bootstrapReady": True,
            "productionReady": False,
            "releaseGateRef": "docs/architecture/world-class-release-gate.md",
            "statusRef": "BOOTSTRAP_STATUS.md",
        },
        "knownBlockers": known_production_blockers(),
        "receiptSafety": {
            "includeRawContent": False,
            "rawPromptContentIncluded": False,
            "rawKvCacheContentIncluded": False,
            "secretValuesIncluded": False,
            "privateMemoryIncluded": False,
        },
        "generatedAt": generated_at,
    }


def validate_release_bundle(bundle: dict[str, Any], root: Path) -> None:
    schema = load_json(schema_by_kind(root)["ReleaseEvidenceBundle"])
    try:
        from jsonschema.validators import validator_for
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: jsonschema. Install with `python -m pip install -r requirements-dev.txt`."
        ) from exc
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(bundle), key=lambda err: list(err.path))
    if errors:
        rendered = []
        for err in errors:
            location = "/".join(str(part) for part in err.path) or "<root>"
            rendered.append(f"  - {location}: {err.message}")
        raise AssertionError("ReleaseEvidenceBundle failed schema validation:\n" + "\n".join(rendered))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Agent Machine release evidence bundle")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--commit-sha", default=DEFAULT_COMMIT_SHA)
    parser.add_argument("--pull-request", type=int)
    parser.add_argument("--workflow-run-id", type=int)
    parser.add_argument("--validation-status", choices=["passed", "failed", "unknown", "not-run"], default="unknown")
    parser.add_argument("--workflow-job-name", default="Validate contracts, examples, CLI, formula, and docs")
    parser.add_argument("--generated-at", default=DEFAULT_GENERATED_AT)
    parser.add_argument("--validated-at")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root_from_file(__file__)
    bundle = generate_release_bundle(
        root=root,
        repository=args.repository,
        branch=args.branch,
        commit_sha=args.commit_sha,
        pull_request=args.pull_request,
        workflow_run_id=args.workflow_run_id,
        validation_status=args.validation_status,
        workflow_job_name=args.workflow_job_name,
        generated_at=args.generated_at,
        validated_at=args.validated_at,
    )
    validate_release_bundle(bundle, root)
    if args.pretty:
        print(json.dumps(bundle, indent=2, sort_keys=True))
    else:
        print(json.dumps(bundle, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
