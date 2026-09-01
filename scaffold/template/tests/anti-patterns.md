<!-- SPDX-FileCopyrightText: 2026 BreachSAFE -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# tests/ — anti-patterns (default real)

Local rules for this folder. They refine, never weaken, the repo's `CLAUDE.md` and the
shared anti-pattern catalog. Enforced by `check_no_mocks.py` when the reusable
`quality-gates-python` workflow is called with `mocks_check: true`.

## Contents

1. [Default real](#1-default-real)
2. [Banned: mocks and monkeypatch](#2-banned-mocks-and-monkeypatch)
3. [The one exception](#3-the-one-exception)

## 1. Default real

Do the hard work: real CLI, real subprocess, a real call, a real (pinned) oracle. A test
double hides the exact wiring the test exists to prove, and a suite of green doubles is the
"N passed, bugs shipped" trap. Set real config through a real `conftest`/env the code
actually reads; drive the real binary through `subprocess`; assert observable output, not a
call count. See `breachsafe-test-harness` (pinned live oracle, real vectors) and the
release loop's real-CLI smoke path.

## 2. Banned: mocks and monkeypatch

Flagged by `check_no_mocks.py` (fails the gate):

- `monkeypatch` — the pytest fixture, including `monkeypatch.setattr` (replacing real
  functions with fakes) and `monkeypatch.setenv/delenv`. Set env through a real fixture the
  code reads, not by patching.
- `unittest.mock` / `MagicMock` / `AsyncMock` / `@patch` / the `mocker` fixture — asserting
  on a double's call count instead of observable behavior (catalog #71) hides the real path.

## 3. The one exception

A genuinely-unavoidable double (a paid external API you must not call in CI, a destructive
operation) is allowed **only** with an explicit `# real-double: <reason>` on the offending
line, paired with a real-path test that proves the real wiring still works (catalog #147).
The marker forces the author to justify it and a reviewer to see it; nothing else passes.
