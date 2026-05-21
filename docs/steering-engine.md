# Deterministic Steering Engine Harness

Status: mock-only validation surface.

## Purpose

The deterministic steering engine harness proves the request parsing, hook descriptor construction, baseline pass, transformed pass, and response-shape wiring without loading model weights or SAE tensors.

## Validation command

```bash
scripts/run-mock-steering.py /tmp/agent-machine-steer-request.json --pretty
```

The validation path requires:

- baseline and transformed outputs differ
- request feature, layer, and strength fields are preserved
- `6-res-jb` maps to hook name `blocks.6.hook_resid_pre`
- the returned shape is compatible with Noetica's steering result contract

## Boundary

This harness does not:

- load GPT-2 Small
- load SAE artifacts
- run real inference
- inject a real activation vector
- claim local runtime readiness

The real activation path must use the same request and response shape after the receipt, loader, policy, and grant gates are satisfied.
