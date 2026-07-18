# Release Evidence Bundle

Agent Machine release evidence bundles are deterministic, secret-free summaries of what was validated, what source revision was evaluated, which contract/example/doc inventories were present, which rendered artifacts were derived, what supply-chain posture was available, and which blockers remain.

A bundle is not a signature by itself. It is the structured payload that future signing, transparency, and release-promotion flows can sign and publish.

## Decision

Agent Machine defines a `ReleaseEvidenceBundle` contract for bootstrap and release-candidate evidence.

The bundle records:

- repository identity;
- branch and commit SHA;
- optional pull request number;
- validation command and workflow run ID;
- schema inventory with file digests;
- example inventory with file digests;
- documentation inventory with file digests;
- rendered artifact digests;
- supply-chain strict-mode availability;
- readiness state;
- known blockers;
- receipt-safety flags.

## Current implementation

Implemented now:

- `contracts/release-evidence-bundle.schema.json`;
- `examples/release-evidence-bundle.bootstrap.json`;
- `src/agent_machine/release_bundle.py`;
- `scripts/generate-release-evidence.py`;
- `scripts/validate-release-bundle.py`;
- `make validate-release-bundle`.

## Validation commands

Generate a bundle from the current checkout:

```bash
python3 scripts/generate-release-evidence.py --pretty
```

Validate bundle example and generated output:

```bash
python3 scripts/validate-release-bundle.py
```

Full validation:

```bash
make validate
```

## Bootstrap behavior

The bootstrap bundle is intentionally secret-free and production-blocked. It may report `validation.status=unknown` when generated outside CI, but it still validates its schema, inventories, rendered artifact digests, supply-chain posture, known blockers, and receipt-safety posture.

## Release-candidate behavior

A release candidate should set:

```text
validation.status = passed
validation.workflowRunId = <green run id>
source.commitSha = <validated commit sha>
source.pullRequest = <PR number, if applicable>
```

It must also have no unresolved release-candidate blockers for the relevant maturity level.

## Production blockers

The current bundle deliberately retains production blockers, including:

- main-branch CI visibility and branch protection policy;
- real image signature/provenance verification;
- real Policy Fabric client or endpoint;
- real Agent Registry grant resolver;
- real AgentPlane evidence submission or staging client;
- local LVM provisioning/probe implementation;
- TopoLVM runtime integration beyond skeleton manifests;
- provider discovery and controlled provider activation;
- M2 Asahi host measurement and provider readiness data;
- signed release evidence bundle;
- rollback, teardown, and wipe workflows.

## Future hardening

Future release bundle work should add:

- signed bundle envelopes;
- provenance attestation references;
- transparency-log submission references;
- generated SBOM references;
- real image signature verification result;
- branch protection status;
- release artifact digests;
- rollback and wipe evidence references.
