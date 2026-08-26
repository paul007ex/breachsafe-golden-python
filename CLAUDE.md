<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->
# breachsafe-golden-python — repository policy

Policy, architecture, licensing, scope. The executable loop and the commands are in
[`AGENTS.md`](AGENTS.md). Read both.

## Instruction hierarchy

1. **`~/claude/CLAUDE.md`** — platform policy: licensing, the OpenSSL 3.5 LTS baseline, the
   Python 3.14 floor, repo identity, the greenfield rule. It auto-loads from any ancestor
   directory.
2. **This file** — rules for this repository. Where it conflicts with the platform file, this one
   wins here, and the conflict is named below with its reason.
3. **[`AGENTS.md`](AGENTS.md)** — the ten-step loop, commands, gate bars, handoff format.
4. **`breachsafe-common/skills/skills/`** — task procedures. That library is **private**; consume
   it from a local checkout.

## What this repository is

The **golden Python repo standard**: the copier scaffold that creates a new Python repo, the
reusable workflows that gate it, and the gate scripts those workflows run.

| Path | What |
|---|---|
| `scaffold/` | Copier template. `uvx copier copy gh:paul007ex/breachsafe-golden-python/scaffold <dir>` |
| `quality-gates/` | Size policy, no-skipped-tests, major-change, anti-pattern diff |
| `.github/workflows/` | Five reusable `workflow_call` gates, plus a repo-local duplicate-code gate |
| `docs/decisions/` | Decision records for changes to the standard |

**This repository is public. That is a functional requirement, not a stance on openness.** A
private repo's reusable workflows are callable only from repos owned by the same account, and a
workflow that checks out its own scripts from a private repo fails under a consumer's
`GITHUB_TOKEN`. Both blockers are why the predecessor arrangement in `breachsafe-common` had zero
live consumers.

**Public does not mean open source.** See Licensing.

## What is deliberately NOT here

The **knowledge layer** stays in the private `breachsafe-common`: `skills/`, `docs/adr/`,
`standards/` (NIST), `reference/`, `threat-modeling/`, `hooks/`, plus the cross-language
`release/` and `testing/` tooling.

The split line: **execution is public, knowledge is private.** A consumer's CI must resolve
execution at run time, so it cannot live in a private repo. Skills and analysis are read from a
checkout, so they stay private and must never be copied here.

Skills references inside `scaffold/` deliberately still point at `breachsafe-common`.

## Changing anything here propagates

A gate, pin, or scaffold edit reaches every repo created or built from this point on. A one-line
change can silently move the standard everyone else is held to.

Treat edits to `core_paths` in `scaffold/template/.bqp-change-gate.toml` as non-surgical
regardless of diff size. They require a decision record under `docs/decisions/` with
`## Options` (scored), `## Steelman`, and `## Pressure-test evidence`.
`quality-gates/check_major_change.py` enforces this.

## Licensing

Multi-license. Every path is annotated in `REUSE.toml`; `reuse lint` must stay at 100%.

| Path | Licence | Why |
|---|---|---|
| `.github/workflows/**`, `quality-gates/**` | **Apache-2.0** | Generic build tooling. Apache/OSS consumers (`qureddy` is Apache-2.0) must call these without a noncommercial leak. |
| everything else first-party | **PolyForm-Noncommercial-1.0.0** | BQP-branded material: scaffold bodies, docs, decision records. |

Two absolute rules:

- **Never relabel upstream material.** Third-party, vendored, or generated content keeps its
  original licence. Making a licence gate pass by mislabelling someone else's work is worse than
  failing the gate.
- **Do not widen the Apache bucket.** It is scoped to generic build tooling. Adding a path is a
  policy change and needs a decision record.

The scaffold bodies are PolyForm-Noncommercial: source-available, not open source, not
commercially reusable. A rendered repo picks its own licence via the `license` answer, which
defaults to PolyForm and offers Apache-2.0 as a deliberate, logged opt-in.

## Two constraints that are easy to break

**1. Workflows and gate scripts are one atomic unit.** `quality-gates-python.yml` and
`major-change-gate.yml` `actions/checkout` **this repo** at `ref: v1` to fetch the scripts they
run. Moving one without the other breaks them, and `v1` must always point at a commit where both
exist.

**2. Never template a GitHub Actions workflow.** Actions `${{ }}` collides with Jinja `{{ }}`,
and `_templates_suffix: .jinja` means only `.jinja` files are substituted. Workflow files
therefore carry no suffix and hardcode owner and ref. The `golden_ref` answer records the
intended ref but does **not** rewrite them.

## Verification standard

Reachability is not execution. A workflow that returns `HTTP 200` has not been proven to run.

`paul007ex/breachsafe-golden-canary` is a repo rendered from this scaffold whose CI calls the
reusable workflow for real. **Nine defects surfaced only there**, each hidden behind the previous,
none visible to reachability checks, YAML linting, or local gate runs. Keep the canary; it is the
only thing that catches this class before a product repo does.

## Do not

- Copy skills into this repo. They stay in `breachsafe-common` and are consumed from a checkout.
- Hand-roll a gate, workflow, or scaffold that already exists here.
- Lower a coverage floor, skip a test, add a blanket `noqa`, or weaken a gate to make it pass.
- Report a gate as passing without its exit code. See the `NOT RUN` rule in
  [`AGENTS.md`](AGENTS.md).
