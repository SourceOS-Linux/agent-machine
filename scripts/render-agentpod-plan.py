#!/usr/bin/env python3
"""Thin wrapper for the AgentPod plan and receipt renderer."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agent_machine.renderers.plan import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
