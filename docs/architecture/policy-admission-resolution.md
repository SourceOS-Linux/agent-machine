# PolicyAdmission Resolution

Agent Machine now has a local Policy Fabric admission resolver for bootstrap and dry-run activation flows. This is a deterministic local-store resolver, not a production Policy Fabric client.

## Purpose

Activation evaluation should not require callers to manually pick a `PolicyAdmission` file forever. The resolver lets Agent Machine scan explicit files or directories and select the matching `PolicyAdmission` by request shape.

The resolver supports:

- explicit policy files;
- local policy store directories;
- request matching by AgentPod ID, request type, deployment receipt ID, AgentMachine ID, and provider ID;
- disambiguation by policy ID or expected status;
- fail-closed missing-admission stub generation;
- semantic validation through governance rules.

## Current commands

Resolve a policy decision from a local store:

```bash
agent-machine policy resolve \
  examples/local-podman-llama-cpp.agent-pod.json \
  --policy-dir examples \
  --expected-status allowed \
  --deployment-receipt-id urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --agent-machine-id urn:srcos:agent-machine:m2-asahi-local \
  --provider-id urn:srcos:agent-machine:inference-provider:asahi-llama-cpp \
  --pretty
```

Evaluate activation using a resolved policy from a local store:

```bash
agent-machine activate evaluate \
  examples/local-podman-llama-cpp.agent-pod.json \
  examples/agent-registry-grant.active-activation.json \
  --policy-dir examples \
  --expected-status allowed \
  --deployment-receipt-id urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --agent-machine-id urn:srcos:agent-machine:m2-asahi-local \
  --provider-id urn:srcos:agent-machine:inference-provider:asahi-llama-cpp \
  --storage-receipt-dir examples \
  --decided-at 2026-05-04T12:51:00Z \
  --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed \
  --pretty
```

Evaluate activation with an explicit policy file:

```bash
agent-machine activate evaluate \
  examples/local-podman-llama-cpp.agent-pod.json \
  examples/policy-admission.allowed-activation.json \
  examples/agent-registry-grant.active-activation.json \
  --deployment-receipt-id urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --storage-receipt-dir examples \
  --pretty
```

## Fail-closed behavior

If no matching policy is found and missing stubs are allowed, the resolver emits a synthetic `PolicyAdmission` with:

```text
decision.status = missing
decision.authorizationGranted = false
```

That stub denies activation-sensitive scopes and causes `ActivationDecision` to fail closed.

If `--no-missing-stub` is provided and no policy matches, resolution fails.

## Ambiguity behavior

If multiple policy decisions match the request, resolution fails unless the caller disambiguates with:

```text
--policy-id <id>
```

or:

```text
--expected-status allowed|denied|missing|not-required|unknown
```

This is deliberate. Silent selection among conflicting policy decisions would be unsafe.

## Bootstrap boundary

This resolver is not a production Policy Fabric client. It does not:

- call a remote Policy Fabric endpoint;
- verify policy bundle signatures;
- resolve revocations online;
- evaluate policy source code;
- prove freshness beyond the contents of local artifacts.

It is the bootstrap adapter shape that a real Policy Fabric client can replace.

## Validation

Policy resolver validation is part of:

```bash
make validate-policy-fabric
make validate
```

The validation path checks:

- directory scanning;
- schema and semantic validation;
- ambiguity rejection;
- allowed/denied disambiguation;
- generated missing stubs;
- CLI policy resolution;
- activation evaluation using a resolved local policy.
