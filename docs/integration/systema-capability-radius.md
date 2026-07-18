# Agent Machine: Systema Capability Radius Integration

## What This Documents

Agent Machine's alignment with Systema's R0–R5 capability radius semantics. The radius defines the maximum scope within which an AgentPod may exercise capabilities.

## Radius Levels in Agent Machine Context

| Radius | Systema label | Agent Machine meaning |
|---|---|---|
| R0 | observe-only | Read probes, health checks, non-mutating queries. No filesystem writes, no network calls beyond mesh. |
| R1 | local-bounded | Read/write within declared workspace directory only. No subprocess execution, no network. |
| R2 | local-execution | Subprocess execution within declared workspace. No network calls. No filesystem access outside workspace. |
| R3 | local-network | R2 + declared outbound network endpoints only (e.g., `127.0.0.1:8080` for local steering). No internet. |
| R4 | mesh-connected | R3 + Prophet Mesh endpoints. No arbitrary internet. |
| R5 | internet-connected | Full internet access within declared capability declaration. Requires explicit policy admission. |

## Mapping to Agent Machine Contracts

### capability-declaration.schema.json

The `capabilityRadius` field (to be added in a follow-on tranche) maps to R0–R5. Until then, the effective radius is inferred from the combination of:
- `allowedFilesystemPaths[]` → R0 if empty, R1 if set
- `allowedSubprocesses[]` → R2 if set
- `allowedNetworkEndpoints[]` → R3/R4/R5 based on endpoint class

### policy-admission.schema.json

Policy decisions reference the declared radius. A request for a capability beyond the declared radius is automatically denied without policy evaluation.

### activation-decision.schema.json

Activation decisions carry the effective radius assigned at admission time. The runtime enforces this radius for the pod's lifetime.

## Radius Enforcement

Enforcement is fail-closed: if a capability request cannot be verified as within the pod's assigned radius, it is denied and a policy-admission record with `verdict: denied` and `rationale: "outside-capability-radius"` is emitted.

In-flight radius downgrades (e.g., due to grant revocation) terminate the pod via `lifecycle.schema.json` `terminated` event.

## Example Radius Profiles

See:
- `examples/reachability/agent-machine-capability-radius.example.json` — R0, R2, R4 examples

## Referenced Schemas

- `contracts/capability-declaration.schema.json`
- `contracts/activation-decision.schema.json`
- `contracts/policy-admission.schema.json`
- `contracts/lifecycle.schema.json`
