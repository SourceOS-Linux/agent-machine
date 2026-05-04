# Image Digest Pinning and Provenance Gate

Agent Machine treats mutable image tags as acceptable only for bootstrap examples and dry-run operator evaluation. Release-candidate and production deployment artifacts must be digest-pinned and must carry non-secret provenance/SBOM references where available.

## Decision

Bootstrap mode may allow mutable image tags when the AgentPod explicitly declares:

```text
runtime.imageReferencePolicy = tag-allowed-bootstrap
```

Strict mode requires:

```text
runtime.imageOrCommand contains @sha256:<digest>
OR runtime.imageDigest is sha256:<digest>

runtime.imageReferencePolicy is digest-required or digest-pinned
runtime.sbomRef is present
runtime.provenanceRef is present
```

Strict mode is a release-candidate gate, not a bootstrap convenience.

## Why this matters

Agent Machine is allowed to render local Quadlet files and Kubernetes manifests. If those artifacts use mutable tags in production-like flows, a later pull could resolve to different code. That would break deterministic evidence, invalidate receipt assumptions, and weaken Policy Fabric and Agent Registry decisions.

Digest pinning gives the receipt chain a stable artifact identity.

## Current implementation

Implemented now:

- optional AgentPod runtime fields:
  - `imageDigest`;
  - `imageReferencePolicy`;
  - `sbomRef`;
  - `provenanceRef`;
- package helper module:
  - `src/agent_machine/supply_chain.py`;
- validation wrapper:
  - `scripts/validate-supply-chain.py`;
- digest-pinned example:
  - `examples/local-podman-llama-cpp.pinned.agent-pod.json`;
- Makefile stage:
  - `validate-supply-chain`.

## Bootstrap mode behavior

Bootstrap mode validates basic consistency but permits mutable tags when explicitly marked.

Expected bootstrap example:

```json
{
  "runtime": {
    "imageOrCommand": "ghcr.io/ggerganov/llama.cpp:server",
    "imageReferencePolicy": "tag-allowed-bootstrap"
  }
}
```

If a mutable image has no explicit policy, the validator warns.

## Strict mode behavior

Strict mode fails unless digest/provenance requirements are satisfied.

Expected strict example:

```json
{
  "runtime": {
    "imageOrCommand": "ghcr.io/ggerganov/llama.cpp@sha256:1111111111111111111111111111111111111111111111111111111111111111",
    "imageDigest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
    "imageReferencePolicy": "digest-pinned",
    "sbomRef": "urn:srcos:sbom:llama-cpp-server-placeholder",
    "provenanceRef": "urn:srcos:provenance:llama-cpp-server-placeholder"
  }
}
```

Strict mode rejects:

- mutable image tags;
- missing image digest;
- malformed digest;
- disagreement between `imageOrCommand@sha256` and `runtime.imageDigest`;
- missing `imageReferencePolicy`;
- `tag-allowed-bootstrap` policy;
- missing SBOM reference;
- missing provenance reference.

## Validation commands

Bootstrap and strict validation together:

```bash
make validate-supply-chain
```

Direct strict validation:

```bash
PYTHONPATH=src python3 -m agent_machine.supply_chain \
  examples/local-podman-llama-cpp.pinned.agent-pod.json \
  --strict
```

## Release-gate rule

A release candidate may not use mutable image tags in activation-capable AgentPods.

Production-ready Agent Machine must additionally connect image digests to:

- DeploymentReceipt artifacts;
- ActivationDecision inputs;
- AgentPlaneRuntimeEvidence artifacts;
- SBOM/provenance references;
- future signed release evidence bundles.

## Non-goals for this bootstrap gate

- Verifying signatures online.
- Pulling container images.
- Resolving mutable tags to real digests.
- Generating SBOMs.
- Submitting provenance to a transparency log.

Those are production-hardening tasks. This bootstrap gate ensures the contract and validator can already distinguish mutable bootstrap examples from digest-pinned release candidates.
