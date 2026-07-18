# Portable AI Runtime Integration

Portable AI Runtime Integration defines how Agent Machine treats a USB/SSD-local SourceOS AI kit as a governed runtime substrate.

The goal is to match the usability of simple portable AI USB projects while exceeding them on activation gates, local/host storage boundaries, runtime receipts, cache/model residency, teardown, and zero-trace evidence.

## Boundary

Agent Machine does not own the product CLI or model-carry manifests.

| Layer | Responsibility |
| --- | --- |
| `SourceOS-Linux/sourceos-devtools` | `sourceosctl portable-ai` CLI and user-facing preflight/prepare/start-plan surface |
| `SourceOS-Linux/sourceos-model-carry` | `PortableAIRoot` and `ModelCarryPack` manifests |
| `SourceOS-Linux/agent-machine` | Runtime activation, residency, cache facts, teardown, and evidence receipts |
| `SocioProphet/policy-fabric` | Admission decisions for prompt egress, host writes, network, tools, and side effects |
| `SocioProphet/agentplane` | Execution evidence, replay, and run linkage |

## Runtime substrate

A portable AI root is treated as a local storage-backed runtime substrate with explicit boundaries:

```text
PortableAIRoot
├── runtimes/     # provider binaries or adapters
├── models/       # model blobs / runtime-managed model cache
├── cache/        # embeddings, retrieval, prompt-prefix, runtime cache
├── state/        # chat/workroom/route state
├── evidence/     # preflight, activation, teardown, wipe receipts
└── tmp/          # temporary runtime files
```

Agent Machine must not infer authorization from layout existence. Activation still requires policy admission and agent/runtime grants.

## New evidence families

### PortableRuntimePreflightReceipt

Captures host and target suitability:

- target root;
- filesystem posture;
- free space;
- large-file support;
- read/write benchmark when requested;
- CPU architecture;
- RAM class;
- runtime availability;
- host-write policy;
- removable-device confidence;
- decision: pass, warn, fail.

### PortableRuntimeActivationReceipt

Captures what was activated:

- runtime provider;
- portable root id;
- model-carry-pack refs;
- loopback bind address and port;
- selected surface handoff;
- cache directories;
- model residency facts;
- policy admission id;
- agent registry grant id;
- prompt-egress posture;
- side-effect posture.

### PortableRuntimeTeardownReceipt

Captures clean shutdown:

- process ids observed;
- runtime provider stopped;
- ports released;
- temporary files removed;
- evidence files persisted;
- host-write audit summary;
- next safe eject state.

### PortableRuntimeWipeReceipt

Captures zero-trace cleanup:

- portable tmp/cache paths wiped;
- host temp/cache paths inspected;
- host writes deleted or explicitly retained;
- hashes of retained evidence;
- failures or manual cleanup requirements.

## Activation rules

Activation must fail closed unless:

1. preflight passes or operator explicitly accepts warnings;
2. portable root manifest validates;
3. model-carry packs are verified or marked not route-eligible;
4. runtime provider is available or explicitly staged;
5. bind address is loopback by default;
6. host-write policy is explicit;
7. prompt-egress policy is denied by default;
8. requested surface is locally available or fallback is selected;
9. Policy Fabric admission allows activation;
10. Agent Registry grant allows the invoking agent/surface to use the runtime.

## Provider support order

Linux-first provider order:

1. `llama.cpp` direct local provider;
2. `vLLM` / `SGLang` on capable Linux GPU hosts;
3. `ollama-compatible` convenience provider;
4. OpenAI-compatible local server adapter;
5. optional MLX/oMLX compatibility only on macOS Apple Silicon adapters.

Ollama support is important for parity, but it is not the SourceOS authority.

## Surface handoff

Runtime activation should expose a route descriptor consumable by:

- TurtleTerm for local terminal-native chat/operator work;
- AgentTerm for Matrix/ChatOps and governed agent event streams;
- BearBrowser for local browser/workspace context;
- a minimal local web fallback;
- optional third-party desktop UI adapters.

The route descriptor must include only local endpoint refs and policy posture, not secrets.

## Zero-trace posture

Zero-trace mode means auditability, not marketing copy.

Agent Machine must record:

- all directories configured for runtime state;
- host paths the provider/surface may touch;
- whether Electron/browser/runtime cache roots were redirected;
- whether temp files were removed on teardown;
- whether host writes remain;
- whether the portable kit is safe to eject.

## Acceptance criteria

M1 is complete when Agent Machine has documentation and schema stubs for portable runtime receipts and can render a no-activation plan.

M2 is complete when Agent Machine can evaluate activation readiness for a portable root and emit a dry-run activation decision.

M3 is complete when Agent Machine can manage start/stop/teardown for at least one Linux-first local provider with evidence.

M4 is complete when TurtleTerm and AgentTerm can consume the route descriptor and display runtime/model/policy state to the user.
