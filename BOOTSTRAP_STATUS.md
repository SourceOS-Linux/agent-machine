# Agent Machine Bootstrap Status

Agent Machine has reached bootstrap-runtime-control-substrate status. It is not production-ready. The remaining bootstrap blocker is external validation proof: `make validate` must be proven in a real runner and GitHub Actions visibility must be resolved or explicitly explained.

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
| CI visibility | Blocked | Connector repeatedly returns no workflow runs/statuses. Tracked in Issue #2. |
| Runtime provider activation | Not implemented | Activation is still a dry-run decision artifact, not runtime mutation. |
| Production readiness | Blocked | Release gate remains open. |

## Bootstrap-complete checklist

The bootstrap MVP should be considered complete only when all items below are checked.

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
- [ ] `make validate` is proven green in a real runner.
- [ ] GitHub Actions visibility is resolved or explicitly documented as unavailable through the connector/API path.

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

- visible green CI run;
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

Agent Machine is bootstrap-ready pending external validation proof. It remains production-blocked by design.
