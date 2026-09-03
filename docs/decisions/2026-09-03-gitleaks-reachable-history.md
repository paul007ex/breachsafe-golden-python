<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->

# Scope Gitleaks to the calling ref's reachable history

## Contents

1. [Context](#context)
2. [Options](#options)
3. [Steelman](#steelman)
4. [Decision](#decision)
5. [Pressure-test evidence](#pressure-test-evidence)

## Context

The reusable Python gate checks out a consumer with full history and asks Gitleaks to scan
`--all`. Git interprets that as every fetched ref, so an unrelated remote branch can fail the
calling pull request. The security boundary is every commit reachable from the calling ref:
secrets committed and later deleted must remain detectable, while unrelated branches must be
assessed by their own runs.

## Options

Weights: security coverage 35, ref isolation 30, determinism 20, simplicity 15.

| Option | Security | Isolation | Determinism | Simplicity | Weighted score |
| --- | ---: | ---: | ---: | ---: | ---: |
| A. Full checkout plus `--log-opts=HEAD` | 10 | 10 | 10 | 10 | 100 |
| B. Full checkout plus `--log-opts=--all` | 10 | 1 | 3 | 10 | 59 |
| C. Shallow checkout plus a working-tree scan | 3 | 10 | 10 | 8 | 73 |

## Steelman

Option B scans the broadest locally available graph and can surface secrets on branches that
have no active CI. That breadth is useful in a separate scheduled repository audit, but it
violates a pull request gate's ownership boundary and makes its result depend on unrelated refs.

Option C is fast and perfectly isolated. It cannot detect a secret that the calling branch
committed and deleted before its current tree, so it is too weak for a history gate.

## Decision

Choose Option A. Preserve `fetch-depth: 0` and scan the complete history reachable from `HEAD`.
This retains deleted-secret detection without importing findings from unrelated refs.

## Pressure-test evidence

On BreachSAFE/qureddy-app PR 172, `--all` imported packet-capture false positives from the
unmerged `spike/wire-trace-tab` branch and failed an unrelated PR. The same checkout with `HEAD`
scanned the calling history and found no leak. A deterministic workflow contract test pins both
the full checkout and the `HEAD` boundary.
