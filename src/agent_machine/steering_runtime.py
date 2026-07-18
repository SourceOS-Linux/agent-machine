"""Controlled local steering runtime preflight and fail-closed server.

This module owns the first real-path entrypoint for Issue #34. It intentionally
keeps activation fail-closed until optional ML dependencies, verified artifacts,
storage receipts, policy admission, and grants are present. It never returns
``status: applied`` unless a future implementation successfully runs a real
activation-injection path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agent_machine.contracts import load_json
from agent_machine.paths import repo_root_from_file
from agent_machine.steering_stub import SteeringStubError, build_stub_steer_result

REPO_ROOT = repo_root_from_file(__file__)
SOURCESET_DIR = REPO_ROOT / "examples" / "steering-sourcesets"
OPTIONAL_RUNTIME_MODULES = {
    "torch": "torch",
    "transformers": "transformers",
    "transformer_lens": "transformer-lens",
    "sae_lens": "sae-lens",
    "safetensors": "safetensors",
    "huggingface_hub": "huggingface_hub",
}


class SteeringRuntimeError(AssertionError):
    """Raised when the real steering runtime cannot proceed safely."""


def load_sourceset(sourceset_id: str) -> dict[str, Any]:
    """Load a registered SteeringSourceset by sourcesetId."""
    for path in sorted(SOURCESET_DIR.glob("*.steering-sourceset.json")):
        payload = load_json(path)
        if payload.get("sourcesetId") == sourceset_id:
            return payload
    raise SteeringRuntimeError(f"sourceset not registered: {sourceset_id}")


def runtime_preflight(sourceset_id: str) -> dict[str, Any]:
    """Return a secret-free readiness record for the real steering path."""
    try:
        sourceset = load_sourceset(sourceset_id)
    except SteeringRuntimeError as exc:
        return {
            "ok": False,
            "status": "not_configured",
            "sourceset": sourceset_id,
            "registered": False,
            "ready": False,
            "missing": [str(exc)],
            "activationImplemented": False,
        }

    missing: list[str] = []
    optional_dependencies = {}
    for module_name, package_name in OPTIONAL_RUNTIME_MODULES.items():
        available = importlib.util.find_spec(module_name) is not None
        optional_dependencies[package_name] = available
        if not available:
            missing.append(f"optional runtime dependency missing: {package_name}")

    activation = sourceset.get("activation", {}) if isinstance(sourceset, dict) else {}
    for item in activation.get("missing", []) if isinstance(activation, dict) else []:
        if isinstance(item, str) and item not in missing:
            missing.append(item)

    ready = not missing and bool(activation.get("loadableToday")) and bool(activation.get("activationImplemented"))

    return {
        "ok": True,
        "status": "available" if ready else "not_configured",
        "sourceset": sourceset_id,
        "registered": True,
        "sourcesetStatus": sourceset.get("status"),
        "ready": ready,
        "model": sourceset.get("model", {}).get("source", {}).get("repo"),
        "sae": sourceset.get("sae", {}).get("source", {}).get("repo"),
        "hook": sourceset.get("sae", {}).get("hook"),
        "optionalDependencies": optional_dependencies,
        "missing": missing,
        "activationImplemented": False,
        "downloadsPerformed": False,
        "message": (
            "Real steering activation is not ready; serve --sourceset will return status=not_configured "
            "until optional dependencies, verified artifacts, storage receipts, policy/grant admission, and activation injection are present."
        ),
    }


def serve_sourceset(sourceset_id: str, host: str = "127.0.0.1", port: int = 8080) -> int:
    """Serve the sourceset-aware local steering endpoint in fail-closed mode."""
    preflight = runtime_preflight(sourceset_id)

    class Handler(BaseHTTPRequestHandler):
        server_version = "AgentMachineSteerRuntime/0.1"

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path not in {"/health", "/ready"}:
                self.send_json({"error": "not_found"}, status_code=404)
                return
            self.send_json({"ok": True, "kind": "NeuronpediaCompatibleLocalSteerRuntime", "preflight": preflight})

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path != "/steer":
                self.send_json({"error": "not_found"}, status_code=404)
                return
            try:
                payload = self.read_json()
                result = build_fail_closed_result(payload, preflight)
            except (json.JSONDecodeError, UnicodeDecodeError, SteeringStubError, SteeringRuntimeError) as exc:
                self.send_json({"error": "invalid_steer_request", "message": str(exc)}, status_code=400)
                return
            self.send_json(result)

        def read_json(self) -> dict[str, Any]:
            length_header = self.headers.get("content-length")
            if not length_header:
                raise SteeringRuntimeError("missing content-length")
            length = int(length_header)
            if length > 1_048_576:
                raise SteeringRuntimeError("request body exceeds 1 MiB")
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise SteeringRuntimeError("steer request root must be a JSON object")
            return payload

        def send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status_code)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - inherited name
            print(f"agent-machine steer runtime: {self.address_string()} - {format % args}", file=sys.stderr)

    print(
        f"agent-machine steer runtime serving http://{host}:{port}/steer sourceset={sourceset_id} ready={preflight.get('ready')}",
        file=sys.stderr,
    )
    if not preflight.get("ready"):
        print(json.dumps({"warning": "real activation not ready", "preflight": preflight}, sort_keys=True), file=sys.stderr)
    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("agent-machine steer runtime stopped", file=sys.stderr)
    finally:
        server.server_close()
    return 0


def build_fail_closed_result(payload: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    """Return status=not_configured unless a future real path proves readiness."""
    result = build_stub_steer_result(payload, status="not_configured")
    missing = preflight.get("missing", [])
    missing_text = "; ".join(str(item) for item in missing[:8])
    result["diff_summary"] = (
        "Agent Machine real steering path is not configured for applied activation. "
        f"Sourceset={preflight.get('sourceset')} ready={preflight.get('ready')}. Missing: {missing_text or 'unknown'}"
    )
    return result
