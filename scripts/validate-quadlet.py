#!/usr/bin/env python3
"""Validate Agent Machine Quadlet deployment templates.

This validator is intentionally conservative. It checks local .container files
for the safety posture we expect from SourceOS-managed AgentPods before we add
full manifest generation and policy admission.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
QUADLET_DIR = REPO_ROOT / "deploy" / "quadlet"

DISALLOWED_VOLUME_FRAGMENTS = (
    "/var/run/docker.sock",
    "/run/docker.sock",
    "/run/podman/podman.sock",
    "/var/run/podman/podman.sock",
)


def iter_quadlet_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.rglob("*.container") if path.is_file())


def parse_quadlet(path: Path) -> dict[str, dict[str, list[str]]]:
    sections: dict[str, dict[str, list[str]]] = {}
    current_section: str | None = None

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                if not current_section:
                    raise AssertionError(f"{path}: line {line_number}: empty section name")
                sections.setdefault(current_section, {})
                continue
            if current_section is None:
                raise AssertionError(f"{path}: line {line_number}: key outside section")
            if "=" not in line:
                raise AssertionError(f"{path}: line {line_number}: expected key=value")
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                raise AssertionError(f"{path}: line {line_number}: empty key")
            sections.setdefault(current_section, {}).setdefault(key, []).append(value)

    return sections


def values(sections: dict[str, dict[str, list[str]]], section: str, key: str) -> list[str]:
    return sections.get(section, {}).get(key, [])


def first_value(sections: dict[str, dict[str, list[str]]], section: str, key: str) -> str | None:
    vals = values(sections, section, key)
    return vals[0] if vals else None


def require_value(sections: dict[str, dict[str, list[str]]], section: str, key: str, path: Path) -> str:
    value = first_value(sections, section, key)
    if value is None or value == "":
        raise AssertionError(f"{path}: missing required {section}.{key}")
    return value


def require_bool_value(
    sections: dict[str, dict[str, list[str]]],
    section: str,
    key: str,
    expected: str,
    path: Path,
) -> None:
    actual = require_value(sections, section, key, path).lower()
    if actual != expected.lower():
        raise AssertionError(f"{path}: {section}.{key} must be {expected}, observed {actual}")


def validate_loopback_ports(path: Path, publish_ports: Iterable[str]) -> None:
    for publish_port in publish_ports:
        if not (publish_port.startswith("127.0.0.1:") or publish_port.startswith("localhost:")):
            raise AssertionError(
                f"{path}: PublishPort must bind to loopback for skeleton local AgentPods: {publish_port}"
            )


def validate_volumes(path: Path, volumes: Iterable[str]) -> None:
    for volume in volumes:
        for fragment in DISALLOWED_VOLUME_FRAGMENTS:
            if fragment in volume:
                raise AssertionError(f"{path}: forbidden socket mount in Volume={volume}")
        if ":/models:" in volume and ":ro" not in volume:
            raise AssertionError(f"{path}: model volume must be mounted read-only: {volume}")


def validate_environment(path: Path, environment_values: Iterable[str]) -> None:
    env = {}
    for item in environment_values:
        if "=" in item:
            key, value = item.split("=", 1)
            env[key] = value
    if env.get("AGENT_MACHINE_RECEIPTS_REQUIRED") != "true":
        raise AssertionError(f"{path}: AGENT_MACHINE_RECEIPTS_REQUIRED=true is required")


def validate_quadlet(path: Path) -> None:
    sections = parse_quadlet(path)
    if "Container" not in sections:
        raise AssertionError(f"{path}: missing [Container] section")

    require_value(sections, "Container", "Image", path)
    require_value(sections, "Container", "Exec", path)
    require_bool_value(sections, "Container", "ReadOnly", "true", path)
    require_bool_value(sections, "Container", "NoNewPrivileges", "true", path)

    security_label_disable = first_value(sections, "Container", "SecurityLabelDisable")
    if security_label_disable is not None and security_label_disable.lower() == "true":
        raise AssertionError(f"{path}: SecurityLabelDisable=true is not allowed")

    privileged = first_value(sections, "Container", "Privileged")
    if privileged is not None and privileged.lower() == "true":
        raise AssertionError(f"{path}: Privileged=true is not allowed")

    network = first_value(sections, "Container", "Network")
    if network is not None and network.lower() == "host":
        raise AssertionError(f"{path}: Network=host is not allowed for skeleton local AgentPods")

    drop_capabilities = [value.lower() for value in values(sections, "Container", "DropCapability")]
    if "all" not in drop_capabilities:
        raise AssertionError(f"{path}: DropCapability=all is required")

    validate_loopback_ports(path, values(sections, "Container", "PublishPort"))
    validate_volumes(path, values(sections, "Container", "Volume"))
    validate_environment(path, values(sections, "Container", "Environment"))


def main() -> int:
    quadlet_files = iter_quadlet_files(QUADLET_DIR)
    if not quadlet_files:
        print("No Quadlet .container files found under deploy/quadlet/")
        return 0

    for path in quadlet_files:
        validate_quadlet(path)
        print(f"VALID quadlet {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
