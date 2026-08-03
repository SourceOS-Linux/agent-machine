"""Local adapter for the InferenceGateway intersection seam.

Both planes serve inference through one contract (sourceos-spec
`inference-gateway-intersection.md`); this is the **local** adapter (agent-machine /
Noetica). It serves a call only through a registered, active `InferenceProvider`
(`contracts/inference-provider.schema.json`) and only when an admitting consent
decision is present — and it emits a `GatewayCallAudit` (memory-mesh
`gateway-call-audit.schema.json` v0.1) on **every** call, including refusals, so that
nothing is ever served un-consented or un-audited.

The controls here are refusals. A gateway never observed denying a call is
indistinguishable from no gateway — so a *denied* call still returns a full audit
(outcome="denied") and no output. Output is returned only on outcome="ok".
"""
from __future__ import annotations

import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from agent_machine.digest import stable_digest

# GatewayCallAudit v0.1 required fields (memory-mesh schemas/gateway-call-audit.schema.json).
GATEWAY_AUDIT_REQUIRED = [
    "schemaVersion", "recordType", "callId", "call_type", "outcome", "caller",
    "model", "epistemicLevel", "recalled_count", "written", "occurred_at", "receipt_hash",
]
_ACTIVE_PROVIDER_STATUS = {"active", "ready", "serving", "enabled"}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _audit(request: Dict[str, Any], outcome: str, error: Optional[str] = None) -> Dict[str, Any]:
    """Build a GatewayCallAudit record. Always fully populated — even for refusals."""
    core = {
        "schemaVersion": "0.1",
        "recordType": "GatewayCallAudit",
        "call_type": "inference",
        "outcome": outcome,
        "caller": (request or {}).get("caller", "unknown"),
        "model": (request or {}).get("model", "unknown"),
        "epistemicLevel": (request or {}).get("epistemicLevel", "operational"),
        "recalled_count": 0,
        "written": False,
        "occurred_at": _now(),
    }
    if error:
        core["error"] = error
    core["callId"] = stable_digest({"c": core["caller"], "m": core["model"], "t": core["occurred_at"], "o": outcome})[7:23]
    core["receipt_hash"] = stable_digest(core)
    return core


def _refuse(request: Dict[str, Any], reason: str) -> Tuple[None, Dict[str, Any]]:
    return None, _audit(request, "denied", error=reason)


def serve(
    request: Dict[str, Any],
    *,
    provider: Optional[Dict[str, Any]] = None,
    backend: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Serve one inference call, fail-closed. Returns (response|None, audit).

    Output is returned only when the call is admitted (outcome="ok"); every other
    path returns (None, denied-audit). Never raises for a bad request — it refuses.
    """
    if not isinstance(request, dict):
        return _refuse({}, "request is not an object")
    for field in ("model", "caller", "purpose", "space"):
        if not request.get(field):
            return _refuse(request, f"request missing required field: {field}")

    consent = request.get("consent")
    if not isinstance(consent, dict) or not consent.get("policyDecisionRef"):
        return _refuse(request, "no admitting consent decision — refused fail-closed")

    if not isinstance(provider, dict):
        return _refuse(request, "no registered InferenceProvider — refused fail-closed")
    if provider.get("status") not in _ACTIVE_PROVIDER_STATUS:
        return _refuse(request, f"provider status {provider.get('status')!r} is not active")

    if not callable(backend):
        return _refuse(request, "no serving backend available")

    try:
        result = backend(request)
    except Exception as exc:  # a backend failure is an audited denial, not a crash
        return _refuse(request, f"backend error: {type(exc).__name__}")
    if not isinstance(result, dict) or "output" not in result:
        return _refuse(request, "backend returned no output")

    audit = _audit(request, "ok")
    response = {
        "output": result["output"],
        "usage": result.get("usage", {}),
        "receipt_hash": audit["receipt_hash"],
    }
    return response, audit
