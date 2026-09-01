# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once it reaches `1.0.0`. Before that, `0.x` releases may include breaking changes.

## [0.1.0] - 2026-09-01

The complete GitHub Copilot port of the mozart orchestration system: 22
personas, the six-shape pipeline, a model map with a hard cross-family gate,
an installer, and the validator tooling that mechanically enforces all of
it. Runtime-validated only mechanically — see `docs/COPILOT_PORT.md`'s
"Pending manual verification" for the outstanding VS Code checks.

### Phase 1 — Scaffold, bundle namespace, validator, fixtures, CI

- Repo skeleton and OSS boilerplate: `LICENSE` (MIT), `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CONTRIBUTING.md`.
- Bundle namespace `.github/mozart/` and the build-time/runtime config split (repo-root `config/` vs the installable bundle).
- `config/toolsets.jsonc` — the verified Copilot tool vocabulary and the Claude-tool-noun-to-Copilot-tool mapping.
- `scripts/check_agents.py` — the mechanical persona validator (frontmatter, body-size cap, bundle-path resolution, model-map cross-checks).
- The fixture corpus under `tests/fixtures/` proving the validator actually rejects malformed personas.
- `scripts/mozart-metrics.sh` and `scripts/mozart-lint.sh`, ported from the Claude Code edition (`mozart-lint.sh` generalized to the `Counterpoint|Codex|Claude` external-review label set).
- CI workflow `.github/workflows/check.yml`, hardened (pinned actions, read-only permissions, no `pull_request_target`).

### Phase 2 — Port doc, base instructions, three exemplars

- `docs/COPILOT_PORT.md` — the harness-mapping source of truth: primitive mapping, the confirmed `.agent.md` schema, bundle namespace rationale, invocation policy, the runtime-surface matrix, the nine translation rules, and known quirks (subagent `model:` fallback; `model:` as a YAML sequence).
- `AGENTS.md` — the base-instructions file, replacing the Claude edition's `CLAUDE.md` as the stanza host.
- Three exemplar personas (`jackson`, `bob`, `sebastian`) stamped directly, proving the frontmatter schema and the `## Model attestation` addition before the remaining 19 were ported at scale.

### Phase 3 — Specialist batch A (13 lenses)

- 13 specialist personas ported: the per-commit review lenses and support agents. Toolset narrowings applied with a stated rationale per agent (D4) — e.g. `librarian` loses shell access, its one real upstream use approximated with `search`/`read`-based archaeology instead.
- `harry`'s step-18 headroom guard fired (upstream 28,525 chars, over the warn band): the Consistency lens content moved to `.github/mozart/agents/harry/PLAN-TEMPLATE.md`, landing the final body at 26,184 chars.

### Phase 4 — Specialist batch B + measured splits

- The remaining 5 specialist personas, plus `scott`'s two-file split: `## Pull request authoring` and `## Page templates` moved to persona-private bundle files, landing scott's body at 22,697 chars.
- Full 20-of-22 persona roster complete (mozart and sebastian's final form pending Phase 5).

### Phase 5 — The conductor, bundle manual, generated manifest

- `.github/mozart/manual/` — the 14-file fence-aware carve of the upstream 2,400-line, 241,189-character conductor persona, verified total by both line-coverage and character-checksum (`tests/coverage-map.tsv`, `--check-carve`).
- `.github/mozart/manual/COUNTERPOINT.md` — the cross-model review gate rewritten from the ground up: runtime family assert, pre-computed input contract, attestation-based success detection, an attestation ledger added to the state-file format. Upstream's "External tool execution" section (:1111-1126) deliberately deleted, not translated — sebastian is a native subagent with no process lifecycle to babysit.
- `.github/agents/mozart.agent.md` — the conductor itself. Final measured body: 22,392 chars, 5% under target, 25% under the hard cap; none of the plan's pre-designated overflow steps were needed.
- `tests/runtime-reads.tsv` — the generated `(agent, bundle-path)` manifest (`--emit-runtime-reads`), reconciled against the plan's prediction with the actual delta explained per row rather than forced to match.
- Two validator bugs found and fixed by exercising the tools against real content: a leading-dot path-stripping bug, and an `EVAL.md` basename-collision false positive (see `docs/COPILOT_PORT.md`'s Implementation notes).
- CI floor raised to 22; `--check-carve` and `--check-doc-refs` added to `check.yml`.

### Phase 6 — Model map, stamper, presets

- `.github/mozart/config/model-map.jsonc` — the canonical active map, seven roles, 22 assignments, shipped at the `claude-bulk` values.
- `scripts/apply_models.py` — the stdlib-only stamper/validator: dry-run default, `--apply` with `.bak` backups, `--check` (drift), `--preset`, `--validate-map`, `--check-families` (D8), `--check-tiers`, `--explain`.
- `config/model-maps/{claude-bulk,gpt-bulk}.jsonc` — the two shipped presets; flipping either preserves the cross-family invariant automatically (`validation` always the non-builder family).
- `tests/fixtures/upstream-tiers.tsv` and the `deep-reviewers` tier exception: `--check-tiers` asserts every role matches its upstream Claude-edition tier exactly, except the one disclosed upgrade (`harry`, `bob`, `ruby`, `valerie` all stamped to this role's opus tier).
- A `--map`/`--min-agents` combinability bug found and fixed, and `--check-tiers`'s semantics corrected from "no downgrade" to "exact match except `deep-reviewers`" against the pre-existing fixture scaffold's own documented scenario.

### Phase 7 — Install bundle and distribution

- `scripts/install-bundle.sh` — `--target` (repo scope: agents + full bundle, nothing from build-time-only `config/`/`tests/`/`scripts/`), `--user-scope` (agent definitions only, to `~/.copilot/agents/`, with the mandatory workspace-scoped warning), `--home`, mutually-exclusive mode enforcement (exit 2), dry-run default, VERSION-newer refusal without `--force`.
- `tests/fixtures/installed-repo/` — a minimal simulated consuming repo (its own `README.md` and `docs/`, no `.github/` of its own) proving non-collision rather than assuming it.
- A `--check-install` gap found and fixed: it only validated this repo's already-committed manifest rows against the installed copy, never re-scanning the installed copy's own agent files for a planted outside-bundle reference. Confirmed experimentally before fixing.
- `README.md`'s Install section and `.github/mozart/INTEGRATION.md`'s install/resolution notes.

### Phase 8 — Documentation finalization

- `README.md` finalized: what it does, the 22-row orchestra table (incl. `sebastian`), the Copilot primitive-mapping summary, the runtime-surface scope table, both install modes, use (first-turn boot sequence), model configuration (the bulk-vs-validation preset switch, headlined), repo layout, a prominent `Configuring your repo` section linking `INTEGRATION.md`, and the relationship to the Claude Code and Codex editions.
- `docs/COPILOT_PORT.md` finalized: the model map section rewritten for the shipped Phase 6 reality with the cross-family switch as the headline, the `deep-reviewers` tier exception documented, the three measured persona splits (mozart/scott/harry) recorded with their final character counts, and an Implementation notes section recording all five check-tool defects found and fixed across Phases 5-7.
