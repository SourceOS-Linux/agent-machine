# Agent Machine

SourceOS Agent Machine is the Linux-first node substrate for local and clustered agent execution. It owns the machine-local runtime layer: hardware/runtime probing, inference provider lifecycle, model residency, cache-aware scheduling facts, AgentPod envelopes, governed side-effect boundaries, activation decisions, and execution receipts that upstream AgentPlane and Policy Fabric can verify.

Agent Machine is not a new agent brain, chat app, or orchestration plane. It is the managed compute surface that lets AgentTerm, TurtleTerm, BearBrowser, AgentPlane, Sociosphere, SourceOS, and Kubernetes-backed clusters ask one question consistently:

> Where can this agent workload run safely, with the right model, cache locality, policy grants, and evidence trail?

## Current status

Agent Machine is a bootstrap runtime-control substrate. It is intentionally production-blocked until the release gate is satisfied.

| Area | Status |
| --- | --- |
| Contracts and examples | Bootstrap-ready |
| Plan / receipt / Quadlet / Kubernetes renderers | Bootstrap-ready |
| StorageReceipt / AgentPlaneRuntimeEvidence / ActivationDecision modeling | Bootstrap-ready |
| PolicyAdmission and AgentRegistryGrant semantic validation | Bootstrap-ready |
| Homebrew bootstrap install | Bootstrap-ready, with documented external Python render dependencies |
| Provider activation | Not implemented |
| GitHub Actions visibility | Blocked / unresolved |
| Production readiness | Blocked by release gate |

Start here:

- [Documentation index](docs/index.md)
- [Quickstart](docs/quickstart.md)
- [Install guide](docs/install.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Bootstrap MVP readiness](docs/architecture/bootstrap-mvp-readiness.md)
- [World-class release gate](docs/architecture/world-class-release-gate.md)

## Quickstart

Install from the direct Homebrew formula:

```bash
brew install --HEAD https://raw.githubusercontent.com/SourceOS-Linux/agent-machine/main/packaging/homebrew/Formula/agent-machine.rb
```

Install render/evaluation dependencies from a checkout:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run safe bootstrap diagnostics:

```bash
agent-machine version
agent-machine paths
agent-machine doctor --format json
agent-machine probe --format json
```

Render a local AgentPod plan:

```bash
agent-machine render plan examples/local-podman-llama-cpp.agent-pod.json --pretty
```

Evaluate allowed activation as a dry-run decision artifact:

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

Full walkthrough: [docs/quickstart.md](docs/quickstart.md).

## Validation

Canonical validation:

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

Important: CI visibility is still unresolved through the current connector/API path. Empty workflow/status results are tracked in Issue #2 and are not proof of pass or failure.

## Install

Agent Machine follows the TurtleTerm and BearBrowser install philosophy: Homebrew is a first-class developer/operator surface, direct repository formulas work before tap promotion, and runtime activation remains explicit and policy-aware.

Immediate direct Homebrew install:

```bash
brew install --HEAD https://raw.githubusercontent.com/SourceOS-Linux/agent-machine/main/packaging/homebrew/Formula/agent-machine.rb
```

Preferred SourceOS tap install:

```bash
brew install SourceOS-Linux/tap/agent-machine
```

Current tap HEAD formula flow:

```bash
brew install --HEAD SourceOS-Linux/tap/agent-machine
```

Local checkout flow:

```bash
brew install --HEAD ./packaging/homebrew/Formula/agent-machine.rb
```

Validate:

```bash
agent-machine version && agent-machine paths && agent-machine probe --format json
```

See [docs/install.md](docs/install.md) for installer philosophy, runtime directory targets, future setup commands, and M2 Asahi notes.

## Core boundary

| Resource | Meaning |
| --- | --- |
| `AgentMachine` | A managed host/node substrate: laptop, workstation, edge box, VM, bare-metal GPU host, or Kubernetes node. |
| `AgentPod` | A schedulable agent workload envelope. On Kubernetes this maps toward a Pod/CRD. Locally it maps toward systemd, rootless Podman Quadlet, bubblewrap, toolbox, or another policy-governed runtime. |
| `InferenceProvider` | A backend adapter such as `llama.cpp`, `vLLM`, `SGLang`, `oMLX`, `Ollama-compatible`, or a remote governed endpoint. |
| `CacheTier` | RAM/NVMe/object-store cache policy for KV cache, prompt-prefix cache, embeddings, retrieval packs, scratch, and evidence staging. |
| `StorageReceipt` | Secret-free evidence for model/cache/scratch/evidence storage across local filesystem, local LVM, TopoLVM, tmpfs, object-store, and remote-volume backends. |
| `PolicyAdmission` | Policy Fabric admission decision/stub for render, placement, activation, cache reuse, side-effect, teardown, and wipe operations. |
| `AgentRegistryGrant` | Agent Registry grant/stub for agent identity, session, provider, model, tool, cache, memory, storage, and evidence scopes. |
| `AgentPlaneRuntimeEvidence` | Secret-free runtime evidence emitted or staged for placement, activation, runtime status, teardown, or wipe events. |
| `ActivationDecision` | Final pre-runtime dry-run decision artifact: activation allowed or fail-closed, with reasons and required preconditions. |

## Product thesis

