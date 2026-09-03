# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for shared unified-diff support."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "diff_support.py"
SPEC = importlib.util.spec_from_file_location("diff_support", MODULE_PATH)
assert SPEC and SPEC.loader
support = importlib.util.module_from_spec(SPEC)
sys.modules["diff_support"] = support
SPEC.loader.exec_module(support)


def test_parse_added_lines_filters_suffixes_and_tracks_post_image_lines() -> None:
    """Preserve added-line locations while excluding unowned file types."""
    diff = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
-old
+first = 1
+second = 2
diff --git a/docs/readme.md b/docs/readme.md
--- a/docs/readme.md
+++ b/docs/readme.md
@@ -0,0 +1 @@
+not source
"""

    assert support.parse_added_lines(diff, {".py"}) == [
        support.AddedLine("src/app.py", 1, "first = 1"),
        support.AddedLine("src/app.py", 2, "second = 2"),
    ]
