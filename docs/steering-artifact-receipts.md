# Steering Artifact Receipts

Status: contract scaffold for Issue #34.

This document defines the artifact receipt shape required before Agent Machine may claim that a local steering run used specific GPT-2 Small model and SAE artifacts.

## Purpose

A local steering smoke record is not sufficient unless the artifact chain is auditable. The receipt must prove which exact model and SAE files were resolved and verified.

A complete `SteeringArtifactReceipt` must include, for each resolved file:

- source repository
- exact file path inside that source
- resolved revision, commit SHA, or immutable tag
- local path where the file was used
- file size in bytes
- SHA-256 digest
- whether the digest was verified

The receipt must not include raw model data, raw SAE tensors, credentials, or tokens.

## Schema and examples

Schema:

```text
contracts/steering-artifact-receipt.schema.json
```

Pending fixture:

```text
examples/steering-artifact-receipts/gpt2-small-res-jb.pending.steering-artifact-receipt.json
```

The pending fixture deliberately contains no artifact records. It exists to validate the receipt envelope and to record the missing fields before artifact resolution.

## Complete receipt requirement

A complete receipt for `gpt2-small.res-jb` must include artifact records for all model, tokenizer, and SAE files used by the runtime. Each artifact record must contain this minimum shape:

```json
{
  "role": "model-weight",
  "source": {
    "type": "huggingface",
    "repo": "openai-community/gpt2",
    "filePath": "model.safetensors",
    "resolvedRevision": "<commit-sha-or-immutable-tag>",
    "url": "https://huggingface.co/openai-community/gpt2/blob/<revision>/model.safetensors"
  },
  "storage": {
    "localPath": "/var/lib/agent-machine/models/.../model.safetensors",
    "sizeBytes": 0,
    "storageReceiptRef": "urn:srcos:agent-machine:storage-receipt:..."
  },
  "digest": {
    "algorithm": "sha256",
    "sha256": "<64 lowercase hex characters>",
    "verified": true
  }
}
```

## Boundary

This contract does not download artifacts and does not close Issue #34. It defines the audit requirement that the real artifact resolver must satisfy before `status: applied` can be accepted.
