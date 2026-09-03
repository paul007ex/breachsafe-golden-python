#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Fail a pull-request diff on a small set of high-signal anti-patterns.

This is deliberately a diff gate, not a replacement for the anti-pattern
catalog or a general-purpose linter.  Only added lines in source/config files
are inspected.  A finding may be accepted in the PR body with:

    ANTIPATTERN ACCEPTED: <rule-id>, because <reason> (#123)

The issue reference is mandatory so an exception cannot silently become a
permanent waiver.  The command prints the categories walked and its exit code
to make the review trail copyable into a PR or job summary.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from diff_support import AddedLine, collect_diff, parse_added_lines as parse_diff_added_lines

SOURCE_SUFFIXES = {
    ".bash", ".go", ".js", ".jsx", ".py", ".pyi", ".rb", ".rs", ".sh",
    ".ts", ".tsx", ".yml", ".yaml",
}
TEST_PARTS = {"test", "tests", "spec", "specs"}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    category: str
    line: AddedLine
    explanation: str


RULES = (
    ("subprocess-shell-true", "subprocess discipline", re.compile(r"\bshell\s*=\s*True\b"), "shell=True makes argument handling depend on a shell"),
    ("os-system", "subprocess discipline", re.compile(r"\bos\.system\s*\("), "os.system has shell parsing and weak error handling"),
    ("production-assert", "unrecoverable aborts", re.compile(r"^\s*assert\b"), "assertions are removed with Python -O and are not input validation"),
    ("unsafe-eval", "unsafe boundary conversions", re.compile(r"\b(?:eval|exec)\s*\("), "eval/exec executes data as code"),
    ("test-skip", "test integrity", re.compile(r"(?:pytest\.mark\.(?:skip|xfail)|unittest\.skip(?:If|Unless)?|pytest\.skip\s*\()"), "skip/xfail suppresses or weakens executable coverage"),
    ("false-branch", "dead code", re.compile(r"^\s*if\s+False\s*:"), "an unconditional false branch is dead code"),
    ("swallowed-exception", "failure visibility", re.compile(r"^\s*except\s+(?:Exception|BaseException)\s*:\s*(?:pass|continue)\s*(?:#.*)?$"), "a broad exception is swallowed and failures become invisible"),
    ("secret-output", "logging discipline", re.compile(r"\b(?:print|pprint|logger?\.|logging\.)[^\n]*(?:password|passwd|secret|token|private[_-]?key)[^\n]*", re.IGNORECASE), "a likely secret is sent to output/logging"),
)

ACCEPTED_RE = re.compile(
    r"ANTIPATTERN ACCEPTED:\s*([^,\n]+),\s*because\s+(.+)", re.IGNORECASE
)
ISSUE_RE = re.compile(r"(?:#\d+|https?://github\.com/[^\s/]+/[^\s/]+/issues/\d+)")


def _is_test_path(path: str) -> bool:
    return bool(TEST_PARTS.intersection(Path(path).parts)) or Path(path).name.startswith("test_")


def parse_added_lines(diff: str) -> list[AddedLine]:
    """Parse unified diff hunks into added lines with their post-image number."""
    return parse_diff_added_lines(diff, SOURCE_SUFFIXES)


def findings(lines: list[AddedLine]) -> list[Finding]:
    found: list[Finding] = []
    for line in lines:
        # The detector's own source necessarily contains rule examples and
        # regexes that look like findings. Its unit tests exercise those
        # examples; scanning the implementation would make the shared gate
        # self-reject rather than review consumer code.
        if line.path == "quality-gates/check_antipattern_diff.py":
            continue
        for rule_id, category, pattern, explanation in RULES:
            if rule_id == "production-assert" and _is_test_path(line.path):
                continue
            if pattern.search(line.text):
                found.append(Finding(rule_id, category, line, explanation))
    return found


def accepted_rules(body: str) -> tuple[set[str], list[str]]:
    accepted: set[str] = set()
    errors: list[str] = []
    for raw in body.splitlines():
        if "ANTIPATTERN ACCEPTED:" not in raw.upper():
            continue
        match = ACCEPTED_RE.search(raw)
        if not match or not match.group(2).strip() or not ISSUE_RE.search(raw):
            errors.append("invalid exception: require '<rule-id>, because <reason> (#issue)'")
            continue
        accepted.add(match.group(1).strip().lower())
    return accepted, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--pr-body-file", type=Path)
    args = parser.parse_args(argv)
    body = os.environ.get("PR_BODY", "")
    if args.pr_body_file:
        try:
            body = args.pr_body_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot read PR body: {exc}", file=sys.stderr)
            return 2
    try:
        diff = collect_diff(args.base_ref, args.head)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    changed = parse_added_lines(diff)
    found = findings(changed)
    accepted, exception_errors = accepted_rules(body)
    print("Anti-pattern diff gate")
    print("Categories walked: " + ", ".join(dict.fromkeys(c for _, c, _, _ in RULES)))
    print(f"Command: git diff --unified=0 --no-ext-diff {args.base_ref}...{args.head}")
    print(f"Added source lines inspected: {len(changed)}")
    for error in exception_errors:
        print(f"FAIL: {error}", file=sys.stderr)
    unresolved = [f for f in found if f.rule_id.lower() not in accepted]
    for finding in found:
        status = "ACCEPTED" if finding.rule_id.lower() in accepted else "NEW"
        print(f"{status}: {finding.rule_id} [{finding.category}] {finding.line.path}:{finding.line.number} — {finding.explanation}")
    if exception_errors or unresolved:
        print("Result: FAIL (exit 1)", file=sys.stderr)
        return 1
    print("Result: PASS (exit 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
