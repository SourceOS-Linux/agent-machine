# M2 Adapter IPC Contract (JSON-over-stdio)

The contract-runner talks to backend adapters (pixi/nix/devbox/mise/bazel) over a
stable **JSON-over-stdio (NDJSON)** protocol: one JSON object per line on stdin
(requests) and stdout (responses); stderr is human logs only. This keeps the runner
small and lets adapters be written in any OSS language.

## Where it lives

| Artifact | Path |
|---|---|
| Schema (draft 2020-12) | `contracts/adapter-ipc.schema.json` |
| Conformance fixtures (accept) | `fixtures/protocol/*.ndjson` |
| Conformance fixtures (reject) | `fixtures/protocol/_reject/*.ndjson` |
| Validator (teeth) | `scripts/validate-adapter-ipc.py` (`make validate-adapter-ipc`) |

## What the contract enforces

- **Envelopes.** A message is exactly one of a *request* (`op`) or a *response* (`ok`),
  each carrying a non-empty string `id`; a response MUST echo its request's `id`.
- **Operations.** `op ∈ {hello, info, lock_validate, lock_hash, env_realize, task_run,
  deps_inventory, lock_update, env_shell}`.
- **Handshake.** A `hello` request MUST declare a `MAJOR.MINOR` `protocol_version`.
- **ok/errors coupling.** `ok:false` ⇒ non-empty `errors`; `ok:true` ⇒ empty `errors`.
- **Error registry.** Every error `code` MUST be one of the canonical codes
  (Protocol Versioning Spec §4.2); unknown codes are rejected.
- **Lane pinning.** A containerized lane MUST pin its image by digest
  (`name@sha256:<hex64>`; SHA-256 is FIPS 180-4).

The validator proves the teeth both ways: every accept fixture validates, and every
reject fixture fails at least one check (a reject that passes fails the run).

## Provenance

Distilled from `M2 Adapter IPC Spec v0.1 (JSON-over-stdio, Subprocess Plugins)` +
`M2 Protocol Versioning & Compatibility Spec v0.1`, SourceOS Spec intake 2026-07-31
(source SHA-256 `59caac80044f046c4b5f37068ba70ab79c336b973f6714f12cdd91c5e7efd9f7`).

Deferred to follow-up (not in this slice): the fixture-replay **test harness** that
runs fixtures against a live adapter subprocess; capability-negotiation runtime
(`missing_required` fail-fast); the reference `pixi` adapter; MAJOR-bump
length-prefixed framing for streaming payloads.
