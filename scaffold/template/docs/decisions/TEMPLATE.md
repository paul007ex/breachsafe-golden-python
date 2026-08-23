<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->
# NNNN — <short decision title>

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded by NNNN
- **Deciders:** <names>
- **PR / issue:** #NNN

> Copy this file to `docs/decisions/NNNN-<slug>.md` for any **non-surgical** change
> (diff > ~150 LOC or > ~8 files, labelled `major`, or touching a designated core path).
> The change-governance CI gate machine-checks that the three `##` sections below exist
> and are filled. It checks structure, not quality — a human reviewer checks quality.

## Context

<!-- What problem or force is prompting this decision? What constraints apply
     (platform invariants, deadlines, existing architecture)? Link the issue. -->

## Options (A/B/C scored)

<!-- List the real alternatives considered — at least three, including "do nothing".
     Score each against the criteria that matter for this decision. Higher = better.
     Adjust the criteria columns to fit; keep a total and a one-line verdict. -->

| Option | Correctness | Simplicity | Cost | Reversibility | Fit to invariants | Total |
|---|---|---|---|---|---|---|
| **A — <name>** | /5 | /5 | /5 | /5 | /5 | /25 |
| **B — <name>** | /5 | /5 | /5 | /5 | /5 | /25 |
| **C — <name>** | /5 | /5 | /5 | /5 | /5 | /25 |

**Chosen:** <A/B/C> — <one-line why it wins>.

## Steelman

<!-- Make the strongest honest case FOR each option you are rejecting, then state
     the specific reason it still loses. This is the anti-motivated-reasoning check:
     if you cannot steelman the alternatives, you have not evaluated them. -->

- **Best case for <rejected option>:** …
  **Why it still loses:** …
- **Best case for <rejected option>:** …
  **Why it still loses:** …

## Pressure-test evidence

<!-- Evidence from an isolated /tmp workstream (throwaway clone or git worktree),
     never the shared checkout. Paste the commands run and the key output, or link
     to a log/gist. Prove the chosen option actually works before committing to it. -->

```
$ # commands run in /tmp/<workstream>
```

## Consequences

<!-- What becomes easier or harder after this decision? Follow-up issues to file.
     What would trigger revisiting it? -->
