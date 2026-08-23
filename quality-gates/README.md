# Quality gates

Two standalone, dependency-light Python scripts ported from `breachsafe/qureddy`
(qureddy's own CI is genuinely well-built — see `docs/adr/ADR-bqp-004-quality-gates-from-qureddy.md`
for the full audit of what was worth taking).

| Path | What | Counters |
|---|---|---|
| `check_size_policy.py` | Enforces file/function/class LOC ceilings (default 400/50/200) via AST walk, counting logical lines (blank lines and a leading docstring excluded) | Files/functions that grow past the point a reviewer can actually hold them in their head |
| `check_no_skipped_tests.py` | Fails if any JUnit XML report contains a skipped test | `@pytest.mark.skip`/xfail masking a test that reports "passed" without exercising anything — qureddy's own `review-process.md` documents the real cost of this (issue #15: 5 hard-failing tests displayed as "192 passed" under a rerun-masking bug) |

Both are crate/repo-agnostic: pass the source dir / JUnit glob as CLI arguments, same
parameterization discipline as `release/validate_release_archive.sh`'s `--binary <name>`.
A reusable CI workflow calling both is at `../ci/quality-gates-python.yml`.

## Anti-pattern diff gate

`check_antipattern_diff.py` is the reusable pull-request gate for a narrow set of
high-signal anti-patterns. The Python quality workflow invokes it after a full
history checkout, using the PR base and head SHAs. It inspects added lines only;
deleted code, historical findings, Markdown examples, and lock files are not
new regressions. It does not replace the quality-review catalog or human
architecture review.

The gate walks these categories: subprocess discipline, unrecoverable aborts,
unsafe boundary conversions, test integrity, dead code, failure visibility, and
logging discipline. Current rule IDs are `subprocess-shell-true`, `os-system`,
`production-assert`, `unsafe-eval`, `test-skip`, `false-branch`,
`swallowed-exception`, and `secret-output`.

An intentional finding must be recorded in the PR body with a linked follow-up
issue, for example:

```text
ANTIPATTERN ACCEPTED: os-system, because the legacy CLI requires it (#123)
```

The reason and issue reference are mandatory. A malformed exception is a gate
failure. The job summary prints the categories, exact diff command, inspected
line count, findings, and `PASS (exit 0)` or `FAIL (exit 1)`.

The reusable workflow contract changes when this step is added. Publish a new
versioned workflow tag (for example `v1.1`) before consumer repositories adopt
it; do not silently move an existing immutable tag.

## What was in qureddy's CI but is NOT here, and why

qureddy also has `scripts/release_gate.py` (a local, checksum-pinned script that builds,
installs, and smoke-tests the release artifact before trusting hosted CI — "the local
gate is authoritative, CI is a thin mirror") and `scripts/audit_phase.py`'s other checks
(phase-2 coverage thresholds, phase-4 exact live-test-name matching, phase-5 exact
self-scan target matching, phase-6 dist-artifact checks).

Neither of those was ported as code. Both are written against qureddy's own specific CI
artifact layout, its own canonical list of live-network test targets, and its own
release/smoke-test shape (a `qureddy` CLI console script, TLS/SSH scan commands) — copying
them verbatim into another repo would produce dead code that always "passes" because
it's checking for qureddy-specific things (a `qureddy` binary, `pq.cloudflareresearch.com`
as a canonical scan target) that don't exist elsewhere. Writing a fake-generic version
that doesn't actually assert on anything real would be worse than not porting it at all.

**The two underlying principles are genuinely worth adopting even though the code
isn't** — if a repo wants either:

- **"Local gate is authoritative, hosted CI is a thin mirror"**: a repo-owned script
  that rebuilds and smoke-tests its own release artifact with checksum-pinned tool
  versions, writing an evidence manifest, so a release isn't trusted just because a
  hosted-CI job happened to go green. Read qureddy's `scripts/release_gate.py` +
  `scripts/release_support.py` as the worked example and adapt the specific build/smoke
  steps to the target repo's own artifact shape.
- **"Assert on facts from CI artifacts, not the exit code"**: qureddy's Phase 7
  (`scripts/audit_phase.py`) re-reads every prior phase's actual output (coverage
  percentage, exact test counts, exact artifact names) and fails if those facts don't
  match expectations, instead of trusting that a prior job merely exited 0. Same
  caveat: the specific facts it checks are qureddy's own; a consuming repo needs its own
  phase list and its own expected facts, not a copy of qureddy's.

This is the same "fill in the blanks yourself" pattern documented in `../testing/README.md`
for the mutation-testing/Hypothesis/Schemathesis configs — a starting point to adapt, not
a drift-synced copy.
