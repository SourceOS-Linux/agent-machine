# World-Class Release Gate

Agent Machine must not graduate from bootstrap prototype to SourceOS runtime component by informal confidence. It graduates only by passing explicit gates that make it deterministic, auditable, policy-bound, reproducible, and hard to misuse.

The standard is intentionally high. Agent Machine sits on the boundary between local machines, clustered AgentPods, model/cache residency, terminal/browser agent surfaces, storage mounts, and execution receipts. A weak runtime here would contaminate every higher plane.

## Release maturity levels

| Level | Meaning | Allowed use |
| --- | --- | --- |
| Prototype | Contracts, examples, and docs are evolving quickly. Validation may be partial. | Design iteration only. No sensitive workload activation. |
| Bootstrap-ready | CLI, install, examples, validation, and deterministic rendering are usable by developers/operators. | Local dry runs, generated plans, skeleton manifests, non-sensitive experiments. |
| Release-candidate | CI is visible and green, contracts are versioned, renderers are deterministic, install surface is tested, and integration stubs exist. | Controlled internal dogfood with explicit policy gates. |
| Production-blocked | Most engineering is present, but one or more release-blocking controls are missing. | No production claim. No sensitive autonomous activation. |
| Production-ready | All release-blocking gates pass, including policy admission, registry grants, runtime evidence, digest pinning, storage receipts, and rollback/wipe paths. | Governed SourceOS runtime component. |

Current status: **Bootstrap-ready in progress; production-blocked by design.**

## Non-negotiable release rule

Agent Machine may not be called production-ready until all release-blocking gates below are satisfied and recorded.

Render output is never authorization. Generated plans, Quadlet files, Kubernetes manifests, and deployment receipts are evidence artifacts only. Activation requires Policy Fabric admission and Agent Registry grant resolution.

## Gate 1: Contract integrity

Status: partially implemented.

Release-blocking requirements:

- Every schema under `contracts/` validates as JSON Schema draft 2020-12.
- Every example under `examples/` validates by `kind` against its schema.
- Every contract has a stable `$id` and `specVersion`.
- Versioning and compatibility rules are documented.
- Promotion path into `SourceOS-Linux/sourceos-spec` is documented.
- Breaking changes require explicit migration notes.

Evidence currently present:

- `scripts/validate-json.py`.
- `src/agent_machine/contracts.py`.
- `Makefile` target `validate-json`.

Missing:

- versioning policy;
- sourceos-spec promotion policy;
- compatibility/deprecation rules.

## Gate 2: Renderer determinism

Status: partially implemented.

Release-blocking requirements:

- AgentPod deployment plan rendering is deterministic.
- DeploymentReceipt rendering is deterministic and schema-validated.
- Quadlet rendering is deterministic and compared against checked-in skeletons.
- Kubernetes rendering is deterministic and semantically compared against checked-in skeletons.
- Renderers have package-owned modules and script wrappers.
- Renderers do not embed secrets.
- Renderers do not emit authorization claims.

Evidence currently present:

- `src/agent_machine/renderers/plan.py`.
- `src/agent_machine/renderers/quadlet.py`.
- `src/agent_machine/renderers/k8s.py`.
- `scripts/render-agentpod-plan.py` wrapper.
- `scripts/render-agentpod-quadlet.py` wrapper.
- `scripts/render-agentpod-k8s.py` wrapper.
- `contracts/agentpod-deployment-plan.schema.json`.
- `contracts/deployment-receipt.schema.json`.

Missing:

- generated manifest receipt support for Quadlet and Kubernetes artifacts;
- renderer unit tests independent of shell `make`;
- digest-pinned image rendering mode.

## Gate 3: Deployment safety

Status: partially implemented.

Release-blocking requirements:

- No privileged containers.
- No raw Docker or Podman socket mounts.
- No host networking unless policy-approved.
- Local endpoints bind loopback by default.
- Kubernetes services are ClusterIP by default.
- Kubernetes egress defaults to deny.
- Model mounts are read-only by default where possible.
- Prompt/KV cache is sensitive by default.
- Evidence outputs are secret-free by default.
- Storage/cache wipe behavior is defined.

Evidence currently present:

- `scripts/validate-quadlet.py`.
- `scripts/validate-yaml.py`.
- `deploy/quadlet/agent-machine-llama-cpp.container`.
- `deploy/k8s/llama-cpp-topolvm-pod.yaml`.
- `docs/architecture/deployment-safety.md`.

Missing:

- storage receipt schema;
- wipe/eviction receipt behavior;
- image digest pinning;
- provenance checks;
- admission-controlled non-loopback exposure flow.

## Gate 4: Installer reliability

Status: bootstrap-ready, not production-ready.

Release-blocking requirements:

- Homebrew direct formula installs the bootstrap CLI and package source.
- SourceOS tap formula is synchronized with the repo-local formula.
- Missing render dependencies fail with direct remediation.
- Render commands work after dependencies are present.
- Formula tests validate installed package source exists.
- Formula strategy for Python dependencies is decided before release candidate.

Evidence currently present:

