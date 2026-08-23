# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the fail-closed Python >= 3.14 floor gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "check_python_floor.py"
SPEC = importlib.util.spec_from_file_location("check_python_floor", MODULE_PATH)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules["check_python_floor"] = gate
SPEC.loader.exec_module(gate)


def _write(tmp_path: Path, body: str) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(body, encoding="utf-8")
    return pyproject


def test_clean_314_floor_passes(tmp_path: Path) -> None:
    pyproject = _write(
        tmp_path,
        '[project]\nrequires-python = ">=3.14"\n'
        '[tool.ruff]\ntarget-version = "py314"\n'
        '[tool.mypy]\npython_version = "3.14"\n',
    )
    assert gate.check(pyproject) == []


def test_requires_python_312_fails(tmp_path: Path) -> None:
    pyproject = _write(tmp_path, '[project]\nrequires-python = ">=3.12"\n')
    violations = gate.check(pyproject)
    assert violations and "requires-python" in violations[0]


def test_requires_python_313_fails(tmp_path: Path) -> None:
    pyproject = _write(tmp_path, '[project]\nrequires-python = ">=3.13"\n')
    assert gate.check(pyproject)


def test_upper_bound_only_has_no_floor_and_fails(tmp_path: Path) -> None:
    pyproject = _write(tmp_path, '[project]\nrequires-python = "<4"\n')
    violations = gate.check(pyproject)
    assert any("no lower bound" in v for v in violations)


def test_missing_requires_python_fails(tmp_path: Path) -> None:
    pyproject = _write(tmp_path, '[project]\nname = "x"\n')
    violations = gate.check(pyproject)
    assert any("unset" in v for v in violations)


def test_ruff_target_py313_fails_even_with_314_floor(tmp_path: Path) -> None:
    pyproject = _write(
        tmp_path,
        '[project]\nrequires-python = ">=3.14"\n[tool.ruff]\ntarget-version = "py313"\n',
    )
    violations = gate.check(pyproject)
    assert violations and "target-version" in violations[0]


def test_mypy_312_fails(tmp_path: Path) -> None:
    pyproject = _write(
        tmp_path,
        '[project]\nrequires-python = ">=3.14"\n[tool.mypy]\npython_version = "3.12"\n',
    )
    violations = gate.check(pyproject)
    assert any("python_version" in v for v in violations)


def test_floor_above_314_passes(tmp_path: Path) -> None:
    pyproject = _write(tmp_path, '[project]\nrequires-python = ">=3.15"\n')
    assert gate.check(pyproject) == []
