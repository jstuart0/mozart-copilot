# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once it reaches `1.0.0`. Before that, `0.x` releases may include breaking changes.

## [Unreleased]

### Added — field-notes harvest: four prose entries, three mechanisms, ported from mozart-orchestration

Four prose field notes ported byte-identical into `mozart.agent.md` (three: known-wrong facts in the
brief, scope empirical findings to platform/version/date, an unattended run needs a decision log) and
`jackson.agent.md` (one: mutation testing finds missing tests, not weak ones). Three related findings
land as **mechanisms** rather than prose — the family's 2026-09-12 campaigns showed prose contracts
inside a persona don't reliably change behavior: M2 (verify the measuring instrument at a known-FAIL
base before trusting it) and M7 (a population floor and a named member on every counting/globbed
check) join `harry.agent.md`'s Verification rules; M4 (name the pre-revision sections a mechanism
touches, in the revision message) joins `.github/mozart/manual/DELIVER.md`'s stage-6 Iterate
procedure, with a 93-char requirement pointing at it from `mozart.agent.md`'s Orchestration
discipline section (chosen over inlining the full M4 text there, which would have cost 721 chars —
75% of the then-remaining headroom to the 30,000-char hard cap — and put two copies of one rule in
one port).

**Measured against the hard cap** (`check_agents.py:101-102`, documented at `docs/COPILOT_PORT.md:559`):
`mozart.agent.md` is now **29,137 chars — 863 chars of headroom, WARN band, not FAIL.**
`harry.agent.md` is **27,567 chars**. The straight seven-entry prose port (no mechanism split) would
have put `mozart.agent.md` at 32,180 chars and broken this port's CI outright; the mechanism/prose
split is what makes this fit. **Residual is roughly one more mozart field note, ever** — the rule at
that ceiling: never compact existing entries to make room; ask first whether a new finding should be
a mechanism instead; if it must be prose and does not fit, refuse the append in all three ports rather
than let copilot alone diverge.

- **`scripts/check-fingerprints.sh`** — narrowed the fingerprint grep back down. It still matches a
  hardcoded personal username and absolute personal home paths (`/Users/[a-z]`, `/home/[a-z]`), plus
  the unpublished sibling port, by name — none of those three reproduced literally in this bullet,
  because each is exactly what the pattern catches, and spelling them out here would trip the check
  this bullet describes. It no longer matches `mozart-orchestration`: this port's published public
  upstream is ordinary provenance, not personal infrastructure, and never should have been in the
  pattern. No path was blacklisted; the property the pattern tests for was narrowed instead, per the
  script's own SCOPE comment. Found this way: an earlier draft of this bullet described widening the
  pattern from `mozart-orchestration` to a `(orchestration|local)` alternation and, in prose, named
  the personal username and the sibling port directly to explain why — which the widened pattern then
  caught, correctly, in this very file.
- A pre-existing hardcoded carve (`check_agents.py:71-73`, `agents/mozart.md` expected at 2400 lines)
  is **already red at base** and env-gated (`MOZART_UPSTREAM_CHECKOUT` unset ⇒ skipped, no CI impact).
  This change widens the drift from 2,437 to 2,470 lines against the unchanged 2,400 constant. Not
  repaired here — out of scope, measured and disclosed per this campaign's plan.
- Cross-port agreement (this port, `mozart-orchestration`, `mozart-codex`) is verified pre-merge with
  `scripts/check-field-note-parity.py`, run by hand across all three worktrees; not CI-wired, since no
  port's CI can see the other two checkouts.

Capability-vs-claim parity: every persona and bundled-doc contract in this port
now promises only actions its `tools:` grant (or the port's mozart-only
dispatch policy, D10) can actually perform, checked in both directions —
overclaiming a capability the grant doesn't have, and understating one it
does.

### Fixed

