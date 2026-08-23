# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the dependency-free anti-pattern diff gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "check_antipattern_diff.py"
SPEC = importlib.util.spec_from_file_location("check_antipattern_diff", MODULE_PATH)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules["check_antipattern_diff"] = gate
SPEC.loader.exec_module(gate)


def test_parse_added_lines_tracks_post_image_numbers() -> None:
    diff = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -2,0 +3,2 @@
+safe = 1
+safe += 1
"""
    assert gate.parse_added_lines(diff) == [
        gate.AddedLine("src/app.py", 3, "safe = 1"),
        gate.AddedLine("src/app.py", 4, "safe += 1"),
    ]


def test_test_assertions_are_not_production_assertions() -> None:
    lines = [
        gate.AddedLine("src/app.py", 4, "assert user_id"),
        gate.AddedLine("tests/test_app.py", 4, "assert result"),
    ]
    result = gate.findings(lines)
    assert [(item.rule_id, item.line.path) for item in result] == [
        ("production-assert", "src/app.py")
    ]


def test_all_high_signal_rules_are_detected() -> None:
    lines = [
        gate.AddedLine("src/app.py", 1, "subprocess.run(command, shell" + "=True)"),
        gate.AddedLine("src/app.py", 2, "os" + ".system(command)"),
        gate.AddedLine("src/app.py", 3, "ev" + "al(value)"),
        gate.AddedLine("tests/test_app.py", 4, "@pytest.mark." + "skip"),
        gate.AddedLine("src/app.py", 5, "if " + "False:"),
        gate.AddedLine("src/app.py", 6, "except Exception: " + "pass"),
        gate.AddedLine("src/app.py", 7, "print(secret_" + "token)"),
    ]
    assert {item.rule_id for item in gate.findings(lines)} == {
        "subprocess-shell-true", "os-system", "unsafe-eval", "test-skip",
        "false-branch", "swallowed-exception", "secret-output",
    }


def test_exception_requires_reason_and_issue_reference() -> None:
    accepted, errors = gate.accepted_rules(
        "ANTIPATTERN ACCEPTED: os-system, because legacy CLI (#14)\n"
        "ANTIPATTERN ACCEPTED: unsafe-eval, because no issue"
    )
    assert accepted == {"os-system"}
    assert len(errors) == 1


def test_markdown_and_deleted_lines_are_not_scanned() -> None:
    diff = """diff --git a/docs/example.md b/docs/example.md
--- a/docs/example.md
+++ b/docs/example.md
@@ -1 +1 @@
-old
+subprocess.run(command, shell=True)
diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1 @@
-subprocess.run(command, shell=True)
+safe_call(command)
"""
    assert gate.parse_added_lines(diff) == [
        gate.AddedLine("src/app.py", 1, "safe_call(command)")
    ]
