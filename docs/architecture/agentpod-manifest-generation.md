# AgentPod Manifest Generation

AgentPod examples are the contract source. Quadlet files and Kubernetes YAML should become generated or reproducibly derived deployment targets, not hand-maintained semantic forks.

## Goal

Define one path from an `AgentPod` JSON object to a concrete deployment surface:

```text
AgentPod JSON
  -> validate against contracts/agent-pod.schema.json
  -> policy/admission preflight
  -> render deployment target
  -> validate generated target
  -> emit generation receipt
```

Supported target surfaces:

| Target | Output |
| --- | --- |
| `local-podman-quadlet` | `deploy/quadlet/*.container` |
| `local-podman` | Podman CLI plan or future systemd unit wrapper |
| `local-systemd` | systemd service/unit plan |
| `kubernetes-pod` | Kubernetes YAML skeleton |
| `kubernetes-crd` | Future AgentPod CRD |

## Source-of-truth rule

The source of truth is the `AgentPod` object plus policy decisions and resolved runtime facts. Generated deployment files are artifacts.

A generated deployment artifact must be reproducible from:

- AgentPod JSON;
- selected target renderer version;
- Policy Fabric admission result;
- Agent Registry grant reference;
- selected AgentMachine profile;
- resolved storage/cache tier facts;
- resolved image digest and provenance facts.

## Required generation inputs

Minimum inputs:

- `AgentPod` ID;
- workload name and purpose;
- runtime mode;
- image or command reference;
- network mode;
- restart policy;
- CPU/memory requests and limits;
- accelerator requirements;
- storage mount declarations;
- port exposure declarations;
- policy flags;
- receipt requirements.

Production inputs additionally require:

- pinned image digest;
- SBOM/provenance references;
- Policy Fabric decision reference;
- Agent Registry grant reference;
- model digest;
- tokenizer digest where applicable;
- cache tier IDs resolved to concrete mount or PVC references;
- storage receipt behavior;
- network policy behavior.

## Quadlet renderer requirements

For `local-podman-quadlet`, the renderer must enforce:

- loopback binding for local inference endpoints unless policy-approved otherwise;
- `ReadOnly=true` where the runtime can support it;
- `NoNewPrivileges=true`;
- `DropCapability=all` by default;
- no privileged mode;
- no host networking by default;
- no Docker or Podman socket mounts;
- model mounts read-only by default;
- cache mounts scoped to approved cache tiers;
- evidence mounts enabled when receipts are required;
- SELinux relabel flags only when compatible with the host profile.

## Kubernetes renderer requirements

For `kubernetes-pod`, the renderer must enforce:

- namespace and service account presence;
- no privileged containers;
- `allowPrivilegeEscalation: false`;
- `readOnlyRootFilesystem: true` where possible;
- seccomp runtime default;
- PVCs for durable model/cache/evidence storage;
- TopoLVM StorageClass use when the storage profile is `topolvm-k8s`;
- ClusterIP by default;
- default-deny egress NetworkPolicy;
- no public ingress unless signed intent and policy approval exist.

## Receipt annotations

Generated manifests should carry non-secret annotations that connect them back to Agent Machine control objects.

Suggested annotations:

```text
agent-machine.sourceos.dev/agent-pod-id
agent-machine.sourceos.dev/agent-machine-id
agent-machine.sourceos.dev/provider-id
agent-machine.sourceos.dev/policy-decision-ref
agent-machine.sourceos.dev/agent-registry-grant-ref
agent-machine.sourceos.dev/receipts-required
agent-machine.sourceos.dev/raw-content-in-receipts
agent-machine.sourceos.dev/generator-version
```

Annotations must not include raw prompt content, raw KV-cache content, private memory, unredacted credentials, or provider secrets.

## Generation receipt

Every generated manifest should have a generation receipt containing:

- generator name and version;
- source AgentPod digest;
- generated artifact path;
- generated artifact digest;
- selected target surface;
- selected AgentMachine profile;
- policy decision reference;
- Agent Registry grant reference;
- image digest references;
- storage resolution summary;
- timestamp.

## Implementation order

1. Keep hand-written skeletons under `deploy/` while schemas stabilize.
2. Add validation for Quadlet and Kubernetes skeletons.
3. Add a pure JSON-to-plan renderer before writing final manifest files.
4. Add Quadlet renderer.
5. Add Kubernetes YAML renderer.
6. Add generation receipts.
7. Add digest-pinning enforcement.
8. Promote stable generated shapes to SourceOS typed contracts.

## Non-goals

- Replacing Kubernetes controllers.
- Treating generated manifests as authorization.
- Embedding secrets in manifests or annotations.
- Making Docker the default local runtime surface.
