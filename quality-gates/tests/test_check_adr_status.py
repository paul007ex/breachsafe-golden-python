# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the dependency-free proposed-ADR diff gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "check_adr_status.py"
SPEC = importlib.util.spec_from_file_location("check_adr_status", MODULE_PATH)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules["check_adr_status"] = gate
SPEC.loader.exec_module(gate)


def _write_adr(decisions: Path, name: str, status: str) -> None:
    decisions.mkdir(parents=True, exist_ok=True)
    (decisions / name).write_text(
        f"# {name}\n\n- **Status:** {status}\n\n## Context\n\nbody\n",
        encoding="utf-8",
    )


def _diff(path: str, added: str) -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -0,0 +1 @@\n"
        f"+{added}\n"
    )


def test_find_adr_refs_covers_token_and_path_forms() -> None:
    text = "implements ADR-0007, ADR-BQP-002, ADR 13 and docs/decisions/0009-thing.md"
    assert gate.find_adr_refs(text) == ["0007", "BQP-002", "13", "0009-thing"]


def test_parse_status_takes_first_word_of_status_field() -> None:
    root = Path(__import__("tempfile").mkdtemp())
    _write_adr(root, "0001-x.md", "Proposed / exploratory — 2026-06-14")
    assert gate.parse_status(root / "0001-x.md") == "proposed"


def test_resolve_adr_matches_number_across_zero_pad_widths() -> None:
    decisions = Path(__import__("tempfile").mkdtemp()) / "docs" / "decisions"
    _write_adr(decisions, "0007-real.md", "Accepted")
    assert gate.resolve_adr("7", decisions) == decisions / "0007-real.md"
    assert gate.resolve_adr("0007", decisions) == decisions / "0007-real.md"
    assert gate.resolve_adr("42", decisions) is None


def test_proposed_adr_in_source_line_is_a_finding() -> None:
    root = Path(__import__("tempfile").mkdtemp())
    decisions = root / "docs" / "decisions"
    _write_adr(decisions, "0007-thing.md", "Proposed")
    lines = gate.parse_added_lines(_diff("src/app.py", "# implements ADR-0007"))
    findings, unresolved = gate.scan(lines, decisions)
    assert unresolved == []
    assert [(f.ref, f.status) for f in findings] == [("0007", "proposed")]


def test_accepted_adr_and_markdown_and_exempt_are_not_findings() -> None:
    root = Path(__import__("tempfile").mkdtemp())
    decisions = root / "docs" / "decisions"
    _write_adr(decisions, "0007-thing.md", "Proposed")
    _write_adr(decisions, "0008-done.md", "Accepted")

    # Accepted ADR -> no finding.
    accepted_lines = gate.parse_added_lines(_diff("src/app.py", "# see ADR-0008"))
    assert gate.scan(accepted_lines, decisions)[0] == []

    # Reference inside a markdown file -> not implementation, not scanned.
    md_lines = gate.parse_added_lines(_diff("docs/notes.md", "see ADR-0007"))
    assert md_lines == []

    # Proposed ADR but with the escape-hatch marker -> no finding.
    exempt = gate.parse_added_lines(
        _diff("src/app.py", "x = 1  # ADR-0007  # adr-exempt: spike, ratifying in #99")
    )
    assert gate.scan(exempt, decisions)[0] == []


def test_main_exits_1_on_proposed_and_0_when_accepted(tmp_path: Path) -> None:
    decisions = tmp_path / "docs" / "decisions"
    _write_adr(decisions, "0007-thing.md", "Proposed")
    _write_adr(decisions, "0008-done.md", "Accepted")

    proposed = tmp_path / "proposed.diff"
    proposed.write_text(_diff("src/app.py", "# implements ADR-0007"), encoding="utf-8")
    assert gate.main(["--diff-file", str(proposed), "--repo-root", str(tmp_path)]) == 1

    accepted = tmp_path / "accepted.diff"
    accepted.write_text(_diff("src/app.py", "# implements ADR-0008"), encoding="utf-8")
    assert gate.main(["--diff-file", str(accepted), "--repo-root", str(tmp_path)]) == 0


def test_main_usage_errors_exit_2(tmp_path: Path) -> None:
    # Neither diff source.
    assert gate.main(["--repo-root", str(tmp_path)]) == 2
    # Both diff sources.
    df = tmp_path / "d.diff"
    df.write_text("", encoding="utf-8")
    assert gate.main(["--base-ref", "main", "--diff-file", str(df)]) == 2
