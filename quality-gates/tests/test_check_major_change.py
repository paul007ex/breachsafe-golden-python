# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for decision-record provenance in the change-governance gate (#36).

The defect: any `docs/decisions/NNNN-*.md` appearing in the diff satisfied the
gate, whether the change wrote it or merely touched it. A change that edits an
unrelated pre-existing record cleared the gate, and the PASS message named that
record as though the change had written it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "check_major_change.py"
SPEC = importlib.util.spec_from_file_location("check_major_change", MODULE_PATH)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules["check_major_change"] = gate
SPEC.loader.exec_module(gate)


VALID_RECORD = """\
# A decision

## Options

| | Option | For | Against | Score |
|---|---|---|---|---|
| **A** | Do it | works | costs | 9/10 |
| **B** | Do not | free | leaves the defect | 4/10 |
| **C** | Half | small | splits one decision in two | 3/10 |

## Steelman

The strongest case for B.

## Pressure-test evidence

Measured, and here is the measurement.
"""


def _record(tmp_path: Path, name: str) -> Path:
    path = tmp_path / "docs" / "decisions" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(VALID_RECORD, encoding="utf-8")
    return path


def test_added_record_wins_over_an_unrelated_modified_one(tmp_path: Path) -> None:
    """The record the change ADDED is the one reported, not a touched stranger."""
    _record(tmp_path, "0001-unrelated.md")
    _record(tmp_path, "0002-written-for-this-change.md")

    found = gate.discover_records(
        ["docs/decisions/0001-unrelated.md", "docs/decisions/0002-written-for-this-change.md"],
        [],
        tmp_path,
        statuses={
            "docs/decisions/0001-unrelated.md": "M",
            "docs/decisions/0002-written-for-this-change.md": "A",
        },
    )

    assert found, "expected at least one candidate"
    first_path, first_provenance = found[0]
    assert first_path.name == "0002-written-for-this-change.md"
    assert first_provenance == "added"


def test_only_a_modified_record_is_reported_as_pre_existing(tmp_path: Path) -> None:
    """A touched stranger still passes, and is labelled so a reader can tell."""
    _record(tmp_path, "0001-unrelated.md")

    found = gate.discover_records(
        ["docs/decisions/0001-unrelated.md"],
        [],
        tmp_path,
        statuses={"docs/decisions/0001-unrelated.md": "M"},
    )

    assert [p for _, p in found] == ["pre-existing"]


def test_provenance_is_unknown_without_status_information(tmp_path: Path) -> None:
    """--numstat-file mode carries no status, so provenance is not guessed."""
    _record(tmp_path, "0001-unrelated.md")

    found = gate.discover_records(
        ["docs/decisions/0001-unrelated.md"],
        [],
        tmp_path,
        statuses=None,
    )

    assert [p for _, p in found] == ["unknown"]


def test_explicit_record_is_labelled_explicit(tmp_path: Path) -> None:
    """--decision-record is an operator assertion, not a diff observation."""
    path = _record(tmp_path, "0003-passed-by-hand.md")

    found = gate.discover_records([], [str(path)], tmp_path, statuses=None)

    assert [p for _, p in found] == ["explicit"]


def test_parse_name_status_reads_git_output() -> None:
    """Rename entries report the destination path, matching numstat handling."""
    out = (
        "A\tdocs/decisions/0002-new.md\n"
        "M\tREUSE.toml\n"
        "D\tscaffold-do-not-use/copier.yml\n"
        "R100\tdocs/old.md\tdocs/new.md\n"
    )

    statuses = gate.parse_name_status(out)

    assert statuses["docs/decisions/0002-new.md"] == "A"
    assert statuses["REUSE.toml"] == "M"
    assert statuses["scaffold-do-not-use/copier.yml"] == "D"
    assert statuses["docs/new.md"] == "R"


def test_added_record_reported_in_pass_message(tmp_path: Path, capsys) -> None:
    """End to end: the PASS line names the added record and says it was added."""
    _record(tmp_path, "0001-unrelated.md")
    _record(tmp_path, "0002-written-for-this-change.md")
    numstat = tmp_path / "numstat.txt"
    numstat.write_text(
        "300\t0\tdocs/decisions/0002-written-for-this-change.md\n"
        "4\t0\tdocs/decisions/0001-unrelated.md\n",
        encoding="utf-8",
    )
    name_status = tmp_path / "name-status.txt"
    name_status.write_text(
        "A\tdocs/decisions/0002-written-for-this-change.md\n"
        "M\tdocs/decisions/0001-unrelated.md\n",
        encoding="utf-8",
    )

    rc = gate.main(
        [
            "--numstat-file", str(numstat),
            "--name-status-file", str(name_status),
            "--changed-root", str(tmp_path),
            "--loc-threshold", "10",
            "--files-threshold", "1",
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "0002-written-for-this-change.md" in out
    assert "added by this change" in out
    assert "0001-unrelated.md" not in out


def test_pre_existing_only_passes_but_warns(tmp_path: Path, capsys) -> None:
    """The false-pass case: it still passes, and the output no longer misleads."""
    _record(tmp_path, "0001-unrelated.md")
    numstat = tmp_path / "numstat.txt"
    numstat.write_text("4\t0\tdocs/decisions/0001-unrelated.md\n", encoding="utf-8")
    name_status = tmp_path / "name-status.txt"
    name_status.write_text("M\tdocs/decisions/0001-unrelated.md\n", encoding="utf-8")

    rc = gate.main(
        [
            "--numstat-file", str(numstat),
            "--name-status-file", str(name_status),
            "--changed-root", str(tmp_path),
            "--loc-threshold", "1",
            "--files-threshold", "1",
        ]
    )

    assert rc == 0
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "pre-existing" in combined
    assert "WARNING" in combined
