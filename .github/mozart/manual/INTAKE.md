# Intake

Second boot read, after `INDEX.md`. Covers shape-boundary disambiguation, the
single-agent passthrough decision, task tiers, and project context
classification — everything intake needs beyond the compact detection table
already in the conductor body.

## Shape-boundary tests

The conductor body's six-shapes table is the compact lookup; these are the
disambiguation rules for the cases that don't sort themselves.

**How the shapes flow into each other.** AUDIT can flow into DELIVER (the
audit becomes the brief for a remediation plan). DIAGNOSE can flow into
DELIVER (the findings become the brief for a fix plan). **DIAGNOSE and AUDIT
can flow into OPERATE** when the fix is an infra/config change to a live
system rather than a code change — an infra-debug investigation becomes the
brief for an OPERATE change plan. **INCIDENT flows into both**: its
durable-fix phase routes to DELIVER (code fix) or OPERATE (config/infra fix)
with full gates restored, and its mitigation phase is an OPERATE-style live
change under relaxed, incident-graded gates. Bug-shaped requests in DELIVER
("fix this bug," "X is broken") trigger DIAGNOSE first by default on
STANDARD/HEAVY tier — investigation happens before planning the fix; if the
diagnosis is that a live-system change is needed, remediation routes to
OPERATE, not DELIVER. **A bug that is an *active outage* is INCIDENT, not
DIAGNOSE** — the difference is whether service is currently down
(mitigate-first) or merely wrong (investigate-first). EVAL flows into
configuration fixes (its own form of DELIVER — bundle-repo commits for
maintainers; overrides, field notes, or upstream PRs for bundle consumers).

**DELIVER vs OPERATE — the boundary.** DELIVER changes files that get
committed and deployed *through a pipeline* (CI, Argo, a release). OPERATE
changes a *running system directly* — the change is live the moment it's
applied, before any git history records it. A manifest edit that lands via a
git commit + Argo sync is DELIVER (otto reviews, jackson writes, CI/Argo
deploys). The same manifest applied straight to the cluster with `kubectl
apply` is OPERATE (otto plans, hank applies, verified empirically). When
both are possible, prefer the DELIVER/GitOps path for anything that has one
— OPERATE is for the direct changes, installs, and live debugging that don't
go through a repo.

## Single-agent passthrough (when orchestration isn't warranted)

Not every request needs the pipeline. When a user's ask is genuinely the job
of **one agent** — not a sequence — dispatch directly. No tier, no state
file, no plan, no counterpoint review, no per-phase gate. Just route the
request and return the result.

This is the **first decision** at intake, before tier/mode/flow/entry-point:
*does this even need orchestration?*

### Passthrough vs. orchestrate

**Passthrough** when the request is:
- A specific named agent's specialty ("have xander look at this," "ask ruby")
- A read-only review / audit / validation with no implementation expected
- A research / lookup / explanation with no expectation of building
- A single deliverable that one persona can produce in one pass

**Orchestrate** (run the pipeline) when the request:
- Will produce a commit, change, or shipped result
- Needs multiple lenses across multiple stages
- Requires a plan that spans phases
- Includes follow-on like "and then fix it" / "and then implement it" / "and ship it"

### Passthrough routing

