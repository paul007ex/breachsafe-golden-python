#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Fail when a repository's root CLAUDE.md drifts from the 1-master + thin-card model.

BQP runs one master policy file (`~/claude/CLAUDE.md`, auto-loaded as Claude Code walks up
from the working directory) and one thin per-repo `CLAUDE.md` that only refines it. A repo
card that restates shared rules instead of linking to the master is how the two rot out of
sync: the master moves, the copy does not, and an agent reads a stale rule as current.

This gate checks the repo card's structure, not its prose. Three requirements, each with a
`path:line`-style message when it fails:

    (a) a root CLAUDE.md exists;
    (b) it has an "Instruction hierarchy" section, and that section names the platform master
        (`~/claude/CLAUDE.md`, or the `$BQP_ROOT/CLAUDE.md` form) so an agent knows which file
        wins for cross-repo policy;
    (c) it opens with a numbered table of contents linking to its headings (platform §9).

Deliberately NOT checked: wording, section order, or how many refinements the card carries. A
repo phrases its own policy; what it may not do is drop the pointer to the master or ship a
Markdown file with no navigable contents.

Warn-first: this gate is opt-in in CI (the `claude_md_check` input defaults to false) so a repo
adopts it when its card is ready, without a surprise red gate on day one.

Exit codes:
    0  the card satisfies the contract
    1  the card violates it (one message per problem on stdout)
    2  usage error, e.g. the target directory does not exist

Note the 2-vs-1 split: a missing target directory is an operator error, not a repository
failing the contract, and must not be reported as one. Same distinction as
check_process_contract.py and check_python_floor.py.

Usage:
    python3 check_claude_md.py --root .
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# A Markdown ATX heading: one to six '#', then the title text.
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

# The platform master, in either documented form. `~/claude/CLAUDE.md` is the path on Paul's
# machine; `$BQP_ROOT/CLAUDE.md` is the portable form the master file uses for itself. Backticks
# around either are fine because the search is a substring match.
MASTER_RE = re.compile(r"~/claude/CLAUDE\.md|\$BQP_ROOT/CLAUDE\.md")

# A numbered table-of-contents entry: `1. [Section](#anchor)`. Two or more of these is a TOC.
TOC_ENTRY_RE = re.compile(r"^\s*\d+\.\s+\[[^\]]+\]\(#[^)]+\)\s*$", re.MULTILINE)

_MIN_TOC_ENTRIES = 2


def find_instruction_hierarchy(text: str) -> tuple[int, str] | None:
    """Return (1-based heading line, section body) for the Instruction hierarchy section.

    The section runs from its heading to the next heading of the same or a higher level, so a
    nested subsection stays part of it. Returns None when no such heading exists.
    """
    lines = text.splitlines()
    start: int | None = None
    start_level = 0
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if not match:
            continue
        level, title = len(match.group(1)), match.group(2)
        if start is None:
            if "instruction hierarchy" in title.lower():
                start, start_level = index, level
            continue
        if level <= start_level:  # a sibling or ancestor heading closes the section
            return start + 1, "\n".join(lines[start:index])
    if start is None:
        return None
    return start + 1, "\n".join(lines[start:])


def references_master(section_body: str) -> bool:
    """True when the section names the platform master file in a recognised form."""
    return MASTER_RE.search(section_body) is not None


def count_toc_entries(text: str) -> int:
    """Number of numbered TOC entries (`N. [text](#anchor)`) anywhere in the document."""
    return len(TOC_ENTRY_RE.findall(text))


def check(root: Path) -> list[str]:
    """Return one message per violation; an empty list means the card satisfies the contract."""
    card = root / "CLAUDE.md"
    if not card.is_file():
        return [f"{card}: no root CLAUDE.md; the per-repo card is required by the 1-master model"]

    text = card.read_text(encoding="utf-8")
    problems: list[str] = []

    section = find_instruction_hierarchy(text)
    if section is None:
        problems.append(
            f"{card}:1: no 'Instruction hierarchy' section; add one that names the platform "
            "master (~/claude/CLAUDE.md) so an agent knows which file wins for cross-repo policy"
        )
    else:
        heading_line, body = section
        if not references_master(body):
            problems.append(
                f"{card}:{heading_line}: the Instruction hierarchy section does not reference "
                "the platform master ~/claude/CLAUDE.md; name it as the master so shared rules "
                "are linked, not restated"
            )

    if count_toc_entries(text) < _MIN_TOC_ENTRIES:
        problems.append(
            f"{card}:1: no numbered table of contents linking to headings "
            "(N. [Section](#anchor)); platform §9 requires every Markdown file to open with one"
        )

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root whose CLAUDE.md is checked (default: current directory).",
    )
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(f"claude-md gate: {args.root} is not a directory", file=sys.stderr)
        return 2

    problems = check(args.root)
    print("CLAUDE.md gate (root card + Instruction hierarchy naming the master + numbered TOC)")
    print(f"Root: {args.root}")
    if problems:
        for problem in problems:
            print(f"  FAIL {problem}")
        print(f"Result: FAIL ({len(problems)} problem(s), exit 1)")
        return 1
    print("Result: PASS (exit 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
