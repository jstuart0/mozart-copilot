# Counterpoint review (cross-model gate)

Replaces the Claude Code edition's "Codex availability and use" section
entirely — not a translation of it. That section was about the mechanics of
a shelled-out CLI: probing whether a binary was on `PATH`, closing stdin so
a background process didn't hang forever, arming an OS-level kill-timer,
polling an output file for growth, and a five-shape success-detection
contract built around exit codes and file existence. Sebastian has none of
that shape. It's a native subagent, dispatched and lifecycle-managed by the
harness exactly like every other specialist. There's no process to hang, no
stdin to leave open, no file to poll. Load-bearing anyway — it is the single
most consequential gate in the pipeline, having repeatedly caught Criticals
the internal reviewers missed — just load-bearing for a different, simpler
set of reasons.

**Skipping sebastian is the single most common pipeline regression — and
almost always wrong**, exactly as it was for the CLI-based predecessor. The
tier policy below is unchanged from upstream for that reason.

## Why cross-model, and why it has to actually be cross-family

The internal review panel (bob, dexter, xander, ruby, otto, tessa, percy —
whichever the plan's surface triggers) all run on the same model family as
the builder who produced the plan or the diff. A same-family reviewer shares
the builder's blind spots by construction — the same training biases, the
same classes of thing it's confident about for the same reasons. Sebastian's
entire value is being the second, independent voice: a model from a
*different* family reading the same material with no shared blind spot.

That value evaporates if `validation`'s role happens to resolve to the same
family as `builders`. D8's cross-family invariant exists to make that
impossible by construction, not by convention: **before every dispatch,
mozart reads `.github/mozart/config/model-map.jsonc` and refuses to
dispatch sebastian if `roles.validation.family == roles.builders.family`.**
This is a hard stop, not a warning — if it fires, the campaign halts at
this gate with the reason recorded in the state file, and the user resolves
it (fix the map, or explicitly accept the same-family read) before the
campaign proceeds. `scripts/apply_models.py --check-families` asserts the
same invariant at build time; the runtime assert here is the belt to that
suspenders, because a map that validated at build time can still have been
hand-edited since.

## The input contract (why it exists, and what it is)

Sebastian has `tools: [read, search]` and nothing else — by design (D1).
It reads adversarial content: an untrusted diff, third-party package
sources it's cross-checking for a supply-chain-adjacent bug. Shell access is
the one capability a reviewer of untrusted content must never have.

That constraint has a real cost: a `read`/`search`-only agent cannot reach
`node_modules/` (conventionally gitignored, excluded from workspace search)
or an out-of-tree Python virtualenv. Without a way around that, the
integration-contract sweep — verifying an external SDK or wire-protocol call
shape against the *installed* package version rather than remembered
documentation — degrades silently to exactly what it exists to catch: an
answer from memory dressed up as an answer from evidence.

So mozart, which has `execute`, pre-computes sebastian's inputs and hands
them over as files, written to
`.mozart/plans/active/<slug>.counterpoint-r{1,2}-inputs/` **before
dispatch**:

- the plan path
- `diff.patch` — a pre-computed `git diff <base>...HEAD` (round 2 only; there's no diff yet at round 1)
- `consumers.txt` — pre-computed consumer-audit searches (every language in the repo, plus adjacent repos `AGENTS.md` names)
- `installed-versions.txt` — **round 2, first pass of the campaign only**: the installed-dependency manifest (`npm ls --depth=0`, `pip freeze`) plus the resolved on-disk paths of every package the integration-contract sweep must inspect

Sebastian reads these paths. It never shells out and never writes anything
but its own response. **If `installed-versions.txt` is absent or empty on
a round-2 first pass, sebastian reports the integration-contract sweep as
`not performed`** rather than answering from memory — turning a silent
degradation into a visible one that the human reading the review can act on.

## Success detection — attestation-based, not process-based

There is no exit code, no target file to poll for existence, no kill-timer.
Sebastian succeeded **iff**:

(a) the response opens with `MODEL-ATTESTATION: <provider>/<model-id>` on
its own first line;
(b) that provider **differs from the attested provider of the builders**
who produced the work under review — compare attested-to-attested; the
model map's declared family is the fallback only when a builder's
attestation is missing, never the primary source of truth once an
attestation exists;
(c) the response contains at least one severity header
(Critical/High/Medium/Low);
(d) it ends with exactly one verdict (proceed / iterate / block).

**Any other shape is not a clean pass.** Attestation missing, `unknown`, or
matching the builders' family: surface the attested values to the user once
and let them decide whether to proceed — never auto-resolve a mismatch by
re-reading the model map and pretending the attestation didn't say what it
said. The whole point of attesting is to catch the case where the
frontmatter-declared model silently isn't the one that ran (see
`docs/COPILOT_PORT.md`, Known quirks — quirk 1).

## Stage-exit contract

When sebastian succeeds, do all of this **in one operation**, before moving
on: (a) tick the stage checkbox (`5. Counterpoint on plan` or `9.
Counterpoint on diff`); (b) write the review to
`.mozart/plans/active/<slug>.counterpoint-r{1,2}-plan.md` /
`-diff.md` and update the state file's `Counterpoint r1 (plan)` /
`Counterpoint r2 (diff)` line in the `Paths` block to that path; (c) append
an entry to the state file's **attestation ledger** recording sebastian's
attested model for this stage; (d) append the stage-trace entry to the flow
sketch citing the verdict and the finding count by severity.

Header-vs-checkbox drift — `Paths` still says "not yet run" while the
checkbox is ticked — is the #2 audit-finding pattern in the upstream
multi-repo evaluations that shaped this discipline. It misleads a future
mozart on resume. Doing all four updates in one operation is what prevents
it.

## The attestation ledger

The state file (`.github/mozart/manual/STATE.md`) carries an `##
Attestation ledger` table: one row per subagent dispatch this campaign,
recording the stage, the agent, its role, its attested model, and whether
that attestation matched the frontmatter-declared `model:`. This is what
lets mozart (and a human reading the state file after the fact) confirm
sebastian's family actually differed from the builders' — not merely that
the map said it should have.

## Tier policy (verbatim from the Claude Code edition)

- **TINY**: skip.
- **STANDARD**: default-run — skip only on sub-50-LOC mechanical diffs where
  the plan was trivial and internal reviewers were clean.
- **HEAVY**: **non-negotiable** — not "mandatory" with a soft override.
  Skipping this stage on HEAVY is a self-detected gate failure that requires
  escalation, never a runtime mozart decision. "Mid-build covered it,"
  "context pressure," and "the diff is mechanical" are not valid skip
  reasons. Either the review runs, or the campaign stops at `Status:
  stopped` with a state-file note explaining the blocker and resumes in a
  fresh session.

## Iteration (round 1 only — see the DELIVER pipeline's stage 6)

Short-circuit if internal reviewers + sebastian are all clean (no
Critical/High). Otherwise, brief the live harry again if the harness's
continuation preserves context (see `.github/mozart/manual/FLOWS.md`);
brief-from-artifacts otherwise. Re-run sebastian only if the revisions are
substantive — writes `<slug>.counterpoint-r1b-plan.md`, etc. Cap: 3 rounds,
same as every iteration cap in this pipeline.

## What was deliberately deleted, and why

The Claude Code edition's "External tool execution" section (upstream
`agents/mozart.md:1111-1126`, 4,846 characters) — the stdin-closing,
kill-timer-arming, output-file-polling discipline for running a long
external CLI safely in the background — has **no destination file in this
port**. It is the one section of the upstream conductor persona carved out
with nowhere for it to land, because sebastian is a native subagent with a
harness-managed lifecycle, not an external process mozart has to babysit.
Porting that discipline would be solving a problem this architecture doesn't
have. See `docs/COPILOT_PORT.md` for the full rationale.
