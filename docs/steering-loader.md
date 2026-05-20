# Steering Receipt Loader

Status: receipt verification tranche for local steering work.

## Purpose

Before any local steering runtime may load model or SAE files, Agent Machine must verify that every artifact referenced by a `SteeringArtifactReceipt` exists locally and matches the receipt's SHA-256 digest.

This document describes the fail-closed loader preflight. It does not claim applied steering.

## Verification command

```bash
scripts/verify-steering-receipt.py \
  examples/steering-artifact-receipts/gpt2-small-res-jb.missing.steering-artifact-receipt.json \
  --expect-status not_configured \
  --pretty
```

The fixture paths intentionally do not exist. The expected result is `status: not_configured`, with missing-file diagnostics for each absent artifact.

## Runtime rule

A future runtime loader must not attempt to load GPT-2 Small or the residual-stream SAE until:

- the receipt validates against `contracts/steering-artifact-receipt.schema.json`
- each referenced local path exists
- each referenced path is a file
- each file's SHA-256 digest matches the receipt

If any check fails, the runtime must fail closed and return a non-applied posture.

## Boundary

This tranche verifies receipt integrity only. It does not:

- load GPT-2 Small into memory
- load the SAE into memory
- run inference
- inject activations
- return `status: applied`

The next implementation tranche may add optional runtime loading after this digest gate succeeds.
