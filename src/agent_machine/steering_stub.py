"""Neuronpedia-compatible local steering endpoint stub.

This module intentionally does not perform activation steering, model loading, SAE
artifact loading, or provider activation. It exists so Noetica can exercise the
local endpoint shape before the real controlled activation path exists.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Literal

SteerStubStatus = Literal["not_configured", "noop"]
_ALLOWED_STUB_STATUSES: set[str] = {"not_configured", "noop"}


class SteeringStubError(AssertionError):
    """Raised when a local steering request does not match the contract."""


def load_steer_request(path: str) -> dict[str, Any]:
    """Load a steer request JSON object from a path or stdin marker."""
    if path == "-":
        payload = json.load(sys.stdin)
    else:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SteeringStubError("steer request root must be a JSON object")
    return payload


def build_stub_steer_result(payload: dict[str, Any], status: SteerStubStatus = "not_configured") -> dict[str, Any]:
    """Return a Noetica-compatible SteeringResult without activation injection."""
    if status not in _ALLOWED_STUB_STATUSES:
        raise SteeringStubError(f"unsupported stub status: {status}")

    prompt = require_string(payload, "prompt")
    model_id = require_string(payload, "model_id")
    steering = require_object(payload, "steering")
    feature_id = require_string(steering, "feature_id")
    layer = require_string(steering, "layer")
    strength = require_number(steering, "strength")

    if status == "noop":
        diff_summary = (
            "Agent Machine local steering stub accepted the request shape but deliberately applied no runtime intervention. "
            "No model, sourceset, or SAE artifact was loaded."
        )
    else:
        diff_summary = (
            "Agent Machine local steering endpoint is not configured for activation. "
            f"Sourceset/model readiness for {model_id} is outside this Issue #32 stub."
        )

    return {
        "status": status,
        "baseline": prompt,
        "steered": prompt,
        "diff_summary": diff_summary,
        "feature_id": feature_id,
        "layer": layer,
        "strength": strength,
    }


def serve_stub(host: str = "127.0.0.1", port: int = 8080, status: SteerStubStatus = "not_configured") -> int:
    """Serve a minimal local HTTP endpoint for contract testing."""
    if status not in _ALLOWED_STUB_STATUSES:
        raise SteeringStubError(f"unsupported stub status: {status}")

    class Handler(BaseHTTPRequestHandler):
        server_version = "AgentMachineSteerStub/0.1"

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path not in {"/health", "/ready"}:
                self.send_json({"error": "not_found"}, status_code=404)
                return
            self.send_json(
                {
                    "ok": True,
                    "kind": "NeuronpediaCompatibleLocalSteerStub",
                    "status": "stubbed",
                    "endpoint": "/steer",
                    "activationImplemented": False,
                    "modelWeightsLoaded": False,
                    "saeArtifactsLoaded": False,
                }
            )

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path != "/steer":
                self.send_json({"error": "not_found"}, status_code=404)
                return
            try:
                payload = self.read_json()
                result = build_stub_steer_result(payload, status=status)
            except (json.JSONDecodeError, UnicodeDecodeError, SteeringStubError) as exc:
                self.send_json({"error": "invalid_steer_request", "message": str(exc)}, status_code=400)
                return
            self.send_json(result)

        def read_json(self) -> dict[str, Any]:
            length_header = self.headers.get("content-length")
            if not length_header:
                raise SteeringStubError("missing content-length")
            length = int(length_header)
            if length > 1_048_576:
                raise SteeringStubError("request body exceeds 1 MiB")
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise SteeringStubError("steer request root must be a JSON object")
            return payload

        def send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status_code)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - inherited name
            print(f"agent-machine steer stub: {self.address_string()} - {format % args}", file=sys.stderr)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"agent-machine steer stub serving http://{host}:{port}/steer status={status}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("agent-machine steer stub stopped", file=sys.stderr)
    finally:
        server.server_close()
    return 0


def require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SteeringStubError(f"missing non-empty string field: {key}")
    return value


def require_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise SteeringStubError(f"missing object field: {key}")
    return value


def require_number(payload: dict[str, Any], key: str) -> int | float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SteeringStubError(f"missing numeric field: {key}")
    return value
