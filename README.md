# Agent Machine

SourceOS Agent Machine is the Linux-first node substrate for local and clustered agent execution. It owns the machine-local runtime layer: hardware/runtime probing, inference provider lifecycle, model residency, cache-aware scheduling facts, AgentPod envelopes, governed side-effect boundaries, and execution receipts that upstream AgentPlane and Policy Fabric can verify.

Agent Machine is not a new agent brain, chat app, or orchestration plane. It is the managed compute surface that lets AgentTerm, TurtleTerm, BearBrowser, AgentPlane, Sociosphere, SourceOS, and Kubernetes-backed clusters ask one question consistently:

> Where can this agent workload run safely, with the right model, cache locality, policy grants, and evidence trail?

## Core boundary

| Resource | Meaning |
| --- | --- |
| `AgentMachine` | A managed host/node substrate: laptop, workstation, edge box, VM, bare-metal GPU host, or Kubernetes node. |
| `AgentPod` | A schedulable agent workload envelope. On Kubernetes this maps toward a Pod/CRD. Locally it maps toward systemd, rootless Podman Quadlet, bubblewrap, toolbox, or another policy-governed runtime. |
| `InferenceProvider` | A backend adapter such as `llama.cpp`, `vLLM`, `SGLang`, `oMLX`, `Ollama-compatible`, or a remote governed endpoint. |
| `ModelResidency` | Evidence that a model/tokenizer/quantization/runtime is loaded, warm, pinned, evictable, or unavailable on a machine. |
| `CacheTier` | RAM/NVMe/object-store cache policy for KV cache, prompt-prefix cache, embeddings, retrieval packs, scratch, and evidence staging. |
| `PlacementFact` | Machine facts consumed by schedulers and policies: accelerator, memory, storage, model residency, cache locality, isolation domain, and trust posture. |
| `AgentMachineReceipt` | Runtime evidence emitted after probing, placement, execution, cache reuse, model load/unload, or policy-mediated side effects. |

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
├── contracts/              # Draft JSON Schemas before promotion to sourceos-spec
├── docs/
│   ├── adr/                # Architecture decision records
│   ├── architecture/       # Runtime, profile, scheduling, and provider docs
│   └── integration/        # AgentPlane, Policy Fabric, AgentTerm, TopoLVM edges
├── examples/               # Conforming example payloads
├── deploy/                 # Future systemd, Quadlet, SELinux, and Kubernetes assets
├── adapters/               # Future provider adapter implementation lanes
└── tools/                  # Future probe and conformance tooling
```

## Initial milestones

1. Define the AgentMachine / AgentPod boundary and schema stubs.
2. Define the backend-neutral InferenceProvider contract.
3. Implement `agent-machine probe` for M2 Asahi and pure Linux profiles.
4. Emit machine/runtime/cache/model receipts consumable by AgentPlane.
5. Add Policy Fabric admission points for sensitive context, model load, cache reuse, and side effects.
6. Add AgentTerm/TurtleTerm/BearBrowser local inference route integration.
7. Add TopoLVM-backed AgentPod placement examples for Kubernetes nodes.

## Non-goals

- Replacing AgentPlane.
- Replacing Policy Fabric.
- Replacing Agent Registry.
- Becoming a chat UI.
- Depending on macOS-only acceleration for the Linux stack.
- Treating cache reuse as safe without identity, tenant, policy, and evidence boundaries.