- **22 sites where a contract's prose disagreed with its `tools:` grant.** The
  7 grantless personas' (`bob`, `dexter`, `ian`, `librarian`, `sarah`,
  `sebastian`, `xander`) field-notes self-append blocks now route the append
  through mozart instead of claiming it directly; `harry`'s Design-It-Twice
  section and three support agents' (`codebase-locator`,
  `codebase-pattern-finder`, `web-search-researcher`) "who calls you" prose no
  longer claim non-mozart dispatch, matching `PIPELINE.md`'s "Requested for"
  column (renamed from "Used by"); `sarah`'s research brief and mozart's edit
  allowlist are reconciled so mozart, holding the grant, is the one who
  persists it; `otto` and `dick`'s bare `"Read-only."` descriptions are
  qualified against the write/ticket actions their bodies already assign
  them; and `manual/TICKETS.md` / `manual/WORKTREES.md` no longer assign a
  ticket transition or an artifact write to `xander`, `sarah`, or
  `sebastian`, none of whom hold `edit` or `execute`. No `tools:` or `agents:`
  grant changed anywhere in the repair — every fix is prose.
- `LEARNINGS.md`'s field-notes roster no longer enumerates names — it
  previously disagreed with itself on whether `sebastian` could self-update
  and omitted `ian`/`sarah` entirely. It now states the rule by grant instead
  of by a hand-maintained list, so it can't drift the same way again.
- Two further contradictions of the same shape, found outside the campaign's
  own matrix while checking the surrounding docs: `PIPELINE.md`'s stage list
  drew sebastian's counterpoint review as if the arrow to its output path were
  sebastian's own write, and `manual/COUNTERPOINT.md` elided the subject of
  "writes `<slug>.counterpoint-r1b-plan.md`" the same way `DELIVER.md:128` did
  before this campaign fixed that instance. Both now name mozart as the
  writer.

### Added

- **A capability-vs-claim drift guard in `scripts/check_agents.py`**
  (`find_capability_claim_violations`, rules V7a-e), run in CI via
  `--self-test --forms` and `--min-agents 22`, with seven new negative
  fixtures under `tests/fixtures/`: a persona claiming the field-notes
  self-append marker without the grant to back it, citing the `agent` tool
  without holding it, claiming non-mozart dispatch, claiming a
  campaign-artifact write without `edit`/`execute` (including the
  self-attributed and mozart-as-recipient variants), or carrying an
  unqualified `"Read-only."` description while holding `edit`/`execute`. The
  artifact-write rule (V7c) is subject-position aware, not merely
  sentence-aware: it distinguishes "mozart persists it to `<path>`" (exempt)
  from "in mozart's brief" or "to mozart" (mozart named, but as the recipient
  or the document, not the writer — still a violation).

### Known limitations

