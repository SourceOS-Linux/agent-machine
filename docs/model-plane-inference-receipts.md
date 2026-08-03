# Model Plane — InferenceReceipt emission (T7-16)

Tranche 7 slice **T7-16: "Model plane capability grants + socket auth"** for
`agent-machine`. Agent Machine grants a model-plane capability to an agent pod and
authenticates the local inference socket. Every completion served over that
authenticated socket must leave a provenance receipt — the `InferenceProvider`
contract already declares `policy.receiptRequired: true`. This slice makes Agent
Machine emit that receipt **natively**, into the estate's single hash-chained
ledger (SEAM-011: a local-only ledger is not permitted).

## What this ships

- `contracts/model-plane/InferenceReceipt.schema.json` — the canonical
  `InferenceReceipt` schema, **vendored verbatim** from
  `SocioProphet/prophet-platform apps/receipt-gateway/schemas/model-plane/`
  (canonical owner: `SourceOS-Linux/sourceos-spec`, Tranche 7). Provenance
  (source commit + sha256) is recorded in the schema's `$comment`.
- `src/agent_machine/inference_receipt.py` — the hash-chain / canonical-JSON /
  ledger machinery is **vendored verbatim** from the canonical emitter
  (`prophet-platform apps/receipt-gateway/tools/inference_receipt_emitter.py`).
  We consume it, we do not re-implement the chain. The only Agent-Machine
  addition is `emit_socket_inference_receipt()`, which binds the two facts socket
  auth resolves — `requestingAgentRef` (the AgentPassport URN) and
  `capabilityLeaseRef` (the AgentCapabilityLease URN that granted the model-plane
  capability) — into the receipt before it is chained, so the grant is covered by
  the tamper-evident hash. Both refs are required arguments: a socket-authed
  inference with no capability grant is not authorized and is never emitted
  (fail-closed at the call site).
- `scripts/validate-inference-receipt.py` — teeth, wired into `make validate` via
  `make validate-inference-receipt`.

## Teeth

The validator fails CI unless all of these hold:

1. A receipt for a socket-authed, capability-granted inference validates against
   the vendored schema.
2. Successive receipts chain (`ledgerPrevHash` continuity; genesis has none).
3. A tampered entry breaks the chain and is rejected.
4. A local-only receipt (a non-genesis entry with no `ledgerPrevHash`, i.e. not
   bound into the ledger) is rejected by **both** the schema and the verifier
   (SEAM-011).
5. An off-device receipt without a capability lease + escalation chain is
   schema-rejected (SEAM-015) — the grant is load-bearing, not decorative.

## Boundary / not in this slice

- `contracts/inference-provider.schema.json` (Agent Machine's own
  `InferenceProvider` declaration) is unchanged. It declares *that* a provider
  requires receipts; the vendored `InferenceReceipt` schema is *what* the emitted
  receipt conforms to. Reconciling the two `InferenceProvider` models
  (Agent Machine's local one vs. the sourceos-spec Model Carry family) is tracked
  upstream and is out of scope here.
- The live socket-auth daemon that calls `emit_socket_inference_receipt()` on
  every real completion, and a persistent ledger service (vs. per-call file), are
  the remaining productionization steps. See the T7-16 follow-up issue.
