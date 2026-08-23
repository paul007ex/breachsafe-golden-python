<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->
# breachsafe-golden-python `scaffold/` — the BreachSAFE golden Python repo scaffolder

This directory is a [copier](https://copier.readthedocs.io) template. It scaffolds a new
BreachSAFE Quantum Platform (BQP) repository that is consistent from the first commit and a
fresh Claude session is *smart on day one*: it inherits the platform invariants (license,
Python 3.14 baseline, issue-driven branch+PR flow, no quality-theater), the full quality-gate
suite, the CI wiring, and the default skill set.

It is source-available under **PolyForm-Noncommercial-1.0.0**. It is not open source.

> **Layout.** The scaffolder was the standalone `breachsafe-repo`, then moved into
> `breachsafe-common` at `scaffold/` (ADR-BQP-005), and now lives here in the **public**
> `breachsafe-golden-python`. `copier.yml` is at `scaffold/copier.yml`, so copier must be
> pointed at the `scaffold` **subdirectory**, not the repo root.
>
> **Public/private split.** CI execution (these workflows, `quality-gates/`, this scaffold)
> is public so consumers can actually resolve `uses:`. The skills library, ADRs, NIST set,
> and reference analysis stay in the **private** `breachsafe-common`. Skills references
> below deliberately still point there. See `breachsafe-common/docs/ci-cd-inventory.md`.

## Create a new repo

Point copier at the `scaffold` subdirectory (where `copier.yml` lives). `project_name` is the
only required answer; everything else has a default.

```bash
# From a local checkout of breachsafe-golden-python (interactive):
uvx --from 'copier>=9,<10' copier copy --trust \
  breachsafe-golden-python/scaffold my-new-repo

# Non-interactive (CI / scripted), accepting all defaults:
uvx --from 'copier>=9,<10' copier copy --defaults --trust \
  -d project_name="My Project" \
  breachsafe-golden-python/scaffold my-new-repo
```

Copier will ask for `project_name`, `project_slug`, `module_name`, `description`,
`github_owner`, `project_type`, `license`, `python_version`, `coverage_min`, `golden_ref`,
and `container_tag`. Accept the defaults for a standard PolyForm-Noncommercial `python-cli`
repo, or override any value with `-d key=value`.

This template defines **no copier `_tasks`**, so `copier copy` only writes files — it does
not init git or install skills for you. Finish the new repo manually afterwards:

```bash
cd my-new-repo
just lock          # REQUIRED: writes uv.lock. CI runs `uv sync --locked` and fails
                   # without it, and OpenSSF Scorecard's Pinned-Dependencies check
                   # needs a committed lockfile. The template cannot ship one:
                   # the resolution depends on the pyproject.toml just rendered.
git init && git add -A && git commit -m "chore: scaffold from breachsafe-golden-python"
just skills-sync   # install the default skill set from breachsafe-common/skills
```

Skipping `just lock` produces a repo whose first CI run dies with:

```
error: Unable to find lockfile at `uv.lock`, but `--locked` was provided.
```

(`--trust` is kept in the commands above for forward-compatibility and to match the
`copier update` invariant; with no `_tasks` or unsafe extensions defined today it is a no-op,
not a requirement.)

Copier 9 has **no `--subdirectory` CLI flag**: it reads `copier.yml` from the source root you
give it, so the source must be the `scaffold/` directory itself (verified working). For remote
consumption, copier resolves a git source at its root, so pull `breachsafe-golden-python`
(a `git clone` or a copier git-ref checkout) and run copier against the checked-out
`scaffold/` path, exactly as above. The always-constant workflow owner is hardcoded
(`paul007ex/breachsafe-golden-python@v1`), so a scaffolded repo's CI points back at the
reusable workflows regardless of how it was rendered.

### License choice

`license` defaults to `PolyForm-Noncommercial-1.0.0` (source-available). `Apache-2.0` is a
**deliberate, reviewed opt-in** for a genuinely-OSS engine repo (e.g. `qureddy` base). The
choice flips every rendered `SPDX-License-Identifier` header, the root `LICENSE` body, the
`REUSE.toml` annotation, and the CLAUDE.md license invariant wording. Apache is never silent;
it is always a logged choice, honoring the platform PolyForm standing invariant.

## Keep an existing repo in sync (drift control)

The reason this is copier and not a GitHub template repo or cookiecutter: copier can re-apply
template changes to a repo that already exists. When this template gains a new gate or fixes
a workflow, propagate it into a scaffolded repo with:

```bash
cd my-new-repo
uvx copier update --trust      # or: just template-update
```

`copier update` uses the `.copier-answers.yml` written at generation time to know which template
version the repo was built from and re-applies the diff. Merge conflicts on hand-edited generated
files are expected and are the drift surfacing correctly; resolve them like any three-way merge.

Skills drift is checked separately by `breachsafe-common/skills/scripts/drift_check.py` (the
private repo), and CI logic is fixed once in `breachsafe-golden-python` and inherited by every
consumer on the next run.

## What gets generated (python-cli)

```
CLAUDE.md                     inherited invariants + process rules + gate cmds + skills
pyproject.toml                ruff superset, mypy --strict, coverage floor, py3.14
justfile                      gates, lint, format-check, typecheck, test, bandit,
                              pip-audit, reuse-lint, secrets, release-gate,
                              skills-sync, template-update
LICENSE, LICENSES/, REUSE.toml, NOTICE-free SPDX headers
.github/
  workflows/ci.yml            verbatim (no Jinja) — load-config job + reusable gates
  workflows/release.yml       verbatim (no Jinja) — reusable release-python.yml
  bqp.env                     module / coverage_min / container_tag for the workflows
  dependabot.yml              pip + github-actions, grouped
  PULL_REQUEST_TEMPLATE.md    audit checklist + decision-record link
  ISSUE_TEMPLATE/             bug_report, feature_request, config
  CODEOWNERS
SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md
REVIEW.md                     BQP code-review bar (severity defs, fuzz/PII/governance rules)
skills.manifest.yaml          default python-cli skill set (installed from breachsafe-common/skills)
src/<module>/{__init__,__main__}.py
tests/{conftest,test_smoke}.py
docs/decisions/TEMPLATE.md    decision-record template (Options A/B/C + Steelman + Pressure-test)
.copier-answers.yml           records the template version for `copier update`
```

## Why workflow files are verbatim

GitHub Actions uses `${{ }}`; Jinja uses `{{ }}`. Templating a workflow YAML silently corrupts
it. So `.github/workflows/*.yml` carry **no** `.jinja` suffix and are copied literally. The
always-constant owner is hardcoded (`uses: paul007ex/breachsafe-golden-python/...@v1`);
`golden_ref` records the intended ref but does **not** rewrite these files. Repo-specific
values (module, coverage_min, container_tag) are written to `.github/bqp.env` and loaded into the
reusable-workflow inputs by a `load-config` job.

## Related components

**In this public repo** (CI execution):

- `../.github/workflows/` — reusable `workflow_call` quality-gate, release, major-change, and
  advisory AI-code-review workflows.
- `../quality-gates/` — the gate scripts those workflows check out and run. Coupled to the
  workflows by an explicit `repository:`/`ref:` checkout; they move together or not at all.

**In the private `breachsafe-common`** (knowledge):

- `skills/` — canonical skills library with install/sync/drift-check tooling. Stays private.
- `docs/adr/`, `standards/`, `reference/`, `threat-modeling/`, `release/`, `testing/`.

**Separate repo:**

- `breachsafe-container` — pinned toolchain image (`ghcr.io/paul007ex/breachsafe-container`),
  runtime infra in its own repo (ADR-BQP-002).
