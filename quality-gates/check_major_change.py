#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Change-governance gate: block non-surgical PRs that lack a decision record.

Implements the §4.5 change-governance policy of the breachsafe-repo design
(docs/specs/2026-08-22-breachsafe-repo-design.md). Conventions are enforced,
not hoped for: a diff that is *not* a surgical fix must carry a decision record
that shows the change was reasoned about (an A/B/C scored comparison, a
steelman, and pressure-test evidence from an isolated /tmp run).

This is a sibling of the other `quality-gates/` scripts (check_size_policy.py,
check_no_skipped_tests.py): standalone, dependency-light, parameterized rather
than hardcoded to any one repo. It uses only the standard library
(`tomllib` ships in Python 3.11+; the breachsafe-container is 3.14).

Classification (a diff is "non-surgical" if ANY of):
  * added + removed LOC  > --loc-threshold   (default 150)
  * files changed        > --files-threshold (default 8)
  * --label == "major"   (case-insensitive; PR label)
  * any changed path matches one of --core-paths (glob, e.g. crypto/**)

If the diff is surgical -> exit 0 (nothing required).
If the diff is non-surgical -> a valid decision record is REQUIRED. A decision
record is a `docs/decisions/NNNN-*.md` file, discovered among the changed files
or supplied with --decision-record, that contains all three of:
    ## Options            (with a markdown table carrying a scored row per A/B/C)
    ## Steelman
    ## Pressure-test evidence
Exit 0 if a valid record is present, else exit 1 with a clear message.
Exit 2 on usage error.

Two ways to feed the diff:
  * git mode (default): `--base-ref origin/main [--head HEAD]` runs
    `git diff --numstat BASE...HEAD` for you.
  * explicit mode: `--numstat-file numstat.txt` reads pre-captured
    `git diff --numstat` output (added<TAB>removed<TAB>path per line), so the
    classifier is testable without a live repo.

Config: any CLI threshold / core-path may also come from a `.bqp-change-gate.toml`
at --config (default `.bqp-change-gate.toml` in the cwd), e.g.:

    loc_threshold = 200
    files_threshold = 10
    core_paths = ["src/*/crypto/**", "**/cbom*.py", ".github/workflows/release*.yml"]

Explicit CLI flags override the config file; the config overrides the built-ins.

Usage:
    python3 check_major_change.py --base-ref origin/main
    python3 check_major_change.py --base-ref main --head HEAD --label major \
        --core-paths "src/*/crypto/**" --core-paths "**/cbom*.py"
    python3 check_major_change.py --numstat-file /tmp/numstat.txt \
        --changed-root /path/to/checkout
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess  # nosec B404 - only invoked with a fixed argv (no shell)
import sys
from pathlib import Path

try:  # Python 3.11+ (breachsafe-container is 3.14)
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only on <3.11
    tomllib = None  # type: ignore[assignment]

DEFAULT_LOC_THRESHOLD = 150
DEFAULT_FILES_THRESHOLD = 8
DECISION_GLOB = "docs/decisions/[0-9]*-*.md"
DECISION_PATH_RE = re.compile(r"docs/decisions/\d+.*\.md$")

REQUIRED_HEADINGS = ("Options", "Steelman", "Pressure-test evidence")
OPTION_LABELS = ("A", "B", "C")


class UsageError(Exception):
    """Raised for a CLI/config misuse -> exit 2."""


# --------------------------------------------------------------------------- #
# Diff collection
# --------------------------------------------------------------------------- #
def parse_numstat(text: str) -> tuple[int, int, list[str]]:
    """Parse `git diff --numstat` output into (added, removed, changed_paths).

    Binary files appear as `-\t-\tpath` and contribute 0 LOC but 1 changed file.
    Renames appear as `added\tremoved\told => new` (or with `{a => b}` braces);
    we take the post-rename path for glob matching.
    """
    added_total = 0
    removed_total = 0
    paths: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_field, removed_field, path_field = parts[0], parts[1], "\t".join(parts[2:])
        if added_field != "-":
            added_total += int(added_field)
        if removed_field != "-":
            removed_total += int(removed_field)
        paths.append(_normalize_rename(path_field))
    return added_total, removed_total, paths


def _normalize_rename(path_field: str) -> str:
    """Return the post-rename path from a numstat path field."""
    # `{old => new}` inline form -> apply the substitution.
    brace = re.search(r"\{(.*?) => (.*?)\}", path_field)
    if brace:
        path_field = path_field.replace(brace.group(0), brace.group(2))
        return re.sub(r"//+", "/", path_field)
    # `old => new` whole-path form.
    if " => " in path_field:
        return path_field.split(" => ", 1)[1]
    return path_field


def git_numstat(base_ref: str, head: str) -> str:
    """Return `git diff --numstat BASE...HEAD` output, or raise UsageError."""
    argv = ["git", "diff", "--numstat", f"{base_ref}...{head}"]
    try:
        result = subprocess.run(  # nosec B603 - fixed argv, no shell, trusted refs
            argv,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - git always present in CI
        raise UsageError("git executable not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise UsageError(
            f"git diff failed ({' '.join(argv)}): {exc.stderr.strip() or exc}"
        ) from exc
    return result.stdout


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
def matched_core_paths(paths: list[str], core_paths: list[str]) -> list[str]:
    """Return changed paths that match any core-path glob."""
    hits: list[str] = []
    for path in paths:
        for pattern in core_paths:
            if fnmatch.fnmatch(path, pattern):
                hits.append(path)
                break
    return hits


def classify(
    added: int,
    removed: int,
    paths: list[str],
    *,
    loc_threshold: int,
    files_threshold: int,
    label: str | None,
    core_paths: list[str],
) -> list[str]:
    """Return the list of reasons the diff is non-surgical (empty == surgical)."""
    reasons: list[str] = []
    total_loc = added + removed
    if total_loc > loc_threshold:
        reasons.append(
            f"changed LOC {total_loc} (+{added}/-{removed}) exceeds threshold {loc_threshold}"
        )
    if len(paths) > files_threshold:
        reasons.append(
            f"files changed {len(paths)} exceeds threshold {files_threshold}"
        )
    if label and label.strip().lower() == "major":
        reasons.append("PR carries the 'major' label")
    core_hits = matched_core_paths(paths, core_paths)
    if core_hits:
        shown = ", ".join(core_hits[:5]) + ("..." if len(core_hits) > 5 else "")
        reasons.append(f"touches core path(s): {shown}")
    return reasons


# --------------------------------------------------------------------------- #
# Decision-record validation
# --------------------------------------------------------------------------- #
def _sections(text: str) -> dict[str, str]:
    """Split markdown into {heading_text: body} keyed by `## ` headings."""
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.*\S)\s*$", line)
        if heading:
            if current is not None:
                sections[current] = "\n".join(buffer)
            current = heading.group(1).strip()
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer)
    return sections


