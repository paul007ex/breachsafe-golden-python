<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->
---
name: Bug report
about: Something is broken or behaves unexpectedly
title: "[bug] "
labels: ["bug", "triage"]
assignees: []
---

## Summary

<!-- One sentence describing the bug. -->

## Severity

- [ ] **Security vulnerability** — STOP. Do not file a public issue. See [`SECURITY.md`](../../SECURITY.md) for the private disclosure process.
- [ ] Critical — crashes, produces wrong output, or silently fails
- [ ] High — misleading output but does not crash
- [ ] Medium — works but is hard to use or under-documented
- [ ] Low — cosmetic, minor inconvenience

## Reproduction

**Command:**

```text
<command you ran>
```

**Steps:**

1.
2.
3.

**Expected:**

<!-- What you expected to happen. -->

**Actual:**

<!-- What actually happened. Paste sanitized output below. -->

```text
<paste output here>
```

## Environment

- Version (commit SHA or release tag):
- Python version (`python --version`):
- OS and version:
- Install method: editable source / wheel / container

## Logs

<!-- Paste relevant, sanitized log lines. Do NOT paste secrets, full PEMs, or full
     subprocess output. Sanitize before posting. -->

```text
<paste sanitized logs>
```

## Anything else

<!-- Other context, screenshots, or related issues. -->
