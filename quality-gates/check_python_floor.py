#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Enforce the platform Python floor: >= 3.14 everywhere, no fallback.

Python 3.12 (and 3.13) are banned across the BreachSAFE Quantum Platform
(Paul, 2026-08-23: "Python 3.14 minimum everywhere, make that hard"). This gate
runs in the reusable ``quality-gates-python`` workflow so every consumer that
adopts it fails CI the moment it declares a floor below 3.14. Advisory rules do
not hold a line under pressure; this one is fail-closed.

It reads the consumer's ``pyproject.toml`` and rejects any of:

* ``[project] requires-python`` whose lowest satisfying version is < 3.14
  (``>=3.12``, ``>=3.13``, ``~=3.12``, ``==3.12.*``, or no lower bound at all).
* ``[tool.ruff] target-version`` below ``py314`` (e.g. ``py312``/``py313``).
* ``[tool.mypy] python_version`` below ``3.14``.

Each violation prints one line naming the key, the offending value, and the fix.
Exit 0 = clean, exit 1 = at least one violation, exit 2 = usage/parse error.

Usage:
    python3 check_python_floor.py --pyproject pyproject.toml
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

FLOOR: tuple[int, int] = (3, 14)
FLOOR_STR = f"{FLOOR[0]}.{FLOOR[1]}"

# Lower-bound operators in a PEP 440 requires-python specifier. `<`/`<=`/`!=`
# never RAISE the floor, so a specifier that carries only those (or nothing)
# leaves < 3.14 reachable and must fail.
_LOWER_BOUND_RE = re.compile(r"(>=|~=|==|>)\s*(\d+)\.(\d+)")


def _min_allowed(requires_python: str) -> tuple[int, int] | None:
    """Lowest (major, minor) the specifier admits, or None if it allows anything old."""
    bounds = [
        (int(major), int(minor))
        for _op, major, minor in _LOWER_BOUND_RE.findall(requires_python)
    ]
    # The effective floor is the highest lower-bound clause present.
    return max(bounds) if bounds else None


def _ruff_target_below(target: str) -> bool:
    match = re.fullmatch(r"py(\d)(\d+)", target.strip())
    if not match:
        return False  # unknown format: not our call to fail on
    return (int(match.group(1)), int(match.group(2))) < FLOOR


def _mypy_version_below(version: str) -> bool:
    match = re.fullmatch(r"(\d+)\.(\d+)", version.strip())
    if not match:
        return False
    return (int(match.group(1)), int(match.group(2))) < FLOOR


def check(pyproject: Path) -> list[str]:
    """Return a list of violation messages (empty == clean)."""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    violations: list[str] = []

    requires_python = data.get("project", {}).get("requires-python")
    if requires_python is None:
        violations.append(
            "[project] requires-python is unset — it must pin '>=3.14' (no fallback)."
        )
    else:
        low = _min_allowed(requires_python)
        if low is None:
            violations.append(
                f"[project] requires-python = {requires_python!r} has no lower bound; "
                f"it must pin '>=3.14'."
            )
        elif low < FLOOR:
            violations.append(
                f"[project] requires-python = {requires_python!r} admits Python "
                f"{low[0]}.{low[1]} (< {FLOOR_STR}); raise the floor to '>=3.14'."
            )

    tool = data.get("tool", {})
    ruff_target = tool.get("ruff", {}).get("target-version")
    if isinstance(ruff_target, str) and _ruff_target_below(ruff_target):
        violations.append(
            f"[tool.ruff] target-version = {ruff_target!r} is below 'py314'; set it to 'py314'."
        )

    mypy_version = tool.get("mypy", {}).get("python_version")
    if isinstance(mypy_version, str) and _mypy_version_below(mypy_version):
        violations.append(
            f"[tool.mypy] python_version = {mypy_version!r} is below {FLOOR_STR!r}; "
            f"set it to '3.14'."
        )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml", type=Path)
    args = parser.parse_args()

    if not args.pyproject.is_file():
        print(f"check_python_floor: no such file: {args.pyproject}", file=sys.stderr)
        return 2

    violations = check(args.pyproject)
    if violations:
        print(f"Python floor gate FAILED ({args.pyproject}) — 3.14 is the platform minimum:")
        for message in violations:
            print(f"  - {message}")
        return 1

    print(f"Python floor gate OK: {args.pyproject} pins >= {FLOOR_STR}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
