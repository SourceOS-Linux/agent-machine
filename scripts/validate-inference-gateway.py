#!/usr/bin/env python3
"""Validate the local InferenceGateway adapter refuses and audits, fail-closed.

The property asserted is a refusal: a call served without a registered active
provider, or without an admitting consent decision, or without a backend, must not
return output — and must still emit a GatewayCallAudit (outcome="denied"). A gateway
never observed refusing is indistinguishable from no gateway. One positive case
confirms an admitted call returns output plus an outcome="ok" audit.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.inference_gateway import serve, GATEWAY_AUDIT_REQUIRED  # noqa: E402

ACTIVE = {"id": "local-ollama", "kind": "InferenceProvider", "status": "active"}
OK_REQ = {
    "model": "llama-3.3-70b", "caller": "human:michael", "purpose": "discover",
    "space": "user-space", "input": "hi",
    "consent": {"policyDecisionRef": "urn:srcos:policy-decision:abc"},
}
def _backend(_req):
    return {"output": "hello", "usage": {"tokens": 3}}

failures = []
def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failures.append(name)

def audit_ok(a):
    return isinstance(a, dict) and all(k in a for k in GATEWAY_AUDIT_REQUIRED)

# ── negative controls: every refusal returns no output + a denied audit ──
for name, req, prov, backend in [
    ("no consent → refused", {**OK_REQ, "consent": {}}, ACTIVE, _backend),
    ("no provider → refused", OK_REQ, None, _backend),
    ("inactive provider → refused", OK_REQ, {**ACTIVE, "status": "draft"}, _backend),
    ("no backend → refused", OK_REQ, ACTIVE, None),
    ("missing field (model) → refused", {k: v for k, v in OK_REQ.items() if k != "model"}, ACTIVE, _backend),
    ("non-dict request → refused", "nope", ACTIVE, _backend),
    ("backend raises → audited denial", OK_REQ, ACTIVE, (lambda _r: (_ for _ in ()).throw(RuntimeError()))),
]:
    resp, audit = serve(req, provider=prov, backend=backend)
    check(name + " [no output]", resp is None)
    check(name + " [denied audit]", audit_ok(audit) and audit["outcome"] == "denied")

# ── positive control: an admitted call returns output + an ok audit ──
resp, audit = serve(OK_REQ, provider=ACTIVE, backend=_backend)
check("admitted call returns output", resp is not None and resp.get("output") == "hello")
check("admitted call ok audit", audit_ok(audit) and audit["outcome"] == "ok")
check("response carries receipt_hash == audit", resp and resp.get("receipt_hash") == audit["receipt_hash"])

if failures:
    print(f"\nFAILED: {len(failures)} check(s)")
    sys.exit(1)
print("\nOK: InferenceGateway local adapter fails closed and audits every call")
