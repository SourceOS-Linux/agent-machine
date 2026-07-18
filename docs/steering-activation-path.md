# GPT-2 Small Controlled Steering Activation Path

Status: Issue #34 implementation-prep. This document records the first controlled activation entrypoint for `gpt2-small.res-jb` and the remaining blockers before #34 can close.

## Scope

This path is GPT-2 Small only.

Gemma sourcesets remain out of scope for #34 closure because Gemma model access depends on operator terms/access verification.

## Commands

Preflight readiness:

```bash
agent-machine steer preflight --sourceset gpt2-small.res-jb --pretty
```

Serve sourceset-aware local endpoint in fail-closed mode:

```bash
agent-machine steer serve --sourceset gpt2-small.res-jb --host 127.0.0.1 --port 8080
```

The existing contract stub remains available:

```bash
agent-machine steer serve-stub --host 127.0.0.1 --port 8080 --status not_configured
```

## Current behavior

`steer preflight` resolves the registered `SteeringSourceset`, checks optional runtime dependency presence, and reports missing activation prerequisites.

`steer serve --sourceset ...` starts a local `/steer` endpoint using the registered sourceset posture. Until all prerequisites are present, it returns a valid Noetica-compatible `SteeringResult` with:

```json
{
  "status": "not_configured"
}
```

It must not return `status: "applied"` until a real forward pass and feature injection succeed.

## Artifact receipt gate

Before any local smoke can be accepted, Agent Machine must emit a complete `SteeringArtifactReceipt` for `gpt2-small.res-jb`.

The receipt must include, for every model, tokenizer, and SAE file used by the runtime:

- source repository
- exact file path
- resolved revision, commit SHA, or immutable tag
- local path
- file size in bytes
- SHA-256 digest
- digest verification status

The receipt contract is defined in:

```text
contracts/steering-artifact-receipt.schema.json
```

and documented in:

```text
docs/steering-artifact-receipts.md
```
## Remaining blockers before #34 can close

- optional ML dependencies installed from `requirements-steering.txt`
- verified GPT-2 Small model artifacts
- verified SAE artifacts for SAELens release `gpt2-small-res-jb`, SAE id `blocks.6.hook_resid_pre`
- digest locks for model and SAE artifacts
- artifact receipt with exact repo, file path, resolved revision, and SHA-256 digest for each model/SAE file
- storage receipt for the resolved artifact locations
- policy admission and agent-registry grant records
- real activation injection implementation
- local smoke record showing `status: applied`, baseline, steered output, and evidence hash

## Noetica integration target

Once the real path is ready, Noetica should work without code changes by setting:

```bash
NEURONPEDIA_BASE_URL=http://localhost:8080
```

Then Noetica `/api/steer` should call Agent Machine `/steer` and receive `status: applied` only after real activation succeeds.

## Boundary

This document and the current `serve --sourceset` entrypoint do not close #34. They add the fail-closed entrypoint and preflight surface needed before the real activation injection implementation lands.
