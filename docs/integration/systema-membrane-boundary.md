# Agent Machine: Systema Membrane Boundary Integration

## What This Documents

Agent Machine's role in Systema's membrane accounting model. Agent Machine owns the machine-local runtime layer; every activation, deployment, and side-effect crosses a membrane that must be declared, admitted, and witnessed.

## Membranes in Agent Machine

### 1. Activation Membrane

The activation membrane controls whether an AgentPod may start executing on this machine.

**Crossing direction:** `declared → preflight → admitted | blocked`

**Admitted when:**
- Policy Fabric returns `admitted` or `conditional` for the AgentPod's capability declaration
- Steering artifact receipts are present and valid (if steering is requested)
- Boot phase is `unlocked-user-session` or later
- Agent Registry grant exists and is not revoked

**Blocked when:**
- Policy Fabric returns `denied`
- Required capability is `not_configured` (fail-closed)
- Artifact receipt is missing or digest mismatch
- Boot phase is insufficient (e.g., `pre-login`)

**Logged:** Every crossing attempt emits an `activation-decision.schema.json` record.

**Witnessed:** `agentplane-runtime-evidence.schema.json` carries a reference to the admission decision.

**Revoked:** If an in-flight AgentPod's grant is revoked, the pod's execution is terminated and a `lifecycle.schema.json` `terminated` event is emitted.

### 2. Side-Effect Membrane

The side-effect membrane controls what mutations a running AgentPod may emit beyond its declared capability radius.

**Crossing direction:** `requested-mutation → policy-check → applied | suppressed`

**Applied when:** the mutation falls within the pod's declared `capability-declaration.schema.json` scope and the policy check passes.

**Suppressed when:** the mutation targets a path, resource, or service outside the declared scope, or the policy denies it.

**Transformed:** Some mutations are rewritten (e.g., write to a sandboxed path rather than the declared path) when the policy returns `conditional`.

### 3. Storage Membrane

The storage membrane governs which volumes an AgentPod may read or write.

**Crossing direction:** `volume-mount-request → storage-receipt-gate → mounted | refused`

**Mounted when:** `storage-receipt.schema.json` exists for the volume, encryption posture meets sensitivity policy, and quota allows.

**Refused when:** receipt is absent, sensitivity is `raw-prompt` or `credentials` (always forbidden), or quota is exceeded.

## Behavior Matrix

| Membrane | admitted | blocked | transformed | logged | witnessed | revoked |
|---|---|---|---|---|---|---|
| Activation | ✓ pod starts | ✓ pod not started, receipt emitted | — | ✓ activation-decision | ✓ runtime-evidence | ✓ lifecycle.terminated |
| Side-effect | ✓ mutation applied | ✓ mutation suppressed, receipt emitted | ✓ rewritten to sandboxed path | ✓ policy-admission record | ✓ runtime-evidence | ✓ grant revoked mid-flight |
| Storage | ✓ volume mounted | ✓ mount refused, receipt emitted | — | ✓ storage-receipt | ✓ runtime-evidence | ✓ volume unmounted |

## Referenced Schemas

- `contracts/activation-decision.schema.json`
- `contracts/capability-declaration.schema.json`
- `contracts/policy-admission.schema.json`
- `contracts/agentplane-runtime-evidence.schema.json`
- `contracts/storage-receipt.schema.json`
- `contracts/lifecycle.schema.json`
- `contracts/agent-registry-grant.schema.json`