| User asks for... | Route directly to |
|---|---|
| Security review (no fix) | **xander** |
| Code-health audit (no fix) | **dexter** |
| Architectural critique (no fix) | **bob** |
| UI/UX review (no fix) | **ruby** |
| Infra / k8s posture review (no fix) | **otto** |
| Cloud posture, or "is this claim about the provider true?" (no fix) | **nina** |
| "Just apply this manifest" / "restart the pod" / "bump this config on the live system" (single reversible change) | **hank** (still runs verify → dry-run → snapshot → apply → verify) |
| "Install X" / "make this infra change" / "debug why the live system is broken" (multi-step or higher-stakes) | **OPERATE pipeline** (don't passthrough) |
| Change-impact analysis on a diff | **ian** |
| Plan-vs-diff validation (no fix) | **valerie** (FULL mode) |
| Test strategy / test quality review (no fix) | **tessa** |
| Plan review (no implementation) | **bob** alone — or **bob + sebastian** if user wants the cross-model read |
| Research / find prior art / "how should we do X" | **sarah** (with parallel codebase-pattern-finder + web-search-researcher when warranted) |
| Find usage examples / patterns | **codebase-pattern-finder** |
| Explain this code | **codebase-analyzer** |
| Locate files / "where does X live" | **codebase-locator** |
| "Does X already exist?" / "is there already a thing for Y?" / "before I build Z, has it been built?" | **librarian** (skip if user confirms greenfield) |
| "Why is X broken?" / "investigate this bug" / "diagnose this failure" / "what's causing Y?" (no fix expected) | **dick** |
| "Update the docs" / "audit the README" / "is the CHANGELOG current?" / "publish this to the wiki" / "document the runbook" | **scott** |
| Plan a feature (no build) | **harry** alone for a quick draft, OR PLAN-ONLY partial flow if user wants the full review/counterpoint pass — ask which |
| Build a feature | **DELIVER pipeline** (don't passthrough) |
| Audit + fix | **AUDIT → DELIVER** (don't passthrough) |

### How to passthrough

1. If the routing isn't obvious, confirm briefly: "This is xander's lane — dispatch him directly without the pipeline?"
2. Brief the agent with the user's request as-is plus any context they need
3. Return the agent's output to the user
4. **No state file, no plan, no commit, no follow-on stages**
5. If the user follows up with "now fix it" or similar, *that's* when you escalate. Often the right entry is stage 11 (Reconcile) when fixes are punch-list-shaped, stage 7 (Implement) when planning is already done, or AUDIT → DELIVER when remediation is broader

### Don't over-orchestrate

If a user says "have ian look at this change," **do not** create a plan, run sebastian, open a state file, or invoke other reviewers. Just run ian and return what he found. Imposing the pipeline on a single-agent request is wasteful and feels heavy.

### Don't under-orchestrate

If a user says "audit this and fix the issues," **do not** just run dexter and call it done. That's a remediation flow — AUDIT → DELIVER. Recognize the "and fix" intent.

### When passthrough graduates to a flow

A passthrough can become a flow if the user follows up. Examples:
- "Have xander review my auth code" → passthrough to xander → user says "okay, fix what he flagged" → enter DELIVER at stage 7 with a tiny ad-hoc plan, or AUDIT → DELIVER if the findings are themed enough to warrant a real remediation plan
- "Research X" → passthrough to sarah → user says "okay, build it" → enter DELIVER at stage 3 (Plan) with sarah's brief as input

When this graduation happens, *now* you create the state file. Not before.

## Task tiers (DELIVER)

Classify at intake. Tier determines which gates run.

| Tier | When | Pipeline adjustments |
|---|---|---|
| **TINY** | Single file, no API/schema/UI/infra/security surface, ~30 LOC, trivial fix | Skip research, skip plan-review fan-out, skip the counterpoint review, skip mid-build specialists. Brief jackson directly with the task → per-phase gate → valerie → commit |
| **STANDARD** | Default for most work | Full pipeline below |
| **HEAVY** | Auth, secrets, schema, migrations, infra/k8s, billing, security-critical | STANDARD + mandatory ian on every phase + mandatory xander mid-build + mandatory sebastian round 2 on the final diff |

When unsure between STANDARD and HEAVY: choose HEAVY. The cost of an extra gate is small; the cost of a missed security or migration concern is not.

## Project context (GREENFIELD vs BROWNFIELD)

Classify at intake alongside tier. Determines whether duplicate-functionality checks (librarian) run.

| Context | When | Effect |
|---|---|---|
| **GREENFIELD** | Brand-new repo, scaffolding-only, or the work introduces an entirely new domain with no peer code in the project | Skip librarian everywhere. There is nothing meaningful to search against |
| **BROWNFIELD** | Existing codebase with prior implementations, utilities, services, or peer features | Librarian runs at stage 4 (plan review) and at stage 8 (mid-build) when the work introduces new functions, classes, modules, services, or shared abstractions |

Detection heuristics:
- `find src -type f 2>/dev/null | wc -l` returning a small number (rough threshold: <20 source files) → likely GREENFIELD
- `git log --oneline | wc -l` very low (<20 commits) → likely GREENFIELD
- The proposed work is in a brand-new directory with no adjacent peer code anywhere in the repo → may be GREENFIELD even if the repo overall is BROWNFIELD (call it BROWNFIELD but tell the librarian explicitly that this domain is new — he'll short-circuit if appropriate)
- User explicitly says "greenfield," "net-new," "from scratch," "new repo," "starting fresh" → GREENFIELD

When in doubt: classify BROWNFIELD. The librarian will short-circuit himself if the work turns out to be greenfield-shaped. False BROWNFIELD costs one cheap search; false GREENFIELD lets duplicates land.

Record the classification in the state file alongside tier/mode/flow.
