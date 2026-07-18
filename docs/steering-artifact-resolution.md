# Steering Artifact Resolution

Status: operator command for producing a complete `SteeringArtifactReceipt`.

## Purpose

The local steering runtime may not claim an applied steering result unless the model and SAE files are resolved to exact source files and verified by SHA-256 digest.

This command prepares that receipt. It does not load GPT-2 Small, load the SAE, run inference, or inject activations.

## Dry run

CI and contributors can validate the receipt shape without network access:

```bash
agent-machine steer resolve-artifacts \
  --sourceset gpt2-small.res-jb \
  --local-dir /tmp/agent-machine-steering-artifacts \
  --receipt-out /tmp/agent-machine-steering-artifact-receipt.json \
  --dry-run \
  --pretty
```

Dry run emits a pending receipt and does not contact Hugging Face.

## Real operator run

On an operator machine with optional steering dependencies installed:

```bash
python3 -m pip install -r requirements-steering.txt

agent-machine steer resolve-artifacts \
  --sourceset gpt2-small.res-jb \
  --local-dir /var/lib/agent-machine/models/steering \
  --receipt-out /var/lib/agent-machine/evidence/gpt2-small-res-jb.steering-artifact-receipt.json \
  --allow-network \
  --pretty
```

The resolver uses `huggingface_hub` with an explicit `local_dir` so the receipt records stable local paths rather than opaque default cache paths.

## Receipt requirements

For each resolved model, tokenizer, and SAE file, the receipt records:

- source repository
- exact file path
- resolved immutable revision / commit SHA
- local path
- file size
- SHA-256 digest
- digest verification status

The GPT-2 Small resolver currently resolves:

```text
openai-community/gpt2:
  config.json
  generation_config.json
  merges.txt
  model.safetensors
  tokenizer.json
  tokenizer_config.json
  vocab.json

jbloom/GPT2-Small-SAEs-Reformatted:
  blocks.6.hook_resid_pre/cfg.json
  blocks.6.hook_resid_pre/sae_weights.safetensors
  blocks.6.hook_resid_pre/sparsity.safetensors
```

## Boundary

A complete artifact receipt is necessary but not sufficient for applied steering. The active steering gate still also requires storage receipt references, policy/grant admission, model loading, SAE loading, activation injection, and a local smoke record with `status: applied`.
