#!/usr/bin/env python3
"""Validate the Ollama serving backend: admitted → real output; failure → audited denial.

Uses an injected transport so no live daemon is required. The property asserted is that
a backend failure (daemon down, malformed response) never becomes a silent success — the
gateway turns it into a denied audit with no output. One positive case confirms a served
call returns the model output with usage.
"""
from __future__ import annotations
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_machine.inference_gateway import serve  # noqa: E402
from agent_machine.inference_backends import ollama_backend  # noqa: E402

ACTIVE = {"id": "local-ollama", "kind": "InferenceProvider", "status": "active"}
REQ = {"model": "llama3.3", "caller": "human:michael", "purpose": "discover",
       "space": "user-space", "input": "say hi",
       "consent": {"policyDecisionRef": "urn:srcos:policy-decision:abc"}}

failures = []
def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond: failures.append(name)

# ── positive: injected transport returns a canned Ollama reply ──
seen = {}
def fake_ok(url, payload):
    seen["url"] = url; seen["payload"] = payload
    return {"response": "hi there", "prompt_eval_count": 3, "eval_count": 2}
resp, audit = serve(REQ, provider=ACTIVE, backend=ollama_backend(transport=fake_ok))
check("served call returns model output", resp and resp["output"] == "hi there")
check("usage mapped from ollama counts", resp and resp["usage"] == {"prompt_tokens": 3, "completion_tokens": 2})
check("audit outcome ok", audit["outcome"] == "ok")
check("request hits /api/generate with model+prompt", seen.get("url","").endswith("/api/generate")
      and seen["payload"]["model"] == "llama3.3" and "say hi" in seen["payload"]["prompt"])

# ── negative: daemon unreachable → transport raises → audited denial, no output ──
def down(url, payload): raise ConnectionError("daemon down")
resp, audit = serve(REQ, provider=ACTIVE, backend=ollama_backend(transport=down))
check("unreachable daemon → no output", resp is None)
check("unreachable daemon → denied audit", audit["outcome"] == "denied")

# ── negative: malformed response (no 'response' field) → audited denial ──
def bad(url, payload): return {"unexpected": True}
resp, audit = serve(REQ, provider=ACTIVE, backend=ollama_backend(transport=bad))
check("malformed reply → no output", resp is None)
check("malformed reply → denied audit", audit["outcome"] == "denied")

# ── still fail-closed on missing consent, even with a working backend ──
resp, audit = serve({**REQ, "consent": {}}, provider=ACTIVE, backend=ollama_backend(transport=fake_ok))
check("no consent still refused with live backend", resp is None and audit["outcome"] == "denied")

if failures:
    print(f"\nFAILED: {len(failures)} check(s)"); sys.exit(1)
print("\nOK: Ollama backend serves when admitted and is an audited denial on any failure")
