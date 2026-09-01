#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Fail an implementation diff that cites an ADR still marked Proposed.

A decision record earns the right to be built once it is Accepted. Shipping code
that cites an ADR whose status is still `Proposed` (or `Draft`) reverses that
order: the implementation lands before the decision it claims to follow is
ratified, and the record can still change out from under the code. This gate is
the machine enforcement for that ordering (proposed-ADR gate, #4).

It is a diff gate, like check_antipattern_diff.py: only added lines in source and
config files are inspected, so an ADR file citing a sibling ADR, or a doc that
merely names one, never trips it. A reference is either an ``ADR-<id>`` token
(``ADR-0007``, ``ADR-BQP-002``, ``ADR 13``) or a decision-file path
(``docs/decisions/0007-thing.md``). Each reference is resolved to a file under the
repository's decisions directory, that file's ``Status:`` field is read, and a
reference to a Proposed/Draft ADR is a finding reported as ``path:line``.

Escape hatch: a genuinely-justified reference to a not-yet-Accepted ADR is allowed
ONLY with an explicit ``# adr-exempt: <reason>`` marker on the offending line,
which forces the author to justify it and a reviewer to see it.

Decisions directory: auto-detected as ``docs/decisions`` then ``docs/adr`` under
--repo-root, or set explicitly with --decisions-dir. An ADR reference that resolves
to no file is reported as a NOTE, not a failure: an unknown citation is a review
matter, and failing on it would turn every typo into a red gate. The hard failure
is strictly a resolved ADR whose status is not yet Accepted.

Two ways to feed the diff (mirrors check_major_change.py, so the gate is testable
without a live repo):
  * git mode (default): ``--base-ref origin/main [--head HEAD]`` runs
    ``git diff --unified=0 BASE...HEAD`` for you.
  * explicit mode: ``--diff-file diff.txt`` reads a pre-captured unified diff.

Exit codes:
    0  no implementation change cites a Proposed/Draft ADR
    1  at least one added source line cites a Proposed/Draft ADR (details on stderr)
    2  usage error, e.g. neither diff source given or the repo root does not exist
"""

from __future__ import annotations

import argparse
import re
import subprocess  # nosec B404 - fixed argv, no shell
import sys
from dataclasses import dataclass
from pathlib import Path

# Source/config suffixes count as "implementation"; markdown deliberately does not,
# so an ADR or doc that names another ADR is never treated as building it.
SOURCE_SUFFIXES = {
    ".bash", ".go", ".js", ".jsx", ".py", ".pyi", ".rb", ".rs", ".sh",
    ".ts", ".tsx", ".toml", ".cfg", ".ini", ".yml", ".yaml",
}

# Directories, relative to --repo-root, that hold decision records, in preference order.
DEFAULT_DECISIONS_DIRS = ("docs/decisions", "docs/adr")

# A status is blocking when the decision it records is not yet ratified. Scope is
# the not-yet-Accepted states; a Superseded/Deprecated/Rejected ADR is a review
# matter, not this gate's failure.
BLOCKING_STATUSES = {"proposed", "draft"}

_ESCAPE = "# adr-exempt:"

# `ADR-0007`, `ADR-BQP-002`, `ADR 13`, `ADR-013`. Captures the id portion.
ADR_TOKEN_RE = re.compile(r"\bADR[-\s]?((?:[A-Za-z]+-)*\d+)\b")
# `docs/decisions/0007-thing.md` or `docs/adr/0007-thing.md`. Captures the file stem.
ADR_PATH_RE = re.compile(r"docs/(?:decisions|adr)/([0-9A-Za-z][-_0-9A-Za-z]*)\.md")
# `- **Status:** Proposed — 2026-06-14`, `Status: Accepted`, `**Status:** Draft`.
STATUS_RE = re.compile(
    r"^\s*(?:[-*]\s*)?\**\s*status\**\s*[:|]\s*\**\s*([A-Za-z][A-Za-z/]*)",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class AddedLine:
    path: str
    number: int
    text: str


@dataclass(frozen=True)
class Finding:
    ref: str
    adr_path: Path
    status: str
    line: AddedLine


def parse_added_lines(diff: str) -> list[AddedLine]:
    """Parse unified diff hunks into added source lines with their post-image number."""
    lines: list[AddedLine] = []
    path: str | None = None
    new_number = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            path = raw[6:]
            continue
        match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", raw)
        if match:
            new_number = int(match.group(1))
            continue
        if path is None or raw.startswith(("--- ", "diff ", "index ")):
            continue
        if raw.startswith("+"):
            if Path(path).suffix.lower() in SOURCE_SUFFIXES:
                lines.append(AddedLine(path, new_number, raw[1:]))
            new_number += 1
        elif raw.startswith((" ", "-")):
            if not raw.startswith("-"):
                new_number += 1
    return lines


def find_adr_refs(text: str) -> list[str]:
    """Return every ADR reference in one line: id tokens and decision-file stems."""
    refs: list[str] = []
    for match in ADR_TOKEN_RE.finditer(text):
        refs.append(match.group(1))
    for match in ADR_PATH_RE.finditer(text):
        refs.append(match.group(1))
    # de-dup, preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for ref in refs:
        key = ref.lower()
        if key not in seen:
            seen.add(key)
            unique.append(ref)
    return unique


def resolve_adr(ref: str, decisions_dir: Path) -> Path | None:
    """Resolve an ADR reference to a decision file, or None if it matches nothing."""
    if not decisions_dir.is_dir():
        return None
    files = sorted(decisions_dir.glob("*.md"))
    ref_l = ref.lower()

    # Exact stem: `0007-thing` cited as a path, or a full filename stem.
    for path in files:
        if path.stem.lower() == ref_l:
            return path

    # Pure number `7` / `0007`: match `NNNN-*.md` across common zero-pad widths.
    if ref.isdigit():
        widths = {2, 3, 4, len(ref)}
        prefixes = {ref.zfill(width) + "-" for width in widths}
        for path in files:
            name = path.name.lower()
            if any(name.startswith(prefix) for prefix in prefixes):
                return path

    # Token as a dash-delimited segment of the stem: `BQP-002` in `adr-bqp-002-title`.
    for path in files:
        stem = path.stem.lower()
        if stem.startswith(ref_l + "-") or f"-{ref_l}-" in f"-{stem}-":
            return path
    return None


def parse_status(adr_path: Path) -> str | None:
    """Return the first word of the ADR's Status field, lowercased, or None."""
    try:
        text = adr_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = STATUS_RE.search(text)
    if not match:
        return None
    # `Proposed / exploratory` -> `proposed`; split on any non-letter.
    return re.split(r"[^A-Za-z]", match.group(1), maxsplit=1)[0].lower()


def scan(
    lines: list[AddedLine], decisions_dir: Path
) -> tuple[list[Finding], list[tuple[AddedLine, str]]]:
    """Return (blocking findings, unresolved references) for the added lines."""
    findings: list[Finding] = []
    unresolved: list[tuple[AddedLine, str]] = []
    for line in lines:
        if _ESCAPE in line.text:
            continue
        for ref in find_adr_refs(line.text):
            adr_path = resolve_adr(ref, decisions_dir)
            if adr_path is None:
                unresolved.append((line, ref))
                continue
            status = parse_status(adr_path)
            if status in BLOCKING_STATUSES:
                findings.append(Finding(ref, adr_path, status or "", line))
    return findings, unresolved


def collect_diff(base: str, head: str) -> str:
    argv = ["git", "diff", "--unified=0", "--no-ext-diff", f"{base}...{head}"]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=True)  # nosec B603
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise ValueError(f"git diff failed: {detail.strip()}") from exc
    return result.stdout


