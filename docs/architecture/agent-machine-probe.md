# Agent Machine Probe

`agent-machine probe` is the local discovery and evidence command for Agent Machine. It must produce a machine-readable report that can be converted into `AgentMachine`, `CacheTier`, `RuntimeCapability`, `PlacementFact`, and receipt objects.

The probe is not a benchmark by default. It is a trust and capability inventory. Benchmark subcommands can be added later.

## Goals

1. Identify the host profile accurately.
2. Discover local runtime envelopes.
3. Discover storage backends and cache/evidence mount safety.
4. Discover inference provider readiness without downloading models or starting unsafe services.
5. Emit secret-free evidence for AgentPlane and Policy Fabric.
6. Fail closed when sensitive cache/evidence assumptions are unsafe.

## Host profile detection

The probe should collect:

- hostname;
- OS and distribution;
- kernel release;
- architecture;
- immutable-host signals such as rpm-ostree availability;
- cgroup mode;
- SELinux mode;
- systemd availability;
- container runtime availability;
- user namespace availability;
- basic memory and disk facts.

Profile classification should prefer explicit evidence over assumptions.

Example profiles:

- `m2-asahi-linux`;
- `sourceos-workstation`;
- `fedora-silverblue`;
- `linux-gpu-node`;
- `linux-edge-node`;
- `kubernetes-node`;
- `macos-apple-silicon-compat`.

## Accelerator detection

The probe should detect accelerators conservatively:

| Accelerator | Detection posture |
| --- | --- |
| CPU | Always present, but record architecture and feature hints. |
| Vulkan | Probe runtime and device availability; do not assume working inference support. |
| CUDA | Detect driver/toolkit/runtime presence where applicable. |
| ROCm/HIP | Detect runtime presence where applicable. |
| Metal | Only applicable to macOS compatibility profile, not M2 Asahi Linux. |
| MLX | Distinguish macOS/Apple Silicon acceleration from Linux CPU-only compatibility. |

For M2 Asahi Linux, Metal must report unavailable and Vulkan must be probe-gated.

## Storage detection

The probe should inspect:

- expected Agent Machine base directories;
- mountpoints;
- filesystem type;
- total/free bytes;
- owner/group/mode;
- world-writable risk;
- symlink traversal risk;
- LVM physical volumes, volume groups, thinpools, and logical volumes where readable;
- LUKS/dm-crypt/fscrypt signals where available;
- TopoLVM/Kubernetes indicators when running on a Kubernetes node;
- tmpfs availability for hot cache;
- object-store configuration only by reference, never by secret value.

The probe should classify storage backend as one of:

- `filesystem`;
- `local-lvm`;
- `topolvm-k8s`;
- `tmpfs`;
- `object-store`;
- `remote-volume`.

## Mount safety checks

Sensitive volumes fail closed when:

- the mountpoint is missing;
- the mountpoint is world-writable;
- the mountpoint is owned by an unexpected user/group;
- a sensitive cache path traverses an untrusted symlink;
- expected encryption is absent;
- expected quota is absent;
- the container runtime cannot bind mount the path safely;
- SELinux labeling is absent or incompatible where SELinux is enforcing.

## Runtime envelope detection

The probe should detect local envelopes:

- systemd service support;
- systemd user service support;
- Podman;
- Quadlet;
- Docker compatibility;
- bubblewrap;
- toolbox;
- Kubernetes node context;
- k3s/kind/k3d/minikube hints where applicable.

Podman/Quadlet should be preferred over Docker for SourceOS-managed long-running local AgentPods.

## Inference provider detection

The probe should detect provider availability without assuming runtime readiness:

- `llama.cpp` binary or server path;
- OpenAI-compatible local endpoints configured for Agent Machine;
- `vLLM` availability on Linux GPU nodes;
- `SGLang` availability on Linux GPU nodes;
- `Ollama-compatible` endpoint availability as compatibility only;
- `oMLX` only under macOS Apple Silicon compatibility profiles;
- embeddings/reranker providers;
- OCR/VLM providers.

Provider detection must record:

- provider type;
- version where available;
- endpoint or binary reference;
- supported API surfaces;
- acceleration path;
- model directory reference;
- policy requirements;
- whether the provider is enabled, disabled, or probe-only.

## Evidence output

The probe output should be JSON-first. It should be able to emit:

- `AgentMachine` candidate object;
- `CacheTier` candidate objects;
- runtime capability facts;
- placement facts;
- warnings;
- hard failures;
- receipt metadata.

No probe output may include secret values, raw prompts, raw KV-cache contents, private memory content, or unredacted credentials.

## Suggested command shape

```text
agent-machine probe
agent-machine probe --format json
agent-machine probe --profile m2-asahi-linux
agent-machine probe --storage-only
agent-machine probe --runtime-only
agent-machine probe --providers-only
agent-machine probe --fail-closed
agent-machine probe --emit examples/local-probe.json
```

These command shapes are design targets, not implemented CLI behavior yet.

## Minimum viable probe

The first implementation should produce:

1. host facts;
2. SELinux mode;
3. cgroup mode;
4. container runtime facts;
5. LVM and mountpoint facts;
6. cache/evidence path safety checks;
7. CPU/Vulkan/CUDA/ROCm/Metal availability flags;
8. provider discovery for `llama.cpp` and local OpenAI-compatible endpoints;
9. one `AgentMachine` JSON candidate;
10. zero or more `CacheTier` JSON candidates.

## Future probe lanes

- benchmark mode;
- model digest inventory;
- tokenizer digest inventory;
- prompt-prefix cache inventory by hash only;
- TopoLVM PVC and StorageClass mapping;
- TPM/FIDO2 attestation hooks;
- signed probe receipts;
- AgentPlane direct receipt submission;
- Policy Fabric direct admission checks.
