# Local SAE Steering Inference Readiness

Status: inspection and registration record. This document records current repository evidence for a Neuronpedia-compatible local steering path. It does not implement an inference server and does not claim runtime readiness.

## Summary verdict

Agent Machine is not currently ready to run local SAE steering for `MODEL_SOURCESET=gpt2-small.res-jb`.

The repository now has:

- a backend-neutral `InferenceProvider` contract
- a probe-only `llama.cpp` provider example
- a local `/steer` contract stub from Issue #32
- registered steering sourceset records from Issue #33

The repository still does not have:

- downloaded model artifacts
- locked SAE artifact digests
- storage receipts for model/SAE artifacts
- a controlled activation path that starts a steering inference server
- real activation injection into a model forward pass

This remains consistent with the repository status: provider activation is not implemented, and production readiness remains blocked by provider discovery and controlled provider activation.

## Repository evidence inspected

Initial inspection occurred on 2026-05-20 against `main` at commit `c306852f26f4fbe62421a9b7801a59815d4daf9e`. Sourceset registration was added after Issue #32 closed.

Relevant repository evidence:

- `README.md` describes Agent Machine as a bootstrap runtime-control substrate and marks provider activation as not implemented.
- `BOOTSTRAP_STATUS.md` states activation remains dry-run control-plane evaluation and does not start a provider.
- `docs/index.md` lists `InferenceProvider` as a contract family but keeps production blocked by provider discovery and controlled activation.
- `contracts/inference-provider.schema.json` defines backend-neutral provider metadata and API surfaces such as OpenAI-compatible chat/completions/embeddings and native HTTP.
- `examples/asahi-llama-cpp.inference-provider.json` is `status: probe-only`, uses `llama.cpp`, and exposes an endpoint/health path for `llama-server`; it is not a steering server.
- `docs/local-steer-endpoint.md` defines the local `/steer` contract and stub behavior.
- `contracts/steering-sourceset.schema.json` defines the sourceset registry shape.
- `examples/steering-sourcesets/` registers GPT-2 Small and Gemma 2B candidates by reference only.

## Current sourceset readiness

| Sourceset | Current repo status | Ready today? | Reason |
| --- | --- | --- | --- |
| `gpt2-small.res-jb` | Registered by reference | No | Sourceset record exists, but artifact digests, storage receipts, policy/grant admission, activation injection, and smoke proof are missing. |
| `gemma-2-2b.pt-res` | Registered by reference, access-sensitive | No | Sourceset record exists, but model terms/access, artifact digests, storage receipts, policy/grant admission, activation injection, and smoke proof are missing. |
| Gemma 9B | Not registered | No | Not admitted in Issue #33; register only after hardware/runtime profile and access posture are settled. |

## Weight and artifact requirements

### GPT-2 Small

Model weights:

- Hugging Face model: `openai-community/gpt2`
- Public model page: `https://huggingface.co/openai-community/gpt2`
- Observed license on model page: MIT

SAE artifacts:

- Hugging Face repo: `jbloom/GPT2-Small-SAEs-Reformatted`
- SAELens release: `gpt2-small-res-jb`
- SAE id: `blocks.6.hook_resid_pre`
- Neuronpedia layer: `6-res-jb`

Still required before readiness:

- exact artifact digest lock
- storage/cache receipt
- policy admission
- agent-registry grant
- controlled activation injection
- local smoke record

### Gemma 2 2B

Model weights:

- Hugging Face model: `google/gemma-2-2b`
- Public model page: `https://huggingface.co/google/gemma-2-2b`
- License/access: Gemma terms; operator must verify account access and accept applicable terms before runtime use.

SAE artifacts:

- Hugging Face repo: `google/gemma-scope-2b-pt-res`
- Artifact path: `layer_20/width_16k/average_l0_71`

Still required before readiness:

- operator access/terms verification
- exact artifact digest lock
- storage/cache receipt
- policy admission
- agent-registry grant
- controlled activation injection
- local smoke record

## Expected local endpoint shape

Target local endpoint for Noetica compatibility:

```text
POST http://localhost:8080/steer
```

Expected request payload shape:

```json
{
  "prompt": "Write one short sentence about Paris.",
  "model_id": "gpt2-small",
  "steering": {
    "feature_id": "10200",
    "layer": "6-res-jb",
    "strength": 5,
    "preset": "optional"
  }
}
```

Expected response payload shape compatible with Noetica `SteeringResult`:

```json
{
  "status": "applied",
  "baseline": "baseline text",
  "steered": "steered text",
  "diff_summary": "short description of observed steering effect",
  "feature_id": "10200",
  "layer": "6-res-jb",
  "strength": 5
}
```

Allowed status values must align with Noetica steering semantics:

- `applied`: a real steering backend applied the requested activation steering.
- `not_configured`: required model/source/SAE/backend configuration is absent.
- `noop`: the endpoint accepted the request shape but deliberately applied no runtime intervention.

Issue #32 provides a stub endpoint that can return `not_configured` or `noop`. `applied` remains blocked on Issue #34.

## Current Agent Machine commands

Current safe bootstrap commands from existing docs:

```bash
agent-machine version
agent-machine paths
agent-machine doctor --format json
agent-machine probe --format json
agent-machine render plan examples/local-podman-llama-cpp.agent-pod.json --pretty
```

Local endpoint contract stub from Issue #32:

```bash
agent-machine steer serve-stub --host 127.0.0.1 --port 8080 --status not_configured
```

Current validation command:

```bash
make validate
```

## Follow-up issues

- Issue #32: local `/steer` endpoint contract — closed.
- Issue #33: steering sourceset registration — current.
- Issue #34: controlled activation for a local steering inference provider — still required.

## Readiness conclusion

Current status: registered but not loadable.

`MODEL_SOURCESET=gpt2-small.res-jb` now has a registry record, but it is not loadable today from the repository state. The self-hosted M2b path still requires at least:

1. artifact digest locks
2. storage receipts
3. policy/grant admission records
4. controlled activation path
5. evidence and grant wiring
6. successful local smoke record

Until those are complete, Noetica should use `NEURONPEDIA_BASE_URL=http://localhost:<port>` only as a configurable endpoint target for contract and UI testing, not as proof that Agent Machine can already perform local SAE steering.
