# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Offline negative tests for the release-signing gate.

The guards must fail closed WITHOUT touching the network — this is the #28 regression
test: an empty or missing .sigstore (or an empty artifact) must never verify.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "verify_release_signed.py"
SPEC = importlib.util.spec_from_file_location("verify_release_signed", MODULE_PATH)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules["verify_release_signed"] = gate
SPEC.loader.exec_module(gate)

_ARGS = (
    "owner/repo",
    "owner/golden/.github/workflows/release-python.yml",
    r"^https://x@",
)


def _wheel(tmp: Path) -> Path:
    w = tmp / "pkg-1.0-py3-none-any.whl"
    w.write_bytes(b"PK\x03\x04payload")
    return w


def test_empty_sigstore_fails_closed(tmp_path: Path) -> None:
    """The exact #28 bug: an empty .sigstore must FAIL, before any network call."""
    wheel = _wheel(tmp_path)
    bundle = tmp_path / "pkg-1.0-py3-none-any.whl.sigstore"
    bundle.write_bytes(b"")
    ok, msg = gate.verify_one(wheel, bundle, *_ARGS)
    assert ok is False
    assert "empty" in msg


def test_missing_sigstore_fails_closed(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    ok, _ = gate.verify_one(wheel, tmp_path / "absent.sigstore", *_ARGS)
    assert ok is False


def test_empty_artifact_fails_closed(tmp_path: Path) -> None:
    wheel = tmp_path / "pkg.whl"
    wheel.write_bytes(b"")
    bundle = tmp_path / "pkg.whl.sigstore"
    bundle.write_bytes(b"nonempty")
    ok, _ = gate.verify_one(wheel, bundle, *_ARGS)
    assert ok is False
