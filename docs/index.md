# Agent Machine Documentation Index

Agent Machine is a bootstrap runtime-control substrate for SourceOS agent workloads. This index points operators and contributors to the current docs.

## Start here

| Document | Purpose |
| --- | --- |
| [Quickstart](quickstart.md) | End-to-end dry-run path: install, doctor, probe, render, governance, activation evaluation. |
| [Install guide](install.md) | Homebrew install philosophy, direct formula, tap formula, runtime directory targets, M2 Asahi notes. |
| [Troubleshooting](troubleshooting.md) | Missing dependencies, CI visibility, validation failures, render delegation, probe expectations. |
| [Bootstrap MVP readiness](architecture/bootstrap-mvp-readiness.md) | Current maturity state, implemented surfaces, blockers, and recommended next work. |
| [World-class release gate](architecture/world-class-release-gate.md) | Release-blocking gates and production-readiness criteria. |
| [Local SAE steering inference readiness](inference-local-steering.md) | Inspection record for Neuronpedia-compatible local steering readiness and current gaps. |
| [Local /steer endpoint contract](local-steer-endpoint.md) | Noetica-compatible local steering endpoint contract and stub behavior. |
| [Steering sourceset registry](steering-sourcesets.md) | Registered model/SAE sourceset records for local steering work. |
| [Steering artifact receipts](steering-artifact-receipts.md) | Artifact-resolution receipt contract for model and SAE files. |
| [Steering artifact resolution](steering-artifact-resolution.md) | Operator command for resolving model/SAE files and emitting a complete receipt. |
| [Steering receipt loader](steering-loader.md) | Fail-closed receipt path and digest verification before runtime loading. |
| [Deterministic steering harness](steering-engine.md) | Mock-only request, hook, baseline, and transformed-response validation surface. |
| [GPT-2 Small steering activation path](steering-activation-path.md) | Fail-closed real-path entrypoint and remaining blockers for controlled activation. |

## Architecture

| Document | Purpose |
| --- | --- |
| [Agent Machine probe](architecture/agent-machine-probe.md) | Host/runtime probe shape and conservative diagnostics. |
| [AgentPod manifest generation](architecture/agentpod-manifest-generation.md) | Contract-to-plan-to-manifest generation rules. |
| [Deployment safety](architecture/deployment-safety.md) | Skeleton-vs-production manifest rules and safety gates. |
| [Receipt chain](architecture/receipt-chain.md) | AgentPod source to plan, manifest, receipt, policy, registry, and AgentPlane evidence. |
| [PolicyAdmission resolution](architecture/policy-admission-resolution.md) | Local Policy Fabric admission resolver and fail-closed missing-decision behavior. |
| [AgentRegistryGrant resolution](architecture/agent-registry-grant-resolution.md) | Local Agent Registry grant resolver and fail-closed missing-grant behavior. |
| [Image digest pinning and provenance](architecture/image-digest-pinning-and-provenance.md) | Supply-chain strict-mode gate for digest-pinned release-candidate artifacts. |
| [Release evidence bundle](architecture/release-evidence-bundle.md) | Deterministic validation/source/inventory/render/supply-chain/readiness bundle. |
| [Signed release bundle envelope](architecture/signed-release-bundle-envelope.md) | Signing envelope contract for release evidence bundles. |
| [Signed release bundle envelope](architecture/signed-release-bundle-envelope.md) | Signing/verification envelope around a release evidence bundle. |
| [Runtime package layout](architecture/runtime-package-layout.md) | Migration from loose scripts to `src/agent_machine/` package modules. |
| [Homebrew Python dependencies](architecture/homebrew-python-dependencies.md) | Current dependency strategy for render/evaluation commands. |
| [Local LVM and TopoLVM profile](architecture/local-lvm-and-topolvm-profile.md) | Local and Kubernetes storage/cache/evidence profile. |
| [World-class release gate](architecture/world-class-release-gate.md) | Production gate and maturity levels. |
| [Bootstrap MVP readiness](architecture/bootstrap-mvp-readiness.md) | Current readiness status. |

## ADRs

| Document | Purpose |
| --- | --- |
| [ADR 0001: Repository boundary](adr/0001-repository-boundary.md) | Defines why Agent Machine owns the machine/node substrate boundary. |
| [ADR 0002: Homebrew bootstrap](adr/0002-homebrew-bootstrap.md) | Defines Homebrew bootstrap install philosophy. |

## Integration docs

| Document | Purpose |
| --- | --- |
| [AgentPlane integration](integration/agentplane.md) | How runtime evidence and receipts align with AgentPlane. |
| [Policy Fabric integration](integration/policy-fabric.md) | How admission and policy decisions gate activation. |
| [AgentTerm integration](integration/agent-term.md) | Operator surface integration expectations. |
| [TopoLVM integration](integration/topolvm.md) | Storage integration expectations. |

## Contracts and examples

Schema contracts live in:

```text
contracts/
```

Conforming examples live in:

```text
examples/
```

Important contract families:

| Kind | Role |
| --- | --- |
| `AgentMachine` | Host/node substrate. |
| `AgentPod` | Schedulable local or Kubernetes workload envelope. |
| `InferenceProvider` | Backend-neutral inference provider declaration. |
| `SteeringSourceset` | Model/SAE artifact registry record for local steering work. |
| `SteeringArtifactReceipt` | Model/SAE artifact-resolution receipt for local steering work. |
| `CacheTier` | Model/cache/scratch/evidence storage tier declaration. |
| `StorageReceipt` | Secret-free storage/cache/evidence proof. |
| `DeploymentReceipt` | Proof that an artifact was derived from a typed source by a generator. |
| `AgentPlaneRuntimeEvidence` | Runtime/placement/activation evidence. |
| `PolicyAdmission` | Policy Fabric admission decision/stub. |
| `AgentRegistryGrant` | Agent Registry grant/stub. |
| `ActivationDecision` | Final dry-run activation decision. |
| `ReleaseEvidenceBundle` | Secret-free release validation/source/inventory/render/supply-chain/readiness evidence. |
| `SignedReleaseBundleEnvelope` | Signing/verification envelope around a release evidence bundle. |

## Validation

Canonical command:

```bash
make validate
```

Validation stages:

```text
validate-json
validate-yaml
validate-quadlet
validate-render
validate-evidence
validate-governance
validate-policy-fabric
validate-agent-registry
validate-activation
validate-supply-chain
validate-release-bundle
validate-sourceos-projections
validate-package
validate-cli
validate-formula
validate-runtime-install-receipts
```

## Current production blockers

Agent Machine remains production-blocked by design until the release gate passes.

Current blockers:

- main-branch CI visibility and branch protection;
- real image digest pinning/provenance from trusted build artifacts;
- real release bundle signature verification;
- real Policy Fabric client or endpoint;
- real Agent Registry client or endpoint;
- real AgentPlane evidence submission/staging client;
- local LVM provisioning/probe implementation;
- TopoLVM runtime integration beyond skeleton manifests;
- provider discovery and controlled provider activation implementation;
- M2 Asahi host measurement/provider readiness data;
- rollback, teardown, and wipe workflows.
- rollback, teardown, and wipe workflows.
