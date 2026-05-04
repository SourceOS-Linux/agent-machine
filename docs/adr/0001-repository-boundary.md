# ADR 0001: Agent Machine Repository Boundary

Status: accepted for bootstrap.

## Context

Agent Machine sits between SourceOS host/node reality and higher-level agent orchestration. It must not become the central agent brain, workspace controller, chat surface, or policy authority. It owns the local and cluster node substrate: probing, runtime envelopes, local/cluster AgentPod execution targets, storage/cache/evidence receipts, provider readiness, and activation decision artifacts.

The surrounding stack already has clear owners:

- AgentPlane owns run/evidence plane and replayable execution records.
- Policy Fabric owns admission and side-effect policy.
- Agent Registry owns agent identity, session grants, tool/model/cache/memory authority, and revocation.
- SourceOS owns OS build/install/update posture.
- TurtleTerm, BearBrowser, and AgentTerm own user/operator surfaces.
- Sociosphere owns workspace state and actuation surfaces.

## Decision

Agent Machine owns the machine/node runtime-control substrate.

In scope:

- `AgentMachine` contracts;
- `AgentPod` contracts;
- `InferenceProvider` contracts;
- model/cache/storage/evidence volume contracts;
- local Quadlet deployment skeletons;
- Kubernetes/TopoLVM deployment skeletons;
- secret-free receipts;
- activation decision evaluation;
- host/runtime/provider probing;
- bootstrap CLI and package-owned validator/renderer/evaluator modules.

Out of scope:

- replacing AgentPlane;
- replacing Policy Fabric;
- replacing Agent Registry;
- becoming a chat UI;
- owning workspace-state routing;
- treating render output as authorization;
- activating providers before governance gates exist.

## Consequences

Agent Machine must be boringly deterministic. It should emit typed facts and decisions that upstream systems can verify. It should fail closed when policy, registry, storage, or evidence gates are missing. It should not hide runtime mutation behind install commands.

This boundary keeps the repo focused and prevents Agent Machine from accreting unrelated orchestration responsibilities.
