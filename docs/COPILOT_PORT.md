# The GitHub Copilot port — mapping, rationale, and known quirks

> v1 (Phase 8 — port complete). This document is the source of truth for how
> mozart's Claude Code edition maps onto GitHub Copilot's primitives. It is a
> build-time reference — it lives at the repo root and is never copied into
> an installed bundle (D14).

## Verdict

The port is feasible with native primitives, not a workaround. Copilot's
subagent mechanism (`agents:` allowlist + the `agent` tool) covers the
dispatch mozart needs; parallel subagent invocation covers fan-out; the
external cross-model reviewer — a shelled-out CLI in the Claude Code edition
— becomes a native in-process subagent (`sebastian`) here, which is a
*strictly simpler* mechanism (no process lifecycle, no stdin/kill-timer
discipline) at the cost of losing shell access for that reviewer, which this
port never wanted to grant it anyway (D1). The two open risks are
unverified, not unfeasible: whether `disable-model-invocation`'s one
documented sentence means what this port assumes (verify-at-implementation,
step 11), and whether the Copilot CLI's `/fleet` can drive mozart's dispatch
protocol at all (out of scope for v1 — D13).

## Primitive mapping

The Claude Code tool noun on the left is what upstream personas declare in
`tools:`; the Copilot tool/tool-set on the right is what this port declares.
Source of truth: `config/toolsets.jsonc`, cross-checked against this table by
`scripts/check_agents.py --check-doc-table`.

| Claude tool | Copilot | note |
|---|---|---|
| `Read` | `read` | |
| `Grep` | `search` | search/codebase, search/usages |
| `Glob` | `search` | search/codebase, search/usages |
| `LS` | `search` | search/codebase, search/usages |
| `Edit` | `edit` | |
| `Write` | `edit` | |
| `Bash` | `execute` | execute/runInTerminal |
| `WebFetch` | `web` | web/fetch |
| `WebSearch` | `web` | web/fetch |
| `TodoWrite` | `todos` | |
| `Task` | `agent` | conductor only; requires non-empty `agents:` |
| `SendMessage` | (no analog) | brief-from-artifacts |
| `MCP server` | `<server>/*` | optional example only (product-neutral) |

`Grep`/`Glob`/`LS` collapse to one Copilot tool set (`search`); `Edit`/`Write`
collapse to `edit`; `WebFetch`/`WebSearch` collapse to `web`. A persona that
listed five or six Claude Code tool nouns typically ends up with three or
four Copilot entries — that's the mapping working as intended, not a
narrowing.

## The `.agent.md` schema (confirmed)

Verified live on 2026-09-01 against `code.visualstudio.com/docs/agent-
customization/custom-agents` and the Copilot VS Code features cheat sheet.
Full frontmatter vocabulary: `description`, `name`, `argument-hint`, `tools`,
`agents`, `model`, `user-invocable`, `disable-model-invocation`, `target`,
`mcp-servers`, `handoffs`, `hooks`.

This port uses six of those twelve fields; the rest are available to the
schema but unused in v1:

