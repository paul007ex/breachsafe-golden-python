#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Shared, dependency-free unified-diff support for repository gates."""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed argv, no shell
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AddedLine:
    """One added source line and its post-image location."""

    path: str
    number: int
    text: str


def parse_added_lines(diff: str, source_suffixes: set[str]) -> list[AddedLine]:
    """Parse unified diff hunks into added source lines with post-image numbers."""
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
            if Path(path).suffix.lower() in source_suffixes:
                lines.append(AddedLine(path, new_number, raw[1:]))
            new_number += 1
        elif raw.startswith((" ", "-")) and not raw.startswith("-"):
            new_number += 1
    return lines


def collect_diff(base: str, head: str) -> str:
    """Collect the zero-context merge-base diff between two fixed Git revisions."""
    argv = ["git", "diff", "--unified=0", "--no-ext-diff", f"{base}...{head}"]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=True)  # nosec B603
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise ValueError(f"git diff failed: {detail.strip()}") from exc
    return result.stdout
