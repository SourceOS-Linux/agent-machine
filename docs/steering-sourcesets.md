# Steering Sourceset Registry

Status: Issue #33 registration records. This document describes the current local SAE steering sourceset registry records and their readiness posture.

The records live under `examples/steering-sourcesets/` and validate against `contracts/steering-sourceset.schema.json`.

## Purpose

A `SteeringSourceset` ties together:

- base model weight source
- SAE artifact source
- local `/steer` endpoint compatibility
- activation readiness
- policy/grant/storage/evidence requirements

A sourceset registration is not a download, not a runtime activation, and not a production admission. It gives Issue #34 a typed target for controlled activation work.

## Registered sourcesets

| Sourceset | Model source | SAE source | Status | Loadable today? |
| --- | --- | --- | --- | --- |
| `gpt2-small.res-jb` | `openai-community/gpt2` | `jbloom/GPT2-Small-SAEs-Reformatted`, release `gpt2-small-res-jb`, SAE id `blocks.6.hook_resid_pre` | `registered-not-loadable` | No |
| `gemma-2-2b.pt-res` | `google/gemma-2-2b` | `google/gemma-scope-2b-pt-res`, path `layer_20/width_16k/average_l0_71` | `registered-blocked-terms` | No |

## GPT-2 Small residual-stream source

Record:

```text
examples/steering-sourcesets/gpt2-small-res-jb.steering-sourceset.json
```

Model:

```text
https://huggingface.co/openai-community/gpt2
```

SAE:

```text
https://huggingface.co/jbloom/GPT2-Small-SAEs-Reformatted
release = gpt2-small-res-jb
sae_id = blocks.6.hook_resid_pre
Neuronpedia layer = 6-res-jb
```

Readiness:

- registered by reference
- no artifact download performed
- no digest lock yet
- no storage receipt yet
- no activation path yet
- no local smoke proof yet

## Gemma 2 2B residual-stream source

Record:

```text
examples/steering-sourcesets/gemma-2-2b-pt-res.steering-sourceset.json
```

Model:

```text
https://huggingface.co/google/gemma-2-2b
```

SAE:

```text
https://huggingface.co/google/gemma-scope-2b-pt-res
artifact path = layer_20/width_16k/average_l0_71
```

Readiness:

- registered by reference
- terms/access verification required for model use
- no artifact download performed
- no digest lock yet
- no storage receipt yet
- no activation path yet
- no local smoke proof yet

## Endpoint compatibility

Both records target the local contract from Issue #32:

```text
POST /steer
```

Request shape:

```json
{
  "prompt": "...",
  "model_id": "...",
  "steering": {
    "feature_id": "...",
    "layer": "...",
    "strength": 5,
    "preset": "optional"
  }
}
```

Response shape must match Noetica `SteeringResult`:

```json
{
  "status": "applied | not_configured | noop",
  "baseline": "...",
  "steered": "...",
  "diff_summary": "...",
  "feature_id": "...",
  "layer": "...",
  "strength": 5
}
```

## Boundary

These registrations do not implement activation injection. Issue #34 owns controlled activation and must not treat these references as proof that weights or SAE artifacts are present locally.
