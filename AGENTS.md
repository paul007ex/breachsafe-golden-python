<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->
# breachsafe-golden-python — agent card

Compact executable card. Policy, architecture, licensing, and scope live in
[`CLAUDE.md`](CLAUDE.md). This file is the loop and the commands.

**This repository defines the standard other repositories inherit.** A change here reaches every
repo scaffolded from it and every repo calling its reusable workflows. Treat edits to
`scaffold/`, `quality-gates/`, and `.github/workflows/` as non-surgical regardless of diff size.

## Read before the first edit

1. `~/claude/CLAUDE.md` — platform policy.
2. [`CLAUDE.md`](CLAUDE.md) — this repository.
3. This file.
4. `breachsafe-common/skills/skills/` — task procedures. That library is **private**; consume it
   from a local checkout.

## The ten-step loop

Every non-trivial change. Report progress as `N/10`.

| # | Step | What it means here |
|---|---|---|
| 1 | **Inventory** | Issue, tree, the files above, applicable skills. Name them. |
| 2 | **Steelman** | Strongest case for current behaviour, then the smallest defensible fix. |
| 3 | **Isolate** | `git clone` to `/tmp`. Never the shared checkout; another agent may be in it. |
| 4 | **Pressure-test** | Alternatives, malformed input, missing input, compatibility, regressions. |
| 5 | **Implement** | Smallest contract-preserving change. |
| 6 | **Regression tests** | A test that fails before the fix. |
| 7 | **Gates** | Run each with a real **exit code**. |
| 8 | **Review** | Ownership, dependencies, duplication, size, logging, errors, extensibility. |
| 9 | **Git** | Evidence on the issue, commit, push, PR. Never commit to `main`. |
| 10 | **Release** | Tag, image, signature, and a real consumer path, each verified **separately**. |

## The NOT RUN rule

**A skipped step is reported as `NOT RUN` with a reason. A green command that did not execute
the required scope is not evidence.**

Every example below happened in this codebase:

| What was reported | What was true |
|---|---|
| `reuse lint \| grep Congratulations` printed nothing | The lint **failed**; empty output was read as a pass. Two releases shipped red. |
| Anti-pattern gate `PASS` | It inspected **0 added lines**. The script was absent and "No such file" exited like a success. |
| `docker ps --filter name=foo` showed healthy | It substring-matched a **different** container. |
| `duplicate-code` green | Its `paths:` filter matched nothing, so the workflow **skipped**. A skip reports no error. |
| jscpd `0 clones` | `minTokens: 50`; the duplicated lines were ~15 tokens, below the detector's floor. |

The shape is always the same: **a check that inspected nothing reported success.** Confirm the
input count was non-zero before believing a pass.

```bash
# Wrong: greps for a success string; empty output looks like silence, not failure.
uvx reuse lint | grep Congratulations

# Right: read the exit code of the thing you care about.
uvx --from 'reuse[charset-normalizer]' reuse lint; echo "exit=$?"
```

## Fast commands

```bash
# Gate scripts, run against any consumer tree
python3 quality-gates/check_size_policy.py --src-dir src
python3 quality-gates/check_no_skipped_tests.py --help    # needs defusedxml
python3 quality-gates/check_antipattern_diff.py --base main
python3 quality-gates/check_major_change.py --help

# Licence
uvx --from 'reuse[charset-normalizer]' reuse lint; echo "exit=$?"

# Duplication, exactly as CI runs it
npx --yes jscpd@4 quality-gates/ --config .jscpd.json; echo "exit=$?"

# Render the scaffold and prove it still works
uvx --from 'copier>=9,<10' copier copy --defaults --trust \
  -d project_name="Smoke" ./scaffold /tmp/smoke
```

## Changing the scaffold or a gate

A scaffold or gate edit propagates to every repo built from this point on. Before changing
`scaffold/`, `quality-gates/`, or `.github/workflows/`:

1. **Render and check the output**, do not read the template and assume. `_templates_suffix:
   .jinja` means only `.jinja` files are substituted; everything else is copied byte-for-byte.
2. **Never template a GitHub Actions workflow.** Actions `${{ }}` collides with Jinja `{{ }}`.
   Workflow files carry no `.jinja` suffix, and owner and ref are hardcoded for that reason.
3. **Verify every `find_prop` / `uses:` / `image:` reference resolves** against a real artifact,
   not against the schema.
4. `docs/decisions/` entry required for a change to `core_paths` in `.bqp-change-gate.toml`, with
   `## Options`, `## Steelman`, and `## Pressure-test evidence`. `check_major_change.py` enforces it.

## Release verification

The tag, the image, and the consumer are three separate claims. Verify each:

```bash
git rev-parse 'v1^{commit}'                      # tag dereferences to the commit you think
curl -s -o /dev/null -w '%{http_code}\n' \
  https://raw.githubusercontent.com/paul007ex/breachsafe-golden-python/v1/.github/workflows/quality-gates-python.yml
```

A workflow that is reachable has not been proven to run. The only proof a consumer can use it is
a consumer using it: `paul007ex/breachsafe-golden-canary` renders from this scaffold and calls
the reusable workflow in real CI. **Nine defects surfaced only there**, none visible to
reachability checks, YAML linting, or local gate runs.

## Handoff format

```
N/10 complete.

Steps run:      <what, with the command and its exit code>
NOT RUN:        <step> — <reason>
Evidence:       <file:line, gate output, run id>
Unverified:     <any claim you did not check>
```

## Authorization

- Issue-driven; branch from `main`; PR; never commit to `main`. One thing per PR.
- New first-party files: `.github/workflows/**` and `quality-gates/**` are **Apache-2.0** so
  Apache consumers can call them without a noncommercial leak. Everything else is
  **PolyForm-Noncommercial-1.0.0**. Do not widen the Apache bucket.
