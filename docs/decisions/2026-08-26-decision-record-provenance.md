<!-- SPDX-FileCopyrightText: 2026 BreachSAFE -->
<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->

# Report decision-record provenance, and do not fail on a pre-existing one

- **Status:** Accepted
- **Date:** 2026-08-26
- **Related:** #36, `paul007ex/breachsafe-common` #102 and its commit `41b8b81`

## Contents

1. [Context](#context)
2. [Options](#options)
3. [Steelman](#steelman)
4. [Pressure-test evidence](#pressure-test-evidence)
5. [Decision](#decision)
6. [Consequences](#consequences)

## Context

`quality-gates/check_major_change.py` required a non-surgical change to carry a decision
record, and accepted any `docs/decisions/NNNN-*.md` that appeared in the diff. `git diff
--numstat`, its only input, carries no add/modify status, so the gate could not tell a record
the change wrote from one it happened to touch.

The gate then printed `PASS - valid decision record present:` and a filename. A reviewer
reading that line has no way to know which of the two they are looking at.

## Options

| | Option | For | Against | Score |
|---|---|---|---|---|
| **A** | Read `--name-status`, prefer added records, state provenance in the message, warn on pre-existing-only | Removes the deception at its source; every existing caller keeps passing; git mode gets it free with no workflow change | A warning in CI output can be scrolled past | **9/10** |
| **B** | Also FAIL when no added record is valid | Strongest reading of "must carry a decision record" | Breaks the legitimate case where amending an existing record is the honest record for a follow-up; this gate reaches every BQP repo, so a passing-to-failing flip can block consumers mid-flight and is itself a change needing its own record | 5/10 |
| **C** | Leave the logic, reword the message to hedge | One-line change, zero risk | The gate still cannot tell the two apart, so the hedge appears on honest changes too and gets ignored everywhere | 3/10 |

## Steelman

**The strongest case for B**, the option not taken. The rule says a non-surgical change must
*carry* a decision record. Carry means bring its own. Under A, a change can still clear the
gate having written nothing, and the only thing standing between that and a merge is a
warning printed to stderr in a CI log that nobody opens. If the gate is worth having, it
should be the thing that stops the merge, not a note hoping a human reads it. A warning that
does not block is a gate that does not gate.

**Why A wins anyway.** B changes a passing state into a failing one for every consumer of a
reusable workflow, on a repo whose own policy says a one-line change here can silently move
the standard everyone else is held to. It also has a real false-positive case: a follow-up
change whose honest record is an amendment to an existing one, which B rejects. The measured
defect was not that a bad change passed. It was that the output could not be told apart from
the honest case. A fixes exactly that, keeps every current caller green, and leaves B
available once there is evidence anyone actually exploited the hole.

## Pressure-test evidence

Replayed against the real diff that exposed the defect, `breachsafe-common` commit `41b8b81`,
77 files, +246/-5380:

```
before  PASS - valid decision record present:
          docs/decisions/0001-change-gate-governs-skills-not-superseded-copies.md

after   PASS - valid decision record:
          docs/decisions/0002-delete-superseded-do-not-use-directories.md
          (added by this change)
```

`0001` documents a different decision and was modified only to add a superseding note. `0002`
is the record written for that change. The old gate would have passed identically with `0002`
absent, naming `0001` either way.

Third case, the same diff with no `--name-status-file`, standing in for a caller that is not
updated:

```
PASS - valid decision record: …/0001-…md (provenance unknown, no add/modify status supplied)
```

It passes, and it does not claim to know something it cannot know.

| Check | Result |
|---|---|
| `quality-gates/tests/test_check_major_change.py`, 7 new tests | 7 failed before the fix, 7 pass after |
| `quality-gates/tests/` full suite | 23 passed, no regression |
| this change run through the gate itself | NON-SURGICAL, FAIL with no record, which is why this file exists |
| `major-change-gate.yml` | unchanged; it calls with `--base-ref`/`--head`, so git mode supplies statuses |

Rename handling was covered explicitly: `R100\told\tnew` records the destination path, which
matches how `parse_numstat` already normalizes renames. Without that, a renamed decision
record would be looked up at a path that no longer exists.

## Decision

**Option A.** Add `parse_name_status()` and `git_name_status()`. `discover_records()` returns
`(path, provenance)` with added records sorted first. The PASS line states provenance:
`added`, `pre-existing`, `unknown`, or `explicit`. A pre-existing-only match passes and emits
a `WARNING` naming the situation.

`--numstat-file` mode gains an optional `--name-status-file`. Without it, provenance is
reported as `unknown` rather than guessed, because numstat cannot distinguish a new file from
an append-only edit.

## Consequences

- Every current caller keeps passing. Git mode gains provenance with no change on their side.
- A reviewer reading CI output can now tell whether the change wrote its own record.
- The hole is narrowed, not closed. A change can still pass on a touched stranger, now
  labelled. Option B stays available if that ever happens for real.
- `--numstat-file` callers get `unknown` until they also pass `--name-status-file`. That is a
  visible gap rather than a silent assumption.
