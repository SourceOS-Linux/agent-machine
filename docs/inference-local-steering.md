# Local SAE Steering Inference Readiness

Status: inspection record for Issue #31. This document records current repository evidence for a Neuronpedia-compatible local steering path. It does not implement an inference server and does not claim runtime readiness.

## Summary verdict

Agent Machine is not currently ready to run local SAE steering for `MODEL_SOURCESET=gpt2-small.res-jb`.

The repository has a backend-neutral `InferenceProvider` contract and a probe-only `llama.cpp` provider example, but no current repository artifact registers:

- `MODEL_SOURCESET=gpt2-small.res-jb`
- GPT-2 Small SAE artifacts
- Gemma 2B or Gemma 9B steering sourcesets
- a Neuronpedia-compatible `POST /steer` endpoint
- an activation command that starts a steering inference server

This is consistent with the repository status: provider activation is explicitly not implemented, and production readiness remains blocked by provider discovery and controlled provider activation.

## Repository evidence inspected

Inspected on 2026-05-20 against `main` at commit `c306852f26f4fbe62421a9b7801a59815d4daf9e`.

Relevant repository evidence:

- `README.md` describes Agent Machine as a bootstrap runtime-control substrate and marks provider activation as not implemented.
- `BOOTSTRAP_STATUS.md` states activation remains dry-run control-plane evaluation and does not start a provider.
- `docs/index.md` lists `InferenceProvider` as a contract family but keeps production blocked by provider discovery and controlled activation.
- `contracts/inference-provider.schema.json` defines backend-neutral provider metadata and API surfaces such as OpenAI-compatible chat/completions/embeddings and native HTTP. It does not define a Neuronpedia-compatible `/steer` API surface.
- `examples/asahi-llama-cpp.inference-provider.json` is `status: probe-only`, uses `llama.cpp`, and exposes an endpoint/health path for `llama-server`; it is not a steering server.
- Repository search found no current references to `MODEL_SOURCESET`, `gpt2-small`, `res-jb`, `Gemma`, or `/steer` as implemented local steering surfaces.

## Current sourceset readiness

| Sourceset | Current repo status | Ready today? | Reason |
| --- | --- | --- | --- |
| `gpt2-small.res-jb` | Not registered | No | No sourceset manifest, no GPT-2 Small SAE artifact reference, no `/steer` endpoint, and no activation path. |
| Gemma 2B | Not registered | No | No Gemma sourceset manifest, no SAE artifact reference, no `/steer` endpoint, and no activation path. |
| Gemma 9B | Not registered | No | No Gemma sourceset manifest, no SAE artifact reference, no `/steer` endpoint, and no activation path. |

## Weight and artifact requirements

### GPT-2 Small

Model weights:

- Hugging Face model: `openai-community/gpt2`
- Public model page: `https://huggingface.co/openai-community/gpt2`
- Observed license on model page: MIT
- Access posture observed from the public page: no account-gating was evident during inspection

Still required before readiness:

- explicit Agent Machine sourceset record for `gpt2-small.res-jb`
- exact GPT-2 Small model artifact reference and digest policy
- exact SAE artifact source and digest policy
- runtime storage/cache placement receipts
- activation policy and agent-registry grant examples for the steering provider

### Gemma 2B / Gemma 9B

Model weights:

- Hugging Face model: `google/gemma-2-2b`
- Public model page: `https://huggingface.co/google/gemma-2-2b`
- Hugging Face model: `google/gemma-2-9b`
- Public model page: `https://huggingface.co/google/gemma-2-9b`
- Observed license on model pages: Gemma license

Access posture:

- Treat Gemma access as terms-sensitive until an operator verifies availability under the relevant Hugging Face account and accepts any required Google terms.
- Do not claim Gemma readiness from public model-card existence alone.

Still required before readiness:

- explicit Agent Machine sourceset record for each Gemma target admitted to scope
- exact model artifact references and digest policies
- exact SAE artifact sources and digest policies
- hardware/runtime profile decision for Gemma model size
- activation policy and grant examples

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

This endpoint shape is a target contract. It is not implemented in Agent Machine at the time of this inspection.

## Current Agent Machine commands

Current safe bootstrap commands from existing docs:

```bash
agent-machine version
agent-machine paths
agent-machine doctor --format json
agent-machine probe --format json
agent-machine render plan examples/local-podman-llama-cpp.agent-pod.json --pretty
```

Current validation command:

```bash
make validate
```

No current Agent Machine command was found that starts a Neuronpedia-compatible local `/steer` server.

## Follow-up issues opened

- Issue #32: define the Neuronpedia-compatible local `/steer` endpoint contract.
- Issue #33: register local steering sourcesets for GPT-2 Small and Gemma.
- Issue #34: implement controlled activation for a local steering inference provider after endpoint and sourceset records exist.

## Readiness conclusion

Current status: not ready.

`MODEL_SOURCESET=gpt2-small.res-jb` is not loadable today from the repository state. The self-hosted M2b path requires at least:

1. local `/steer` contract definition
2. sourceset registration
3. model and SAE artifact references with digest policy
4. controlled activation path
5. evidence and grant wiring
6. successful local smoke record

Until those are complete, Noetica should use `NEURONPEDIA_BASE_URL=http://localhost:<port>` only as a configurable endpoint target for future experiments, not as proof that Agent Machine can already perform local SAE steering.
