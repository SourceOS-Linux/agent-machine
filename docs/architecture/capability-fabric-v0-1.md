# Capability Fabric v0.1

Status: draft architecture patch. Runtime behavior is not enabled by this document.
Scope: extends Agent Machine from a runtime-control substrate into a governed capability fabric while preserving its existing boundary: Agent Machine owns machine-local execution, activation decisions, receipts, and evidence, but not agent cognition, AgentPlane orchestration, Policy Fabric policy authorship, or Agent Registry authority.

## Why this patch exists

Agent Machine already treats activation as something that must be admitted by policy and evidenced by receipts. The next boundary is narrower and more operational: every agent action that can observe, mutate, export, egress, remember, publish, or interact with a protected party must pass through an explicit capability contract.

This patch turns the lessons from sandbox export discipline, A2A/MCP swarming, evaluation gates, and Alexandrian safeguarding into Agent Machine contracts. It does not make Agent Machine an agent brain or policy authority. It makes Agent Machine a better enforcement substrate for capability law.

## Normative thesis

Agent Machine is a signed, stateful, policy-governed capability fabric with explicit planes, typed interactions, short-lived grants, evidence-grade artifacts, revocation, and testable invariants.

The machine may run agents. It must not trust agents.

## Plane separation

Agent Machine recognizes two separate planes:

- A2A control plane: identity, attestation, discovery, negotiation, UX contract, grant issuance, revocation, and settlement.
- MCP tool plane: narrowly scoped tool calls after grants exist.

Tool servers must not self-authorize. MCP binding is a consequence of A2A negotiation, PolicyAdmission, AgentRegistryGrant state, and local activation evidence.

Required lifecycle:

```text
HELLO
ATTEST
DISCOVER
NEGOTIATE
UX_CONTRACT
GRANT
BIND
EXECUTE
AUDIT_SETTLE
```

`REVOKE` is not a final phase. It is an interrupt that must invalidate grants even when a runtime process still exists.

## New contract families

The patch introduces five draft schemas.

| Kind | Purpose |
| --- | --- |
| `A2AStateMachine` | Defines the required A2A lifecycle, control/tool plane split, phase outputs, and revocation interrupt semantics. |
| `CapabilityDeclaration` | Defines one MCP-exposed capability with server/tool/effect, danger class, schema refs, quotas, data classes, and policy hook. |
| `ArtifactBoundary` | Defines default-deny export policy, path buckets, realpath/symlink checks, depth-capped enumeration, manifests, and audit ledger requirements. |
| `EvalGateProfile` | Defines loop budgets, metric thresholds, publish/finalize behavior, and fail-closed evaluation gating. |
| `InteractionSafetyPack` | Defines typed roles, rooms, communication primitives, incident severity, data planes, jurisdiction gating, and launch gates for safety-critical domains. |

These are draft-local Agent Machine contracts until stabilized and promoted into `sourceos-spec`.

## Core invariants

1. Prompt authority is not execution authority. Any material action requires a declared capability, PolicyAdmission, active AgentRegistryGrant, and local activation evidence.
2. Visibility is not exportability. Readable paths are not exportable by default. Exportability is controlled by an `ArtifactBoundary`.
3. Copy-to-artifact is the safe export path. Evidence selected from sensitive buckets must be copied into an approved artifact root before export.
4. Symlink escapes are denied. Export checks resolve real paths and block escapes from allowed roots.
5. Enumeration is sensitive. Directory enumeration must be depth-capped unless an explicit policy exception is recorded.
6. Revocation beats kill. Authorization collapse must happen even if process termination lags.
7. Egress is a capability. Direct network access is not a runtime default. External calls route through declared, policy-gated egress capabilities.
8. Memory is a capability. Memory write, read, summarize, trim, and partition operations are governed context transforms, not ambient scratchpad behavior.
9. Evaluation gates are authorization gates. Weak faithfulness, weak context precision, weak relevancy, exhausted iteration budget, or failed security eval blocks publish/finalize.
10. High-risk interactions are typed. Safety-critical domains use role, space, primitive, severity, data-plane, and jurisdiction contracts instead of moderation-only controls.
11. Records and evidence are separate planes. User-owned records and safety evidence must be modeled separately, with sealed packets only when triggered.
12. Receipts stay secret-free. Contracts and examples must not require raw prompt content, secret values, private memory, raw media, or credential material.

## Implementation order

Phase 0: Contracts only.

- Add schemas and examples.
- Add mappings in `agent_machine.contracts`.
- Keep runtime behavior unchanged.

Phase 1: Validation hooks.

- Add negative fixtures for denied export, symlink escape, expired grant, revoked grant, no-grant MCP call, direct egress, and failed eval finalization.
- Ensure `make validate` exercises all new examples.

Phase 2: Local enforcement stubs.

- Add artifact-boundary checker.
- Add capability declaration resolver.
- Add eval-gate dry-run evaluator.
- Add A2A lifecycle trace validator.
- Emit secret-free run-ledger events.

Phase 3: Production connectors.

- Add connector-backed MCP servers for graph, relational, and vector retrieval.
- Add signed images and policy bundles.
- Add SPIRE workload identity, OPAL or signed policy-bundle distribution, and OpenLineage/Marquez lineage sink.

## Acceptance tests to add next

```text
deny_export_runtime_home
deny_export_platform_scaffolding
deny_export_kernel_pseudofs
deny_symlink_escape_from_artifact_root
deny_uncapped_recursive_export
deny_mcp_bind_without_a2a_grant
deny_expired_grant
deny_revoked_grant_even_if_process_alive
deny_direct_network_without_egress_capability
deny_memory_cross_namespace_write
deny_publish_when_eval_gate_fails
deny_minor_private_adult_channel
deny_provider_minor_interaction_without_reviewed_jurisdiction_pack
seal_safety_packet_for_s3_plus_incident
```

## Non-goals

- Do not implement provider activation in this patch.
- Do not replace Policy Fabric, AgentPlane, Agent Registry, or sourceos-spec.
- Do not add live egress or connector access.
- Do not store raw prompts, raw media, private memory, secrets, or credentials in examples.
- Do not make youth-facing interactions available by default.
