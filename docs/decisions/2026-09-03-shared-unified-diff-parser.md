<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->

# Share unified-diff parsing across repository gates

## Contents

1. [Context](#context)
2. [Options](#options)
3. [Steelman](#steelman)
4. [Decision](#decision)
5. [Pressure-test evidence](#pressure-test-evidence)

## Context

Two quality gates independently parse added lines and collect merge-base diffs. Their literal
duplication now exceeds the repository's enforced 0.3% copy-paste ceiling and blocks unrelated
gate maintenance.

## Options

Weights: semantic stability 35, duplication removal 30, direct-script compatibility 20,
implementation size 15.

| Option | Stability | Deduplication | Compatibility | Size | Weighted score |
| --- | ---: | ---: | ---: | ---: | ---: |
| A. One dependency-free support module | 10 | 10 | 10 | 9 | 99 |
| B. Keep both implementations and suppress the clone | 10 | 1 | 10 | 10 | 73 |
| C. Make one gate import the other gate | 5 | 10 | 6 | 10 | 72 |

## Steelman

Option B changes no runtime code and minimizes immediate regression risk, but it converts an
enforced architecture signal into an exception while leaving two owners for one parser.

Option C removes the duplicate without a third file. It couples two independently invoked policy
gates and makes the anti-pattern gate an accidental dependency of the ADR gate.

## Decision

Choose Option A. Both scripts retain their one-argument adapters while a small shared module owns
diff collection, line numbering, and suffix filtering. The module has no third-party dependency,
so direct CLI execution remains intact.

## Pressure-test evidence

The pre-change jscpd run reports two clones and 1.69% duplication against the unchanged 0.3%
threshold. Existing tests exercise both public gate adapters; a focused support-module test pins
suffix filtering and post-image line numbers.