The scheduler is the product. Local and clustered agent workloads are dominated by repeated context: system instructions, repo state, tool schemas, memory packs, retrieval context, prompt prefixes, and conversation history. Agent Machine treats model residency and cache locality as first-class scheduling inputs instead of incidental runtime details.

The immediate design reference is the oMLX-style local inference product pattern: OpenAI-compatible local endpoints, model lifecycle controls, hot/cold cache tiers, continuous batching, cache efficiency metrics, and a native operator view. Agent Machine generalizes that pattern into a SourceOS/Linux contract with policy admission, signed provenance, Agent Registry identity binding, TopoLVM/cache placement, and AgentPlane receipts.

## Platform profiles

### M2 Asahi Linux profile

M2 Asahi is Linux on Apple Silicon, not macOS. The initial M2 Asahi path is Linux ARM64 with CPU and Vulkan-capability probing. It must not assume Metal or macOS-only MLX acceleration.

Initial backend order:

1. `llama.cpp` CPU/ARM64 baseline.
2. `llama.cpp` Vulkan probe path where the Asahi graphics stack supports the workload.
3. OpenAI-compatible local server facade.
4. Lightweight CPU embeddings/reranking.
5. MLX CPU-only experiments only as compatibility tests, not as the primary acceleration strategy.
6. No hard runtime dependency on oMLX for Asahi.

### Pure Linux profile

Pure Linux nodes cover Fedora Silverblue/SourceOS workstations, bare-metal GPU hosts, VMs, and Kubernetes nodes.

Initial backend order:

1. `vLLM` and `SGLang` for Linux GPU serving where supported.
2. `llama.cpp` CUDA/HIP/Vulkan/CPU paths according to hardware.
3. `Ollama-compatible` adapter only as a convenience compatibility layer.
4. TopoLVM-backed model/cache/scratch/evidence volumes for Kubernetes AgentPods.
5. Signed OCI/systemd/Quadlet deployment for immutable SourceOS-style nodes.

### macOS Apple Silicon compatibility profile

macOS Apple Silicon may use oMLX/MLX as an optional backend, but this repo remains Linux-first. oMLX informs the product pattern; it does not define the core Agent Machine contract.

## Integration map

| Upstream plane | Integration role |
| --- | --- |
| `SourceOS-Linux/sourceos-spec` | Canonical schemas, JSON-LD vocabulary, OpenAPI/AsyncAPI fragments after contracts stabilize. |
| `SociOS-Linux/agentos-spine` | Linux-side assembly map and workspace integration. |
| `SocioProphet/agentplane` | Validated runs, replay/evidence artifacts, run receipts, executor placement. |
| `SocioProphet/policy-fabric` | Admission decisions, side-effect policy, cache reuse policy, sensitive context release. |
| Agent Registry | Agent identities, sessions, grants, revocation, memory/tool authority. |
| `SourceOS-Linux/agent-term` | Terminal-native operator surface and ChatOps event stream. |
| TurtleTerm / BearBrowser | First-class local surfaces that consume governed inference routes and machine receipts. |
| TopoLVM | Kubernetes/local storage model for cache, models, scratch, evidence, and artifact staging. |

## Repository layout

```text
agent-machine/
├── bin/                    # Bootstrap CLI
├── contracts/              # Draft JSON Schemas before promotion to sourceos-spec
├── docs/
│   ├── adr/                # Architecture decision records
│   ├── architecture/       # Runtime, profile, scheduling, governance, release-gate docs
│   └── integration/        # AgentPlane, Policy Fabric, AgentTerm, TopoLVM edges
├── examples/               # Conforming example payloads
├── packaging/              # Homebrew and future package/install surfaces
├── deploy/                 # Quadlet and Kubernetes skeleton deployment assets
├── scripts/                # Validation and wrapper entrypoints
└── src/agent_machine/      # Transitional Python package implementation
```

## Initial milestones

1. Define the AgentMachine / AgentPod boundary and schema stubs.
2. Define the backend-neutral InferenceProvider contract.
3. Implement `agent-machine probe` for M2 Asahi and pure Linux profiles.
4. Emit machine/runtime/cache/model receipts consumable by AgentPlane.
5. Add Policy Fabric admission points for sensitive context, model load, cache reuse, and side effects.
6. Add AgentTerm/TurtleTerm/BearBrowser local inference route integration.
7. Add TopoLVM-backed AgentPod placement examples for Kubernetes nodes.

## Production blockers

Agent Machine is not production-ready until the release gate passes. Current blockers include:

- visible green CI run;
- image digest pinning and provenance gate;
- real Policy Fabric client or endpoint;
- real Agent Registry grant resolver;
- real AgentPlane evidence submission/staging client;
- local LVM provisioning/probe implementation;
- TopoLVM runtime integration beyond skeleton manifests;
- provider discovery and controlled activation implementation;
- M2 Asahi host measurement and provider readiness data;
- release evidence bundle with signed/provenance artifacts;
- rollback, teardown, and wipe workflows.

## Non-goals

- Replacing AgentPlane.
- Replacing Policy Fabric.
- Replacing Agent Registry.
- Becoming a chat UI.
- Depending on macOS-only acceleration for the Linux stack.
- Treating cache reuse as safe without identity, tenant, policy, and evidence boundaries.
- Treating render output as authorization.
- Starting runtime providers before activation gates exist.
