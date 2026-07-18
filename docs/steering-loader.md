# Steering Receipt Loader

Status: receipt verification tranche for local steering work.

## Purpose

Before any local steering runtime may load model or SAE files, Agent Machine must verify that every artifact referenced by a `SteeringArtifactReceipt` exists locally and matches the receipt's SHA-256 digest.

This document describes the fail-closed loader preflight. It does not claim applied steering.
Status: receipt verification and CI-safe synthetic loading tranche for local steering work.

## Purpose

Before any local steering runtime may use model or SAE files, Agent Machine must verify that every artifact referenced by a `SteeringArtifactReceipt` exists locally and matches the receipt's SHA-256 digest.

The loader re-verifies the receipt immediately before any load attempt. This prevents a stale preflight check from being trusted after files on disk have changed.

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
## CI-safe load command

```bash
scripts/load-steering-receipt.py \
  examples/steering-artifact-receipts/synthetic.available.steering-artifact-receipt.json \
  --attempt-load \
  --expect-status available \
  --expect-model-loaded true \
  --expect-sae-loaded true \
  --pretty
```

The synthetic fixture contains small text artifacts, not model or SAE weights. It proves the `SteeringLoader.load()` path re-verifies digests at load time and only reports loaded after the receipt is valid.

## Runtime rule

A future runtime loader must not attempt to use GPT-2 Small or the residual-stream SAE until:

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
## Operator runtime imports

The loader contains an optional runtime-import path for operator machines after a complete artifact receipt exists. Optional runtime dependencies are not part of normal validation and must remain outside the default bootstrap path.

## Boundary

This tranche does not:

- run inference
- inject activations
- return `status: applied`
- claim runtime readiness

It adds the digest-gated load envelope that future activation code must use.
