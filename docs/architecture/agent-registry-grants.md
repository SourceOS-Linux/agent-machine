# Agent Registry Grants

Agent Machine must resolve an Agent Registry grant before it exposes tools, model providers, cache, memory, storage, or evidence scope to a non-human runtime participant.

This grant is a local SourceOS control-plane artifact. It may consume external identity, reputation, or certificate-tier signals, but those signals are non-authoritative verifier inputs. The canonical authorization decision remains the locally resolved `AgentRegistryGrant`.

## Activation boundary

```text
AgentPod
  -> Policy Fabric admission
  -> Agent Registry grant request
  -> optional external verifier inputs
  -> local grant resolution
  -> ActivationDecision
  -> runtime placement or fail-closed
```

A generated plan, manifest, deployment receipt, third-party reputation score, or external certificate is not sufficient to activate an AgentPod. Activation requires a local grant whose status is `active`, whose authorization flag is `true`, whose allowed scope covers the requested activation operation, and whose safety flags prove that no raw prompts, KV-cache material, secrets, or private memory were included.

## Grant request shape

The request side of `contracts/agent-registry-grant.schema.json` records:

- `agentPodId`: the AgentPod requesting activation or privileged runtime exposure.
- `requestedAgentIdentityRef`: the non-human runtime identity being resolved.
- `sessionRef`: the session boundary for the grant.
- `workroomRef` and `topicRef`: the workspace/topic context for policy binding.
- `requestedScope.providerIds`: requested model/provider surfaces.
- `requestedScope.modelRefs`: requested model identities or model-family refs.
- `requestedScope.toolRefs`: requested tool capabilities.
- `requestedScope.cacheScopeRefs`: requested cache reuse or cache mount scopes.
- `requestedScope.memoryScopeRefs`: requested memory scopes.
- `requestedScope.storageScopeRefs`: requested storage scopes.
- `requestedScope.evidenceScopeRefs`: requested evidence/receipt write scopes.
- `requestedExpiresAt`: requested expiration for the grant.

The request payload must not contain secret values, raw prompts, raw KV-cache contents, private memory contents, API keys, private wallet keys, or raw credentials.

## Grant response shape

The response side records:

- `grant.status`: `active`, `missing`, `expired`, `revoked`, `denied`, or `unknown`.
- `grant.authorizationGranted`: true only when the local registry resolved an active grant.
- `grant.grantRef`: stable reference for the resolved grant, or null when missing.
- `grant.grantDigest`: digest of the resolved grant evidence, or null when missing.
- `grant.expiresAt`: actual expiration if a grant exists.
- `grant.revocationStatus`: revocation state of the resolved grant.
- `grant.revocationRef`: revocation record reference if applicable.
- `grant.revocationHookRef`: hook the runtime can check before and during activation.
- `scope.allowed`: exact provider, model, tool, cache, memory, storage, and evidence scopes allowed.
- `scope.denied`: exact scopes denied.

Allowed scope must be no broader than the requested scope. Denied scope is explicit so operators can distinguish an unrequested capability from a requested-but-denied capability.

## External trust signals

External systems can be useful for agent identity verification, reputation, counterparty checks, and certificate-tier claims. They are not the Agent Registry.

When used, external trust signals must be recorded under `grant.externalTrustSignals` with:

- the provider reference;
- the signal type;
- the signal reference;
- a digest when available;
- verification time;
- `authority: non-authoritative-verifier-input`.

This keeps PCH/ERC-8004-style identity, reputation, and certificate-tier checks pluggable without making any external gateway the SourceOS root of trust.

## Fail-closed rules

Activation fails closed when:

- `agentRegistryRequired=true` and no grant exists;
- the grant is `missing`, `expired`, `revoked`, `denied`, or `unknown`;
- the grant allows no explicit activation scope;
- the requested provider is not present in allowed provider scope;
- required activation tools are absent from allowed tool scope;
- the grant is missing a revocation hook;
- the grant payload includes secrets, raw prompts, raw KV-cache contents, or private memory contents.

## Relation to receipts

`DeploymentReceipt` proves deterministic derivation. `PolicyAdmission` proves policy admission. `AgentRegistryGrant` proves identity/session/tool/provider/storage authorization. `ActivationDecision` combines those inputs and either permits scoped activation or records fail-closed reasons.

None of these artifacts should include raw prompt content, KV-cache contents, secret values, private memory, or raw user data.