def find_decisions_dir(repo_root: Path, explicit: Path | None) -> Path:
    """Return the decisions directory to resolve against.

    An explicit --decisions-dir wins. Otherwise the first of docs/decisions,
    docs/adr that exists is used; if neither exists, docs/decisions is returned as
    the reported default so an unresolved reference has a name to print.
    """
    if explicit is not None:
        return explicit if explicit.is_absolute() else repo_root / explicit
    for candidate in DEFAULT_DECISIONS_DIRS:
        path = repo_root / candidate
        if path.is_dir():
            return path
    return repo_root / DEFAULT_DECISIONS_DIRS[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = parser.add_argument_group("diff source (choose git mode or --diff-file)")
    src.add_argument("--base-ref", help="base git ref for `git diff --unified=0 BASE...HEAD`")
    src.add_argument("--head", default="HEAD", help="head git ref (default: HEAD)")
    src.add_argument(
        "--diff-file",
        type=Path,
        help="read a pre-captured unified diff instead of running git",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="repository root ADR files are resolved under (default: .)",
    )
    parser.add_argument(
        "--decisions-dir",
        type=Path,
        help="decisions directory (default: auto-detect docs/decisions then docs/adr)",
    )
    args = parser.parse_args(argv)

    if not args.base_ref and not args.diff_file:
        print("error: provide --base-ref (git mode) or --diff-file", file=sys.stderr)
        return 2
    if args.base_ref and args.diff_file:
        print("error: use either --base-ref or --diff-file, not both", file=sys.stderr)
        return 2
    if not args.repo_root.is_dir():
        print(f"error: --repo-root {args.repo_root} is not a directory", file=sys.stderr)
        return 2

    if args.diff_file:
        if not args.diff_file.is_file():
            print(f"error: --diff-file {args.diff_file} not found", file=sys.stderr)
            return 2
        diff = args.diff_file.read_text(encoding="utf-8")
    else:
        try:
            diff = collect_diff(args.base_ref, args.head)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    decisions_dir = find_decisions_dir(args.repo_root, args.decisions_dir)
    lines = parse_added_lines(diff)
    findings, unresolved = scan(lines, decisions_dir)

    print("Proposed-ADR gate (implementation must cite an Accepted ADR)")
    print(f"Decisions directory: {decisions_dir}")
    print(f"Added source lines inspected: {len(lines)}")
    for line, ref in unresolved:
        print(
            f"NOTE: ADR '{ref}' at {line.path}:{line.number} resolved to no file "
            f"under {decisions_dir}; not treated as a failure."
        )
    if not findings:
        print("Result: PASS (exit 0)")
        return 0

    print(
        "Implementation cites an ADR that is not yet Accepted. Ratify the ADR first, or "
        "add `# adr-exempt: <reason>` on the line if the reference is deliberate:",
        file=sys.stderr,
    )
    for finding in findings:
        print(
            f"  {finding.line.path}:{finding.line.number}: cites ADR '{finding.ref}' "
            f"({finding.adr_path}) with status '{finding.status}' (not Accepted)",
            file=sys.stderr,
        )
    print(f"Result: FAIL ({len(findings)} reference(s), exit 1)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
