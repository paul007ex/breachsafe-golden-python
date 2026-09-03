# SPDX-License-Identifier: Apache-2.0
"""Regression tests for reusable quality-workflow security boundaries."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "quality-gates-python.yml"


def test_gitleaks_scans_the_calling_refs_complete_reachable_history() -> None:
    """Keep full history while excluding commits reachable only from unrelated refs."""
    workflow = WORKFLOW.read_text()

    assert "fetch-depth: 0" in workflow
    assert '--log-opts="HEAD"' in workflow
    assert '--log-opts="--all"' not in workflow
