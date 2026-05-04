# ADR 0001: Agent Machine and AgentPod Boundary

- Status: accepted
- Date: 2026-05-04

## Context

SourceOS needs a first-class runtime substrate for local and clustered agent workloads. Existing repositories already own adjacent planes: SourceOS substrate, typed contracts, AgentOS spine, AgentPlane execution evidence, Policy Fabric admission, Agent Registry identity, and AgentTerm/TurtleTerm/BearBrowser operator surfaces.

The missing layer is the machine substrate that knows what hardware is present, which runtime envelopes are available, which models are resident, which caches are warm, and what evidence can be emitted for placement and replay.

A separate `agent-pod` repository was considered. That split would prematurely separate local and cluster forms of the same contract.

## Decision

Create one repository: `SourceOS-Linux/agent-machine`.

Define two first-class resource types inside it:

- `AgentMachine`: a managed compute substrate. It may be a laptop, workstation, edge node, VM, bare-metal GPU host, or Kubernetes node.
- `AgentPod`: a schedulable workload envelope. On Kubernetes it maps toward Pod or CRD semantics. Locally it maps toward systemd, rootless Podman Quadlet, bubblewrap, toolbox, or another governed runtime envelope.

`AgentPod` is not a separate repository at this stage. It is a contract inside Agent Machine.

## Consequences

The same contract can cover M2 Asahi Linux workstations, Fedora Silverblue or SourceOS local machines, rootless local runtimes, Kubernetes pods with TopoLVM-backed volumes, GPU nodes running vLLM or SGLang, CPU/edge nodes running llama.cpp, and optional macOS Apple Silicon compatibility through oMLX-style adapters.

Agent Machine owns machine-local facts and runtime evidence. It does not own global orchestration, policy authorship, agent identity, or user-facing chat semantics.

## Boundary rules

1. Agent Machine exposes placement facts, but global placement policy belongs above it.
2. Agent Machine executes AgentPods only after the relevant policy and identity checks are satisfied.
3. Agent Machine manages model/runtime/cache lifecycle, but stable schemas promote to `sourceos-spec` after review.
4. Agent Machine emits receipts, but AgentPlane remains the durable execution and replay evidence plane.
5. Agent Machine may support oMLX-style patterns, but Linux profiles must not depend on macOS-only acceleration.

## Initial resource set

- `AgentMachine`
- `AgentPod`
- `InferenceProvider`
- `ModelArtifact`
- `ModelResidency`
- `CacheTier`
- `RuntimeCapability`
- `PlacementFact`
- `AgentMachineReceipt`

## Open questions

- Whether AgentPod should later split into a Kubernetes operator repository after the CRD stabilizes.
- Which minimal provider adapter should be implemented first after `agent-machine probe`.
- How cache metadata should be summarized without exposing sensitive workload content.
