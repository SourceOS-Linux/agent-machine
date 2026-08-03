"""InferenceReceipt emission for Agent Machine (Tranche 7 / T7-16).

T7-16 = "Model plane capability grants + socket auth". Agent Machine grants a
model-plane capability to an agent pod and authenticates the local inference
socket; every completion served over that authenticated socket MUST leave a
provenance receipt (its InferenceProvider contract already declares
`policy.receiptRequired`). This module makes Agent Machine emit that receipt
NATIVELY, into the estate's one hash-chained ledger (SEAM-011: no local-only
ledger).

CONSUME-NOT-FORK: the hash-chain / canonical-JSON / ledger machinery below is
VENDORED VERBATIM from the canonical emitter
  SocioProphet/prophet-platform apps/receipt-gateway/tools/inference_receipt_emitter.py
  @ commit abd98805,
  sha256:6881246b8e41a515fb1b29df645faeb9be17d8195d22a7e0d5ce15f8477d8e6a
(canonical owner: SourceOS-Linux/sourceos-spec, Tranche 7). Do NOT re-implement
the chain here; refresh by re-copying from prophet-platform so the ledger stays
interoperable with the receipt-gateway. `emit_socket_inference_receipt` is the
only Agent-Machine-specific addition: it binds the capability grant
(capabilityLeaseRef) and requesting agent (requestingAgentRef) that socket auth
resolved, then delegates to the vendored `emit_receipt`.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl  # POSIX advisory locking (Linux/macOS)
except ImportError:  # pragma: no cover
    fcntl = None

import jsonschema

# Vendored schema shipped alongside the repo contracts (see contracts/model-plane/).
SCHEMA = Path(__file__).resolve().parents[2] / "contracts" / "model-plane" / "InferenceReceipt.schema.json"

_UNSET = object()  # distinguishes "estimate it" from an explicit None (record null)


# --- BEGIN vendored-verbatim block (prophet-platform inference_receipt_emitter.py) ---
def sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _last_entry(f) -> dict | None:
    """Last non-blank ledger entry, constant memory (deque(maxlen=1) over the file)."""
    f.seek(0)
    tail = deque((line for line in f if line.strip()), maxlen=1)
    return json.loads(tail[0]) if tail else None


def emit_receipt(ledger: Path, *, base_model_digest: str, task: str, input_text: str,
                 output_text: str, provider_daemon: str = "inferenced", tier: str = "T1",
                 tokenizer_digest: str | None = None, compute_device: str = "cpu",
                 input_token_count=_UNSET, output_token_count=_UNSET,
                 extra: dict | None = None) -> dict:
    """Append one InferenceReceipt to the hash-chained ledger, return it.

    Read-tail + append happen under an exclusive advisory lock so concurrent emitters
    cannot race into duplicate ledgerSeq or a broken chain (single-writer per entry).

    `extra` (Agent-Machine addition, not a chain change) merges caller-supplied
    top-level fields such as requestingAgentRef / capabilityLeaseRef / providerRef
    BEFORE the entry is chained, so they are covered by the tamper-evident hash.
    """
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a+", encoding="utf-8") as f:
        if fcntl is not None:
            fcntl.flock(f, fcntl.LOCK_EX)
        try:
            prev = _last_entry(f)
            seq = (prev["ledgerSeq"] + 1) if prev else 0
            receipt = {
                "id": f"urn:srcos:inference-receipt:{task}-{seq}",
                "type": "InferenceReceipt",
                "specVersion": "2.1.0",
                "issuedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "providerDaemon": provider_daemon,
                "tier": tier,
                "baseModelDigest": base_model_digest,
                "tokenizerDigest": tokenizer_digest,
                "task": task,
                "inputHash": sha256(input_text),
                "inputTokenCount": len(input_text.split()) if input_token_count is _UNSET else input_token_count,
                "outputHash": sha256(output_text),
                "outputTokenCount": len(output_text.split()) if output_token_count is _UNSET else output_token_count,
                "dataResidencyClass": "on_device_only",
                "escalatedFrom": None,
                "escalationChain": [],
                "computeDevice": compute_device,
                "ledgerSeq": seq,
            }
            if extra:
                receipt.update(extra)
            if seq >= 1:
                # hash-chain: bind this entry to the canonical prior entry (SEAM-011)
                receipt["ledgerPrevHash"] = sha256(canonical(prev))
            f.write(canonical(receipt) + "\n")
            f.flush()
        finally:
            if fcntl is not None:
                fcntl.flock(f, fcntl.LOCK_UN)
    return receipt


def verify_ledger(ledger: Path, validator: "jsonschema.Draft202012Validator") -> tuple[bool, str]:
    if not ledger.exists():
        return False, f"ledger not found: {ledger}"
    try:
        lines = [l for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError as exc:
        return False, f"cannot read ledger: {exc}"
    prev = None
    for i, line in enumerate(lines):
        try:
            r = json.loads(line)
        except json.JSONDecodeError as exc:
            return False, f"entry {i} is not valid JSON: {exc}"
        errs = sorted(validator.iter_errors(r), key=lambda e: list(e.path))
        if errs:
            return False, f"entry {i} schema-invalid: {errs[0].message}"
        if r["ledgerSeq"] != i:
            return False, f"entry {i} has ledgerSeq {r['ledgerSeq']} (expected {i})"
        if i >= 1:
            expect = sha256(canonical(prev))
            if r.get("ledgerPrevHash") != expect:
                return False, f"entry {i} chain broken: ledgerPrevHash != hash(entry {i-1})"
        prev = r
    return True, f"{len(lines)} receipts: schema-conformant + unbroken hash-chain"
# --- END vendored-verbatim block ---


def load_validator() -> "jsonschema.Draft202012Validator":
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def emit_socket_inference_receipt(
    ledger: Path,
    *,
    base_model_digest: str,
    task: str,
    input_text: str,
    output_text: str,
    requesting_agent_ref: str,
    capability_lease_ref: str,
    provider_ref: str | None = None,
    provider_daemon: str = "inferenced",
    tier: str = "T1",
    tokenizer_digest: str | None = None,
    compute_device: str = "cpu",
) -> dict:
    """T7-16: emit a receipt for a completion served over the authenticated model socket.

    Socket auth resolved WHO asked (`requesting_agent_ref`, an AgentPassport URN) and
    under WHICH grant (`capability_lease_ref`, an AgentCapabilityLease URN). Both are
    recorded in the receipt and covered by the hash-chain. A socket-authed inference
    with no capability grant is not authorized and must not be emitted, so both refs
    are required arguments (fail-closed at the call site).
    """
    if not requesting_agent_ref.startswith("urn:srcos:agent-passport:"):
        raise ValueError("requesting_agent_ref must be an AgentPassport URN (urn:srcos:agent-passport:...)")
    if not capability_lease_ref.startswith("urn:srcos:lease:"):
        raise ValueError("capability_lease_ref must be an AgentCapabilityLease URN (urn:srcos:lease:...)")
    extra = {
        "requestingAgentRef": requesting_agent_ref,
        "capabilityLeaseRef": capability_lease_ref,
    }
    if provider_ref is not None:
        extra["providerRef"] = provider_ref
    return emit_receipt(
        ledger,
        base_model_digest=base_model_digest,
        task=task,
        input_text=input_text,
        output_text=output_text,
        provider_daemon=provider_daemon,
        tier=tier,
        tokenizer_digest=tokenizer_digest,
        compute_device=compute_device,
        extra=extra,
    )
