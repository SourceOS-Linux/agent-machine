# External Trust Signal Providers

`ExternalTrustSignalProvider` is the adapter contract for optional external identity, reputation, certificate-tier, counterparty, and registry lookup signals used by the local Agent Registry grant resolver.

External trust signals are verifier inputs only. They are never authorization, never runtime placement permission, and never a replacement for local SourceOS grant resolution.

## Boundary

```text
AgentPod
  -> local grant request
  -> optional ExternalTrustSignalProvider adapter
  -> local Agent Registry resolver
  -> AgentRegistryGrant
  -> ActivationDecision
```

The adapter can represent PCH/ERC-8004-style prior art: identity assertion, certificate tier, reputation score, counterparty check, and registry lookup. The adapter must not bind Agent Machine to PCH, ERC-8004, x402, Base, USDC, any hosted dashboard, any payment rail, or any external root of trust.

## Request shape

The request side records:

- `providerRef`: external verifier provider or local mirror reference.
- `agentPodId`: AgentPod under evaluation.
- `requestedAgentIdentityRef`: non-human runtime participant identity.
- `sessionRef`: session boundary.
- `workroomRef` and `topicRef`: workspace context.
- `requestedSignalTypes`: identity, cert-tier, reputation, counterparty, registry lookup, or other.
- `verificationFreshnessSeconds`: maximum accepted age for the signal.
- `requestedExpiresAt`: requested validity window.
- `signatureRequired`: whether signatures are required for the signal to be usable.

## Response shape

The response side records:

- `status`: `available`, `unavailable`, `stale`, `malformed`, `unsigned`, `denied`, or `error`.
- `usableForGrantResolution`: true only when the response may be considered by the local grant resolver.
- `authority`: fixed to `non-authoritative-verifier-input`.
- `freshness`: max age, observed age, and freshness result.
- `signals`: one or more typed signals.
- `failureReason`: required when the response is not usable.

Each signal records provider reference, signal type, signal reference, optional digest, verification time, freshness, signature posture, authority, failure reason, and notes.

## Semantic rules

A usable adapter response must satisfy all of these conditions:

- status is `available`;
- `usableForGrantResolution=true`;
- response authority is `non-authoritative-verifier-input`;
- response freshness is true;
- at least one signal is present;
- every signal uses the requested provider reference;
- every signal type was requested;
- every signal authority is `non-authoritative-verifier-input`;
- if signatures are required, every signal has an observed signature, signature reference, and signer reference;
- no raw prompt, KV-cache, secrets, private memory, API keys, private wallet keys, raw credentials, or raw user data appear in the payload.

An unusable adapter response must be ignored by the local grant resolver or cause fail-closed behavior when local policy requires that signal. Stale, unavailable, malformed, unsigned, denied, or error responses cannot authorize activation.

## Non-authority rule

External trust signal providers can reduce or annotate local risk. They cannot widen requested scope, grant tools, grant storage, grant cache reuse, grant memory access, expose models, or activate an AgentPod. Only local `PolicyAdmission` plus local `AgentRegistryGrant` can lead to an `ActivationDecision` that allows activation.
