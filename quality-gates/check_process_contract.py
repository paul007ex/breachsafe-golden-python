#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Fail when a repository does not carry the BreachSAFE process contract.

The contract (breachsafe-common#57, golden-python#19) splits four concerns across four surfaces:

    CLAUDE.md    repository policy, architecture, licensing, scope, instruction hierarchy
    AGENTS.md    compact agent card: the numbered loop, commands, gate bars, handoff
    skills       task procedures
    CI gates     machine enforcement

This script is the machine enforcement for the first two. It checks structure, not prose: that
both files exist, that they point at each other, that the loop is present and numbered 1..10
with no gaps, and that the NOT RUN rule is stated.

Deliberately NOT checked: wording, ordering of the steps, or length. A repository may phrase its
loop for its own domain. What it may not do is ship an agent card with a loop that skips a number,
because an agent reporting "7/10" against a nine-step list is reporting nothing.

Exit codes:
    0  contract satisfied
    1  contract violated (details on stdout)
    2  usage error, e.g. the target directory does not exist

Note the 2-vs-1 split: a missing target directory is an operator error, not a policy violation,
and must not be reported as a repository failing the contract. See golden-python#18 for the same
distinction in check_python_floor.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_STEPS = 10
NOT_RUN_PATTERN = re.compile(r"NOT[ _]RUN", re.IGNORECASE)
# A numbered step is a leading "N." in prose or a "| N |" cell in a table. Both are in use.
STEP_PATTERNS = (
    re.compile(r"^\s*(\d{1,2})\.\s+\S", re.MULTILINE),
    re.compile(r"^\s*\|\s*(\d{1,2})\s*\|", re.MULTILINE),
)


def _numbered_steps(text: str) -> set[int]:
    """Every distinct step number the document declares, by either supported notation."""
    found: set[int] = set()
    for pattern in STEP_PATTERNS:
        found |= {int(m) for m in pattern.findall(text)}
    return {n for n in found if 1 <= n <= REQUIRED_STEPS}


def check(root: Path) -> list[str]:
    """Return one message per violation; empty means the contract is satisfied."""
    problems: list[str] = []
    claude, agents = root / "CLAUDE.md", root / "AGENTS.md"

    for path in (claude, agents):
        if not path.is_file():
            problems.append(f"{path.name} is missing; the process contract requires both files")

    if problems:
        return problems

    claude_text = claude.read_text(encoding="utf-8")
    agents_text = agents.read_text(encoding="utf-8")

    if "AGENTS.md" not in claude_text:
        problems.append("CLAUDE.md does not reference AGENTS.md; the two must point at each other")
    if "CLAUDE.md" not in agents_text:
        problems.append("AGENTS.md does not reference CLAUDE.md; the two must point at each other")

    steps = _numbered_steps(agents_text)
    missing = sorted(set(range(1, REQUIRED_STEPS + 1)) - steps)
    if missing:
        problems.append(
            f"AGENTS.md loop is not numbered 1..{REQUIRED_STEPS}; missing {missing}. "
            "An agent reporting 'N/10' against an incomplete list is reporting nothing."
        )

    if not NOT_RUN_PATTERN.search(agents_text):
        problems.append(
            "AGENTS.md does not state the NOT RUN rule. A skipped step must be reported as "
            "NOT RUN with a reason; a green command that did not execute the required scope is "
            "not evidence."
        )

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to check (default: current directory).",
    )
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"process contract: {args.root} is not a directory", file=sys.stderr)
        return 2

    problems = check(args.root)
    print("Process contract (CLAUDE.md + AGENTS.md + numbered loop + NOT RUN rule)")
    print(f"Root: {args.root}")
    if problems:
        for problem in problems:
            print(f"  FAIL {problem}")
        print(f"Result: FAIL ({len(problems)} problem(s))")
        return 1
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
