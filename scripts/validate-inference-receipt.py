#!/usr/bin/env python3
"""Teeth for T7-16: Agent Machine emits spec-conformant, hash-chained InferenceReceipts.

Proves (exit 0 only if ALL hold):
  1. A receipt emitted for a socket-authed, capability-granted inference validates
     against the vendored InferenceReceipt.schema.json.
  2. Successive receipts chain (ledgerPrevHash continuity; genesis has none).
  3. A TAMPERED entry breaks the chain and is rejected.
  4. A LOCAL-ONLY receipt (non-genesis entry with no ledgerPrevHash — i.e. not bound
     into the estate ledger) is rejected by BOTH the schema and the verifier (SEAM-011).
  5. An OFF-DEVICE receipt without a capability lease + escalation is schema-rejected
     (SEAM-015) — the socket-auth grant is load-bearing, not decorative.

exit 0 = all teeth bite; 1 = a tooth failed to bite (regression).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from agent_machine.inference_receipt import (  # noqa: E402
    canonical, emit_socket_inference_receipt, load_validator, sha256, verify_ledger,
)

DIGEST = "sha256:" + "a" * 64
AGENT = "urn:srcos:agent-passport:app-helper-42"
LEASE = "urn:srcos:lease:model-plane-inference-0001"
PROVIDER = "urn:srcos:inference-provider:local-llama-cpp"


def main() -> int:
    validator = load_validator()
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as d:
        ledger = Path(d) / "inference-ledger.jsonl"

        # Tooth 1 + 2: emit chained, socket-authed receipts; whole ledger conforms + chains.
        for i in range(3):
            r = emit_socket_inference_receipt(
                ledger, base_model_digest=DIGEST, task="agent_classification",
                input_text=f"authed prompt {i}", output_text=f"completion {i}",
                requesting_agent_ref=AGENT, capability_lease_ref=LEASE, provider_ref=PROVIDER,
            )
            if list(validator.iter_errors(r)):
                failures.append(f"emitted receipt {i} is schema-invalid")
            if r.get("capabilityLeaseRef") != LEASE or r.get("requestingAgentRef") != AGENT:
                failures.append(f"receipt {i} did not bind socket-auth grant/agent")
        ok, msg = verify_ledger(ledger, validator)
        if not ok:
            failures.append(f"chain should be valid but: {msg}")
        else:
            print(f"OK conformance+chain: {msg}")

        # Tooth 3: tamper entry 1 -> chain must break.
        lines = ledger.read_text(encoding="utf-8").splitlines()
        import json
        e1 = json.loads(lines[1]); e1["outputHash"] = sha256("tampered")
        lines[1] = canonical(e1)
        ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok, msg = verify_ledger(ledger, validator)
        if ok:
            failures.append("tampered receipt NOT detected — chain has no teeth")
        else:
            print(f"OK tamper-evidence: {msg}")

    # Tooth 4: local-only receipt (seq>=1, no ledgerPrevHash) rejected by schema AND verifier.
    with tempfile.TemporaryDirectory() as d:
        import json
        ledger = Path(d) / "local-only.jsonl"
        base = emit_socket_inference_receipt(
            ledger, base_model_digest=DIGEST, task="t", input_text="a", output_text="b",
            requesting_agent_ref=AGENT, capability_lease_ref=LEASE)
        local_only = dict(base)
        local_only["ledgerSeq"] = 1
        local_only.pop("ledgerPrevHash", None)  # unchained -> local-only
        schema_rejects = bool(list(validator.iter_errors(local_only)))
        with ledger.open("a", encoding="utf-8") as f:
            f.write(canonical(local_only) + "\n")
        verifier_rejects = not verify_ledger(ledger, validator)[0]
        if schema_rejects and verifier_rejects:
            print("OK local-only rejected: schema + verifier both refuse an unchained entry")
        else:
            failures.append(
                f"local-only entry accepted (schema_rejects={schema_rejects}, verifier_rejects={verifier_rejects})")

    # Tooth 5: off-device receipt without lease/escalation is schema-rejected (SEAM-015).
    off_device = {
        "id": "urn:srcos:inference-receipt:x-0", "type": "InferenceReceipt",
        "specVersion": "2.1.0", "issuedAt": "2026-08-03T00:00:00Z",
        "providerDaemon": "inferenced", "tier": "T3", "baseModelDigest": DIGEST,
        "task": "t", "inputHash": sha256("a"), "outputHash": sha256("b"),
        "dataResidencyClass": "external_permitted",  # off-device, but no lease/escalation
        "ledgerSeq": 0,
    }
    if list(validator.iter_errors(off_device)):
        print("OK SEAM-015: off-device receipt without lease+escalation is rejected")
    else:
        failures.append("off-device receipt without lease/escalation was accepted (SEAM-015 hole)")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("PASS: T7-16 InferenceReceipt teeth all bite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
