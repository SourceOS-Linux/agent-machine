#!/usr/bin/env python3
"""Detect the merge-duplication pathology across every tracked file.

Four commits titled "merge: resolve conflicts keeping all content from both sides"
concatenated both halves of every conflict instead of resolving them. That left a
CLI that would not compile, a schema that had never once parsed, dead code after a
`return` that silently disabled grant resolution, and nine copies of the same
Makefile target — none of which any check would have noticed.

Every check here is cheap and total. The expensive part was never the detection;
it was that nothing looked.

Duplicate JSON keys deserve special mention: `json.load` accepts them and keeps
the last, so a duplicated block can round-trip through every schema validator in
the repo while quietly discarding the first definition.
"""

from __future__ import annotations

import ast
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def tracked(*globs: str) -> list[Path]:
    out = subprocess.run(["git", "ls-files", *globs], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
    return [REPO_ROOT / f for f in out]


def rel(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT))


def check_python_compiles(failures: list[str]) -> int:
    """Must be compile(), not ast.parse().

    `ast.parse` accepts a repeated keyword argument — the exact defect that made
    cli.py unimportable — because that is rejected during compilation, not
    parsing. A parse-only check reports this file as healthy.
    """
    files = tracked("*.py")
    for f in files:
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")
        except SyntaxError as exc:
            failures.append(f"{rel(f)}:{exc.lineno}: does not compile: {exc.msg}")
    return len(files)


def check_python_no_shadowed_defs(failures: list[str]) -> int:
    """A module-level name defined twice means the first is dead and unreachable."""
    files = tracked("*.py")
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        except SyntaxError:
            continue  # already reported by the compile check
        seen: dict[str, int] = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name in seen:
                    failures.append(
                        f"{rel(f)}:{node.lineno}: '{node.name}' redefined "
                        f"(first at line {seen[node.name]}); the earlier one is dead code"
                    )
                seen[node.name] = node.lineno
    return len(files)


def check_python_no_code_after_return(failures: list[str]) -> int:
    """Statements after a return in the same block never execute."""
    files = tracked("*.py")
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for i, stmt in enumerate(body[:-1]):
                if isinstance(stmt, ast.Return):
                    nxt = body[i + 1]
                    failures.append(
                        f"{rel(f)}:{nxt.lineno}: unreachable statement after return "
                        f"on line {stmt.lineno}"
                    )
                    break
    return len(files)


def _duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    counts = collections.Counter(k for k, _ in pairs)
    dupes = [k for k, n in counts.items() if n > 1]
    if dupes:
        raise ValueError(f"duplicate key(s): {', '.join(sorted(dupes))}")
    return dict(pairs)


def check_json(failures: list[str]) -> int:
    files = tracked("*.json")
    for f in files:
        text = f.read_text(encoding="utf-8")
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            failures.append(f"{rel(f)}:{exc.lineno}: does not parse: {exc.msg}")
            continue
        try:
            # Parses fine, but a duplicated block silently discards the earlier copy.
            json.loads(text, object_pairs_hook=_duplicate_keys)
        except ValueError as exc:
            failures.append(f"{rel(f)}: {exc}")
    return len(files)


def check_makefile(failures: list[str]) -> int:
    mk = REPO_ROOT / "Makefile"
    if not mk.exists():
        return 0
    lines = mk.read_text(encoding="utf-8").splitlines()
    targets: dict[str, list[int]] = collections.defaultdict(list)
    phony = 0
    for i, line in enumerate(lines, 1):
        if line.startswith(".PHONY:"):
            phony += 1
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+):(?!=)", line)
        if m:
            targets[m.group(1)].append(i)
    if phony > 1:
        failures.append(f"Makefile: {phony} .PHONY lines; expected 1")
    for name, at in sorted(targets.items()):
        if len(at) > 1:
            failures.append(f"Makefile: target '{name}' declared {len(at)}x at lines {at}")
    return 1


def main() -> int:
    failures: list[str] = []
    counts = {
        "python parses": check_python_compiles(failures),
        "python has no shadowed top-level defs": check_python_no_shadowed_defs(failures),
        "python has no code after return": check_python_no_code_after_return(failures),
        "json parses and has no duplicate keys": check_json(failures),
        "makefile has no duplicate targets": check_makefile(failures),
    }
    for label, n in counts.items():
        print(f"  checked {n:>4} file(s): {label}")
    if failures:
        print(f"\n{len(failures)} merge-duplication defect(s):\n", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print("\nOK no merge-duplication defects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
