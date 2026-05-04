# Bootstrap MVP Readiness

Agent Machine is now a coherent bootstrap runtime-control substrate. It is not production-ready, but it has crossed the threshold from design notes into an executable control-plane prototype with typed contracts, deterministic renderers, governance semantics, evidence stubs, activation decisions, install surfaces, and operator quickstart coverage.

## Current readiness status

| Area | Status | Notes |
| --- | --- | --- |
| Contract schemas | Bootstrap-ready | Core schemas exist and are validated by `make validate`. |
| Examples | Bootstrap-ready | Examples cover AgentMachine, AgentPod, InferenceProvider, CacheTier, receipts, evidence, policy, grants, and activation decisions. |
| Renderers | Bootstrap-ready | Plan, receipt, Quadlet, and Kubernetes renderers are package-owned and wrapper-exposed. |
| Deployment skeletons | Bootstrap-ready | Local Quadlet and Kubernetes/TopoLVM skeletons exist and are compared against generated outputs. |
| Storage receipts | Bootstrap-ready | Local LVM and TopoLVM receipt examples exist; activation evaluation can resolve receipts from files/directories. |
| Governance semantics | Bootstrap-ready | PolicyAdmission and AgentRegistryGrant semantics are validated beyond JSON Schema. |
| Activation decisions | Bootstrap-ready | Activation decisions can be evaluated from AgentPod + PolicyAdmission + AgentRegistryGrant + receipts. |
| CLI | Bootstrap-ready | Shell bootstrap CLI delegates render and activation evaluation to Python package CLI. |
| Homebrew install | Bootstrap-ready, not fully self-contained | Formula installs package source and examples; Python render dependencies remain documented external deps. |
| CI visibility | Blocked | Workflow/status queries through the connector return no runs/statuses. Tracked in Issue #2. |
| Runtime activation | Not implemented | No provider is started; activation evaluation remains a decision artifact only. |
| Production readiness | Blocked by design | Release gate remains open in Issue #3. |

## What works structurally

The current bootstrap chain is:

```text
AgentPod JSON
  -> AgentPodDeploymentPlan
  -> DeploymentReceipt
  -> Quadlet / Kubernetes render comparison
  -> StorageReceipt validation
  -> PolicyAdmission semantic validation
  -> AgentRegistryGrant semantic validation
  -> AgentPlaneRuntimeEvidence validation
  -> ActivationDecision evaluation
```

The operator path is documented in:

```text
docs/quickstart.md
```

The release gate is documented in:

```text
docs/architecture/world-class-release-gate.md
```

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

## Current CLI surfaces

Safe bootstrap commands:

```bash
agent-machine version
agent-machine paths
agent-machine doctor --format json
agent-machine probe --format json
```

Render/evidence-planning commands:

```bash
agent-machine render plan examples/local-podman-llama-cpp.agent-pod.json --pretty
agent-machine render receipt examples/local-podman-llama-cpp.agent-pod.json --pretty
agent-machine render quadlet examples/local-podman-llama-cpp.agent-pod.json --compare deploy/quadlet/agent-machine-llama-cpp.container
agent-machine render k8s examples/k8s-topolvm.agent-pod.json --compare deploy/k8s/llama-cpp-topolvm-pod.yaml
```

Activation evaluation command:

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

## Bootstrap MVP definition

The bootstrap MVP is considered structurally complete when all of the following are true:

1. `make validate` passes in a real runner.
2. GitHub Actions visibility is confirmed or explicitly explained.
3. Homebrew direct formula installs the bootstrap CLI, package source, docs, contracts, and examples.
4. `agent-machine doctor --format json` and `agent-machine probe --format json` run without render dependencies.
5. Render commands fail with clear dependency remediation if `jsonschema`/`PyYAML` are absent.
6. Render commands work when dependencies are present.
7. Activation evaluation produces both fail-closed and allowed decision examples deterministically.
8. The quickstart exercises the path without runtime mutation.
9. The release gate explicitly marks production blockers.

## Current blockers to bootstrap MVP completion

### 1. CI visibility

The repository has `.github/workflows/validate.yml`, but connector checks repeatedly return no visible workflow runs or statuses for recent commits.

Tracked by:

```text
Issue #2: Verify GitHub Actions visibility for Agent Machine validation workflow
```

### 2. Real execution proof

The repo has validation commands and CI configuration, but this connector path does not prove the workflow ran. A real local or GitHub Actions execution of `make validate` is still required.

### 3. Dependency packaging policy

Homebrew currently documents Python render dependencies rather than packaging them as Homebrew resources. This is acceptable for bootstrap, but not release-candidate.

Tracked by:

```text
docs/architecture/homebrew-python-dependencies.md
```

## Production blockers

Agent Machine is not production-ready until these release-blocking gaps are closed:

- visible green CI run;
- image digest pinning and provenance gate;
- real Policy Fabric admission client or endpoint;
- real Agent Registry grant resolver;
- real AgentPlane evidence submission/staging client;
- local LVM provisioning/probe implementation;
- TopoLVM runtime integration beyond skeleton manifests;
- provider discovery and activation implementation;
- M2 Asahi host measurement and provider readiness data;
- release evidence bundle with signed/provenance artifacts;
- rollback, teardown, and wipe workflows.

## Risk posture

Current bootstrap risk is acceptable for dry-run/operator evaluation because:

- activation is evaluated, not executed;
- render artifacts are explicitly not authorization;
- missing policy or grants fail closed;
- unsafe storage receipts fail closed;
- runtime directories are not automatically created;
- no model provider is started;
- no raw prompts, KV cache, secrets, or private memory are emitted in receipts.

Production risk remains unacceptable until live policy, registry, evidence, provenance, and runtime controls are implemented.

## Recommended next implementation sequence

1. Confirm `make validate` in a real runner.
2. Resolve GitHub Actions visibility.
3. Add image digest pinning/provenance schema fields and strict renderer mode.
4. Add Policy Fabric client/stub module.
5. Add Agent Registry client/stub module.
6. Add AgentPlane evidence staging/submission module.
7. Add local LVM probe/planning commands.
8. Add provider discovery commands.
9. Add controlled provider activation behind ActivationDecision.
10. Add release evidence bundle generation.
