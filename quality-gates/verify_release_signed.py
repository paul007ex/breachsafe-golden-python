# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed release-signing gate.

Every .whl/.tar.gz asset on a published Release must carry BOTH a provenance
attestation (``gh attestation verify --signer-workflow``) AND a verifiable sigstore
signature (``cosign verify-blob``). An empty/missing .sigstore, a tampered artifact,
a mismatched signer identity, or a signing step that produced nothing all FAIL.

This replaces a name-grep that passed an empty .sigstore (golden #28). The empty/missing
guards fire before any network or crypto call, so they are unit-testable offline.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

OIDC_ISSUER = "https://token.actions.githubusercontent.com"
DIST_SUFFIXES = (".whl", ".tar.gz")


def _rc(cmd: list[str]) -> int:
    return subprocess.run(cmd, capture_output=True, text=True, check=False).returncode


def verify_one(
    artifact: Path, bundle: Path, repo: str, signer_workflow: str, signer_regexp: str
) -> tuple[bool, str]:
    """Verify one distribution. Guards (offline) run before any network/crypto call."""
    if not artifact.is_file() or artifact.stat().st_size == 0:
        return False, f"artifact missing or empty: {artifact.name}"
    if not bundle.is_file() or bundle.stat().st_size == 0:
        return False, f"empty or missing .sigstore bundle: {artifact.name}"
    if (
        _rc(
            [
                "gh",
                "attestation",
                "verify",
                str(artifact),
                "--repo",
                repo,
                "--signer-workflow",
                signer_workflow,
            ]
        )
        != 0
    ):
        return False, f"gh attestation verify failed: {artifact.name}"
    if (
        _rc(
            [
                "cosign",
                "verify-blob",
                "--bundle",
                str(bundle),
                "--certificate-oidc-issuer",
                OIDC_ISSUER,
                "--certificate-identity-regexp",
                signer_regexp,
                str(artifact),
            ]
        )
        != 0
    ):
        return False, f"cosign verify-blob failed: {artifact.name}"
    return True, f"verified: {artifact.name}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Fail-closed release-signing verification gate."
    )
    ap.add_argument("--tag", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--signer-workflow", required=True)
    ap.add_argument("--signer-identity-regexp", required=True)
    a = ap.parse_args(argv)

    view = subprocess.run(
        [
            "gh",
            "release",
            "view",
            a.tag,
            "-R",
            a.repo,
            "--json",
            "assets",
            "--jq",
            ".assets[].name",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    dists = [n for n in view.stdout.split() if n.endswith(DIST_SUFFIXES)]
    if not dists:
        print(f"::error::no distributions (.whl/.tar.gz) on {a.tag}")
        return 1

    failed = False
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for d in dists:
            subprocess.run(
                [
                    "gh",
                    "release",
                    "download",
                    a.tag,
                    "-R",
                    a.repo,
                    "-p",
                    d,
                    "-p",
                    f"{d}.sigstore",
                    "-D",
                    str(tmp),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            ok, msg = verify_one(
                tmp / d,
                tmp / f"{d}.sigstore",
                a.repo,
                a.signer_workflow,
                a.signer_identity_regexp,
            )
            print(("PASS: " if ok else "::error::") + msg)
            failed = failed or not ok

    if failed:
        print(f"::error::release {a.tag} has unsigned or unverifiable distributions")
        return 1
    print(
        f"PASS: every distribution on {a.tag} carries a verified attestation + signature"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