def _find_section(sections: dict[str, str], prefix: str) -> str | None:
    """Return the body of the first section whose heading starts with prefix."""
    lowered = prefix.lower()
    for heading, body in sections.items():
        if heading.lower().startswith(lowered):
            return body
    return None


def _options_table_ok(options_body: str) -> bool:
    """True iff the Options body has a markdown table with a scored A/B/C row."""
    table_rows = [ln for ln in options_body.splitlines() if ln.strip().startswith("|")]
    if not table_rows:
        return False
    found: set[str] = set()
    for row in table_rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        for label in OPTION_LABELS:
            # matches "A", "Option A", "A -- do nothing", "**A**", etc.
            if re.match(rf"^\**(option\s+)?{label}\b", first, re.IGNORECASE):
                # the row must also carry a numeric score somewhere in its cells
                if any(re.search(r"\d", cell) for cell in cells[1:]):
                    found.add(label)
    return set(OPTION_LABELS).issubset(found)


def validate_decision_record(path: Path) -> list[str]:
    """Return a list of problems with one decision record (empty == valid)."""
    problems: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read {path}: {exc}"]
    sections = _sections(text)
    for required in REQUIRED_HEADINGS:
        if _find_section(sections, required) is None:
            problems.append(f"missing required heading '## {required}'")
    options_body = _find_section(sections, "Options")
    if options_body is not None and not _options_table_ok(options_body):
        problems.append(
            "'## Options' lacks a markdown table with a scored (numeric) row for each of A/B/C"
        )
    return problems


def discover_records(
    paths: list[str],
    explicit: list[str],
    changed_root: Path,
) -> list[Path]:
    """Collect candidate decision-record paths from the diff and --decision-record."""
    candidates: list[Path] = []
    for path in paths:
        if DECISION_PATH_RE.search(path):
            candidates.append(changed_root / path)
    for extra in explicit:
        candidates.append(Path(extra))
    # de-dup while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