- `packaging/homebrew/Formula/agent-machine.rb`.
- `SourceOS-Linux/homebrew-tap/Formula/agent-machine.rb`.
- `docs/architecture/homebrew-python-dependencies.md`.
- `docs/install.md`.
- `docs/troubleshooting.md`.

Missing:

- live Homebrew install test evidence;
- final Python dependency packaging decision;
- release artifact installer lane.

## Gate 5: CI and validation visibility

Status: blocked by visibility ambiguity.

Release-blocking requirements:

- `make validate` passes locally.
- GitHub Actions workflow is visible for commits and pull requests.
- CI runs `make validate` on push and pull request.
- CI output is inspectable.
- Failure logs are retrievable.
- Branch protection can require the validation job when the repo is ready.

Evidence currently present:

- `.github/workflows/validate.yml`.
- `Makefile` target `validate`.
- Issue #2 tracking Actions visibility.

Missing:

- confirmed green Actions run;
- branch protection policy;
- artifact/log retrieval proof.

## Gate 6: Policy Fabric admission

Status: missing; release-blocking.

Release-blocking requirements:

- Define a Policy Fabric admission request schema or stub.
- Admission input includes AgentPod, deployment plan, manifest digest, cache tier facts, provider facts, requested network exposure, storage classes, and side-effect scope.
- Admission output includes decision reference, decision digest, allowed scope, denied scope, obligations, expiration, and revocation hooks.
- Activation fails closed when admission is required but missing.

Required issue: Policy Fabric admission stub.

## Gate 7: Agent Registry grant

Status: missing; release-blocking.

Release-blocking requirements:

- Define Agent Registry grant reference shape.
- Grant covers agent identity, session identity, tool grants, model/provider authorization, cache/memory scope, storage/evidence scope, expiration, and revocation status.
- Activation fails closed when grant is required but missing.

Required issue: Agent Registry grant stub.

## Gate 8: AgentPlane runtime evidence

Status: missing; release-blocking.

Release-blocking requirements:

- Define AgentPlane runtime evidence submission stub.
- Runtime evidence includes AgentMachine ID, AgentPod ID, provider ID, deployment receipt ID, Policy Fabric decision reference, Agent Registry grant reference, image digest, model digest, tokenizer digest, storage receipts, cache reuse decision, and runtime status.
- AgentPlane must not infer missing deployment metadata after execution.

Required issue: AgentPlane receipt emission stub.

## Gate 9: Image digest and provenance

Status: missing; release-blocking.

Release-blocking requirements:

- Container images are digest-pinned for release-candidate and production deployments.
- Tags are allowed only in prototype/bootstrap skeletons.
- Image digest appears in receipts.
- SBOM/provenance reference is recorded where available.
- Unsigned or unpinned runtime artifacts cannot be promoted to production-ready.

Required issue: image digest pinning and provenance.

## Gate 10: Storage and cache receipts

Status: missing; release-blocking.

Release-blocking requirements:

- Define storage receipt schema.
- Receipts cover local filesystem, local LVM, TopoLVM PVC, tmpfs, object-store, and remote-volume backends.
- Receipts record volume class, mount/PVC reference, filesystem, size, encryption posture, quota, snapshot lineage, policy domain, sensitivity, wipe/eviction status, and timestamp.
- Raw prompt/KV-cache content is never included.

Required issue: storage receipt schema.

## Gate 11: M2 Asahi profile correctness

Status: partially implemented.

Release-blocking requirements:

- M2 Asahi is treated as Linux on Apple Silicon, not macOS.
- Metal is unavailable on M2 Asahi.
- Vulkan is probe-gated.
- `llama.cpp` CPU/ARM64 remains baseline until measured otherwise.
- oMLX is not a hard dependency for M2 Asahi.

Evidence currently present:

- `examples/m2-asahi-local-lvm.agent-machine.json`.
- `docs/architecture/agent-machine-probe.md`.
- `docs/troubleshooting.md`.

Missing:

- real `agent-machine probe` data from the M2 Asahi host;
- benchmark/profiling lane;
- provider readiness checks.

## Gate 12: Release evidence bundle

Status: missing; release-blocking.

Release-blocking requirements:

- Release candidate includes validation summary.
- Release candidate includes schema inventory.
- Release candidate includes generated artifact digests.
- Release candidate includes deployment receipts.
- Release candidate includes known limitations.
- Release candidate includes rollback and wipe instructions.

## Release-blocking issue set

The initial required release-blocking issues are:

1. Policy Fabric admission stub.
2. Agent Registry grant stub.
3. AgentPlane receipt emission stub.
4. Image digest pinning and provenance.
5. Storage receipt schema.
6. GitHub Actions visibility / CI confirmation.
7. World-class release gate tracking issue.

## Promotion rule

Promotion requires evidence, not assertion. Each gate must have:

- owner or owning subsystem;
- validation command or proof artifact;
- failure behavior;
- documented remediation;
- linked issue/PR history;
- explicit release status.

Until then, Agent Machine remains a bootstrap runtime substrate, not production runtime infrastructure.
