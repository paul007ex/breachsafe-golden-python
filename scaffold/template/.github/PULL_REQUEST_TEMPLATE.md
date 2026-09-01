<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->

## Summary

<!-- One paragraph describing what this PR does and why. -->

## Type of change

<!-- Check exactly one. One thing per PR. -->

- [ ] feat — new feature
- [ ] fix — bug fix
- [ ] docs — documentation only
- [ ] test — test changes only
- [ ] refactor — internal restructure, no behavior change
- [ ] build — build/dependency change
- [ ] ci — CI/workflow change
- [ ] chore — other maintenance
- [ ] perf — performance improvement
- [ ] security — security fix or hardening

## Related issue

<!-- Link to the issue this PR addresses. If none, explain why. -->

Fixes #

### Fidelity to the issue's proposed fix

- [ ] This PR implements the issue's `### Suggested fix` as written
- [ ] This PR diverges from the suggested fix. Reason and rationale:

  -

## Change governance (standing process rules)

<!-- "Non-surgical" = diff > ~150 LOC or > ~8 files, OR labelled `major`, OR
     touching a designated core path. Non-surgical changes are blocked by CI
     unless a decision record is present. -->

- [ ] This change is **surgical** (small, single-purpose) — no decision record required.
- [ ] This change is **non-surgical**. A decision record is linked below and contains the
      mandatory `## Options (A/B/C scored)`, `## Steelman`, and `## Pressure-test evidence`
      sections (copied from `docs/decisions/TEMPLATE.md`):

  Decision record: `docs/decisions/`
- [ ] The change was pressure-tested in an isolated `/tmp` workstream, not the shared checkout
      (evidence linked in the decision record).

## Decisions made

<!-- List every micro-decision a future maintainer would ask "why did they do that?" about.
     One line each. -->

-

## Audit checklist

Every box must be honestly checked or the PR is not ready.

### Scope

- [ ] One thing per PR
- [ ] Mechanical formatting changes are in a separate commit from behavior changes
- [ ] No out-of-scope work bundled in

### Code

- [ ] Every public function has a Google-style docstring
- [ ] No `print()` in library code (only output adapters and the CLI write to stdout)
- [ ] All datetimes are timezone-aware UTC
- [ ] SPDX header on every new source file

### Quality gates (run `just gates`)

<!-- State PASS / FAIL / NOT RUN with reason. -->

- [ ] `ruff check .` — PASS / FAIL / NOT RUN:
- [ ] `ruff format --check .` — PASS / FAIL / NOT RUN:
- [ ] `mypy src/<module> --strict` — PASS / FAIL / NOT RUN:
- [ ] `pytest` (coverage floor enforced) — PASS / FAIL / NOT RUN: (N tests, X% coverage)
- [ ] `bandit -r src/<module>` — PASS / FAIL / NOT RUN:
- [ ] `pip-audit` — PASS / FAIL / NOT RUN:
- [ ] `reuse lint` — PASS / FAIL / NOT RUN:
- [ ] Secret scan (`gitleaks`) — PASS / FAIL / NOT RUN:

### Tests

- [ ] Every new function with non-trivial logic has at least one test
- [ ] Error paths and boundary values are tested, not just happy paths
- [ ] No new `@pytest.mark.skip` or marker-gated carve-outs
- [ ] No coverage floor lowered and no gate weakened to make CI pass (no quality-theater)

### Security bar (hard merge blockers)

- [ ] No `verify=False` or `ssl.CERT_NONE` introduced
- [ ] No `shell=True` introduced
- [ ] No `eval`, `exec`, or `pickle.loads` on untrusted input
- [ ] No logging of secrets, full PEMs, full traces, or full subprocess output
- [ ] Subprocess calls have explicit `timeout`, list-form args, `shell=False`
- [ ] No `random` for security-sensitive randomness (use `secrets`)

### Dependencies

<!-- Only relevant if pyproject.toml changed. -->

- [ ] Every new dependency justified (replaces meaningful code, actively maintained,
      redistribution-compatible license, recognizable maintainer)
- [ ] `pip-audit` passes (no HIGH or CRITICAL CVEs) — PASS / FAIL / NOT RUN:

## Conformance scorecard

Rate this change against the pre-merge anti-pattern categories. Source: the
`breachsafe-review-gate` and `breachsafe-quality-review` skills. Check each category that is
clean for this PR, then report the tally.

- [ ] Size policy / LOC: surgical scope within the size gate, or a linked decision record
      justifies a non-surgical diff
- [ ] Tests fail before the fix: the new or changed tests are red when the fix is reverted
- [ ] Gates green: `just gates` passed on real exit codes, no gate weakened to pass
- [ ] Docs and changelog: both updated for any behaviour change (or N/A stated with reason)
- [ ] Anti-patterns clean: the pre-commit anti-pattern self-check ran and nothing is left
      flagged without human sign-off
- [ ] CI hygiene: no skip-masking, no never-ran workflow presented as coverage
- [ ] Supply-chain: dependencies pinned and justified, `pip-audit` clean, provenance intact

Report the score as **X / 7 categories cleared.** Score: __ / 7

- [ ] **Changed files rendered (full before/after), diff is non-empty.** A review that
      inspected zero added lines is not a review. See anti-pattern catalog entry #76.2 in
      `breachsafe-quality-review/references/comprehensive-anti-pattern-catalog.md`
      (breachsafe-common).

## Reviewer notes

<!-- Anything you want the reviewer to focus on. Out-of-scope flags. Open questions. -->

-

---

By submitting this PR I confirm:

- [ ] I read `CONTRIBUTING.md` before writing this code
- [ ] I am the author of this code, or it is sourced with provenance and terms compatible with this release
- [ ] I agree to the [Code of Conduct](../CODE_OF_CONDUCT.md)
