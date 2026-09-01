# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the dependency-free CLAUDE.md drift gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "check_claude_md.py"
SPEC = importlib.util.spec_from_file_location("check_claude_md", MODULE_PATH)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules["check_claude_md"] = gate
SPEC.loader.exec_module(gate)

# A card that satisfies every requirement: numbered TOC, Instruction hierarchy section, and a
# reference to the platform master inside that section.
GOOD_CARD = """\
# CLAUDE.md — example

## Contents

1. [Instruction hierarchy](#instruction-hierarchy)
2. [Repository specifics](#repository-specifics)

## Instruction hierarchy

1. Platform `~/claude/CLAUDE.md` (auto-loads by walking up) is the single master.
2. This file: repo-specific refinements only.

## Repository specifics

Repo notes here.
"""


def _write_card(root: Path, text: str) -> None:
    (root / "CLAUDE.md").write_text(text, encoding="utf-8")


def test_find_instruction_hierarchy_returns_line_and_scoped_body() -> None:
    line, body = gate.find_instruction_hierarchy(GOOD_CARD)
    assert line == 8  # the '## Instruction hierarchy' heading line
    assert "single master" in body
    assert "Repository specifics" not in body  # the next sibling heading closes the section


def test_references_master_accepts_both_documented_forms() -> None:
    assert gate.references_master("see `~/claude/CLAUDE.md` first")
    assert gate.references_master("resolves from $BQP_ROOT/CLAUDE.md")
    assert not gate.references_master("see the platform policy file")


def test_count_toc_entries_counts_only_numbered_anchor_links() -> None:
    assert gate.count_toc_entries(GOOD_CARD) == 2
    assert gate.count_toc_entries("1. plain list item\n2. another") == 0


def test_check_passes_on_a_well_formed_card(tmp_path: Path) -> None:
    _write_card(tmp_path, GOOD_CARD)
    assert gate.check(tmp_path) == []


def test_check_flags_missing_card(tmp_path: Path) -> None:
    problems = gate.check(tmp_path)
    assert len(problems) == 1
    assert "no root CLAUDE.md" in problems[0]


def test_check_flags_missing_hierarchy_and_toc(tmp_path: Path) -> None:
    _write_card(tmp_path, "# CLAUDE.md\n\nSome prose with no sections at all.\n")
    problems = gate.check(tmp_path)
    assert len(problems) == 2
    assert any("Instruction hierarchy" in p for p in problems)
    assert any("numbered table of contents" in p for p in problems)


def test_check_flags_hierarchy_that_omits_the_master(tmp_path: Path) -> None:
    card = GOOD_CARD.replace(
        "1. Platform `~/claude/CLAUDE.md` (auto-loads by walking up) is the single master.",
        "1. Read the platform policy, then this file.",
    )
    _write_card(tmp_path, card)
    problems = gate.check(tmp_path)
    assert len(problems) == 1
    assert "does not reference the platform master" in problems[0]
    assert f"{tmp_path / 'CLAUDE.md'}:8:" in problems[0]


def test_main_exits_1_on_bad_card_and_0_on_good(tmp_path: Path) -> None:
    _write_card(tmp_path, "# CLAUDE.md\n\nnothing here.\n")
    assert gate.main(["--root", str(tmp_path)]) == 1

    _write_card(tmp_path, GOOD_CARD)
    assert gate.main(["--root", str(tmp_path)]) == 0


def test_main_usage_error_exits_2_on_missing_dir(tmp_path: Path) -> None:
    assert gate.main(["--root", str(tmp_path / "does-not-exist")]) == 2