| field | used here | how |
|---|---|---|
| `name` | yes | must equal the filename stem (`bob.agent.md` → `bob`) |
| `description` | yes | ~30–50 words, no jokes — what a reader sees browsing `.github/agents/` |
| `tools` | yes | explicit on every persona, never omitted (Copilot's omit-means-all default would silently over-grant) |
| `model` | yes | a scalar string, never a YAML sequence (see Known quirks) |
| `agents` | yes | `[]` on every specialist; mozart's full allowlist |
| `user-invocable` | yes | `true` on exactly one file (`mozart.agent.md`); `false` on every specialist (D10) |
| `disable-model-invocation` | no (left at default) | see Invocation policy below |
| `argument-hint`, `target`, `mcp-servers`, `handoffs`, `hooks` | no | no v1 persona needs them; `mcp-servers` stays unused because this repo is product-neutral (an MCP example lives only as a mapping-table row, never a named server in a `tools:` line) |

## Bundle namespace and the build-time/runtime config split (D9, D14)

**Single resolution path.** Every file any agent reads at runtime lives under
`<workspace>/.github/mozart/` — one namespace, one path, no fallback, no
search order in v1. If the bundle is absent from a workspace, an agent stops
and names the missing path; it does not improvise. `.github/mozart/README.md`
states the membership contract in one sentence: everything under it is a
runtime read and installs with the bundle; nothing outside it is.

**Why one path and not two.** An earlier revision of this plan added a
second resolution step — an agent falling back to `~/.copilot/agents/`'s
sibling `~/.copilot/mozart/` when the workspace bundle is missing. That
second step depends on a capability this port cannot verify: whether an
agent's `read`/`search` tools, which VS Code scopes to the current workspace,
can reach outside it at all. The harness *loading agent definitions* from a
user-scope directory is a different capability from an *agent's own tool
calls* reaching outside the workspace, and conflating them would ship a
fallback that reads as coverage and silently isn't. So v1 ships **one**
resolution path. `--user-scope` installs agent *definitions* only (the
verified harness path, `~/.copilot/agents/`) and prints that the bundle
itself is still workspace-scoped and must be installed per-repo. The
two-step form is documented here as **designed-for-v2, unvalidated** — Open
question 2(d) in the campaign plan names validating it as a named follow-up,
not a promise.

**Root-vs-bundle divergence from the Codex CLI edition.** `mozart-codex`
keeps `INTEGRATION.md` and `PIPELINE.md` at its repo root, because that port
is used from a clone and its harness resolves its own base-instructions file
by directory walk. This port is designed to be *installed into someone
else's repository*, where a repo-root file this port ships would collide
with (or simply be invisible next to) that repository's own files. So every
document an agent reads at runtime — `PIPELINE.md`, `LEARNINGS.md`,
`INTEGRATION.md`, `EVAL.md`, `VERSION`, the active model map — lives inside
the bundle, and nothing agent-read duplicates at repo root. This repo's own
root `README.md` links into the bundle rather than containing the content
itself.

**Build-time vs runtime, one canonical location per file** (D14): a file is
either read by an agent at runtime — and lives in the bundle — or it's a
build-time-only input to the validator/stamper/tests — and lives at the repo
root, never installed. The active model map is the one file with two
readers (mozart reads it at runtime for the family assert; `apply_models.py`
writes it at build time), which is exactly why it lives inside the bundle:
a repo-root location would resolve for the stamper and not for the
conductor. `scripts/check_agents.py --check-install` enforces this
mechanically once the runtime-read manifest exists (Phase 5): every runtime
read must resolve inside the bundle, and the installed tree must have no
`config/`, `tests/`, or `scripts/` of its own.

## Invocation policy (D10)

Exactly one agent is `user-invocable: true` — **mozart**. All specialists are
`false`, reachable only through mozart's `agents:` allowlist, so intake,
tiering, the counterpoint gate, worktree isolation, ticket lifecycle, and PR
authorization can't be routed around. The upstream single-agent passthrough
survives: a user can still say "have bob look at this plan," and mozart
routes it directly without imposing pipeline overhead.

**`disable-model-invocation` stays at its documented default (unset,
effectively `false`) on every persona.** The one documented sentence for
this field is that it "prevents subagent invocation by other agents" — under
that reading, setting it on a specialist would prevent mozart from
dispatching it, which would disable the orchestra outright. That reading is
**single-source and unverified**. `false` is the safe value under either
plausible reading (either it does nothing extra, or it correctly leaves
mozart's dispatch path open), so nothing downstream depends on resolving the
ambiguity before shipping.

**`disable-model-invocation` confirmation — PENDING MANUAL.** Step 11 of the
campaign plan calls for confirming this field's actual behavior against an
installed VS Code build (does it block *user* invocation, *agent*
invocation, or both?) before the exemplar personas ship. That confirmation
requires a human with Copilot access in VS Code and has **not** been run —
it is not guessed at here. It is carried forward as a Manual verification
item (see the campaign plan's Manual checklist) rather than asserted. Because
the default value is safe under either reading, this port ships without
waiting on it.

**Surface caveat**: `user-invocable` is a VS Code field. Under the Copilot
CLI (out of scope for v1 runtime — see Runtime-surface matrix), specialists
may remain directly addressable via `--agent=<name>`, so this policy binds
where v1 claims support and is documented as not binding elsewhere.

## Runtime-surface matrix (D13)

| surface | status | notes |
|---|---|---|
| VS Code | **supported** | the only runtime this port designs and validates against |
| Copilot CLI | **loads-but-unvalidated** | agent files are read, the roster appears, `--agent=mozart` runs; whether the dispatch protocol works under `/fleet` is not claimed |
| Cloud coding agent | **out of scope** | ignores `model:`, has no subagent primitive; a documented asymmetry, not a v1 target |

`user-invocable` may not bind on the CLI (see Invocation policy). Designing
a CLI-specific orchestration protocol now would mean writing against
semantics this campaign cannot test — deferred, not rejected.

## Translation rules

Nine rules, applied to every ported persona and every bundle document:

1. **`CLAUDE.md` → `AGENTS.md`** — the base-instructions filename a
   consuming repo's stanza lives in.
2. **Tool nouns → `config/toolsets.jsonc`** — see Primitive mapping above.
3. **`ToolSearch` framing → "tool-set / MCP availability"** — Copilot has no
   deferred-tool-loading concept; a persona's `## Code retrieval` section is
   rewritten around "does this workspace expose a finer-grained search tool"
   rather than a specific loading mechanism.
4. **"single parallel tool-call message" → "parallel subagent dispatch"** —
   the underlying behavior (fan out independent work in one turn) is
   identical; only the vocabulary describing the primitive changes.
5. **Frontmatter always explicit** — `tools:` never omitted, `model:` always
   a scalar string, `agents: []` on every specialist, `user-invocable: false`
   on every specialist.
6. **`## Code retrieval` generalized** — no product-specific index named;
   every ported persona's retrieval guidance is harness-generic.
7. **The external cross-model reviewer's name changes** (9 upstream files
   reference it): the shelled-out CLI reviewer becomes `sebastian`, the
   native in-process counterpoint subagent (D1, D2).
8. **Bundled-doc references → `.github/mozart/...`** — every reference to a
   pipeline, learnings, or integration document is rewritten to its bundle
   path; nothing agent-read is cited at repo root (D9).
9. **Add `## Model attestation`** — every persona gains the section defined
   below, addressing the subagent model-fallback quirk.

## The counterpoint reviewer (D1, D2)

`sebastian` (J.S. Bach — counterpoint's master; a first name, matching the
roster) is the independent second-model read on a plan (round 1) and a diff
(round 2), reproducing the value the Claude Code edition's external CLI
reviewer provided: a model from a *different family* than whichever family
produced the work, running a fixed battery of contract checks a same-family
per-commit reviewer structurally can't substitute for.

**Toolset: `read, search` only — never `execute`.** Sebastian reads
adversarial content by design: an untrusted diff, third-party package
sources it's cross-checking for a supply-chain-adjacent integration bug.
Shell access is the one capability a reviewer of untrusted content must
never have. That constraint has a real cost, addressed by the input
contract below.

**Why the input contract exists.** A `read`/`search`-only reviewer cannot
reach everything the integration-contract sweep needs to see:
`node_modules/` is conventionally gitignored and excluded from workspace
search, and a Python virtualenv frequently lives outside the workspace
entirely. Without a way around that, the sweep — verifying an external SDK
or wire-protocol call shape against the *installed* package version rather
than remembered documentation — degrades silently to exactly what it exists
to catch. So mozart, which has `execute`, pre-computes the reviewer's inputs
and hands them over as files:

- the plan path
- `diff.patch` — a pre-computed `git diff <base>...HEAD`
- `consumers.txt` — pre-computed consumer-audit greps
- `installed-versions.txt` — the installed-dependency manifest (`npm ls
  --depth=0`, `pip freeze`) plus the resolved on-disk paths of every package
  the integration sweep must inspect

written to `.mozart/plans/active/<slug>.counterpoint-r{1,2}-inputs/` before
sebastian is dispatched. Sebastian reads these paths; it never shells out
and never writes. **If `installed-versions.txt` is absent or empty,
sebastian reports the integration-contract sweep as not performed** rather
than answering it from memory — a silent degradation converted into a
visible one.

**The four contract checks, ported from the Claude Code edition's reviewer
prompts** (round 1 plan-review and round 2 diff-review instructions in the
upstream conductor persona):

1. **Cross-language consumer audit** — for any public surface the plan/diff
   gates, renames, removes, or restricts, find every consumer in every
   language in the repo (plus adjacent repos the base-instructions file
   names) and flag any consumer in a non-admin context that would break.
2. **Response-shape contract check** — for any endpoint split, replaced, or
   duplicated, verify the new response shape matches the old one, or that
   the divergence is documented; a static-language cast is not a runtime
   contract.
3. **Immutability check** — for any change to a Kubernetes manifest field on
   an existing stateful resource, flag whether the field is immutable and
   whether a recreation/migration step is present.
4. **Integration-contract sweep** — **required on round 1** (the first
   diff-review pass of a campaign, not a later re-run): for every external
   SDK or wire-protocol call site the diff touches, verify the call shape
   against the *installed* package version — not remembered documentation —
   using the resolved paths in `installed-versions.txt`. A green mocked test
   suite is not evidence for this check.

Plus the **wiring-sites exhaustiveness check**: the plan's `Pattern parity /
wiring sites` section must enumerate every existing site a new pattern
should reach, and sebastian's cross-language consumer audit is the pass
that verifies that enumeration is exhaustive, not just that the sites listed
are correct.

**NET-NEW framing**: mozart briefs sebastian with what the internal panel
already found (one line per finding), so sebastian spends its budget on
issues the internal panel didn't already catch rather than re-deriving them.

**Output contract**: the response opens with the attestation line, then
severity-tagged findings (Critical/High/Medium/Low), then exactly one
verdict — proceed, iterate, or block.

## Why external tool execution is deleted, not ported

The Claude Code edition dedicates a whole conductor section to the discipline
of running a long external CLI process safely in the background: closing
stdin so the process doesn't hang forever waiting on it, arming an
OS-level kill-timer at launch, backgrounding the call, polling output-file
growth every few minutes, and a documented escalation path when the process
stalls or the kill-timer fires. All of that exists because the reviewer was
an *external process* — a binary invoked over a shell, with its own
lifecycle, its own hang modes, and no supervision from the harness beyond
what mozart built by hand.

Sebastian has none of that shape. It's a native subagent, dispatched the
same way every other specialist is dispatched, with its lifecycle managed by
the harness like any other subagent invocation. There's no process to hang,
no stdin to leave open, no kill-timer to arm, and no output file to poll for
growth — the harness returns sebastian's response when it's done, the same
way it returns any subagent's response. Porting the stdin/kill-timer/polling
discipline into this edition would be solving a problem this architecture
doesn't have. It is deliberately **deleted**, not translated — the one
section carved out of the upstream conductor body with no destination file
at all (see the campaign plan's fence-aware section map, upstream lines
1111–1126, 4,846 characters).

## Per-agent toolset rationale

| agent | tools | why |
|---|---|---|
| `jackson` | `read, search, edit, execute, web` | builder — writes code, runs tests/lints/builds, fetches external docs when a task calls for it. Direct translation of the upstream `Read, Grep, Glob, Edit, Write, Bash, WebFetch` set through the primitive mapping |
| `bob` | `read, search` | read-only architectural review (D4). Upstream's `bob` carries `Edit` for "update the plan file directly with your corrections"; this port narrows that away deliberately — bob's deliverable is findings and a verdict, and harry (or mozart) applies the resulting plan edit. The narrowing is stated in bob's own body, not silently dropped |
| `sebastian` | `read, search` | D1 — a reviewer of adversarial content (an untrusted diff, third-party package sources) must not be able to act on what it reads. Its one structural gap (reaching `node_modules`/an out-of-tree venv) is closed by mozart's pre-computed input contract, not by widening sebastian's own toolset |
| `dexter`, `ian`, `codebase-analyzer`, `codebase-pattern-finder` | `read, search` | static reading only — code-health audit, change-impact tracing, and codebase documentation never need to write or run anything |
| `codebase-locator` | `search` | path/name lookup only; it doesn't even read file contents by design ("Don't read file contents" is one of its own rules), so it doesn't get `read` either |
| `xander`, `sarah` | `read, search, web` | external research (advisory lookups, best-practices research); no command need — xander vets dependencies via registries and advisory feeds, not by running anything locally |
| `web-search-researcher` | `read, search, web, todos` | as upstream — `todos` because it tracks multi-step research queries |
| `librarian` | `read, search` | **narrowed** (D4) — upstream's `Bash` had no stated use in the verdict-producing work; its one real use was the greenfield quick-check's `git log`/`find` commands, which this port approximates with a `search`/`read`-based file-count and README/CHANGELOG skim instead. Grep-shaped, not shell-shaped, archaeology |
| `valerie` | `read, search, execute` | runs the plan's Automated commands — that *is* her job (deep-reviewers role, upstream opus tier) |
| `otto` | `read, search, execute` | `kubectl apply --dry-run=server`, `helm template`, `helm search repo --versions` |
| `percy` | `read, search, execute, web` | measurement-first: `EXPLAIN`, bundle deltas, load probes; `web` for release-note/advisory lookups |
| `tessa` | `read, search, execute, edit` | runs suites to assess seams; `edit` for her own findings doc and, in TDD mode, the test contract — never source or test files (Copilot's `edit` is coarser than Claude Code's `Write`/`Edit` split; the boundary is now a stated discipline in her body rather than a capability wall — see her persona) |
| `harry`, `ruby` | `read, search, edit, execute, web` | deep-reviewers (upstream opus tier). Harry writes the plan file directly; ruby implements and verifies UI in a browser — both need the full builder set |
| `hank`, `scott` | `read, search, edit, execute, web` | builders (upstream sonnet tier). Hank mutates live infrastructure (`kubectl`, `helm`) and edits config in place; scott edits in-repo docs, clones/pushes the GitHub wiki, and calls external wiki APIs |
| `dick` | `read, search, execute, web` | reviewers tier — investigates read-only. Deliberately **no** `edit`: "You do not have Edit or Write for source code. You cannot fix the thing you found. That's the point" is upstream's own framing, and it holds unchanged under this port's coarser `edit` grant because dick never receives one |

## The model map

**Headline: `validation` always runs the non-builder model family, and it's
a hard gate, not a convention.** The canonical active map lives at
`.github/mozart/config/model-map.jsonc` — read at runtime by mozart before
every counterpoint dispatch (the family assert) and written at build time by
`scripts/apply_models.py --apply` (D14, one file two readers). Seven roles
reproduce upstream's three model tiers exactly (D3) — five or six roles
would silently re-tier someone:

| role | claude-bulk (shipped active map) | gpt-bulk |
|---|---|---|
| `conductor` | Claude Opus 4.5 | GPT-5.4 |
| `deep-reviewers` | Claude Opus 4.5 | GPT-5.4 |
| `builders` | Claude Sonnet 4.5 | GPT-5.3-Codex |
| `reviewers` | Claude Sonnet 4.5 | GPT-5.3-Codex |
| `support` | Claude Sonnet 4.5 | GPT-5.3-Codex |
| `fast-scan` | Claude Haiku 4.5 | GPT-5.4-mini |
| `validation` | **GPT-5.4** | **Claude Opus 4.5** |

Flip the entire roster's family with one command, and `validation` flips
with it, in the opposite direction, automatically — that's the whole point
of shipping the switch as two presets rather than one hand-edited map:

```sh
python3 scripts/apply_models.py --preset claude-bulk --apply   # 21 builders/reviewers on Anthropic, sebastian on GPT-5.4
python3 scripts/apply_models.py --preset gpt-bulk --apply      # 21 builders/reviewers on OpenAI,    sebastian on Claude Opus 4.5
```

`apply_models.py --check-families` exits 1 the moment `roles.validation.family
== roles.builders.family` — a same-family counterpoint review is a
contradiction of what sebastian is *for* (D8), so this is enforced as code,
not left as a documentation warning a preset author could forget.

**The `deep-reviewers` tier exception.** `--check-tiers` asserts every
agent's role matches its upstream Claude-edition tier *exactly* — an
undisclosed upgrade is caught the same as an undisclosed downgrade (Phase 6
found this the hard way: see Implementation notes below). `deep-reviewers`
is the one disclosed exception. Its four members are `harry` (upstream
opus — no change), plus `bob`, `ruby`, and `valerie` (upstream sonnet,
deliberately stamped up to this port's opus tier). That decision was made
once, in Phase 2's exemplar stamping (`bob`), carried through every
subsequent phase, and is now the encoded invariant `--check-tiers` protects:
`deep-reviewers` may sit *at or above* its members' upstream tier; every
other role must match exactly, in either direction.

**Model-id string convention.** The plan's role table gives human-readable
model names, not literal API identifiers — those are user-edited and
conservative-double-sourced by design (Context, "What we're assuming"). This
port derives a scalar `model:` string mechanically from the display name:
lowercase, spaces to hyphens, dot preserved (`Claude Sonnet 4.5` →
`claude-sonnet-4.5`, `GPT-5.4` → `gpt-5.4`, `GPT-5.3-Codex` →
`gpt-5.3-codex`). `apply_models.py` validates every role's `model` as shape
only (a non-empty scalar string) — never membership in a hard-coded ID list
— so this convention is a stamping default, not a validated constraint; edit
`.github/mozart/config/model-map.jsonc` directly, or a preset in
`config/model-maps/`, for your org's actual model policy.

Every role also carries a same-family `fallback`, surfaced by
`apply_models.py --explain` and never itself stamped into a persona's
`model:` — for when the primary is org-disabled or deprecated (a real risk:
global model policy went GA 2026-08-26).

- `jackson` — role `builders` → `claude-sonnet-4.5`
- `bob` — role `deep-reviewers` → `claude-opus-4.5` (the tier exception)
- `sebastian` — role `validation` → `gpt-5.4` (the non-builder family, D8)

## Model attestation

Canonical text, copied verbatim into every persona's `## Model attestation`
section:

> Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its
> own first line, where `<provider>` is `anthropic` or `openai`. If you
> cannot determine your own model, emit `MODEL-ATTESTATION: unknown` rather
> than guessing. This line exists because a subagent's `model:` frontmatter
> can silently fall back to the parent's (see Known quirks) — the
> attestation is what lets mozart detect that at runtime instead of trusting
> the frontmatter blindly, and it's what lets mozart confirm sebastian's
> family actually differs from the builders' rather than merely asserting it
> (D8).

## Known quirks

1. **Subagent `model:` can silently fall back to the parent's.** A
   dispatched subagent has been observed running under its parent's model
   rather than its own declared `model:` (tracked upstream as
   vscode#307572, community #191450). `## Model attestation` on every
   persona is this port's mitigation: mozart compares the attested model
   against the frontmatter-declared one after every dispatch rather than
   trusting the frontmatter alone.
2. **`model:` as a YAML sequence is a hard failure, not a silent
   coercion** (github/copilot-cli#2133) — `scripts/check_agents.py` asserts
   `model:` is a scalar string and fails explicitly, rather than letting a
   list silently resolve to something unintended.

## Corrected body-size figure

The upstream conductor persona (`agents/mozart.md`) is cited in the research
brief as "~143KB." Measured with the character-accurate two-delimiter
extractor and `wc -m` (not the lossy `awk 'NR>1 && /^---$/{p=1;next} p'` +
`wc -c` combination the first plan revision used, which double-counts
nothing but under-measures by dropping every bare `---` line after the
frontmatter and overstates nothing while still landing on the wrong number
by conflating bytes with characters), the true figure is **241,189
characters** — about 66% larger than the brief's estimate. This is why
`agents/mozart.md` needs an 8× reduction (to fit the 30,000-character body
cap) rather than the roughly 5× the stale estimate would have implied, and
why the campaign plan treats every body-size claim as a number to
re-measure, never one to trust from a prior document.

## Measured splits

Three personas needed the fence-aware overflow discipline the plan
pre-designated, all measured with the same two-delimiter-extractor +
`wc -m` convention as the upstream figure above:

- **`mozart`** — the conductor. The 2,400-line, 241,189-character upstream
  body is carved into 14 `manual/` reference files, retained conductor-body
  sections, and one deliberate deletion (see below). Final measured body:
  **22,392 characters** — 5% under the 23,589-char target, 25% under the
  30,000-char hard cap. None of the plan's three pre-designated overflow
  steps (Consistency lens → `manual/WIRING-SITES.md`; Orchestration
  discipline split; narration cadence → `manual/NARRATION.md`) were needed.
- **`scott`** — the technical writer. Two sections moved to persona-private
  bundle files: `## Pull request authoring` (25,681 chars) →
  `.github/mozart/agents/scott/PR-AUTHORING.md`, `## Page templates`
  (2,376 chars) → `.github/mozart/agents/scott/DOC-TEMPLATES.md`. Final
  measured body: **22,697 characters**. The plan's pre-designated third
  overflow block (`## External wiki workflow`, 2,610 chars →
  `EXTERNAL-WIKI.md`) never fired — scott stayed under the warn band with
  two moves, not three.
- **`harry`** — the planner. Upstream body measured 28,525 chars, over the
  27,000-char warn band. The plan's step-18 **headroom guard fired**: the
  Consistency lens content moved to `.github/mozart/agents/harry/PLAN-TEMPLATE.md`.
  Final measured body: **26,184 characters**, back under the warn band. This
  is the one persona whose pre-designated overflow move actually triggered —
  `tests/runtime-reads.tsv` carries the resulting `harry` ×
  `agents/harry/PLAN-TEMPLATE.md` row as a real citation, not a hypothetical
  one (confirmed in the Phase 5 runtime-reads reconciliation).

## Implementation notes

Three check-tool defects were found by exercising the validators against
real content rather than only the fixture corpus — each is recorded here
because the fixture corpus alone would not have caught any of them:

1. **Model-map path-stripping (Phase 5).** `find_outside_bundle_violations()`'s
   `model-map` token cleanup used `.strip("...")`, which removes matching
   characters from *both* ends — including the meaningful leading `.` in
   `.github/mozart/config/model-map.jsonc`. Latent since Phase 1; never
   triggered until `mozart.agent.md` became the first persona to legitimately
   cite the canonical path. Fixed to `.rstrip(".,;:)")` (trailing prose
   punctuation only).
2. **`EVAL.md` basename collision (Phase 5).** The same function assumed
   every tracked bundle-doc basename has exactly one canonical location.
   `EVAL.md` legitimately has two — `.github/mozart/EVAL.md` (the
   ledger/report schema) and `.github/mozart/manual/EVAL.md` (the pipeline
   procedure), a distinction `manual/INDEX.md` calls out explicitly. Fixed by
   replacing the single-prefix check with a per-basename set of valid
   prefixes.
3. **`--check-install` never re-scanned the installed copy's own agent files
   (Phase 7).** It only verified that this repo's already-committed
   `runtime-reads.tsv` rows resolve inside the target directory — a file
   planted directly into the installed copy's `.github/agents/` (never
   indexed into this repo's manifest) passed silently. Confirmed
   experimentally before fixing: planting
   `tests/fixtures/invalid-outside-bundle-read.agent.md` into a simulated
   install and re-running `--check-install` returned 0, not the required 1.
   Fixed by having `cmd_check_install` additionally scan the installed
   directory's own `.github/agents/*.agent.md` bodies with the existing
   `find_outside_bundle_violations()`.

Two further corrections, scoped to `apply_models.py` rather than
`check_agents.py`, from Phase 6: `--map` silently ignored a combined
`--min-agents` flag because `main()`'s dispatch returned on the first
matching flag (fixed by threading `min_agents` into `cmd_map` directly); and
`--check-tiers`'s first design ("no downgrade below upstream tier") was too
loose to catch an *upward* undisclosed retier, caught by the pre-existing
`tests/fixtures/map-retiered.jsonc` scaffold's own documented scenario —
redesigned to the exact-match-except-`deep-reviewers` rule described above.

## Pending manual verification

Every item below requires a human with Copilot access; none can be
mechanically checked, and this port does not claim they've passed:

- **`disable-model-invocation` semantics** — not yet confirmed against an
  installed VS Code build (step 11). Carried as a Manual item; see Invocation
  policy above for why nothing ships blocked on it.
- **Agent picker scope** — open this repo in VS Code with Copilot and
  confirm only `mozart` appears in the agent picker, and that it dispatches
  specialists successfully.
- **Model availability** — confirm every model ID in the active map appears
  in your org's model picker; enterprise policy can disable models
  org-wide, and no script can query this.
- **Real-repo install** — `scripts/install-bundle.sh --target <repo> --apply`
  into a real work repo, then confirm mozart resolves
  `.github/mozart/manual/INDEX.md` on its first turn, and that the family
  assert reads `.github/mozart/config/model-map.jsonc` from the installed
  copy (not a cached or stale one).
- **Cross-family validation in practice** — run a TINY DELIVER end-to-end
  and confirm the model indicator VS Code shows for `sebastian` is actually
  the other family, not merely that its `MODEL-ATTESTATION` line claims so
  (see Known quirks — self-reported model identity is a signal, not
  ground truth).
