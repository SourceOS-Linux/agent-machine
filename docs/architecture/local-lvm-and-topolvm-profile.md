# Local LVM and TopoLVM Storage Profile

Agent Machine supports two related but distinct storage profiles:

1. `local-lvm`: host-managed LVM or LVM-thin volumes mounted into local AgentPods through systemd, rootless Podman, Quadlet, Docker compatibility, or another local runtime envelope.
2. `topolvm-k8s`: Kubernetes-native TopoLVM storage consumed through StorageClasses, PersistentVolumeClaims, and AgentPod-style workloads.

The shared abstraction is not TopoLVM itself. The shared abstraction is a governed storage contract for models, cache, scratch, evidence, and workload-local state.

## Decision

Agent Machine treats local LVM as a first-class advanced workstation/node profile and TopoLVM as the Kubernetes implementation of the same storage semantics.

This avoids two failures:

- treating local workstations as unmanaged directories under `~/.cache`;
- treating TopoLVM as if it could be mounted directly under Docker without the Kubernetes CSI control plane.

Local Agent Machine storage should be able to behave like cluster storage when the workload requires quota isolation, snapshot lineage, cache lifecycle, and evidence-grade receipts.

## Terminology

| Term | Meaning |
| --- | --- |
| `filesystem` | Baseline local directories. Lowest operational complexity. Good for first boot and simple developer flows. |
| `local-lvm` | Host LVM/LVM-thin volumes mounted into local AgentPods. Best for advanced local nodes. |
| `topolvm-k8s` | Kubernetes TopoLVM-backed PVCs used by AgentPods in a single-node or multi-node cluster. |
| `tmpfs` | Memory-backed cache/scratch tier for hot ephemeral data. |
| `object-store` | Durable cold tier such as S3-compatible storage, MinIO, or another governed backing store. |
| `remote-volume` | Externally provided network/block storage. Must be policy-gated before sensitive cache use. |

## Volume classes

Agent Machine should use stable logical volume classes across local and cluster deployments.

| Volume class | Purpose | Typical lifetime | Sensitive by default |
| --- | --- | --- | --- |
| `agent-models` | Model artifacts, quantized files, tokenizer assets, provider manifests | Durable | Yes |
| `agent-cache-hot` | RAM/tmpfs prompt fragments, short-lived runtime state | Ephemeral | Yes |
| `agent-cache-warm` | Local NVMe/LVM KV cache, prompt-prefix cache, embeddings, reranker state | Semi-durable | Yes |
| `agent-cache-cold` | Replicated or object-backed cache packs | Durable | Yes |
| `agent-scratch` | Temporary build/run workspace | Ephemeral | Usually |
| `agent-evidence` | Receipts, probe reports, run summaries, policy decisions, non-secret audit artifacts | Durable | Mixed |
| `agent-artifacts` | User-visible outputs and generated work products | Durable | Policy-dependent |

## Local LVM path

The local profile is:

```text
LVM volume group / thinpool
  -> logical volume per volume class or workload
  -> filesystem
  -> host mountpoint
  -> bind mount into local AgentPod runtime envelope
  -> storage receipt emitted to AgentPlane-compatible evidence
```

The preferred local runtime order is:

1. systemd user or system service where the workload is not containerized;
2. rootless Podman with Quadlet for long-running local AgentPods;
3. Podman CLI for development/testing;
4. Docker compatibility where required by external tooling;
5. bubblewrap/toolbox for narrower local isolation cases.

Docker compatibility is allowed, but it should not define the SourceOS default. Rootless Podman, Quadlet, systemd, and SELinux fit the SourceOS governance model better.

## Kubernetes TopoLVM path

The Kubernetes profile is:

```text
TopoLVM CSI
  -> StorageClass
  -> PersistentVolumeClaim or ephemeral CSI volume
  -> Kubernetes Pod / future AgentPod CRD
  -> mounted model/cache/scratch/evidence volume
  -> storage receipt emitted through Agent Machine and AgentPlane
```

In this mode, Kubernetes owns scheduling integration and PVC lifecycle. Agent Machine still owns the contract-level vocabulary: volume class, cache tier, sensitivity, evidence, wipe posture, and model/cache residency facts.

## M2 Asahi implications

M2 Asahi is Linux on Apple Silicon. The local storage path should not assume macOS, Metal, or macOS-only MLX acceleration.

For M2 Asahi, local LVM is useful because inference performance may be bounded by CPU/Vulkan availability. Structured storage gives the node a different advantage:

- pre-warmed GGUF model residency;
- explicit model cache quotas;
- local embedding and reranking indexes;
- prompt-prefix and retrieval-pack cache isolation;
- clean scratch teardown;
- durable evidence staging;
- repeatable probe results for AgentPlane and Policy Fabric.

## Safety and governance rules

1. Prompt/KV cache is sensitive by default.
2. Cache reuse must be scoped by agent identity, policy domain, tenant/workroom, model digest, tokenizer digest, and runtime adapter.
3. Cache receipts must summarize cache lineage without storing prompt text or secret values.
4. Evidence volumes must be durable but secret-free unless explicitly classified and encrypted.
5. Wipe events should be recorded as receipts.
6. Snapshots must record parent lineage and policy domain.
7. Model volumes must record digest/provenance, not only local file paths.
8. Runtime bind mounts must be read-only unless write access is required and policy-approved.
9. Host mountpoints must be stable and discoverable by `agent-machine probe`.
10. The local profile must fail closed if an expected sensitive volume is missing, world-writable, or mounted with unsafe permissions.

## Storage receipt fields

A storage receipt should include at least:

- receipt ID;
- AgentMachine ID;
- storage backend: `filesystem`, `local-lvm`, `topolvm-k8s`, `tmpfs`, `object-store`, or `remote-volume`;
- volume class;
- cache tier where applicable;
- host mount path or PVC name;
- filesystem type;
- size and free bytes;
- encryption posture;
- quota policy;
- snapshot parent or lineage marker;
- policy domain;
- sensitivity class;
- wipe/eviction status;
- timestamp;
- probe/runtime version.

## Implementation order

1. Add `CacheTier` schema.
2. Add example payloads for M2 Asahi local LVM and Linux workstation local LVM.
3. Add `agent-machine probe` design for detecting LVM, mountpoints, filesystem flags, SELinux mode, and container bind-mount capability.
4. Add Podman/Quadlet examples before Docker examples.
5. Add Kubernetes TopoLVM examples after the local schema is stable.

## Non-goals

- Requiring LVM for all local machines.
- Treating TopoLVM as a direct Docker volume driver.
- Storing raw prompts, secrets, or private memory contents in receipts.
- Replacing Kubernetes storage scheduling when running in Kubernetes mode.
