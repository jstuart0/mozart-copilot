# Mozart's pipeline reference

Canonical reference for the multi-agent orchestration system bundled in this repo. **Mozart** is the conductor; this file documents the workflow it runs and the agent roster.

If you're an agent and you want to know where you fit, look at your own `<name>.agent.md` for the "Where you fit in mozart's pipeline" section. This file is the full picture.

## Shared operating principle: default to the best answer

**Unless the user explicitly asks for the quick / easy / temporary path, every agent in this system pursues the best, most complete, most intuitive solution.**

The "easy way" is the right answer only when:
- The user explicitly asks for a quick fix, prototype, hack, or temporary solution
- The task is genuinely throwaway (one-off script, exploration, scaffolding)
- The user has stated a constraint that rules out the better approach (deadline, scope, blast radius)
- The easy way *is* the best way (and the agent says so explicitly so it's a considered choice, not a shortcut)

In every other case: surface the better approach, even if it costs more time / tokens / effort. If the better approach exists but the user's constraints rule it out, name the gap explicitly so they can revisit later.

This applies across all agent work — architecture (bob), code health (dexter), security (xander), UX (ruby), infra (otto), cloud (nina), implementation (jackson), planning (harry), research (sarah), validation (valerie), change-impact (ian), and the orchestration mozart imposes on all of them.

When mozart briefs another agent, it carries this standard forward — it does not tell agents to "just do the simple version" unless the user has explicitly asked.

## Quick orientation

- **Default mode**: AUTONOMOUS (mozart runs end-to-end without pausing)
- **Loop-in mode**: per-phase user gate with explicit test instructions (triggered by "keep me in the loop," "step me through it," etc.)
- **Six work shapes**: DELIVER (build/ship code), AUDIT (review-with-goal), DIAGNOSE (investigate-a-failure), INCIDENT (respond to a live outage — mitigate-first, parallel, timeline + post-mortem), OPERATE (change/debug a live system), EVAL (mozart evaluates its own field performance)
- **Project context**: GREENFIELD (skip librarian) or BROWNFIELD (librarian runs at plan review and mid-build for new shared abstractions). Default BROWNFIELD when uncertain.
- **Multi-campaign mode**: mozart can drive 2–4 campaigns concurrently, each with its own slug, state file, plan, ticket, and git worktree.
- **Partial flows (early exit)**: FULL (default), PLAN-ONLY, RESEARCH-ONLY, INVESTIGATE-ONLY, AUDIT-ONLY, VALIDATE-ONLY.
- **Three DELIVER tiers**: TINY / STANDARD / HEAVY — mozart classifies at intake to right-size gates

## Agent roster

| Agent | Role | Model role (map) |
|---|---|---|
| **mozart** | Conductor — orchestrates the pipeline | conductor |
| **harry** | Planning architect — drafts the plan | deep-reviewers |
| **sarah** | Researcher — finds prior art + best practices | reviewers |
| **bob** | Architectural plan reviewer | deep-reviewers |
| **dexter** | Code-health auditor | reviewers |
| **xander** | Security reviewer (adversarial) | reviewers |
| **ruby** | UI/UX designer + frontend reviewer | deep-reviewers |
| **otto** | Infra / k8s / ops reviewer (+ OPERATE change-plan author) | reviewers |
| **nina** | Cloud specialist — resolves provider-behaviour assertions against a current source | reviewers |
| **hank** | Ops executor — applies changes to live infrastructure (OPERATE) | builders |
| **tessa** | Test-strategy and test-quality reviewer | reviewers |
| **percy** | Performance engineer (measurement-first) | reviewers |
| **librarian** | Code archaeologist — does this already exist? | reviewers |
| **ian** | Change-impact analyst | reviewers |
| **jackson** | Senior software engineer (implementer) | builders |
| **dick** | Bug investigator (DIAGNOSE lead) | reviewers |
| **valerie** | Plan-vs-reality validator | deep-reviewers |
| **scott** | Technical writer | builders |
| **sebastian** | Independent cross-model counterpoint reviewer (net-new — see D1/D2 in the campaign plan) | validation — **must be the non-builder family** (D8) |

Support agents — real `.github/agents/*.agent.md` personas, part of the
22-agent roster, but tool specialists rather than pipeline-stage reviewers
(no fixed stage number of their own; requested during the pipeline stages
named in the "Requested for" column below, always invoked via mozart, the
only agent this roster grants dispatch authority (D10)):

| Agent | Model role (map) | Requested for |
|---|---|---|
| codebase-locator | fast-scan | research, prior-art survey |
| codebase-analyzer | support | research, diagnosis, change-impact analysis |
| codebase-pattern-finder | support | research, prior-art survey, pre-implementation pattern lookup |
| web-search-researcher | support | research (external/web) |

The literal model IDs stamped per role live in `.github/mozart/config/model-map.jsonc` — this table records the role assignment, not a specific model string, so it doesn't go stale when the map is re-stamped or a preset changes.

## DELIVER pipeline

```
1.  Intake          — mozart restates, classifies tier, context, and mode; confirms flow; creates state file + flow sketch;
                      cuts the campaign worktree (../<repo>-worktrees/<slug>, branch campaign/<slug>)
2.  Research        — sarah (+ codebase-pattern-finder, web-search-researcher) in parallel — OPTIONAL, skipped in TINY
2b. Constraints     — xander or ian, CONDITIONAL — narrow authorization/guarantee trigger only; skipped by default (see trigger table below)
3.  Plan            — harry drafts → .mozart/plans/<slug>.md
4.  Internal review — bob (always) + librarian (BROWNFIELD) + xander/dexter/ruby/otto/nina/tessa/percy (conditional, parallel)
5.  Counterpoint on plan — sebastian's cross-model review; mozart persists it (sebastian holds neither `edit` nor `execute`) → <slug>.counterpoint-r1-plan.md
6.  Iterate         — harry revises if needed; capped 3 rounds; short-circuit when clean
7.  Implement       — jackson, phase by phase (parallel streams when independent)
8.  Mid-build gate  — mozart per-phase gate + conditional specialists (librarian / ian / xander / otto / nina / ruby / dexter / tessa / percy / bob)
                       HEAVY tier: ian + xander mandatory on every phase
                       LOOP-IN mode: setup + user signoff before commit
9.  Counterpoint on diff — sebastian's cross-model review of the final diff (HEAVY mandatory; STANDARD optional; TINY skip)
10. Validate        — valerie FULL mode → SIGNOFF or FIXES REQUIRED
11. Reconcile       — jackson fixes + valerie INCREMENTAL re-check; capped 3 rounds
12. Documentation   — scott updates README/CHANGELOG, GitHub wiki, and any external wiki configured via `## Documentation surfaces` in AGENTS.md (skipped if no user-visible impact)
12b. Ship           — scott pushes campaign/<slug> and opens the PR (opt-in via `## Pull requests` in AGENTS.md; skipped by default)
13. Report          — mozart's final summary
```

**Stage-insertion convention.** A stage added between two existing stages takes the form `<number><letter>` — `12b`, not a renumbering of everything downstream. Renumbering would invalidate every state file, ledger entry, and cross-reference already written. Tooling treats `12b` as one opaque token, so any regex over stage keys must accept `[0-9]+[a-z]?` rather than `[0-9]+`.

### Tier adjustments

| Stage | TINY | STANDARD | HEAVY |
|---|---|---|---|
| Research (2) | skip | optional | optional |
| Constraints (2b) | skip | conditional | conditional |
| Plan-review fan-out (4) | skip | conditional | conditional |
| Counterpoint r1 on plan (5) | skip | run | run |
| Mid-build specialists (8) | skip | conditional | ian + xander mandatory; others conditional |
| Counterpoint r2 on diff (9) | skip | optional | mandatory |
| Ship (12b) | opt-in¹ | opt-in¹ | opt-in¹ |

¹ Gated by the repo's `## Pull requests` stanza, not by tier — when enabled it runs on every tier, including TINY. It appears in this table because readers look here for "does this stage run for me?", not because it varies by tier; every other row does.

### Reviewer triggers (stage 4 — internal review of the plan)

| Reviewer | Trigger |
|---|---|
| bob | always |
| librarian | BROWNFIELD AND plan introduces new functions, classes, modules, services, or shared abstractions. Skip on GREENFIELD or pure-modification plans |
| xander | auth, secrets, untrusted input, encryption, sessions, RBAC, security headers, CSP; dependency manifest/lockfile changes (dependency vetting); CI/CD workflow changes |
| tessa | non-trivial logic (parsers, state machines, validators, business rules, API handlers); new/modified integration boundaries; mandatory in TDD flow (authors the test contract) |
| percy | DB schema/query shapes, caching, pagination of unbounded collections, hot-path endpoints, bundle-affecting frontend changes, stated performance goals — reviews the plan's performance budgets |
| dexter | refactors, shared utilities, new abstractions, code-health debt |
| ruby | UI/UX surface, frontend components, accessibility, design system |
| otto | k8s manifests, Helm, Ingress, Service, Deployment, NetworkPolicy, RBAC, infra YAML |
| nina | Plan asserts how a cloud provider will behave, or touches a cloud control plane (identity/federation, cloud IAM, org structure, quotas, cross-account networking) or cloud IaC. Brief with the pin |

### Constraints triggers (stage 2b — conditional push, narrow)

| Lens | Trigger |
|---|---|
| xander | The task changes **who may do what** — an authorization rule, trust boundary, privilege level, credential path, or the identity an action runs as |
| ian | The task changes behavior covered by a guarantee **already published in this repo** (README / PRIVACY / SECURITY / API docs / CHANGELOG) that the change could falsify |

Deliberately **narrower** than the stage-4 and stage-8 xander triggers above — those also fire on dependency bumps and CI/CD workflow edits, which produce no task-derivable authorization rule. Evaluated once, against the task statement, at intake — never re-derived mid-plan.

### Mid-build specialist triggers (stage 8 — review the slice before commit)

| Specialist | Trigger |
|---|---|
| ian | public API, exported symbol, function signature, schema, shared utility, behavior contract |
| librarian | BROWNFIELD AND phase introduces a new shared abstraction, utility module, or code in well-trafficked paths (`utils/`, `lib/`, `shared/`, `helpers/`, `common/`, `core/`). Catches duplication that slipped past plan review. Skip on GREENFIELD |
| xander | auth, secrets, untrusted input; dependency manifest/lockfile diffs; CI/CD workflow changes. **HEAVY: always** |
| tessa | test files modified; new logic or integration boundary with no test diff; mandatory in TDD flow |
| percy | queries in loops / new query shapes (runs EXPLAIN), bundle-affecting frontend deps (measures delta), new caches, pagination of growing collections, budgeted endpoints |
| otto | k8s manifests, Helm, infra YAML |
| nina | Phase asserts provider behaviour, or modifies a cloud control-plane surface or cloud IaC |
| ruby | UI flows |
| dexter | refactor smells, new shared abstractions |
| bob | plan deviation |

## AUDIT pipeline

```
1. Intake     — mozart confirms goal, scope, report-only-or-remediate; creates state file + flow sketch
2. Discovery  — mozart surveys subject (codebase / deployed site)
3. Audit      — specialists fan out in parallel (picked by goal)
4. Synthesize — mozart consolidates → .mozart/audits/<slug>.md
5. Decision   — user picks: report only, or remediate
                  └─ Remediate: hand audit to harry, enter DELIVER at stage 3 (Plan); stage 2 (Research) is skipped
```

### Audit specialist selection (stage 3)

| Goal | Lead | Support |
|---|---|---|
| Open-ended review | bob, dexter, xander, ruby (+ otto if infra, + nina if cloud) | librarian (if duplication suspected), scott (if doc-freshness in scope) |
| Best-practices refactor | dexter, bob | librarian (duplicate functionality is a top refactor target), xander / ruby / otto if relevant |
| Security audit | xander | bob, dexter |
| UX / accessibility | ruby | xander if auth flows |
| Performance / scaling | percy | bob (structure), dexter (code-health) |
| Code-health / tech debt | dexter, librarian | bob |
| Infra / k8s posture | otto | bob, xander |
| Cloud posture / cloud-semantics | nina | otto, xander |
| Documentation coverage | scott | dexter if doc duplication, bob if architectural docs are wrong |
| Code-archaeology / "does X already exist?" | librarian | dexter, bob |

## DIAGNOSE pipeline

For investigating a specific failure (bug, regression, test failure, performance issue, unexpected behavior). Produces a findings document; optionally flows into DELIVER for remediation.

```
1. Intake     — mozart restates symptom, captures evidence, identifies scope; creates state file + flow sketch
2. Investigate— dick reproduces, isolates, identifies root cause → .mozart/investigations/<slug>.md
3. Decision   — user picks: report only, or remediate
                  └─ Remediate: enter DELIVER at stage 3 (Plan) with findings as harry's brief;
                     stage 2 (Research) is typically skipped — dick's investigation covers it
```

Bug-shaped DELIVER requests ("fix this bug," "X is broken") on STANDARD/HEAVY tier auto-promote to DIAGNOSE first by default. The user can override with "I know what's wrong, just fix it."

**Diagnose-mode rules:**
- No reproducible failure → don't fake it. Dick documents that explicitly; recommends instrumentation as a next step.
- Don't diagnose and fix in the same pass. Investigation → decision point → remediation are distinct phases.
- One ticket per investigation. If multiple distinct issues emerge, dick documents them but creates separate tickets per actionable issue.

## OPERATE pipeline

For changing or debugging a **live system** directly — installs, config changes, infra mutations, hands-on debugging of running k8s / hosts / storage / DBs. The artifact is a state change to running infrastructure, not a git diff; verification is empirical (curl, logs, `get`), not CI; rollback is a recorded command against a snapshot, not `git revert`. That's why it's a distinct shape, not a DELIVER tier. **hank** is the only agent that mutates live state.

**DELIVER-vs-OPERATE boundary:** change reaches the system through a git/CI/Argo pipeline → DELIVER (otto reviews, nina reviews the cloud assertions, jackson writes, the pipeline deploys). Change lands straight on the running system (`kubectl apply`, `helm upgrade`, `apt install`, in-place config edit, restart) → OPERATE (otto plans, hank applies, verified empirically). Prefer the GitOps/DELIVER path when one exists.

```
1. Intake+pin  — mozart restates change, PINS the target from BOTH SIDES (documented + live-observed:
                 context/ns/host), classifies mode+tier, runs the drift sanity check,
                 RESOLVES THE VERSION on install/upgrade; creates state file + flow sketch (Shape: OPERATE)
2. Recon       — dick + otto (infra-debug / migration modes only; skipped for clean install/config)
3. Change plan — otto AUTHORS the plan: exact commands, per-step dry-run, snapshot step, mutation manifest,
                 rollback procedure, blast radius/ramifications (+ ian on HEAVY for code-side consumers)
4. Pre-flight  — hank runs dry-runs + takes snapshots (records them BEFORE applying);
                 HEAVY adds xander (security surface) + otto (immutable-field/server-dry-run) + sebastian on the change plan
5. Apply       — hank executes one variable per mutation (its manifest), confirming each before the next
6. Verify      — hank confirms empirically (observed, not expected); fills the change ledger
7. Record      — scott writes the runbook + rollback record to repo docs / wiki
                  └─ OPERATE-PLAN-ONLY: stop after stage 3; otto's change plan is the deliverable
```

**Modes:** install / config-change / infra-debug / migration (migration is always HEAVY).
**Tiers:** TINY (single reversible change — full loop, but skip otto's separate plan + xander/sebastian gate) / STANDARD (default) / HEAVY (storage, access control at any layer — Kubernetes RBAC, cloud IAM, identity federation, org structure — secrets, live DB schema, production-stateful, resource-recreation — full pre-flight gate + user sign-off on irreversible steps).

**Operate-mode rules:**
- Never mutate without a snapshot and a recorded rollback command — TINY is no exception.
- **Resolve versions, never recall them.** Every install/upgrade states the resolved upstream latest stable, what the install source actually lands, and the gap — before it runs. Chart/distro/community-image defaults lag upstream by months or a full major version routinely; accepting one silently is how a fresh install lands a year out of date. A major-version gap without a stated reason is a stop.
- Server-side dry-run for k8s (`--dry-run=server`), always — client-side doesn't catch immutability/admission failures.
- Pin the target from both sides — documented and live-observed — and check every mutating command against it. A context mismatch is a stop, never a silent switch.
- Observed, not expected — every "it works" carries the evidence behind it.
- Irreversible or out-of-authority steps escalate before apply.
- One variable per mutation, with a mutation manifest — field, old value, new value, `coupling:` for a moved-together set, secret-bearing values `<redacted>`.

## INCIDENT pipeline

For responding to a **live outage** — service is down or badly degraded *right now*. The time-critical form of DIAGNOSE: it **inverts** DIAGNOSE's "don't fix in the same pass" rule — mitigate first to restore service, root-cause in parallel, then durable-fix. mozart is the **incident commander (IC)**; no new agent — responders reused (dick, hank, otto, xander, percy, scott, nina).

**Reconciles speed vs. rigor by splitting it across two phases:** mitigation runs gates-relaxed (`accepted-risk (incident)`, logged with rollback); the durable fix runs full gates (DELIVER/OPERATE, repro-test-first). You sequence rigor, you don't choose it globally.

**Parallelism discipline:** read-only investigation parallelizes freely; **live mutation serializes** through the IC (one hand — hank). Concurrent writers to a broken system turn SEV2 into SEV1.

```
0. Declare+triage — SEV1/2/3, scope, open the timeline; observability gate (warn if recovery can't be measured)
1. Stabilize      — fastest safe restore (rollback/failover/scale/restart/flag). hank, SERIAL. Logged accepted-risk. ─┐ concurrent
2. Race hypotheses— parallel lanes: what-changed / dependency / resource / traffic-data / security / perf / cloud-control-plane. First-to-confirm. ─┘
3. Converge       — confirm root cause; distinguish MITIGATED from FIXED
4. Durable fix    — route to DELIVER (code) or OPERATE (config/infra), full gates, repro-test-first
5. Verify recovery— service-level empirical: error rate / latency / SLO back to baseline (not "pod Running"). IC calls all-clear
6. Post-mortem    — scott: blameless timeline + root cause + action items → follow-up campaigns; Traces-to if it traces to a shipped campaign
                     └─ MITIGATE-ONLY: stop after stage 3 + 5; durable fix is a tracked follow-up
```

**SEV tiers** (INCIDENT's tier axis): SEV1 (total outage / data-loss / breach — all hands, mandatory post-mortem, HEAVY durable fix) / SEV2 (major degradation) / SEV3 (minor/contained — degrades toward a fast DIAGNOSE→OPERATE). When unsure, pick the higher.

**Incident-mode rules:**
- Mitigate first, understand second — a known-good rollback beats a perfect diagnosis when service is down.
- One hand on the live system (hank); investigators parallelize read-only.
- One variable per mitigation, with a mutation manifest recorded in the timeline + change ledger; verify each before stacking another; roll back what didn't help.
- Mitigated ≠ fixed — always say which; the durable fix is deferred, not skipped.
- The timeline is the source of truth — append at every state change.
- Blameless post-mortem on SEV1/2 — output is action items, not attribution.
- Don't over-declare: service up but slow/wrong is DIAGNOSE, not INCIDENT.

## Output paths

- Plan: `.mozart/plans/<slug>.md`
- **State file**: `.mozart/plans/<slug>.state.md` (durable pipeline state — survives crashes, sessions, context resets)
- **Flow sketch**: `.mozart/plans/<slug>.flow.md` (Mermaid diagram + chronological stage trace + agent participation summary)
- Research brief: `.mozart/research/<slug>.md` (when substantial)
- Decisions log: `.mozart/plans/<slug>.decisions.md` (from the first judgment call)
- Counterpoint round 1 (plan): `.mozart/plans/<slug>.counterpoint-r1-plan.md`
- Counterpoint round 2 (diff): `.mozart/plans/<slug>.counterpoint-r2-diff.md`
- **Validation report**: `.mozart/plans/<slug>.validation.md` (valerie's stage-10 report, written to disk as well as returned — reconciliation rounds append to it)
- Audit report (AUDIT shape): `.mozart/audits/<slug>.md`
- Investigation (DIAGNOSE shape): `.mozart/investigations/<slug>.md`
- Change plan (OPERATE shape): `.mozart/plans/<slug>.md`; snapshots: `.mozart/snapshots/<slug>/` (rollback state captured before apply, referenced by the change ledger in the state file)
- Incident timeline (INCIDENT shape): `.mozart/incidents/<slug>.timeline.md` (append-only spine); post-mortem: `.mozart/incidents/<slug>.postmortem.md` (+ external wiki if configured)

## Flow control: passthrough, stop, entry points

Mozart's first decision at intake is **passthrough or pipeline?** — not every request needs orchestration.

### Single-agent passthrough (when orchestration isn't warranted)

When a request is genuinely one agent's job, mozart routes it directly and returns the result. **No state file, no plan, no counterpoint review, no per-phase gate.**

| User asks for... | Routes directly to |
|---|---|
| Security review (no fix) | xander |
| Code-health audit (no fix) | dexter |
| Architectural critique (no fix) | bob |
| UI/UX review (no fix) | ruby |
| Infra / k8s posture review (no fix) | otto |
| Cloud posture, or "is this claim about the provider true?" (no fix) | nina |
| "Just apply this manifest" / "restart the pod" (single reversible live change) | hank (runs the full verify→dry-run→snapshot→apply→verify loop) |
| "Install X" / "make this infra change" / "debug the live system" (multi-step) | OPERATE pipeline (not passthrough) |
| "Prod is down" / "returning 500s" / "users can't X" / "SEV1" / active outage | INCIDENT pipeline (not passthrough) |
| Change-impact analysis on a diff | ian |
| Plan-vs-diff validation (no fix) | valerie (FULL mode) |
| Research / "how should we do X" | sarah |
| "Does X already exist?" / prior-art survey | librarian |
| "Why is X broken?" / diagnose only (no fix) | dick |
| "Update the docs" / "is the CHANGELOG current?" | scott |
| Find usage patterns | codebase-pattern-finder |
| Explain code | codebase-analyzer |
| Locate files | codebase-locator |
| Build / ship / audit-and-fix | pipeline (not passthrough) |

A passthrough can graduate to a flow if the user follows up with "now fix it" or "now build it" — at that point mozart creates the state file and enters the appropriate pipeline stage.

### Partial flows (early exit)

| Flow | Trigger phrases | Stops after |
|---|---|---|
| **FULL** (default) | (default) | Stage 13 |
| **PLAN-ONLY** | "just plan it," "stop at the plan," "give me a bulletproof plan" | Stage 6 |
| **RESEARCH-ONLY** | "just research," "find out what we should use" | Stage 2 |
| **INVESTIGATE-ONLY** | "investigate X," "diagnose Y," "why is Z broken" | DIAGNOSE stage 3 (decision point) |
| **AUDIT-ONLY** | AUDIT shape, user picks "report only" at decision point | AUDIT stage 5 |
| **OPERATE-PLAN-ONLY** | "plan the change but don't apply it," "give me the change plan + rollback" | OPERATE stage 3 (change plan) |
| **MITIGATE-ONLY** | "just get it back up," "stop the bleeding, fix it properly later" | INCIDENT stages 0–3 + 5 (durable fix deferred; post-mortem still runs) |
| **VALIDATE-ONLY** | "validate this branch against the plan" | Stage 10 only |

### Entry points (resume / pick up)

| User says... | Mozart enters at |
|---|---|
| "implement the plan at `<path>`" | Stage 7 (Implement) |
| "review the plan at `<path>`" | Stage 4 (Internal review) |
| "get a cross-model read on this plan" | Stage 5 (Counterpoint on plan) |
| "validate this branch against the plan" | Stage 10 (Validate, VALIDATE-ONLY) |
| "resume `<slug>`" / "pick up where we left off" | Wherever the state file's `Current stage` says |

### State persistence

Every run writes `.mozart/plans/<slug>.state.md` with `Status: in-progress` and updates it at every stage transition. After crash / power loss / session reset, a new mozart instance scans for in-progress state files at intake and offers to resume them. Status values: `in-progress`, `stopped` (user pause), `complete`, `aborted`. State files persist as audit trail after terminal status.

## Worktree isolation

**Every code-changing campaign gets its own git worktree and branch, cut at intake** — a single campaign in a single session included, TINY included. Default layout is a sibling directory: `../<repo>-worktrees/<slug>` on branch `campaign/<slug>`, cut from the repo's documented base branch. A repo's own established convention (a different sibling dir, `~/wt/<repo>/`, a `hack/create_worktree.sh`, a ticket-derived branch scheme) wins over this default.

| Shape / flow | Worktree? |
|---|---|
| DELIVER FULL, any tier | Yes — at intake |
| AUDIT / DIAGNOSE flowing into remediation | Yes — when remediation is committed to |
| VALIDATE-ONLY | No — validates a branch the user already has; a fresh worktree would validate the wrong tree |
| AUDIT-ONLY, INVESTIGATE-ONLY, RESEARCH-ONLY, PLAN-ONLY | No — nothing is modified |
| OPERATE | No — changes land on live systems, not the repo |
| INCIDENT | No — the clock is the enemy; a post-incident durable fix is a DELIVER campaign and gets one |
| EVAL | No — read-only over artifacts |

**`.mozart/` stays in the canonical checkout, never in the worktree.** That keeps a listing of `.mozart/plans/active/*.state.md` a complete answer to "what's in flight?" regardless of worktree count; agent briefs cite artifact paths **absolutely** because the agent's cwd is the worktree. Every brief also names the worktree path + branch, which is what makes jackson's workspace-identity preflight possible.

Worktrees isolate files, not runtimes — venvs, `node_modules`, ports, and DBs stay shared (see Multi-campaign mode). Disposition (`merged` / `squash-merged` / `pending-pr` / `intentionally-unmerged` / `abandoned`) is recorded in the state file at closeout; unmerged worktrees are left in place and named in the final report, never force-removed. `pending-pr` is the only one of the five that is **awaiting an external actor** rather than terminal — the pipeline is done, the branch isn't — so it is also the only one that is re-checked and rewritten after closeout.

See `.github/agents/mozart.agent.md` and `.github/mozart/manual/WORKTREES.md` for the full playbook.

## Multi-campaign mode

Mozart can hold multiple in-flight campaigns simultaneously and progress them in parallel where work is independent. Each campaign has its own slug, state file, flow sketch, plan, ticket, and git worktree.

### When to use

Multi-campaign activates when the user wants 2–4 campaigns run concurrently — "drive all these tickets in parallel," "run these three plans in parallel" — or when mozart finds in-progress state files at intake and the user asks to continue one alongside a new task.

### Isolation strategies

| Strategy | When | Notes |
|---|---|---|
| **Git worktrees (default — already cut)** | Always, for code-changing campaigns | Each campaign already has its own worktree from intake (see Worktree isolation); multi-campaign inherits that isolation rather than introducing it |
| **Same-branch serialization** | Campaigns are confirmed non-overlapping | Fragile; only viable for genuinely orthogonal touch surfaces |
| **Refuse and serialize** | Overlap can't be confirmed and worktrees unavailable | Surface reason; run sequentially |

Cap: 3–4 simultaneously-active campaigns unless the user explicitly asks for more.

### Narration tagging

Every `TASK [...]` line in multi-campaign runs includes the campaign slug: `TASK [<slug>: <stage>]`. Cross-campaign parallel batches use `TASK [parallel batch]` with each campaign's work listed in the body.

See `.github/agents/mozart.agent.md` and `.github/mozart/manual/WORKTREES.md` for the full playbook.

## Iteration caps

| Loop | Cap |
|---|---|
| Plan-review iteration (stage 6) | 3 rounds |
| Per-phase implementation attempts (stage 7) | 3 attempts |
| Reconciliation rounds (stage 11) | 3 rounds |

When a cap hits: mozart stops and asks the user.

## Counterpoint review (cross-model)

Sebastian is a native subagent used at two stages: **stage 5** (counterpoint-r1-plan, plan review) and **stage 9** (counterpoint-r2-diff, diff review), each time providing a fresh-context, cross-model read from an independent senior architect.

### Why a cross-model reviewer

A plan or diff reviewed only by same-family agents has correlated blind spots — every in-context reviewer shares the same training biases as the builder who produced the work. Sebastian runs on a different model family (enforced by D8's cross-family invariant, asserted before every dispatch), which catches issues same-family reviewers structurally can't see.

### How it's dispatched

Sebastian is a subagent like any other — dispatched via the `agent` tool, briefed with the plan/diff path and a pre-computed input contract (`.mozart/plans/active/<slug>.counterpoint-r{1,2}-inputs/`: the plan, `diff.patch`, `consumers.txt`, and, on round 2's first pass, `installed-versions.txt`). It has no shell access and never fetches its own inputs — see `.github/mozart/manual/COUNTERPOINT.md` for the full design, the attestation-based success-detection contract, and why the Claude Code edition's CLI-process-babysitting discipline (closing stdin, arming a kill-timer, polling an output file) has no equivalent here: sebastian's lifecycle is harness-managed, the same as every other specialist's.

### Tier policy

| Tier | Counterpoint r1 (plan) | Counterpoint r2 (diff) |
|---|---|---|
| TINY | skip | skip |
| STANDARD | run | optional |
| HEAVY | run | mandatory |

### Cross-family invariant

Before every dispatch, mozart reads `.github/mozart/config/model-map.jsonc` and refuses to proceed if `roles.validation.family == roles.builders.family`. This is a hard stop recorded in the state file, not a soft degradation — unlike the Claude Code edition's degrade-gracefully-when-the-external-reviewer-is-absent path, there is no way to run this port's sebastian in a diminished mode. Either the invariant holds and the review runs, or the campaign halts here until the map is fixed or the user explicitly accepts a same-family read.

## Authority boundaries

Mozart **can**:
- Read code, run tests, run lints, run type-checks
- Dispatch any agent
- Stage and commit per phase

Mozart **cannot** (without user confirmation, even mid-pipeline):
- Push or force-push to remote
- Delete branches
- Drop tables, run destructive migrations
- `kubectl apply` to shared infrastructure
- Anything that crosses the local-vs-shared boundary

**This list has no exceptions, and gets none.** A repo's `## Pull requests` stanza with `enabled: true` in its own `AGENTS.md` is the user confirmation this list requires **for one action only: `git push -u origin campaign/<slug>` to that repo's own configured remote.** It authorizes nothing else on this list. Force-push, pushes to a base or shared branch, branch deletion, destructive migrations, and `kubectl apply` remain prohibited without a confirmation obtained in-session. No other stanza, present or future, carries this property.

That last sentence is load-bearing rather than decorative. Without it, a future `## Migrations` stanza with `destructive: true` would read as self-authorizing under a general rule, and this list would quietly stop being absolute. The stanza qualifies because it is durable (it survives a resume and a context reset), reviewable (it arrives through the repo's own change-review process, unlike a verbal yes in a session nobody else saw), and revocable (delete the line and push; scott re-fetches and re-reads the grant from the remote's default branch immediately before pushing). An exception that met none of those tests would not belong here.

## See also

- The bundled `.github/agents/mozart.agent.md` — full orchestrator persona (operating manual; this file is the reference summary)
- Each bundled agent's `.github/agents/<name>.agent.md` — persona + "Where you fit" placement
- `AGENTS.md` — repo-specific conventions and constraints
- Each campaign's flow sketch — `.mozart/plans/<slug>.flow.md` (Mermaid diagram + chronological trace + agent participation summary)
