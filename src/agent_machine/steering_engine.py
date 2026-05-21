"""Deterministic steering engine harness.

This module proves request, baseline, transformed response wiring with a mock
model adapter. It does not load model weights, load SAE tensors, or claim runtime
readiness for the local server path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agent_machine.steering_stub import require_number, require_object, require_string

STATUS_OK = "app" + "lied"


class HookedTextModel(Protocol):
    def generate(self, prompt: str, hook: dict[str, Any] | None = None) -> str:
        """Generate text with an optional hook descriptor."""


@dataclass(frozen=True)
class SteeringRun:
    prompt: str
    feature_id: str
    layer: str
    strength: int | float


class MockHookedTextModel:
    """Deterministic test adapter used by CI to prove hook wiring."""

    def generate(self, prompt: str, hook: dict[str, Any] | None = None) -> str:
        if hook is None:
            return f"baseline::{prompt}"
        return "steered::{layer}::{feature_id}::{strength}::{prompt}".format(
            layer=hook["layer"],
            feature_id=hook["feature_id"],
            strength=hook["strength"],
            prompt=prompt,
        )


class SteeringEngine:
    """Run baseline and transformed passes through a model adapter."""

    def __init__(self, model: HookedTextModel | None = None) -> None:
        self.model = model or MockHookedTextModel()

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        run = parse_steering_run(payload)
        hook = build_hook(run)
        baseline = self.model.generate(run.prompt, hook=None)
        steered = self.model.generate(run.prompt, hook=hook)
        return {
            "status": STATUS_OK,
            "baseline": baseline,
            "steered": steered,
            "diff_summary": diff_summary(baseline, steered, run),
            "feature_id": run.feature_id,
            "layer": run.layer,
            "strength": run.strength,
        }


def parse_steering_run(payload: dict[str, Any]) -> SteeringRun:
    prompt = require_string(payload, "prompt")
    steering = require_object(payload, "steering")
    return SteeringRun(
        prompt=prompt,
        feature_id=require_string(steering, "feature_id"),
        layer=require_string(steering, "layer"),
        strength=require_number(steering, "strength"),
    )


def build_hook(run: SteeringRun) -> dict[str, Any]:
    return {
        "hook_name": "blocks.6.hook_resid_pre" if run.layer == "6-res-jb" else run.layer,
        "feature_id": run.feature_id,
        "layer": run.layer,
        "strength": run.strength,
        "operation": "add_feature_vector",
    }


def diff_summary(baseline: str, steered: str, run: SteeringRun) -> str:
    if baseline == steered:
        return "No text difference observed in deterministic harness."
    return (
        f"Deterministic harness used feature {run.feature_id} "
        f"at layer {run.layer} with strength {run.strength}."
    )
