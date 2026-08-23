#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Apply branch protection to a repo's default branch (run manually).

Branch protection is one of the highest-weighted OpenSSF Scorecard checks, but
it cannot be set from the scaffold: it is repository state, not a file. This
script applies a strict, opinionated ruleset to the default branch of a repo via
the ``gh`` CLI (GitHub REST ``branches/{branch}/protection`` endpoint):

  * required pull-request reviews (configurable approving-review count)
  * required status checks (strict / up-to-date, optional named contexts)
  * no force pushes, no branch deletion
  * enforce for administrators (``enforce_admins``)
  * required linear history

It is a *run-manually* tool, not a workflow step: applying protection needs a
token with admin rights on the repo, which CI's ``GITHUB_TOKEN`` deliberately
lacks.

Free-plan caveat: the classic branch-protection API rejects PRIVATE repos on the
GitHub Free plan with "Upgrade to GitHub Pro or make this repository public".
This script detects that response and prints a clear, actionable message instead
of a raw API error.

Usage:
    python set_branch_protection.py --repo owner/name [--dry-run]
    python set_branch_protection.py --repo owner/name --review-count 2 \
        --required-check CI --required-check CodeQL

Stdlib only (argparse, json, subprocess, shutil); shells out to ``gh``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # noqa: S404 - shelling out to the trusted `gh` CLI is the point
import sys

# Substring GitHub returns when the classic protection API is used on a private
# repo under a plan that does not include protected branches.
_UPGRADE_MARKER = "Upgrade to GitHub Pro"


def _fail(message: str, code: int = 1) -> "int":
    """Print an error to stderr and return an exit code."""
    print(f"error: {message}", file=sys.stderr)
    return code


def build_payload(review_count: int, required_checks: list[str]) -> dict[str, object]:
    """Build the branch-protection request body for the classic protection API."""
    return {
        "required_status_checks": {
            # strict = branch must be up to date before merging.
            "strict": True,
            "contexts": required_checks,
        },
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "required_approving_review_count": review_count,
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
        },
        # No push/merge restrictions to specific actors.
        "restrictions": None,
        "required_linear_history": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }


def resolve_default_branch(repo: str) -> str | None:
    """Best-effort lookup of the repo's default branch via ``gh``.

    Returns None if ``gh`` is missing, unauthenticated, or the repo is
    unreachable -- callers fall back to a sensible default so ``--dry-run`` works
    offline.
    """
    if shutil.which("gh") is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["gh", "api", f"repos/{repo}"],  # noqa: S607 - `gh` resolved from PATH
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    branch = data.get("default_branch")
    return branch if isinstance(branch, str) else None


def apply_protection(repo: str, branch: str, payload: dict[str, object]) -> int:
    """PUT the protection payload; translate the free-plan error into guidance."""
    if shutil.which("gh") is None:
        return _fail("the `gh` CLI is required to apply protection (install: https://cli.github.com)")
    path = f"repos/{repo}/branches/{branch}/protection"
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["gh", "api", "-X", "PUT", path, "--input", "-"],  # noqa: S607
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        print(f"OK: branch protection applied to {repo}@{branch}")
        return 0

    stderr = proc.stderr or ""
    if _UPGRADE_MARKER in stderr or _UPGRADE_MARKER in (proc.stdout or ""):
        return _fail(
            f"{repo} is a PRIVATE repo on a plan without protected branches.\n"
            "  Branch protection (and its OpenSSF Scorecard credit) requires either:\n"
            "    - making the repository PUBLIC, or\n"
            "    - upgrading to GitHub Pro / Team / Enterprise.\n"
            "  No changes were made."
        )
    return _fail(f"gh api failed (exit {proc.returncode}):\n{stderr.strip()}")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        description="Apply strict branch protection to a repo's default branch via gh.",
    )
    parser.add_argument("--repo", required=True, metavar="owner/name", help="Target repository.")
    parser.add_argument(
        "--branch",
        default=None,
        help="Branch to protect (default: the repo's default branch, else 'main').",
    )
    parser.add_argument(
        "--review-count",
        type=int,
        default=1,
        help="Required approving review count (default: 1).",
    )
    parser.add_argument(
        "--required-check",
        action="append",
        default=[],
        metavar="CONTEXT",
        dest="required_checks",
        help="Required status-check context; repeat for several (default: none, strict-only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the intended request without calling the API.",
    )
    args = parser.parse_args(argv)

    if "/" not in args.repo:
        return _fail("--repo must be in owner/name form", code=2)
    if args.review_count < 0:
        return _fail("--review-count must be >= 0", code=2)

    payload = build_payload(args.review_count, args.required_checks)

    branch = args.branch or resolve_default_branch(args.repo) or "main"
    path = f"repos/{args.repo}/branches/{branch}/protection"

    if args.dry_run:
        print(f"DRY RUN — would call: gh api -X PUT {path} --input -")
        print(f"target: {args.repo}@{branch}")
        print("payload:")
        print(json.dumps(payload, indent=2))
        return 0

    return apply_protection(args.repo, branch, payload)


if __name__ == "__main__":
    sys.exit(main())
