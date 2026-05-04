# Signed Release Bundle Envelope

Agent Machine release evidence bundles need a signing envelope before they can become release-candidate or production promotion artifacts. The current bootstrap lane defines the envelope shape and examples, but does not implement cryptographic signing or verification.

## Decision

Define `SignedReleaseBundleEnvelope` as the contract wrapper around a `ReleaseEvidenceBundle`.

The envelope records:

- subject kind and reference;
- subject digest;
- source commit SHA;
- workflow run ID;
- signature status;
- signing algorithm;
- key or identity reference;
- signature digest/reference;
- transparency log reference;
- certificate reference;
- verification result;
- receipt-safety flags.

## Bootstrap states

Bootstrap supports two non-production states:

| State | Meaning |
| --- | --- |
| `unsigned` | The bundle is intentionally unsigned. This is acceptable only for bootstrap development. |
| `signed-placeholder` | The envelope shape contains placeholder signing metadata, but verification is not implemented. |

Neither state is production-valid.

## Production state

Production requires:

```text
signature.status = signed
verification.verified = true
verification.verificationStatus = passed
```

Production signing should eventually use a verifiable signing lane such as keyless signing with transparency-log evidence, or another SourceOS-approved signing policy.

## Current implementation

Implemented now:

- `contracts/signed-release-bundle-envelope.schema.json`;
- `examples/signed-release-bundle-envelope.unsigned.json`;
- `examples/signed-release-bundle-envelope.signed-placeholder.json`.

## Validation

The examples validate through `validate-json` because `SignedReleaseBundleEnvelope` is mapped in `src/agent_machine/contracts.py`.

```bash
make validate-json
```

## Non-goals for this bootstrap lane

- Generating real signatures.
- Verifying real signatures.
- Submitting to a transparency log.
- Managing signing keys.
- Claiming production readiness.

## Future hardening

Next steps:

1. Add a signing CLI that can wrap a generated `ReleaseEvidenceBundle`.
2. Add a verifier CLI that checks the signature and updates verification status.
3. Add transparency-log references.
4. Add policy-controlled signing key selection.
5. Add branch protection and required validation checks before allowing production promotion.
