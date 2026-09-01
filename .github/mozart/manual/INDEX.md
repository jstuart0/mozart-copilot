# Manual index

Boot read #1, every run. Read this, then `INTAKE.md` (boot read #2), before doing
anything else. Everything else in this manual is read on demand — the
conductor body tells you when each one applies; this table is the map.

| File | What's in it | Read when |
|---|---|---|
| `INTAKE.md` | Shape-boundary disambiguation, single-agent passthrough, task tiers, project context (GREENFIELD/BROWNFIELD) | Every run, at intake (boot read #2) |
| `FLOWS.md` | Continuation-vs-fresh-dispatch detail, operating modes, build-time flags (TDD), partial flows, resume/entry points, run identification + prior-art discovery | Intake; whenever a partial flow, resume, or continuation decision comes up |
| `WORKTREES.md` | Worktree isolation (when/how to cut one, layout, who-runs-where), multi-campaign mode | Every code-changing campaign at intake; whenever running >1 campaign |
| `STATE.md` | State-file format, directory convention, in-progress-run detection at intake, resume discipline, the pipeline flow sketch (proposed/actual/deviations) | Creating or updating any state file or flow sketch; every intake's stale-run sweep |
| `CONTEXT-BUDGET.md` | The campaign-digest discipline for large-`AGENTS.md` repos | Intake, when `AGENTS.md` exceeds ~1,000 lines |
| `COUNTERPOINT.md` | The cross-model review gate: family assert, pre-computed input contract, attestation-based success detection, tier policy | Before dispatching sebastian at DELIVER stages 5/9 (or OPERATE's HEAVY pre-flight gate) |
| `DELIVER.md` | The 13-stage (+12b) DELIVER pipeline in full | Any DELIVER-shaped campaign |
| `AUDIT.md` | The AUDIT pipeline (discovery → fan-out → synthesize → decision point) | Any AUDIT-shaped campaign |
| `DIAGNOSE.md` | The DIAGNOSE pipeline (intake → investigate → decision point) | Any DIAGNOSE-shaped campaign |
| `OPERATE.md` | The OPERATE pipeline (intake+pin → recon → change plan → pre-flight → apply → verify → record) | Any live-system change or debug |
| `INCIDENT.md` | The INCIDENT pipeline (declare → stabilize ‖ race hypotheses → converge → durable fix → verify → post-mortem) | An active outage — mozart as incident commander |
| `manual/EVAL.md` (this directory) | The EVAL **pipeline procedure**: stages (scope → metrics → fix verification → sampling → synthesize → ledger) | Evaluating mozart's own field performance |
| `TICKETS.md` | Ticket lifecycle: when tickets are created, project resolution, body/comment templates, lifecycle responsibilities | Any commit-producing or investigation-producing run, when ticketing is configured |

Two files above `manual/` in the bundle, not listed in this table's rows
because they aren't part of the manual carve, but cited constantly from
inside it:

- `.github/mozart/PIPELINE.md` — full stage-by-stage roster reference (agent
  roster, stage tables) — the document every specialist persona cites for
  "the full reference"
- `.github/mozart/LEARNINGS.md` — the field-notes append-only protocol every
  persona's Field notes section points to
- `.github/mozart/INTEGRATION.md` — how a consuming repo declares ticketing
  / documentation surfaces / code retrieval / worktrees / pull-request
  authorization in its `AGENTS.md`
- `.github/mozart/EVAL.md` — the eval ledger **schema** and
  pipeline-economics reference. **Not the same file as `manual/EVAL.md`
  above** — that one is the procedure; this one is the schema. Conflating
  them is exactly how the runtime-read count drifted during planning; both
  are real, distinct, required reads.

Everything under `.github/mozart/` is a runtime read, per the bundle's
membership contract (`.github/mozart/README.md`). Nothing outside it is.
