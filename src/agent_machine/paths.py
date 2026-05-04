"""Repository and runtime path helpers for Agent Machine."""

from __future__ import annotations

from pathlib import Path


def repo_root_from_file(file_path: str | Path) -> Path:
    """Resolve the repository root from a file path under repo-owned scripts/modules."""
    path = Path(file_path).resolve()
    for candidate in [path, *path.parents]:
        if (candidate / "contracts").is_dir() and (candidate / "examples").is_dir():
            return candidate
    raise RuntimeError(f"Unable to locate Agent Machine repo root from {file_path!s}")


def default_config_path() -> Path:
    return Path("/etc/agent-machine")


def default_state_path() -> Path:
    return Path("/var/lib/agent-machine")


def default_model_cache_path() -> Path:
    return default_state_path() / "models"


def default_runtime_cache_path() -> Path:
    return default_state_path() / "cache"


def default_evidence_path() -> Path:
    return default_state_path() / "evidence"


def default_runtime_path() -> Path:
    return Path("/run/agent-machine")
