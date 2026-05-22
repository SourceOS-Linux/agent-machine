# AgentRegistryGrant Resolution

Agent Machine now has a local Agent Registry grant resolver for bootstrap and dry-run activation flows. This is a deterministic local-store resolver, not a production Agent Registry client.

## Purpose

Activation evaluation should not require callers to manually select an `AgentRegistryGrant` forever. The resolver lets Agent Machine scan explicit files or directories and select the matching grant by request shape.

The resolver supports:

- explicit grant files;
- local grant store directories;
- request matching by AgentPod ID, requested agent identity, session, optional AgentMachine, workroom, and topic;
- disambiguation by grant ID or expected grant status;
- fail-closed missing-grant stub generation;
- semantic validation through governance rules;
- activation evaluation using a locally resolved grant.

## Current commands

Resolve a grant from a local store by explicit grant ID:

```bash
agent-machine registry resolve \
  examples/local-podman-llama-cpp.agent-pod.json \
  --grant-dir examples \
  --grant-id urn:srcos:agent-machine:agent-registry-grant:active-loopback-activation \
  --requested-agent-identity-ref urn:srcos:agent:local-inference-provider \
  --session-ref urn:srcos:session:local-bootstrap \
  --agent-machine-id urn:srcos:agent-machine:m2-asahi-local \
  --pretty
```

Resolve a grant by status and request shape:

```bash
agent-machine registry resolve \
  examples/local-podman-llama-cpp.agent-pod.json \
  --grant-dir examples \
  --expected-status revoked \
  --requested-agent-identity-ref urn:srcos:agent:local-inference-provider \
  --session-ref urn:srcos:session:local-bootstrap \
  --agent-machine-id urn:srcos:agent-machine:m2-asahi-local \
  --workroom-ref urn:srcos:workroom:local-default \
  --topic-ref urn:srcos:topic:agent-machine \
  --pretty
```

Evaluate activation using a resolved registry grant:

```bash
agent-machine activate evaluate \
  examples/local-podman-llama-cpp.agent-pod.json \
  examples/policy-admission.allowed-activation.json \
  --grant-dir examples \
  --grant-id urn:srcos:agent-machine:agent-registry-grant:active-loopback-activation \
  --deployment-receipt-id urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --requested-agent-identity-ref urn:srcos:agent:local-inference-provider \
  --session-ref urn:srcos:session:local-bootstrap \
  --agent-machine-id urn:srcos:agent-machine:m2-asahi-local \
  --provider-id urn:srcos:agent-machine:inference-provider:asahi-llama-cpp \
  --storage-receipt-dir examples \
  --decided-at 2026-05-04T12:51:00Z \
  --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed \
  --pretty
```

## Fail-closed behavior

If no matching grant is found and missing stubs are allowed, the resolver emits a synthetic `AgentRegistryGrant` with:

```text
grant.status = missing
grant.authorizationGranted = false
grant.revocationStatus = unavailable
```

That stub denies requested scopes and causes `ActivationDecision` to fail closed.

If `--no-missing-stub` is provided and no grant matches, resolution fails.

## Ambiguity behavior

If multiple grants match the request, resolution fails unless the caller disambiguates with:

```text
--grant-id <id>
```

or:

```text
--expected-status active|revoked|expired|denied|missing|unknown
```

This is deliberate. Silent selection among conflicting grants would be unsafe.

## Scope behavior

The resolver can construct a requested scope for generated missing stubs from CLI arguments:

```text
--provider-id
--model-ref
--tool-ref
--storage-scope-ref
--evidence-scope-ref
```

For resolved real grants, schema and governance validation ensure `scope.allowed` does not exceed `request.requestedScope`.

## Bootstrap boundary

This resolver is not a production Agent Registry client. It does not:

- call a remote Agent Registry endpoint;
- verify grant signatures;
- resolve revocations online;
- prove session freshness;
- bind identity to live proof-of-life;
- prove grant freshness beyond the contents of local artifacts.

It is the bootstrap adapter shape that a real Agent Registry client can replace.

## Validation

Agent Registry resolver validation is part of:

```bash
make validate-agent-registry
make validate
```

The validation path checks:

- directory scanning;
- schema and semantic validation;
- ambiguity rejection;
- active activation grant resolution;
- revoked grant resolution;
- generated missing stubs;
- grant-id disambiguation;
- CLI registry resolution;
- activation evaluation using a resolved local grant.
