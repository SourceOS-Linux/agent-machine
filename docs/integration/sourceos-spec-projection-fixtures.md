# SourceOS Spec Projection Fixtures

Status: integration fixtures for pending SourceOS typed-contract projections

## Purpose

This directory records Agent Machine examples that conform to the SourceOS/SociOS projection contracts proposed in `SourceOS-Linux/sourceos-spec` PR #89 and its successor PRs.

The fixtures intentionally live under `fixtures/sourceos-spec/` rather than `examples/` because Agent Machine's canonical `examples/` directory is validated through repo-local `kind`-based contracts. The SourceOS projection contracts use the broader SourceOS `type` discriminator and must not be forced into the repo-local example validator until the projection schemas are promoted and synchronized.

## Fixtures

| Fixture | SourceOS projection type | Purpose |
| --- | --- | --- |
| `fixtures/sourceos-spec/sourceosmodelcarryref.json` | `SourceOSModelCarryRef` | Approved on-device reference to a governed model/service profile carried by SourceOS without mutable model state. |
| `fixtures/sourceos-spec/inferenceprovider.json` | `InferenceProvider` | Backend-neutral provider capability shape for local/cluster/remote governed inference. |
| `fixtures/sourceos-spec/modelresidency.json` | `ModelResidency` | Observed model availability and cache/load state on an Agent Machine. |
| `fixtures/sourceos-spec/placementfact.json` | `PlacementFact` | Machine-local scheduling and policy fact for runtime placement. |
| `fixtures/sourceos-spec/agentmachinereceipt.json` | `AgentMachineReceipt` | Runtime evidence emitted after probe, placement, execution, cache reuse, model load/unload, or policy-mediated side effects. |

## Validation

Run:

```bash
make validate-sourceos-projections
```

or as part of the full gate:

```bash
make validate
```

The local validator checks structural fixture shape, expected `type` discriminators, required projection fields, and `urn:srcos:` identity posture. Full JSON Schema validation belongs in `SourceOS-Linux/sourceos-spec` once the projection schemas merge.

## Boundary rules

1. These fixtures are not runtime activation authority.
2. These fixtures do not start providers, download models, mutate caches, or grant tool use.
3. Agent Machine's repo-local contracts remain authoritative for bootstrap runtime validation until the SourceOS projection schemas are promoted.
4. SourceOS projection fixtures are compatibility artifacts for the cross-repo Foundry path: `functional-model-surfaces → sourceos-spec → sourceos-model-carry → agent-machine → agentplane`.
