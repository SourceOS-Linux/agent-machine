# Agent Machine Bootstrap Status

Agent Machine has reached bootstrap-runtime-control-substrate status. It is not production-ready. The bootstrap MVP now has real GitHub Actions validation proof through PR #9: workflow run `25322297618` completed successfully and ran the canonical `make validate` path before merge.

## Current status

| Area | Status | Notes |
| --- | --- | --- |
| Repository boundary | Complete for bootstrap | ADR 0001 defines Agent Machine as the machine/node runtime-control substrate. |
| Homebrew bootstrap | Complete for bootstrap | ADR 0002 and formulas install the bootstrap CLI, docs, contracts, examples, and package source. |
| Contracts | Complete for bootstrap | Core JSON Schemas exist for machine, pod, provider, cache, receipts, evidence, policy, grants, and activation decisions. |
| Examples | Complete for bootstrap | Examples cover local Podman/Quadlet, Kubernetes/TopoLVM, StorageReceipt, PolicyAdmission, AgentRegistryGrant, AgentPlaneRuntimeEvidence, and ActivationDecision. |
| Renderers | Complete for bootstrap | Package-owned plan, receipt, Quadlet, and Kubernetes renderer paths exist and are validated. |
| Governance semantics | Complete for bootstrap | Policy/grant semantic validators distinguish render-only from activation-scoped authority. |
| Activation evaluator | Complete for bootstrap | Evaluates AgentPod + PolicyAdmission + AgentRegistryGrant + deployment receipt ID + storage receipt refs into ActivationDecision. |
| Storage receipt resolver | Complete for bootstrap | Activation evaluator resolves StorageReceipt objects from files or directories and fails closed on unsafe receipts. |
| CLI | Complete for bootstrap | Bootstrap shell CLI delegates render and activation evaluation to Python package CLI. |
| Docs | Complete for bootstrap | README, docs index, quickstart, install, troubleshooting, readiness, release gate, ADRs, and integration stubs exist. |
| CI validation proof | Complete for bootstrap | PR #9 validation run `25322297618` passed before merge. |
| Main-branch CI visibility | Open follow-up | Post-merge push-run visibility remains uncertain through the connector/API path. Tracked in Issue #2. |
| Runtime provider activation | Not implemented | Activation is still a dry-run decision artifact, not runtime mutation. |
| Production readiness | Blocked | Release gate remains open. |

## Bootstrap-complete checklist

The bootstrap MVP is structurally complete. It remains bounded to dry-run/runtime-control evaluation, not live provider activation.

- [x] Repository boundary documented.
- [x] Homebrew bootstrap strategy documented.
- [x] README routes users to quickstart, readiness, and release-gate docs.
- [x] Documentation index exists and links are backed by files.
- [x] Quickstart covers install, doctor, probe, render, governance, and activation evaluation.
- [x] Troubleshooting covers dependency, validation, render, probe, and CI visibility failures.
- [x] JSON schemas exist for all bootstrap artifacts.
- [x] Examples validate by `kind` through schema mapping.
- [x] Quadlet skeleton is generated/compared from AgentPod source.
- [x] Kubernetes/TopoLVM skeleton is generated/compared from AgentPod source.
- [x] StorageReceipt examples exist for local LVM and TopoLVM.
- [x] PolicyAdmission examples exist for missing, denied, render-only allowed, and activation-scoped allowed states.
- [x] AgentRegistryGrant examples exist for missing, revoked, render-only active, and activation-scoped active states.
- [x] AgentPlaneRuntimeEvidence examples exist for local and Kubernetes flows.
- [x] ActivationDecision examples exist for fail-closed and allowed flows.
- [x] Activation evaluator resolves storage receipts from file/directory inputs.
- [x] Shell CLI delegates render commands to the Python package CLI.
- [x] Shell CLI delegates activation evaluation to the Python package CLI.
- [x] `make validate` includes JSON, YAML, Quadlet, render, evidence, governance, activation, package, CLI, and formula checks.
- [x] `make validate` is proven green in a real GitHub Actions runner through PR #9 run `25322297618`.
- [x] PR-triggered GitHub Actions visibility is confirmed through the connector/API path.
- [ ] Main-branch push workflow visibility is resolved or explicitly documented as unavailable through the connector/API path.

## Canonical validation command

```bash
make validate
```

Current validation stages:

```text
validate-json
validate-yaml
validate-quadlet
validate-render
validate-evidence
validate-governance
validate-activation
validate-package
validate-cli
validate-formula
```

## Canonical dry-run activation command

```bash
agent-machine activate evaluate \
  examples/local-podman-llama-cpp.agent-pod.json \
  examples/policy-admission.allowed-activation.json \
  examples/agent-registry-grant.active-activation.json \
  --deployment-receipt-id urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --storage-receipt-dir examples \
  --decided-at 2026-05-04T12:51:00Z \
  --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed \
  --pretty
```

Expected decision:

```text
status: allowed
activationAllowed: true
```

This is still dry-run control-plane evaluation. It does not start a provider.

## CI proof record

The first real validation proof was produced through PR #9.

| Field | Value |
| --- | --- |
| PR | `#9` — Harden validation workflow for bootstrap proof |
| Successful run | `25322297618` |
| Successful job | `Validate contracts, examples, CLI, formula, and docs` |
| Canonical command | `make validate` |
| Merge commit | `bceca6e92847edb19c2fd0f45709de45fe430e03` |

The PR run proved that the validation path can pass in GitHub Actions. Post-merge push-run discovery still returned no visible run through the connector at the time of update, so Issue #2 remains open for main-branch visibility.

## Fail-closed guarantees at bootstrap

Agent Machine currently fails closed when activation evaluation sees:

- invalid AgentPod kind;
- missing activation-scoped policy;
- denied policy;
- missing activation-scoped grant;
- revoked grant;
- missing deployment receipt ID;
- missing storage receipt refs;
- unresolved storage receipt refs;
- invalid StorageReceipt schema;
- raw-content safety violation;
- world-writable storage;
- symlink traversal observation;
- required encryption not observed;
- required quota not observed.

## Production blockers

The following remain production-blocking:

- main-branch CI visibility and branch-protection policy;
- image digest pinning and provenance gate;
- real Policy Fabric client or endpoint;
- real Agent Registry grant resolver;
- real AgentPlane evidence submission/staging client;
- local LVM provisioning/probe implementation;
- TopoLVM runtime integration beyond skeleton manifests;
- provider discovery and controlled provider activation implementation;
- M2 Asahi host measurement/provider readiness data;
- release evidence bundle with signed/provenance artifacts;
- rollback, teardown, and wipe workflows.

## Decision

Agent Machine is bootstrap-ready as a dry-run runtime-control substrate. It remains production-blocked by design.
