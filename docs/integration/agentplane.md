# AgentPlane Integration

AgentPlane is the durable run/evidence plane. Agent Machine should emit or stage typed evidence for AgentPlane instead of asking AgentPlane to infer missing runtime metadata after the fact.

## Current bootstrap artifacts

Agent Machine currently models:

- `DeploymentReceipt`;
- `StorageReceipt`;
- `AgentPlaneRuntimeEvidence`;
- `ActivationDecision`.

These are local evidence/control artifacts. They do not yet submit to a live AgentPlane endpoint.

## Required future integration

A production integration must provide:

- AgentPlane evidence submission/staging client;
- durable evidence queue for offline/local-first operation;
- retry and idempotency keys;
- evidence digesting and signing hooks;
- clear separation between placement, activation, runtime status, teardown, and wipe evidence.

## Safety rule

AgentPlane evidence must never include raw prompt content, raw KV-cache contents, private memory, unredacted credentials, or model-provider secrets.