# --------------------------------------------------------------------------- #
# Config + CLI
# --------------------------------------------------------------------------- #
def load_config(config_path: Path) -> dict[str, object]:
    if not config_path.is_file():
        return {}
    if tomllib is None:  # pragma: no cover - <3.11 only
        print(
            f"warning: {config_path} present but tomllib unavailable; ignoring",
            file=sys.stderr,
        )
        return {}
    try:
        with config_path.open("rb") as handle:
            return tomllib.load(handle)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise UsageError(f"cannot parse {config_path}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = parser.add_argument_group("diff source (choose git mode or --numstat-file)")
    src.add_argument("--base-ref", help="base git ref for `git diff --numstat BASE...HEAD`")
    src.add_argument("--head", default="HEAD", help="head git ref (default: HEAD)")
    src.add_argument(
        "--numstat-file",
        type=Path,
        help="read pre-captured `git diff --numstat` output instead of running git",
    )
    parser.add_argument(
        "--changed-root",
        type=Path,
        default=Path("."),
        help="repo root that changed paths are relative to (default: .)",
    )
    parser.add_argument("--label", help="PR label; 'major' forces non-surgical")
    parser.add_argument(
        "--core-paths",
        action="append",
        default=[],
        metavar="GLOB",
        help="glob whose match forces non-surgical (repeatable)",
    )
    parser.add_argument(
        "--decision-record",
        action="append",
        default=[],
        metavar="PATH",
        help="extra decision-record path to consider (repeatable)",
    )
    parser.add_argument("--loc-threshold", type=int, help=f"default {DEFAULT_LOC_THRESHOLD}")
    parser.add_argument("--files-threshold", type=int, help=f"default {DEFAULT_FILES_THRESHOLD}")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(".bqp-change-gate.toml"),
        help="optional TOML config (default: .bqp-change-gate.toml)",
    )
    return parser


def resolve_settings(args: argparse.Namespace, config: dict[str, object]) -> tuple[int, int, list[str]]:
    """CLI flag > config file > built-in default."""
    loc_threshold = (
        args.loc_threshold
        if args.loc_threshold is not None
        else int(config.get("loc_threshold", DEFAULT_LOC_THRESHOLD))  # type: ignore[arg-type]
    )
    files_threshold = (
        args.files_threshold
        if args.files_threshold is not None
        else int(config.get("files_threshold", DEFAULT_FILES_THRESHOLD))  # type: ignore[arg-type]
    )
    core_paths = list(args.core_paths)
    if not core_paths:
        cfg_core = config.get("core_paths", [])
        if not isinstance(cfg_core, list):
            raise UsageError("config 'core_paths' must be an array of glob strings")
        core_paths = [str(item) for item in cfg_core]
    return loc_threshold, files_threshold, core_paths


def _resolve_inputs(args: argparse.Namespace) -> tuple[str, int, int, list[str]]:
    """Validate args, load config/settings, and return (numstat, loc, files, core_paths)."""
    if not args.base_ref and not args.numstat_file:
        raise UsageError("provide --base-ref (git mode) or --numstat-file")
    if args.base_ref and args.numstat_file:
        raise UsageError("use either --base-ref or --numstat-file, not both")
    config = load_config(args.config)
    loc_threshold, files_threshold, core_paths = resolve_settings(args, config)
    if args.numstat_file:
        if not args.numstat_file.is_file():
            raise UsageError(f"--numstat-file {args.numstat_file} not found")
        numstat = args.numstat_file.read_text(encoding="utf-8")
    else:
        numstat = git_numstat(args.base_ref, args.head)
    return numstat, loc_threshold, files_threshold, core_paths


def _valid_records(records: list[Path]) -> list[Path]:
    """Return the subset of decision records that pass validation (prints problems)."""
    valid: list[Path] = []
    for record in records:
        problems = validate_decision_record(record)
        if problems:
            print(f"\n  decision record {record} is INVALID:", file=sys.stderr)
            for problem in problems:
                print(f"    - {problem}", file=sys.stderr)
        else:
            valid.append(record)
    return valid


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        numstat, loc_threshold, files_threshold, core_paths = _resolve_inputs(args)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    added, removed, paths = parse_numstat(numstat)
    reasons = classify(
        added, removed, paths, loc_threshold=loc_threshold,
        files_threshold=files_threshold, label=args.label, core_paths=core_paths,
    )
    if not reasons:
        print(
            f"change-gate: SURGICAL (+{added}/-{removed} across {len(paths)} file(s)); "
            "no decision record required."
        )
        return 0

    print("change-gate: NON-SURGICAL change detected:", file=sys.stderr)
    for reason in reasons:
        print(f"  - {reason}", file=sys.stderr)

    records = discover_records(paths, args.decision_record, args.changed_root)
    if not records:
        print(
            "\nFAIL: a non-surgical change requires a decision record at "
            f"'{DECISION_GLOB}' among the changed files (or passed with "
            "--decision-record) containing:\n"
            "  ## Options   (markdown table with a scored A/B/C row)\n"
            "  ## Steelman\n"
            "  ## Pressure-test evidence\n"
            "None was found in this diff.",
            file=sys.stderr,
        )
        return 1

    valid = _valid_records(records)
    if valid:
        print(f"\nchange-gate: PASS - valid decision record present: {valid[0]}")
        return 0

    print(
        "\nFAIL: decision record(s) present but none satisfies all of "
"\nFAIL: decision record(s) present but none satisfies all of "
        "'## Options' (scored A/B/C table), '## Steelman', "
        "'## Pressure-test evidence'.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
