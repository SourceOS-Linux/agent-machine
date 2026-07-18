# Security

Agent Machine is the Linux-first runtime-control substrate for local and clustered agent execution. It is expected to become sensitive infrastructure because it can govern hardware/runtime probing, inference provider lifecycle, model residency, cache-aware scheduling, AgentPod activation, side-effect boundaries, and runtime evidence.

## Current posture

Agent Machine is production-blocked until release gates are satisfied.

Current default posture:

- dry-run render/evaluate behavior only by default;
- no provider activation by default;
- no declared listener by default;
- no declared credential store by default;
- no declared background service by default;
- no browser or terminal control;
- no model provider process launched until policy, registry, and evidence gates land.

The current authority declaration lives in `TRUST_SURFACE.yaml`.

## Blocking rule

Block changes that introduce any of the following without updating `TRUST_SURFACE.yaml`:

- provider activation or lifecycle management;
- model server, OpenAI-compatible endpoint, WebSocket, HTTP, gRPC, MCP, ACP, or other listener;
- systemd, Quadlet, Kubernetes, LaunchAgent, cron, scheduled task, or service installer;
- container, VM, Podman, Docker, Lima, Kubernetes, or local sandbox runtime;
- model cache, prompt cache, scratch, evidence, local LVM, TopoLVM, or object-store authority;
- credential, token, API key, OAuth, SecretRef, SSH-agent, keychain, or provider auth handling;
- PolicyAdmission, AgentRegistryGrant, or AgentPlane evidence bypass;
- logs or receipts that expose secrets, prompts, local paths, model-provider tokens, workload identity, or sensitive runtime metadata.

## Required local commands

Before runtime activation ships, Agent Machine must provide or map:

```text
scripts/doctor
scripts/network-surface
scripts/credential-surface
scripts/policy-surface
scripts/purge
scripts/prove-clean
```

## Cleanup and revocation

Uninstall must remove authority, not just binaries.

`prove-clean` must verify no Agent Machine process, service unit, Quadlet unit, provider process, listener, credential, cache, state directory, config directory, or runtime evidence residue remains unless explicitly retained by the user.