- **The drift guard covers only references that name a grantless persona.**
  It's exact and closed over `.github/mozart/**` for that population — 233
  lines enumerated, 32 carrying a persistence verb, all 32 adjudicated by
  hand, 6 true positives, 0 remaining. A pronoun or role noun ("the
  researcher") naming the same persona indirectly is invisible to it, and no
  sweep this campaign could construct closes that gap; its own 10-phrase
  role-noun probe was disqualified as hand-built vocabulary, the same
  instrument the gap disqualifies.
- **The population-pin gate (`C10b` in the campaign's own verification
  runner) is a count, not a detector.** It fails whenever the number of
  (grantless-persona-name, persistence-verb) lines changes in either
  direction, forcing a human to adjudicate the new member — it doesn't
  recognize the defect itself. Its baseline is also non-portable across
  independently-worded repairs of the same defects: the plan predicted 36
  entries, the shipped tree measured 31, from correct repairs phrased
  differently than the plan's own scratch wording. Re-derive it fresh next
  time; don't reuse this number.
- **`LEARNINGS.md:3` can no longer go stale; `:105` still can.** `:3` now
  describes the rule generically; `:105` still names the same 7 personas as
  a worked example, pinned only by a gate that lives outside this repo in a
  gitignored verification runner.
- **Only 4 of the campaign's 12 verification gates have a CI home** — the
  ones folded into `check_agents.py` above. The other 8, including the
  population pin, exist only in that gitignored runner and are hand-run, not
  enforced on every push.
- **The field-notes guard (V7a) doesn't catch a deleted `## Field notes
  (append-only)` section**, only a malformed one — the section heading is
  also the rule's own trigger. (The implementation plan claimed it "fails on
  deletion"; it doesn't.)

## [0.3.0] - 2026-09-02

OSS-readiness hardening: the campaign removes personal-infrastructure
fingerprints, hardens both Python CLIs' exit-code and modifier contracts,
re-bases the model maps onto live model IDs the harness actually offers, and
adds three install/launch trust mechanisms — an ownership manifest, install-time
trust roots, and a launch-wrapper provenance gate — each documented with its
honest limits in `SECURITY.md`. No runtime persona behavior changes; the model
default flip from `913f0b3` (5 of 22 agents) is what makes this a minor, not a
patch, release.

### Added

- `scripts/check-fingerprints.sh` — a committed CI guard against
  personal-infrastructure path fingerprints. Exit contract `0` = clean, `1` =
  fingerprint found, `2` = the search itself errored (a real error never reads
  as clean); the guard excludes itself from its own scan.
- **Ownership manifest** at `<copilot-home>/mozart-manifest.txt` (mode `0600`,
  one `<sha256>  <absolute-path>` line per installed file, union-with-dedup so a
  later reinstall with different flags never forgets a path an earlier one
  wrote). The documented uninstall procedure consumes it.
- **Install-time trust roots** at `<copilot-home>/mozart-trust/roots` (dir
  `0700`, file `0600`), recorded from a physical-identity canonicalization of the
  install root; a successful `--target … --apply` also appends the target root to
  the user-side list, and prints the override notice when there is no user-side
  home to record into.
- A live model-ID allowlist (`KNOWN_MODELS`) and a `check_model_ids` gate across
  both map entry points, with per-role family binding so a declared `family` must
  match its model's real provider.
- Operator **upgrade / uninstall / troubleshoot** documentation in `README.md`; a
  trust-boundary section with five known limits in `SECURITY.md`; and a decision
  registry resolving every `D<n>` ID in `docs/COPILOT_PORT.md`.

### Changed

- **`install-bundle.sh --target` now refuses symlinked container directories and
  unconsented non-identical overwrites**, on both install branches, and prints
  the real copied file count instead of a hardcoded figure. A fresh install into
  an empty target is unaffected.
- **`scripts/mozart` now refuses a repo-local bundle differing from the installed
  one unless the repo root is trusted** — a **bundle provenance** gate that is
  consent + baseline comparison, not authenticity (no signature, no content
  checksum). Trust is recorded at install time or named for a single invocation
  by `MOZART_TRUST_REPO_BUNDLE=<repo-root>`; the gate guards the wrapper's `exec`
  only and is bypassed by a bare `copilot` launch and by VS Code. Limits are
  enumerated in `SECURITY.md`.
- **`check_agents.py` action flags now compose** — previously only the first
  action flag was honored and the rest were silently ignored; now every action
  runs in one invocation and the highest-priority status is returned (`1` > `2` >
  `0`). Modifier flags are accepted only with the action that consumes them,
  otherwise the run exits `2` naming both flags, and `--emit-runtime-reads` is
  mutually exclusive with all other actions.
- `--force-clobber` now composes with `--target` (previously `--user-scope`
  only); the two shipped install commands in `.github/mozart/INTEGRATION.md` are
  repaired to match, each carrying the "use it on a deliberate upgrade; do not add
  it to routine commands" caution.
- Version bumped to `0.3.0` rather than `0.2.1`: a default-model change across 5
  of 22 agents plus the dispatch-semantics and installer-refusal changes are not
  patch-level.

### Fixed

- **The shipped model maps referenced models the harness no longer offers**, so
  the installed roster could not be dispatched. Every map is re-based onto live
  model IDs, all 22 personas are re-stamped by `apply_models.py` (never
  hand-edited), and the new `check_model_ids` gate — bound through all three read
  entry points and the `--preset … --apply` write path — stops a dead ID from
  ever shipping again.
- Personal-infrastructure path fingerprints removed from tracked text; the two
  upstream checkout paths parameterized to a non-matching placeholder; the manual
  `INDEX.md` document count corrected to the real file count.
- CI hardening: the workflow pins `ubuntu-24.04` and the Python interpreter,
  asserts (by positive content) that the PyYAML frontmatter cross-check actually
  ran, wires the negative map/roster fixtures through both entry points, and
  every new exit-code step asserts a required error substring rather than a bare
  nonzero exit (so an exit `2` for the wrong reason can never read as caught).

## [0.2.0] - 2026-09-01

Global install: one `install-bundle.sh --user-scope --apply` now installs
and launches mozart for use in any repo on the machine — the standalone
Copilot CLI via a new `mozart` wrapper, VS Code via two pasted settings —
instead of requiring a per-repo `--target` bundle install. Installation and
launch are mechanically verified; live dispatch behavior (subagent grant
inheritance, `/fleet`) is wired but not yet manually confirmed — see
`docs/COPILOT_PORT.md`'s "Pending manual verification".

### Added

- `scripts/mozart` — the CLI wrapper. Resolves the Copilot home
  (`--copilot-home` > `--home`'s `<dir>/.copilot` > `$COPILOT_HOME` >
  `~/.copilot`), enforces a symlink contract for a non-default home, `cd`s
  to the git repo root before exec (announced on stderr), and execs
  `copilot --agent mozart --add-dir <bundle>` — no flags of its own.
- `scripts/install-bundle.sh --user-scope` full-stack mode: agent
  definitions, the bundle, and the wrapper, all installed in one pass, with
  `--no-bundle`/`--no-wrapper` escapes and a printed VS Code paste-block
  (`chat.agentFilesLocations`, `chat.additionalReadAccessFolders`).
- `scripts/check_agents.py --check-install --layout {repo,user}` and
  `apply_models.py --agents-dir` — the same drift/membership checks now run
  against an installed (out-of-tree) copy, not just the source checkout.
- `.github/agents/mozart.agent.md`'s `## Bundle resolution` section and the
  matching one-line resolution sentence in all 21 specialists: the two-step
  boot probe (workspace bundle, then the user-scope bundle), the
  first-narration-line root+`VERSION` report, and the halt text naming the
  exact CLI/VS Code/install remedies.

### Changed

- **`--user-scope` installs the full stack by default** (D1) — agent
  definitions, the bundle, and the wrapper, not agent definitions alone.
  The previous default's only reachable outcome was agents that halt on
  their first read; `--no-bundle`/`--no-wrapper` reproduce the old
  agents-only behavior explicitly.
- **The force flags are split by consent question, not by artifact** (D11):
  `--force` now means only "move an installed bundle backwards"; a new
  `--force-clobber` is required to overwrite any pre-existing file the
  installer didn't write and that isn't byte-identical to what it would
  install — the wrapper binary on `PATH`, or an agent-definitions file
  sharing a name in the shared `~/.copilot/agents/` namespace. **A
  hand-edited installed agent now needs `--force-clobber` on the next
  install** — a hand-modified file is indistinguishable from a stranger's,
  so it's no longer silently overwritten.
- **The predecessor's negative gate is retired.** `grep -rn
  '\.copilot/mozart' .github/agents/` — the blanket ban
  `find_outside_bundle_violations()` used to enforce — is replaced by D3's
  three-part rule: the bare user-scope root is a legal grant target, a path
  component under it is not, and a shell copy of it at command position is
  not (github/copilot-cli#2173).
- **`--no-bundle` now refuses unconditionally when a bundle is already
  installed, with no override flag.** Previously `--no-bundle` would
  silently leave an older bundle in place while updating agent
  definitions — precisely the agents/bundle skew the `VERSION` contract
  exists to prevent. There is no flag to force through this refusal;
  `install-bundle.sh` prints the two real remedies (drop `--no-bundle`, or
  remove the installed bundle first). **This is the one change that can
  turn a previously-working scripted invocation into a hard failure** — a
  script that ran `--no-bundle` against a machine with any prior bundle
  install now needs updating.

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
- `tests/fixtures/upstream-tiers.tsv`, transcribed from each upstream persona's own `model:` frontmatter (not `agents/README.md`'s Model column, which is stale — see the reconciliation note below): `--check-tiers` asserts every role matches its upstream tier exactly, `sebastian` exempt by name.
- A `--map`/`--min-agents` combinability bug found and fixed, and `--check-tiers`'s semantics corrected from "no downgrade" to exact-match against the pre-existing fixture scaffold's own documented scenario.

### Phase 7 — Install bundle and distribution

- `scripts/install-bundle.sh` — `--target` (repo scope: agents + full bundle, nothing from build-time-only `config/`/`tests/`/`scripts/`), `--user-scope` (agent definitions only, to `~/.copilot/agents/`, with the mandatory workspace-scoped warning), `--home`, mutually-exclusive mode enforcement (exit 2), dry-run default, VERSION-newer refusal without `--force`.
- `tests/fixtures/installed-repo/` — a minimal simulated consuming repo (its own `README.md` and `docs/`, no `.github/` of its own) proving non-collision rather than assuming it.
- A `--check-install` gap found and fixed: it only validated this repo's already-committed manifest rows against the installed copy, never re-scanning the installed copy's own agent files for a planted outside-bundle reference. Confirmed experimentally before fixing.
- `README.md`'s Install section and `.github/mozart/INTEGRATION.md`'s install/resolution notes.

### Phase 8 — Documentation finalization

- `README.md` finalized: what it does, the 22-row orchestra table (incl. `sebastian`), the Copilot primitive-mapping summary, the runtime-surface scope table, both install modes, use (first-turn boot sequence), model configuration (the bulk-vs-validation preset switch, headlined), repo layout, a prominent `Configuring your repo` section linking `INTEGRATION.md`, and the relationship to the Claude Code and Codex editions.
- `docs/COPILOT_PORT.md` finalized: the model map section rewritten for the shipped Phase 6 reality with the cross-family switch as the headline, the three measured persona splits (mozart/scott/harry) recorded with their final character counts, and an Implementation notes section recording all five check-tool defects found and fixed across Phases 5-7.

### Reconciliation round 1 — codex r2 (BLOCK)

- `scripts/install-bundle.sh` — `set -euo pipefail` so a failed `mkdir`/`cp` aborts before the success message; two `&&`-as-assignment idioms in `version_gt` rewritten to explicit `if`/`then` (a latent `set -e` hazard, not yet triggered). Negative test added: install into an unwritable target refuses with a non-zero exit and no success message.
- `scripts/apply_models.py` — `main()`'s dispatch reworked so `--check`, `--check-families`, `--check-tiers`, `--validate-map`, and `--explain` compose in one invocation (aggregated exit) instead of the first-matching-flag-wins dispatch that silently dropped the rest (the same class of bug as Phase 6's `--map`/`--min-agents` gap). `--preset ... --apply` now runs the full validation battery (structure + families + tiers) before stamping and refuses to stamp a map that fails any of them.
- `.github/mozart/INTEGRATION.md` — the installed-map hand-edit guidance corrected: editing only `.github/mozart/config/model-map.jsonc` in an installed copy moves the runtime family assert but not the agents' pinned `model:` frontmatter (the stamper isn't installed — D14). Documents both real options and states which is recommended.
- `scripts/check_agents.py` — D10 enforcement completed: exactly one `user-invocable: true` agent, it must be named `mozart` (roster-level checks for zero and for a wrong name), and `mozart` must hold the `agent` tool with a non-empty `agents:`; any non-mozart agent with a non-empty `agents:` or the `agent` tool is now rejected. A new negative fixture (`invalid-non-mozart-dispatch-authority.agent.md`) proves the non-mozart-usurpation case via `--self-test`; the mozart-positive-requirement and the two roster-level cases were verified directly (not as committed fixtures — a filename-based negative fixture literally named `mozart.agent.md` can't carry the `invalid-*` glob prefix `--self-test` discovers by). `--check-carve` now independently asserts the upstream source's line range and character total (hardcoded plan constants, with a live re-derivation from the upstream file cross-checked when present) rather than trusting the TSV header as authoritative — the header is a cross-check now, not the source of truth.
- `.github/agents/jackson.agent.md` — a mistranslation fixed: jackson has `agents: []` and cannot dispatch subagents; "parallel subagent dispatch" reworded to upstream's actual meaning (batching independent tool work / parallel streams under mozart's coordination).
- `.github/mozart/VERSION` bumped to `0.1.0` to match this changelog; `.github/mozart/README.md`'s membership-contract wording reconciled with the runtime-reads manifest's classes; `.github/mozart/PIPELINE.md`'s "not personas" wording for support agents corrected — they are real `.github/agents/*.agent.md` personas and count toward the 22-agent roster.
- **`deep-reviewers` tier "exception" removed — it was never real.** `agents/README.md`'s Model column lists `bob`/`ruby`/`valerie` as `sonnet`; their actual `model:` frontmatter reads `opus`, matching `harry`. All four `deep-reviewers` members are upstream opus. `tests/fixtures/upstream-tiers.tsv` is now transcribed from frontmatter, not the stale README column; `--check-tiers`'s `deep-reviewers`-only upgrade carve-out is removed — exact tier match applies uniformly, `sebastian` exempt by name. A non-gating DATA cross-check reports the three README/frontmatter disagreements without failing CI.
