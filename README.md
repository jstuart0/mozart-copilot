# mozart-copilot

A multi-agent software-delivery orchestration suite for **GitHub Copilot**.

`mozart` is a senior delivery *conductor*: it doesn't write the code itself, it
decides which specialist runs, when, and in what order — then dispatches them
as Copilot subagents and drives the work end-to-end. This repo is the GitHub
Copilot port of the mozart orchestration system (originally built as a Claude
Code plugin; also ported to OpenAI Codex CLI as `mozart-codex`).

> **Status: scaffold only.** This is Phase 1 of an active build-out — repo
> skeleton, the bundle namespace, the tool vocabulary, and the validator
> tooling are in place; no agent personas have been ported yet. Not ready to
> install or use. See `.mozart/plans/active/` for the in-flight campaign plan
> and `docs/COPILOT_PORT.md` (Phase 2+) for the harness mapping.

## What it does

*(to be filled in as the pipeline personas land — Phase 8)*

## The orchestra

*(orchestra table lands with the personas — Phases 2–5)*

## How it maps to GitHub Copilot

*(primitive mapping lands in `docs/COPILOT_PORT.md` — Phase 2)*

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

*(usage lands with the conductor — Phase 5)*

## Configuring your repo

*(link to `.github/mozart/INTEGRATION.md` lands — Phase 7/8)*

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
docs/                     port rationale (COPILOT_PORT.md — Phase 2+)
```

## Relationship to the Claude Code and Codex editions

This is a faithful port. The orchestration *methodology* — pipeline stages,
tiering, gates, state-file and flow-sketch artifacts, ticket lifecycle,
narration cadence — is harness-neutral and identical across editions. Only the
dispatch / continuation / cross-model-review plumbing differs, per
`docs/COPILOT_PORT.md`.

## License

MIT — see [LICENSE](LICENSE).
