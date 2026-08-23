<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->
# breachsafe-golden-python

The golden Python repo standard for the **BreachSAFE Quantum Platform (BQP)**: the copier
scaffold that creates a new Python repo, the reusable GitHub Actions workflows that gate it,
and the gate scripts those workflows run.

This repo is **public**. That is a functional requirement, not a stance on openness. A
private repo's reusable workflows are callable only from repos owned by the same account,
and a workflow that checks out its own scripts from a private repo fails under a consumer's
`GITHUB_TOKEN`. Both blockers are why the predecessor arrangement had zero live consumers.

Public does not mean open source. See [Licensing](#licensing).

## What is here, and what deliberately is not

This repo holds **CI execution**. The BQP **knowledge** layer stays in the private
`breachsafe-common`.

| Here (public) | In private `breachsafe-common` |
|---|---|
| `scaffold/` copier template (`python-cli`) | `skills/` canonical skills library |
| `quality-gates/` gate scripts | `docs/adr/` decision ledger |
| `.github/workflows/` reusable workflows | `standards/` vendored NIST 800-53 |
| oss-fuzz / ClusterFuzzLite templates | `reference/` crypto-posture analysis |
| | `threat-modeling/`, `release/`, `testing/`, `hooks/` |

Skills references inside `scaffold/` still point at `breachsafe-common` on purpose. Skills
are private and stay private. `just skills-sync` in a rendered repo reads from a local
checkout of that private repo.

Rationale and the evidence behind the split: `breachsafe-common/docs/ci-cd-inventory.md`.

## Reusable workflows

Call these from a consumer repo with `uses:`. All are `Apache-2.0` so an Apache/OSS repo
(`qureddy`) can consume them without a noncommercial leak.

| Workflow | `workflow_call` | Purpose |
|---|:---:|---|
| `quality-gates-python.yml` | yes | Lint, type, arch, test, SAST, deps, REUSE |
| `release-python.yml` | yes | Fail-closed release: OIDC publish, cosign, SLSA |
| `major-change-gate.yml` | yes | Blocks a non-surgical change with no decision record |
| `ai-code-review.yml` | yes | Advisory automated review |
| `scorecard-verify.yml` | yes | OpenSSF Scorecard verification |
| `duplicate-code.yml` | **no** | jscpd gate. Repo-local, hardcoded scan paths. |

```yaml
jobs:
  gates:
    uses: paul007ex/breachsafe-golden-python/.github/workflows/quality-gates-python.yml@v1
    with:
      module: <import_name>
      coverage_min: <n>
      container_tag: <tag>
```

### Workflows and gate scripts are one unit

`quality-gates-python.yml` and `major-change-gate.yml` check out **this repo** to fetch the
scripts they run:

```yaml
- uses: actions/checkout@...
  with:
    repository: paul007ex/breachsafe-golden-python
    ref: v1
    path: .bqp-common
```

Moving the workflows without `quality-gates/`, or the reverse, breaks them. They travel
together. The `ref:` is a release tag, so `v1` must keep pointing at a commit where both
exist.

### `duplicate-code.yml` is the fragile one

It has no `workflow_call` and hardcodes `release/`, `quality-gates/`, `testing/` in its
`paths:` filter. A `paths:` filter that matches nothing **skips** rather than fails, so a
directory rename silently stops the gate with no red build. Only `quality-gates/` exists in
this repo; the other two live in `breachsafe-common`. Fix the paths before relying on it.

## Create a new repo

```bash
uvx --from 'copier>=9,<10' copier copy --trust \
  gh:paul007ex/breachsafe-golden-python/scaffold my-new-repo
```

Full options, drift control via `copier update`, and what gets generated:
[`scaffold/README.md`](scaffold/README.md).

**Known limitation.** `.github/workflows/*.yml` in the template are copied verbatim, because
GitHub Actions `${{ }}` collides with Jinja `{{ }}` and templating them corrupts the file.
Owner and ref are therefore hardcoded in the rendered CI. The `golden_ref` answer records the
intended ref but does not rewrite those files; repoint them by hand if you need a different
ref.

## Licensing

Multi-license, every path annotated in `REUSE.toml`, `reuse lint` clean.

| Path | License |
|---|---|
| `.github/workflows/**`, `quality-gates/**` | **Apache-2.0** |
| `scaffold/**`, docs, root config | **PolyForm-Noncommercial-1.0.0** |

The Apache bucket exists so Apache-licensed consumers can call the gates. It is scoped to
generic build tooling and is a lead-authorized exception recorded in `breachsafe-common`
ADR-BQP-005 3.1. Do not widen it.

The scaffold bodies are PolyForm-Noncommercial: source-available, not open source, not
commercially reusable. A rendered repo picks its own license via the `license` answer, which
defaults to PolyForm and offers Apache-2.0 as a deliberate logged opt-in.
