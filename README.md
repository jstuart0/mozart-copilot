# mozart-copilot

A multi-agent software-delivery orchestration suite for **GitHub Copilot**.

`mozart` is a senior delivery *conductor*: it doesn't write the code itself, it
decides which specialist runs, when, and in what order — then dispatches them
as Copilot subagents and drives the work end-to-end. This repo is the GitHub
Copilot port of the mozart orchestration system (originally built as a Claude
Code plugin; also ported to OpenAI Codex CLI as `mozart-codex`).

> **Status: port complete, runtime validated only mechanically.** The 22
> personas, the six-shape pipeline, the model map, the installer, and the
> validator tooling are all in place and pass their own gates — `check_agents.py`,
> `apply_models.py`, and `install-bundle.sh`'s bite tests all run green. What
> hasn't run yet is a live VS Code session: whether the agent picker shows
> only `mozart`, whether `disable-model-invocation` means what this port
> assumes, and whether a cross-model counterpoint review actually lands on a
> different model family in practice rather than only in its attestation
> line. Those are the campaign plan's Manual checklist — see
> `docs/COPILOT_PORT.md`'s "Pending manual verification" section.

## What it does

Mozart orchestrates work across six shapes:

- **DELIVER** — build a feature: research → plan → review → implement → validate → ship → document
- **AUDIT** — review against a goal: discover → fan-out → synthesize → optionally remediate
- **DIAGNOSE** — investigate a failure: intake → investigate → present findings → optionally remediate → optionally publish post-mortem
- **INCIDENT** — respond to a live outage: declare+triage → stabilize ‖ race hypotheses → converge → durable fix → verify recovery → blameless post-mortem. Mitigate first to restore service (logged + reversible), root-cause in parallel, then durable-fix with full gates restored; mozart is the incident commander, and a running timeline is the spine
- **OPERATE** — change or debug a live system: intake+context pin → recon → change plan → pre-flight (dry-run+snapshot) → apply → verify observed → record rollback. Verified empirically, reversed by a recorded rollback, not `git revert`
- **EVAL** — evaluate mozart's own field performance from past campaign artifacts and improve the configuration. No separate entry point — reached through the conductor like every other shape (D12)

At intake it **tiers** the task (TINY / STANDARD / HEAVY; SEV1/2/3 for
incidents) to right-size the gates, classifies the project (GREENFIELD /
BROWNFIELD), and recognizes when a request is genuinely a single agent's
job — routing it directly instead of imposing the full pipeline.

## The orchestra

| Agent | Role | Model role |
|---|---|---|
| **mozart** | Conductor — runs the pipeline, dispatches the rest (this is the only agent you invoke directly — D10) | `conductor` |
| harry | Planner — produces the phased implementation plan | `deep-reviewers` |
| bob | Architect reviewer — design, layering, trade-offs | `deep-reviewers` |
| ruby | UX reviewer — states, accessibility, responsive, voice; implements and verifies UI in a browser | `deep-reviewers` |
| valerie | Validator — checks implementation against the plan; runs the plan's Automated commands | `deep-reviewers` |
| jackson | Implementer — writes and reconciles code, phase by phase | `builders` |
| hank | Ops executor — applies changes to live infrastructure (OPERATE) | `builders` |
| scott | Technical writer — documentation, CHANGELOG, release notes; opens the PR when the repo opts in | `builders` |
| sarah | Technical researcher — surfaces prior art and best practices | `reviewers` |
| dexter | Code-health reviewer — duplication, complexity, naming, test seams | `reviewers` |
| xander | Security reviewer — threat model, injection, auth, secrets | `reviewers` |
| otto | Infrastructure-ops reviewer — infra, config, deployment, ops | `reviewers` |
| tessa | Test-strategy and test-quality reviewer | `reviewers` |
| percy | Performance engineer — measurement-first | `reviewers` |
| librarian | Code archaeologist — does this already exist? (BROWNFIELD only) | `reviewers` |
| ian | Change-impact analyst — ripple effects from the diff | `reviewers` |
| dick | Bug investigator — DIAGNOSE lead; reproduces, isolates, roots out. No `edit` — findings and a verdict, never a fix | `reviewers` |
| codebase-analyzer | Reads and summarizes code for higher-level agents | `support` |
| codebase-pattern-finder | Finds usage patterns across the codebase | `support` |
| web-search-researcher | Searches the web and fetches external pages | `support` |
| codebase-locator | Finds files matching a description or topic; doesn't read file contents by design | `fast-scan` |
| **sebastian** | Independent cross-model counterpoint reviewer — DELIVER stages 5 and 9. Read-only by design (D1) | `validation` — always the non-builder family (D8) |

Each specialist is a Copilot subagent defined in [`.github/agents/`](.github/agents/).
Only `mozart` is `user-invocable: true` (D10); every specialist is reachable
solely through mozart's `agents:` allowlist, so intake, tiering, the
counterpoint gate, worktree isolation, ticket lifecycle, and PR
authorization can't be routed around. The upstream single-agent passthrough
survives — you can still say "have bob look at this plan," and mozart routes
it directly without imposing pipeline overhead.

## How it maps to GitHub Copilot

Mozart's architecture rests on Copilot's native `.agent.md` subagent
mechanism: the `agents:` frontmatter allowlist plus the `agent` tool cover
the dispatch mozart needs, and parallel subagent invocation covers fan-out.

The **independent cross-model reviewer** — a shelled-out `codex exec` CLI
call in the Claude Code edition — becomes a native in-process subagent
(`sebastian`) here: no process lifecycle, no stdin/kill-timer discipline, no
output-file polling. Same value (a different model family auditing the
work), a strictly simpler mechanism.

