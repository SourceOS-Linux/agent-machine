# Deployment Safety

Agent Machine deployment files are currently skeleton targets. They make the local and Kubernetes runtime contracts concrete, but they are not production release manifests.

This distinction matters. Agent Machine runs sensitive agent infrastructure: model stores, prompt-prefix cache, KV cache, retrieval packs, tool surfaces, browser/terminal runtimes, scratch workspaces, and execution evidence. A runnable manifest is not automatically a safe manifest.

## Current deployment surfaces

| Surface | File | Status |
| --- | --- | --- |
| Local Podman Quadlet | `deploy/quadlet/agent-machine-llama-cpp.container` | Skeleton local AgentPod template |
| Kubernetes / TopoLVM | `deploy/k8s/llama-cpp-topolvm-pod.yaml` | Skeleton cluster AgentPod template |

These files are intended to drive contract alignment and validation. They should not be treated as final production deployment artifacts.

## Required gates before production use

Before any sensitive workload uses an Agent Machine deployment, the following gates are required.

### 1. Image digest pinning

Container images must be pinned by digest. Tags are mutable and are insufficient for repeatable agent execution.

Required evidence:

- image reference;
- immutable digest;
- registry origin;
- SBOM reference where available;
- vulnerability scan reference where available.

### 2. Signed provenance

Runtime artifacts must have signed provenance where possible. This includes container images, local binaries, installer artifacts, schemas, generated manifests, and release bundles.

Required evidence:

- signer identity;
- signature reference;
- attestation reference;
- source commit;
- build workflow identity.

### 3. Policy Fabric admission

Policy Fabric must approve the workload before activation. The deployment should be treated as desired state, not authorization by itself.

Admission should cover:

- workload purpose;
- allowed agent identity;
- allowed model/provider;
- allowed cache reuse domain;
- allowed network exposure;
- allowed storage classes;
- allowed side effects;
- required receipts.

### 4. Agent Registry grant

Every non-human runtime participant must resolve through Agent Registry before the workload starts handling sensitive context.

Grant checks should cover:

- agent identity;
- session identity;
- tool grants;
- model/provider authorization;
- memory/cache scope;
- revocation status;
- expiration.

### 5. Network policy

Network exposure must be denied by default.

Local defaults:

- bind inference endpoints to loopback only;
- deny external exposure unless explicitly policy-approved;
- avoid host networking by default.

Kubernetes defaults:

- ClusterIP only for skeleton services;
- default-deny egress;
- explicit ingress policy before any cross-pod or external access;
- no public ingress without signed intent and policy approval.

### 6. Storage safety

Storage mounts carry sensitive cache and model state. Every deployment must treat prompt/KV cache as sensitive.

Required checks:

- model volume mounted read-only where possible;
- cache volume scoped by identity and policy domain;
- evidence volume secret-free by default;
- scratch volume explicitly ephemeral or lifecycle-managed;
- no world-writable sensitive mountpoints;
- encryption posture recorded;
- quota and wipe behavior recorded;
- snapshot lineage recorded when snapshots are allowed.

### 7. Receipt emission

Agent Machine deployments must emit receipts for placement, runtime, storage, and policy-relevant events.

Receipts must not include:

- raw prompt content;
- raw KV-cache content;
- private memory contents;
- unredacted credentials;
- model-provider secrets.

Receipts should include:

- AgentMachine ID;
- AgentPod ID;
- provider ID;
- model digest where applicable;
- tokenizer digest where applicable;
- image digest where applicable;
- storage backend and volume class;
- policy decision reference;
- Agent Registry grant reference;
- timestamp and runtime version.

### 8. Runtime hardening

Local and Kubernetes runtimes should enforce least privilege.

Required defaults:

- no privileged containers;
- no secret values in specs;
- no host network unless policy-approved;
- no raw Docker socket mounts;
- read-only root filesystem where possible;
- dropped capabilities by default;
- SELinux labels preserved where SELinux is enforcing;
- seccomp default profile where Kubernetes supports it.

## Skeleton manifest limitations

The current skeletons intentionally omit some production controls so the repo can stabilize the contract first.

Known missing controls:

- digest-pinned images;
- generated manifests from AgentPod objects;
- live Policy Fabric admission checks;
- live Agent Registry grant resolution;
- signed deployment bundles;
- storage receipt sidecar or controller;
- model digest inventory;
- tokenizer digest inventory;
- NetworkPolicy ingress design;
- PodDisruptionBudget / Deployment / StatefulSet controller shape;
- service monitor / metrics surface.

## Promotion rule

A deployment file may move from skeleton to production candidate only when it has:

1. schema-backed source object;
2. generated or reproducible manifest path;
3. image digest pinning;
4. policy admission reference;
5. Agent Registry grant reference;
6. storage receipt behavior;
7. network policy behavior;
8. validation in CI;
9. documented rollback and wipe behavior.

## Implementation order

1. Validate YAML syntax and basic safety in CI.
2. Add manifest generation from AgentPod examples.
3. Add digest-pinned image references.
4. Add deployment receipt schema.
5. Add Policy Fabric admission stub.
6. Add Agent Registry grant stub.
7. Add local Quadlet activation plan.
8. Add Kubernetes controller shape after the schema stabilizes.
