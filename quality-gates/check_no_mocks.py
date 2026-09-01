#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Fail if checked-in tests reach for a mock/monkeypatch instead of the real thing.

The BreachSAFE default is real: real CLI, real subprocess, a real call, a real (pinned)
oracle. A test double hides the exact wiring the test exists to prove, and a green suite
built on doubles is the "N passed, bugs shipped" failure mode this repo family exists to
catch. `pytest`'s `monkeypatch` and `unittest.mock` are the usual shortcuts, so this gate
flags them by name.

A genuinely-unavoidable double (a paid external API, a destructive operation) is allowed
ONLY with an explicit ``# real-double: <reason>`` marker on the offending line, which forces
the author to justify it and a reviewer to see it. Anything else is a finding.

Related: anti-pattern-catalog #147 (never fake wiring without a paired real-path test) and
`breachsafe-test-harness` (pinned live oracle, real vectors, "green != tested").

Usage:
    python3 check_no_mocks.py --tests-dir tests
    python3 check_no_mocks.py --tests-dir tests --tests-dir integration
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Identifiers that mean "a test double is in play." Word-boundary matched so a substring
# inside an unrelated name (e.g. `mocker_config`) does not trip the gate on its own.
_BANNED = (
    r"\bmonkeypatch\b",
    r"\bunittest\.mock\b",
    r"\bfrom\s+mock\b",
    r"\bimport\s+mock\b",
    r"\bMagicMock\b",
    r"\bAsyncMock\b",
    r"\bMock\s*\(",
    r"@(?:mock\.)?patch\b",
    r"\bmocker\b",
)
_PATTERN = re.compile("|".join(_BANNED))
_ESCAPE = "# real-double:"


def scan(dirs: list[Path]) -> list[tuple[Path, int, str]]:
    """Return (file, line, text) for every banned double outside a full-line comment."""
    findings: list[tuple[Path, int, str]] = []
    for d in dirs:
        for f in sorted(d.rglob("*.py")):
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue  # a full-line comment is prose, not usage
                if _PATTERN.search(line) and _ESCAPE not in line:
                    findings.append((f, n, stripped[:100]))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tests-dir",
        action="append",
        default=None,
        help="test directory to scan (repeatable); defaults to 'tests'",
    )
    args = parser.parse_args()
    dirs = [Path(x) for x in (args.tests_dir or ["tests"]) if Path(x).is_dir()]
    if not dirs:
        print("no test directories to scan; nothing to check", file=sys.stderr)
        return 0
    findings = scan(dirs)
    if not findings:
        print(f"PASS: no mock/monkeypatch in {', '.join(str(d) for d in dirs)}")
        return 0
    print(
        "Mock/monkeypatch in tests. The default is real (real CLI, real call, real oracle); "
        "add `# real-double: <reason>` on the line only for an unavoidable double, paired with "
        "a real-path test (catalog #147):",
        file=sys.stderr,
    )
    for f, n, text in findings:
        print(f"  {f}:{n}: {text}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