Full primitive mapping, the nine translation rules, the counterpoint
reviewer's design, and every known quirk (including the subagent
`model:`-fallback issue `## Model attestation` exists to catch):
[`docs/COPILOT_PORT.md`](docs/COPILOT_PORT.md).

### Runtime-surface scope

| surface | status |
|---|---|
| VS Code | **supported** — the only runtime this port designs and validates against |
| Copilot CLI | **loads-but-unvalidated** — agent files are read, the roster appears, `--agent=mozart` runs; whether the dispatch protocol works under `/fleet` is not claimed |
| Cloud coding agent | **out of scope** — ignores `model:`, has no subagent primitive |

## Install

There are two install modes. Most people only need the first.

**Repo scope (`--target`)** — installs the full bundle into a consuming
repo: `.github/agents/*.agent.md` and the whole of `.github/mozart/`.
Nothing from this repo's own `config/`, `tests/`, or `scripts/` is
installed — those are build-time-only (D14).

```sh
scripts/install-bundle.sh --target /path/to/your-repo --apply
```

Dry-run by default (omit `--apply` to preview, writes nothing). Refuses to
overwrite an already-installed bundle whose `.github/mozart/VERSION` is
newer than this repo's, unless you pass `--force`.

**User scope (`--user-scope`)** — installs *agent definitions only*, into
`~/.copilot/agents/` (the verified Copilot CLI harness path). This does
**not** install the bundle. Every repo you want mozart to orchestrate still
needs its own `--target` install — an agent installed only at user scope
halts on its first read and names the missing path. `--user-scope` prints
this as a warning on every run.

```sh
scripts/install-bundle.sh --user-scope --apply
```

`--target` and `--user-scope` are mutually exclusive (passing both exits 2).
See `.github/mozart/INTEGRATION.md` for why there's exactly one bundle
resolution path and no fallback.

## Use

In VS Code with Copilot, open the agent picker and select `mozart` (it's the
only agent that appears there — every specialist is `user-invocable: false`).
Hand it the task:

```
add SSO via our IdP to the admin panel
audit this repo for tech debt
investigate why staging queries are slow
resume the campaign at .mozart/plans/active/<slug>.state.md
```

On its first turn, mozart reads `.github/mozart/manual/INDEX.md` (the
routing table for the rest of the bundle) and then `.github/mozart/manual/INTAKE.md`
(shape-boundary tests, task tiers, project context) before doing anything
else — the two mandatory boot reads (D7). It then runs intake (shape, tier,
mode, slug), creates a state file and a flow sketch, and conducts the
pipeline, narrating each specialist dispatch so you can follow along. If the
bundle isn't installed in the workspace, mozart stops and names the missing
path rather than improvising (D9) — see Install above.

## Configuring your repo

Mozart adapts to your **ticketing**, **documentation**, **code-retrieval**,
**worktree**, and **pull-request** setup via stanzas in the consuming repo's
`AGENTS.md`. **See [`.github/mozart/INTEGRATION.md`](.github/mozart/INTEGRATION.md)
for the contract and per-system templates.** If a stanza is absent, the
corresponding behavior is skipped or falls back to a sensible default. The
bundle location makes this file less discoverable than a repo-root
`INTEGRATION.md` (see the divergence from the Codex edition in
`docs/COPILOT_PORT.md`) — this section exists specifically to surface it.

## Model configuration

Every agent's `model:` is stamped from `.github/mozart/config/model-map.jsonc`
— seven roles (`conductor`, `deep-reviewers`, `builders`, `reviewers`,
`support`, `fast-scan`, `validation`), 22 assignments. The headline
invariant: **`validation` always runs a different model family than
`builders`** (D8) — sebastian's counterpoint review is only worth running if
it's a genuinely different model auditing the work, not a same-family echo.
`scripts/apply_models.py --check-families` enforces this as a hard exit-1
gate, not a convention.

Two shipped presets flip the whole roster's family in one move while
preserving that invariant:

```sh
python3 scripts/apply_models.py --preset claude-bulk --apply   # builders on Anthropic, sebastian on GPT-5.4
python3 scripts/apply_models.py --preset gpt-bulk --apply      # builders on OpenAI,    sebastian on Claude Opus 4.5
```

Dry-run by default; `--apply` writes and backs up every changed file to
`<file>.bak` first. To tune a single role or model ID instead of switching
the whole preset, hand-edit `.github/mozart/config/model-map.jsonc` directly,
then run `apply_models.py --apply` to stamp the roster from it —
`--check` (drift), `--check-families` (D8), and `--check-tiers` (every
agent's role matches its upstream Claude-edition tier exactly, except the
one disclosed `deep-reviewers` upgrade — see `docs/COPILOT_PORT.md`) all
validate the result before you ship it.

## Repo layout

```
.github/agents/           specialist + conductor persona definitions (.agent.md)
.github/mozart/           the installable runtime bundle (manual/, agents/<name>/,
                           PIPELINE.md, LEARNINGS.md, INTEGRATION.md, EVAL.md,
                           config/model-map.jsonc, VERSION)
.github/workflows/        CI (check.yml)
config/                   build-time-only config: toolsets.jsonc, model-maps/
scripts/                  validator, stamper, install script, lint/metrics
tests/                    fixture corpus + coverage/runtime-read manifests
docs/                     port rationale and known quirks (COPILOT_PORT.md)
```

## Relationship to the Claude Code and Codex editions

This is a faithful port. The orchestration *methodology* — pipeline stages,
tiering, gates, state-file and flow-sketch artifacts, ticket lifecycle,
narration cadence — is harness-neutral and identical across editions. Only the
dispatch / continuation / cross-model-review plumbing differs, per
`docs/COPILOT_PORT.md`.

## License

MIT — see [LICENSE](LICENSE).
