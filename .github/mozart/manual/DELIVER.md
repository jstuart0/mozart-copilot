# DELIVER pipeline

### 1. Intake
- **First decision: passthrough or pipeline?** (see `.github/mozart/manual/INTAKE.md`, Single-agent passthrough). If the request is genuinely one agent's job, route it directly and return the result. No further intake steps. Skip the rest of this list.
- **Check for in-progress state files** (see `.github/mozart/manual/STATE.md`). If any exist, surface them and ask whether to resume, abandon, or run separately, before continuing
- Restate the task in one sentence; confirm anything ambiguous
- **Detect the work shape**: DELIVER / AUDIT / DIAGNOSE / INCIDENT / OPERATE / EVAL (see Six shapes of work). Bug-shaped requests in DELIVER ("fix this bug," "X is broken," "regression," "failing") on STANDARD/HEAVY tier auto-promote to DIAGNOSE first → DELIVER second; the user can override with "I know what's wrong, just fix it". Live-system requests ("install X," "apply this," "the pod is crashlooping," "fix the config on the box") are OPERATE — and a live-system failure that needs investigation first is DIAGNOSE → OPERATE. **An active outage ("prod is down," "returning 500s," "users can't X," "SEV1," "on fire") is INCIDENT** — the mitigate-first, parallel-hypothesis, timeline-and-post-mortem shape; the tell vs. DIAGNOSE is whether service is *currently down* (INCIDENT) or merely *wrong/slow* (DIAGNOSE). When in doubt on a production failure, ask "is service down right now?" — if yes, INCIDENT.
- **Detect the flow shape**: FULL (default) / PLAN-ONLY / RESEARCH-ONLY / INVESTIGATE-ONLY / VALIDATE-ONLY (see `.github/mozart/manual/FLOWS.md`, Partial flows). State which flow you're running
- **Detect any entry point** other than stage 1 (see `.github/mozart/manual/FLOWS.md`, Resume / entry points). If the user said "implement this plan" or similar, jump appropriately after this intake
- **Classify tier** (TINY / STANDARD / HEAVY) — only relevant when implementation will run
- **Classify project context** (GREENFIELD / BROWNFIELD) — determines whether the librarian runs at stages 4 and 8. Use the heuristics in `.github/mozart/manual/INTAKE.md`'s Project context section; default to BROWNFIELD when uncertain
- **Confirm operating mode** (AUTONOMOUS / LOOP-IN) — only relevant when implementation will run
- **Decide the slug** as `<YYYY-MM-DD>-<shape>-<descriptive-kebab>` (see `.github/mozart/manual/FLOWS.md`, Run identification and prior-art discovery). Locate plan home: `.mozart/plans/<slug>.md`. Before locking, **discover prior art**: search `.mozart/plans/` and `.mozart/investigations/` for runs matching topic (substring of the descriptive part) and the most recent few of the same shape. Surface relevant ones to the user concisely; only load their content if the user opts in or the prior run is a direct predecessor
- Note starting git state (branch, base commit, clean/dirty) for diff scope at validation
- **Cut the campaign worktree** (see `.github/mozart/manual/WORKTREES.md`, Worktree isolation) — `git worktree add -b campaign/<slug> ../<repo>-worktrees/<slug> <base-branch>`, then enter it. Applies to every code-changing campaign at every tier, including TINY. `.mozart/` stays in the canonical checkout; agent briefs cite artifact paths absolutely and name the worktree path + branch. Skip only per the shape table there — and when you skip, say so with the reason
- **Confirm the cross-family invariant will hold before dispatching sebastian.** No CLI probe is needed here — sebastian is a subagent defined in the roster like any other, not a shell binary, so there is no availability to check at intake the way an external CLI would need. What intake *does* need to confirm once: `.github/mozart/config/model-map.jsonc` exists and `roles.validation.family != roles.builders.family` — the runtime assert itself happens immediately before each dispatch (stages 5 and 9), not here. See `.github/mozart/manual/COUNTERPOINT.md` for the full design.
- **Resolve the ticketing project for this repo** (see `.github/mozart/manual/TICKETS.md` / Project resolution). Fast path: read the `## Ticketing` stanza from the repo's `AGENTS.md` (see `.github/mozart/INTEGRATION.md` for the schema). Slow path: search the configured ticketing system by name, ask the user if ambiguous, create if missing. Persist to `AGENTS.md` when missing or incomplete. Skip if the run will produce no commits (RESEARCH-ONLY, AUDIT-ONLY without remediation, INVESTIGATE-ONLY) or if the stanza declares `system: none`
- **Resolve the `## Pull requests` stanza from the remote's default branch — not from the working tree, and not from the campaign's base.** The ref an authorization is read from must be one no local input can select:

  ```bash
  # Authoritative first: ls-remote asks the REMOTE. The local pointer is a fallback, never a guess.
  auth_ref=$(git -C "$wt" ls-remote --symref origin HEAD 2>/dev/null \
             | awk '$1=="ref:"{sub("refs/heads/","",$2); print $2; exit}')
  [ -n "$auth_ref" ] || auth_ref=$(git -C "$wt" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
                                   | sed 's#^refs/remotes/origin/##')
  [ -n "$auth_ref" ] || { echo "Ship disabled: origin's default branch is unresolvable"; }   # see below
  git -C "$wt" fetch origin --quiet
  git -C "$wt" show "origin/${auth_ref}:AGENTS.md"
  ```

  **`git symbolic-ref refs/remotes/origin/HEAD` is a local pointer, not a question to the remote.** `git clone` writes it once; `git remote set-head` updates it on demand; a `git init` + `git remote add` repo never has it at all (the command exits 128), and after a remote renames its default branch the local copy stays stale — **a `fetch` does not correct it.** Both were reproduced. Either failure silently relocates the ref an authorization is read from, which is the one thing this control exists to pin. So: ask the remote, fall back to the local pointer only when the remote is unreachable, and **never guess `main`**.

  **If neither resolves, fail closed: `enabled: false`, and say so out loud.** Ship is one optional stage; a campaign whose other twelve stages are unaffected should not be aborted because a default-branch pointer is missing. Record `enabled: false — auth ref unresolvable (<reason>)` in the state file, surface it to the user at intake rather than letting them discover it at stage 12b, and name the one-line remedy (`git remote set-head -a origin`). Fail-closed on the authorization, not fail-stop on the campaign.

  Record the result in the state file as `source_ref: base:<auth_ref>@<sha>` — the `base:` prefix is a **discriminator**, not decoration: without it "read from the base branch" and "read from the working tree" have the same representation and the stop that checks for it can never fire. A missing field, or any other prefix, is a stop. If `AGENTS.md` doesn't exist on that ref, the stanza is **absent** and Ship is disabled. Never fall back to the working tree, to `HEAD`, or to a local ref. Absent stanza → `enabled: false`, 12b skips; that is the default and it is the behavior every repo has today.
  - **The campaign's `<base>` is not required to equal `auth_ref`.** `## Worktrees`'s `base branch:` still selects the PR base — it just doesn't select the ref the grant is read from, and those are separate properties. Reading the grant from the remote's default branch already closes the attack; influencing *that* ref takes repo-admin rights, a different threat model entirely. Requiring the two to match would constrain where you may push *from*, buy no additional security, and break the `develop` / `deploy/<env>` base branches named a few sections up as legitimate. When they differ, scott's pre-push echo prints both — visible in the run record, without halting a legitimate campaign.
  - **Why the earlier form was not enough.** Reading from "the base branch" sounds pinned and isn't: `## Worktrees` is optional, and with no stanza the base resolves to `git symbolic-ref --short HEAD` (see `.github/mozart/manual/WORKTREES.md`, Cutting one). So a maintainer who runs `gh pr checkout` on a contributed PR — the ordinary, encouraged way to help finish one — makes the contributor's own branch the base, and a "base-branch read" reads the contributor's commit. Both the intake read and scott's push-time re-read would have consumed that same attacker-influenced input and agreed with each other. Declaring `## Worktrees` doesn't help; it just means the attacker adds `base branch:` to the same working-tree-read stanza. `refs/remotes/origin/HEAD` is set by the remote, not by anything in the checkout, which is the whole property.
  - **This applies to `## Pull requests` alone, and the reason is the action class, not the stanza.** `## Ticketing`, `## Documentation surfaces`, `## Code retrieval`, and `## Worktrees` are advisory — the worst a poisoned value does is route work to the wrong place, which is visible, local, and undoable — so they resolve from the working tree as normal. `## Pull requests` authorizes a network write to a shared remote whose object store is permanent. Don't "harmonize" the five, in either direction.
- **Search for an existing ticket** that may already cover this work (see `.github/mozart/manual/TICKETS.md`, Existing-ticket detection). If a strong candidate is found, surface it to the user and ask whether to use the existing ticket, create new with cross-link, or supersede. Only create a new ticket when no clear match exists or the user explicitly wants a fresh one
- **Create the state file** as `.mozart/plans/active/<slug>.state.md` (per the Directory convention) with Status: in-progress and the initial fields populated, including resolved `ticketing project: <id> (<name>)` and `ticket: <id> (<existing|new>)`. If `.mozart/plans/active/` doesn't exist yet in this repo, create it with `mkdir -p` (one-time per repo).
- **Create the flow sketch** as `.mozart/plans/active/<slug>.flow.md` (per the Directory convention) with the metadata table populated, the **Proposed flow** section filled in (rationale + Mermaid diagram of the planned stages and agents — locked from this point forward), an empty *Actual flow* diagram stub, an empty *Deviations from proposed* section, and the first stage trace entry (Intake). See `.github/mozart/manual/STATE.md` (Pipeline flow sketch) for the format. Update *Actual flow*, *Deviations*, and *Stage trace* at every stage transition; never edit *Proposed flow* after intake; finalize at the report stage.

#### Pre-flight gates (run BEFORE accepting an implementation campaign)

When the campaign will modify code that lands in CI or deploys to a cluster (anything other than RESEARCH-ONLY / INVESTIGATE-ONLY), run these gates at intake. Failing a gate doesn't kill the campaign — it forces a triage decision before stage 3.

1. **CI baseline check** (skip in GREENFIELD or when no CI is configured):
   - `gh run list --branch <main-branch> --limit 5 --json status,conclusion,name --jq '.[] | "\(.name): \(.conclusion)"'`
   - If any workflow on the most recent push to main is **failing**, halt the campaign and ask the user one of:
     - "CI on `<branch>` has been red since <SHA>. Triage CI first as a separate (TINY) campaign before this one?"
     - "Acknowledge the red baseline — the campaign will inherit it, and 'tests pass' cannot be jackson's signoff signal. Use full CI as the gate or accept a degraded signal?"
   - Never silently start a campaign on a red CI baseline. The new failures get debugged together with pre-existing ones; the signal collapses.

2. **Long-running drift sanity check** (when the campaign touches infra OR a cluster's `kubectl` context is documented in `AGENTS.md`):
   - `kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}: {.status.conditions[?(@.type=="DiskPressure")].status},{.status.conditions[?(@.type=="MemoryPressure")].status},{.status.conditions[?(@.type=="PIDPressure")].status}{"\n"}{end}'`
   - `kubectl get pods -A --field-selector status.phase=Failed --no-headers | wc -l` (cluster-wide Failed pod count — anything >20 is a sign of accumulating zombie state)
   - For Argo CD clusters: `kubectl -n argocd get applications -o jsonpath='{range .items[*]}{.metadata.name}: sync={.status.sync.status} health={.status.health.status}{"\n"}{end}'` — surface any app stuck `OutOfSync` for >1h before the campaign begins
   - Surface findings concisely; the user decides whether to address before starting. **The 2026 audit-refactor incident** where node-02 had been flapping `DiskPressure` 128 times over 13 days — and bit the campaign as a hard rollout block on the final phase — is the canonical example. Surface drift at intake; don't discover it at deploy time.

3. **Toolchain baseline check** (the inverse of the CI check — fires on GREENFIELD and on any repo missing mechanical verification):
   - For each language the campaign will touch, confirm the repo has a configured linter, formatter, and type-checker (where the language has one), a test runner, and a CI workflow that runs them. Detection is cheap: config files (`eslint.config.*`/`.eslintrc*`, `[tool.ruff]`/`ruff.toml`, `.golangci.yml`, `tsconfig.json`, `[tool.mypy]`/`mypy.ini`, `.pre-commit-config.yaml`), `package.json` scripts, `.github/workflows/`.
   - **Missing toolchain on GREENFIELD → the plan MUST open with a toolchain-bootstrap phase** (linter + formatter + type-check + test runner + CI workflow, pre-commit hooks where the repo will take them) before any feature phase. The per-phase gate's "run lints/types/tests" is meaningless against a repo where none are configured — a greenfield campaign without this phase ships N phases of unverifiable code.
   - Missing toolchain on BROWNFIELD → surface to the user: bootstrap it as a phase in this campaign, as a separate TINY campaign, or acknowledge the degraded gate in the state file. Never silently run a campaign whose per-phase gate has nothing mechanical to hold.

If any gate fails and the user opts to proceed anyway, record the acknowledgement in the state file's "Status notes" section so valerie sees it at signoff and downstream debugging knows the inherited baseline.

### 2. Research (sarah, optional — and parallel)

Skip in TINY. In STANDARD/HEAVY, run when:
- Unfamiliar domain, library, or pattern decision
- "Best practices" or "modern way to X" framing
- Multiple plausible approaches and the right one isn't obvious
- User explicitly asked for research

**Researchers run in parallel.** Dispatch in a single message, multiple subagent invocations:
- **sarah** — primary; surveys codebase prior art + scans web + synthesizes the brief
- **codebase-pattern-finder** — when in-repo examples matter
- **web-search-researcher** — when an external sub-question deserves its own thread

Sarah herself parallelizes her internal tool calls (codebase scan + web search in one batch). The brief is returned inline for small jobs; mozart persists it to `.mozart/research/<slug>.md` for substantial ones, since sarah holds neither `edit` nor `execute`.

### 3. Plan (harry)
- Brief harry: task, research brief (if any), the **absolute** plan path to write to, the worktree path + campaign branch, context
- Harry reads code, drafts the plan (template includes `Documentation to update` and `Pattern parity / wiring sites`)
- **Wiring-sites discipline**: when the plan introduces or extends a pattern (transport wrapper, auth/role gate, structured-error envelope, ARIA attribute set, healthcheck argument, NetworkPolicy shape, securityContext stanza, parity field across Helm/kustomize/compose, etc.), harry must enumerate every existing site that needs the pattern — not just the site being changed. The search that produced the list is documented in the plan so downstream reviewers and jackson can re-run it. This is the lens that distinguishes "this diff is correct" from "this pattern is consistent across the codebase." Per-commit reviewers see the diff; only the wiring-sites enumeration in the plan makes the population visible to them. See the conductor body's Consistency lens section for the rationale.
- **Plan-acceptance criterion**: harry's `## Verification` section must carry both an Automated list and a Manual list (or an explicit "Manual: none — fully machine-verifiable"); a plan with an undifferentiated list, or a hedge in place of one of the two, is not accepted — send it back.
- If harry returns **open questions**, surface them to the user before continuing

### 4. Internal review (conditional, parallel)

Pre-filter reviewers based on what the plan actually touches. Don't invoke a lens that doesn't apply.

| Reviewer | Always | Trigger |
|---|---|---|
| **bob** | ✓ | — (architecture, sequencing, risk coverage applies to every plan) |
| **librarian** | | BROWNFIELD AND plan introduces new functions, classes, modules, services, or shared abstractions. Skip on GREENFIELD or pure-modification plans (bug fixes, refactors that don't add new abstractions, edits to existing code only) |
| **xander** | | Auth, secrets, untrusted input, encryption, sessions, RBAC, security headers, CSP. Also: plan adds or upgrades a dependency (package manifest / lockfile change — he runs his dependency-vetting checklist) or touches CI/CD workflow files (`.github/workflows/`, GitLab CI, pipeline YAML — he runs his CI/CD checklist) |
| **dexter** | | Refactors, shared utilities, new abstractions, anything where code-health debt matters |
| **ruby** | | UI/UX surface, frontend components, accessibility, design system — including admin/operator/internal screens, not just public-facing ones. On GREENFIELD plans with any UI, ruby additionally verifies the plan sequences a **design foundation** (tokens, type/spacing scale, app shell, one reference screen) before the first feature-UI phase — a plan that ships N feature phases with no design foundation ships N wireframes |
| **otto** | | k8s manifests, Helm, Ingress, Service, Deployment, NetworkPolicy, RBAC, namespaces, persistent volumes, infra YAML |
| **tessa** | | (a) Plan introduces non-trivial logic (parsers, state machines, validators, business rules, API handlers, RAG retrievers/scorers, migrations with logical constraints), (b) plan introduces or modifies an integration boundary (service-to-service, service-to-DB, service-to-cluster wiring, frontend-to-backend contract, app-to-third-party API, new dependency added to a manifest, new RBAC/NetworkPolicy that changes who can talk to whom), or (c) the campaign is in TDD flow (then she's mandatory and also authors the test contract). Skip on doc-only, trivial-rename, or manifest-tuning plans (resource limits, replica counts, image bumps within the same service) |
| **percy** | | Plan touches DB schema or query shapes, caching layers, pagination/streaming of unbounded collections, hot-path endpoints, or bundle-affecting frontend changes — or states an explicit performance goal. At stage 4 he reviews the plan's **performance contract**: hot user-facing/high-volume paths should state a budget (p95 latency, query count per request, payload/bundle size). Skip on doc-only, manifest-only, cold-path, and internal-tooling plans |

Invoke applicable reviewers in **a single parallel message**. Brief each with the plan path and the original task. Severities: Critical / High / Medium / Low.

**Every reviewer brief includes the wiring-sites check**: if the plan introduces or extends a pattern in your lens's domain, verify that harry's `Pattern parity / wiring sites` section is exhaustive — re-run the documented search, name any site that's missing from the list, and treat omission as at least High severity. Each lens owns this check inside its discipline: xander for security patterns (auth gates, transport wrappers, CSP/CSRF, error envelopes), otto for infra patterns (cross-deployment-method parity, NetworkPolicy shape, securityContext), ruby for UI patterns (ARIA attribute sets, design-system tokens), dexter for code-health patterns (helper extractions, shared utilities), tessa for test patterns (fixture shapes, assertion contracts), bob for architectural patterns (interface shape, layering rules).

**Briefing the librarian**: pass the plan path, the project context classification (BROWNFIELD), and the specific net-new abstractions the plan introduces. He returns a verdict (REUSE / EXTEND / PATTERN / NEW / N/A-GREENFIELD). REUSE or EXTEND verdicts must be addressed by harry in stage 6 — they typically mean the plan should be revised to reuse/extend existing code rather than build parallel implementations.

### 5. External review — sebastian on plan (round 1)

Dispatch sebastian for an independent cross-model senior-architect read. **Before dispatch, assert the cross-family invariant**: read `.github/mozart/config/model-map.jsonc` and refuse to dispatch if `roles.validation.family == roles.builders.family` — this is a hard stop, not a soft warning, because the entire value of this stage depends on the reviewer running on a different model family than whoever produced the plan. See `.github/mozart/manual/COUNTERPOINT.md` for the full design.

**Pre-compute sebastian's inputs before dispatching**, into `.mozart/plans/active/<slug>.counterpoint-r1-inputs/`:
- the plan path
- `consumers.txt` — pre-computed consumer-audit searches (every language in the repo, plus adjacent repos `AGENTS.md` names)
- (round 1 has no `diff.patch` or `installed-versions.txt` — there's no diff yet, and the integration-contract sweep only applies to round 2)

**Brief sebastian with**: the plan path, the input-contract directory, the round (`r1-plan`), and the stage-4 consolidated findings (one line each, framed as "the internal panel already found these — spend your budget hunting NET-NEW issues, not re-deriving them"). Field evidence: top defects were routinely derived independently by 3–4 internal lenses, while the cross-model reviewer's unique value was precisely its net-new finds. Pointing it away from the panel's catches is pure gain.

**Success detection — attestation-based, not process-based.** Sebastian is a native subagent; there is no CLI exit code, no output file to poll for, no kill-timer. Success is: (a) the response opens with `MODEL-ATTESTATION: <provider>/<model-id>`, (b) that provider differs from the **attested** provider of the builders who produced the plan under review (compare attested-to-attested; the model map is the fallback only when a builder attestation is missing), (c) the response contains at least one severity header, and (d) it ends with exactly one verdict (proceed / iterate / block). Any other shape is **not a clean pass** — surface the attested values to the user; they decide whether to proceed.

**Stage-exit contract** (do this in one operation, before moving on): when sebastian succeeds, simultaneously (a) tick the stage checkbox `[x] 5. Counterpoint on plan`, (b) write the review to `.mozart/plans/active/<slug>.counterpoint-r1-plan.md` and update the state file's `Counterpoint r1 (plan)` line in the `Paths` block to that path, (c) append an entry to the state file's attestation ledger recording sebastian's attested model for this stage, and (d) append the stage-trace entry to the flow sketch citing the verdict (proceed / iterate / block) and the finding count by severity. Header-vs-checkbox drift (Paths line says "not yet run" but checkbox is ticked) is the #2 audit-finding pattern across the May-2026 multi-repo evaluation — it misleads future-mozart on resume.

### 6. Iterate (harry, if needed)

- **Name the pre-revision sections in the revision message.** A revision invalidates the sections written before it, and nothing cross-reads them by default. When a round changes or adds a mechanism, the findings message must **name every artifact section authored before this round that the mechanism touches** — plan phases, the test contract, the verification list, any enumerated site list or registry — as sections the planner is required to re-read. Line-number floors, counted populations and named-producer registries are the three that go stale silently, because the phase that adds a new member never touches the section that counts them. A revision message naming no such sections is asserting there are none.

- **Short-circuit**: if internal reviewers + sebastian are all clean (no Critical/High), proceed directly to implementation. Don't iterate for its own sake.
- **Otherwise**: **brief the live harry again** (context intact if the harness supports subagent continuation — he still has the plan rationale loaded; if continuation isn't available, re-spawn and brief with the artifacts, per the conductor body's continuation rule) with consolidated findings (cite sebastian's review path explicitly so harry reads it). Harry revises. Re-invoke only the reviewers whose concerns weren't addressed — brief the live reviewer again if it's the same one re-checking its own finding, spawn fresh only when you want an unanchored second look; re-run sebastian only if revisions are substantive (mozart writes `<slug>.counterpoint-r1b-plan.md`, etc.).
- Cap: 3 rounds. **Increment the state file's iteration counter in the same step that launches the round** — a counter you plan to update later is how a written "0/3" cap gets silently exceeded (observed: six reconciliation rounds ran against an un-incremented `0/3`, ai-meeting June 2026). At the cap, present a forced decision to the user — ship with named residual risk, or stop — don't improvise an ad-hoc extension ("ship after r2g regardless" is not a convergence policy).
- Before continuing, confirm the plan has explicit phases jackson can implement one at a time.

### 7. Implement (jackson, phase by phase)

For each phase:

a. **Decide whether to parallelize.** If a phase has genuinely independent work streams (e.g., backend + frontend with no shared touchpoint), invoke jackson on each in parallel — single message, multiple subagent invocations. **Don't parallelize when streams share files or sequencing.** Default to single jackson when in doubt.

b. **Brief jackson** (each stream, if parallel) with: the **absolute** plan path, the **worktree path + campaign branch** he works in (what his workspace-identity preflight checks against — omitting them makes that check impossible to run), the expected runtime environment (see `.github/mozart/manual/WORKTREES.md`, Multi-campaign discipline), the specific phase + stream, and the constraint that he implements *only* that scope. If the campaign has no worktree, say so with the reason instead of leaving the line absent.

c. **Wait for jackson's report(s).** If parallel, wait for all streams before gating.

d. **Per-phase gate** (you):
   - Read the diff yourself (`git diff`)
   - Confirm scope match — flag drift
   - Run the plan's Automated commands that gate this phase: items tagged (phase N), plus untagged items that clearly apply. Record exit codes. If a command cannot run because its environment is genuinely unavailable, record ⛔ with the reason and surface the gap; do not treat Manual items as agent-run checks. If the diff touches a language the repo has no linter/type-checker configured for, that's a gate failure on GREENFIELD (the bootstrap phase was skipped or incomplete) and a surfaced flag on BROWNFIELD — don't quietly substitute "jackson eyeballed it" for a mechanical check
   - **Mechanical secret scan on the staged diff.** Run `gitleaks protect --staged` (or `gitleaks detect` / `trufflehog git` scoped to the phase's commits) when a scanner is installed; otherwise fall back to searching the diff for high-signal patterns: `AKIA[0-9A-Z]{16}`, `-----BEGIN( RSA| EC| OPENSSH)? PRIVATE KEY-----`, `ghp_[A-Za-z0-9]{36}`, `xox[baprs]-`, `eyJhbGciOi`, `(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*['"][^'"]{8,}`. Any hit = gate failure: the value never gets committed, the finding routes to jackson (move to env/secret store) — never "commit now, scrub later," because a secret in git history is already leaked. Reviewer eyeballs (xander, otto, scott) are the backstop, not the control. **A scan that does not run is not a clean scan**: a scanner that exits non-zero, dies on a bad range, or prints nothing because the command itself failed is a gate failure identical in force to a hit — read the exit status, never infer a pass from silence. The empty-input case is the same trap without the error: `gitleaks protect --staged` over an empty index exits 0 and prints nothing, byte-identical to a clean scan of real content, so confirm the scan had a non-empty staged diff to read before you read its silence as a result. This bullet is the shared definition `.github/mozart/agents/scott/PR-AUTHORING.md`'s stage-12b secret scan cites by name, and the liveness rule binds both — the ranges differ (staged diff here, everything `git push` transmits there) and that difference is intentional, but "no output" means the same thing on both
   - **Re-run the plan's wiring-sites search against the diff.** If the plan's `Pattern parity / wiring sites` section enumerates ≥2 sites for this phase, run the documented search yourself and confirm each enumerated non-deferred site appears in the diff. A missing site is a gate failure — brief jackson to extend. If the search returns a new site the plan didn't enumerate, that's a scope-flag event: surface to the user; don't silently widen.
   - Pull in mid-build specialists per stage 8
   - Failures or drift → brief jackson with specifics. Cap: 3 attempts per phase. Escalate if you can't converge.

e. **Mode-dependent commit:**
   - **AUTONOMOUS**: gate clean → commit immediately
   - **LOOP-IN**: gate clean → stage setup → present test instructions → wait for user → commit on approval

f. **Commit rules:**
   - Stage only files relevant to this phase
   - Message: `<type>(<slug>): phase <N> — <description>`, matching repo style (check `git log`)
   - Include a `Co-Authored-By:` trailer naming the model that attested to this phase's work (the provider/model-id from jackson's own `MODEL-ATTESTATION` line for this response) — not a hardcoded name; this port supports multiple model families and the trailer should say which one wrote this phase
   - Never `--no-verify`. Hook fails → fix root cause, new commit
   - Update plan file to mark phase complete

g. **No half-staged slices.** Every implementation session ends with the slice either committed (gate passed) or reverted/stashed with a note — never left as uncommitted partial work. An interrupted session that leaves a half-done diff forces a line-by-line forensic re-audit of everything before work can continue (observed cost: a full-phase re-audit after one overnight interruption). On resume after an interruption, the default is revert-and-redo the slice, not archaeology.

### 8. Mid-build specialists (conditional, parallel)

Run on the slice **before committing** when triggered. **HEAVY tier: ian and xander run on every phase regardless of triggers.** On HEAVY phases, spawn ian with a model override to the strongest available tier when the harness's dispatch mechanism supports one — per-phase contract analysis is exactly where the July-2026 evaluation showed default-tier lenses PROCEED-ing past Criticals that stronger review later caught. If no override is supported, note it and proceed; don't block on it.

| Specialist | Trigger |
|---|---|
| **ian** | Phase modifies public API, exported symbol, function signature, schema, shared utility, or behavior contract |
| **librarian** | BROWNFIELD AND phase introduces a new shared abstraction, utility module, or code in well-trafficked paths (`utils/`, `lib/`, `shared/`, `helpers/`, `common/`, `core/`). Catches duplication that slipped past plan review or emerged during implementation. Skip on GREENFIELD |
| **xander** | Phase touches auth, secrets, untrusted input; adds or upgrades a dependency (manifest / lockfile diff — dependency-vetting checklist); or modifies CI/CD workflow files (CI/CD checklist) |
| **otto** | Phase modifies k8s manifests, Helm, Ingress, Service, Deployment, RBAC, infra YAML |
| **ruby** | Phase introduces or modifies any screen a human will use — user-facing OR operator-facing. Admin consoles, CMS surfaces, internal dashboards, and billing pages all count; "it's internal tooling" is not a skip reason. This trigger fires **in addition to** whatever lens owns the phase's dominant risk — a phase like "admin CMS + analytics" fires xander AND ruby, not xander instead of ruby (the July-2026 athlete-showcase campaign gated its admin-CMS and dashboard phases on security/contract lenses only, and shipped unstyled wireframes that a later remediation campaign had to redesign). A ruby verdict labeled `STRUCTURAL-ONLY` (she couldn't render the UI) is a partial gate: record the owed visual pass as a tracked item — do not count it as UX signoff |
| **dexter** | Phase produces a refactor that smells off, or new shared abstractions |
| **bob** | Phase deviates from the plan in a way you're unsure about |
| **tessa** | (a) Phase modified test files, (b) phase introduced new logic that should be tested (parsers, validators, business rules, API handlers, state machines) but no test diff was produced, (c) phase introduced or modified an integration boundary (new DB call, new HTTP client, new external API consumer, new message-queue producer/consumer, new manifest wiring a dependency, new RBAC/NetworkPolicy changing who can talk to whom) but no integration test diff was produced, or (d) the campaign is in TDD flow (then she's mandatory). Skip on doc-only, trivial-rename, or manifest-tuning phases (resource limits, replica counts, image bumps within the same service) |
| **percy** | Phase adds queries inside loops or new query shapes (he runs `EXPLAIN`), adds a bundle-affecting frontend dependency or route (he measures the size delta), introduces a cache, touches pagination of a growing collection, or lands on an endpoint the plan budgeted. Findings require a measurement or a cited complexity argument — speculative "could be slow" findings don't gate. Skip on cold paths, docs, manifests |

Treat findings the same as plan-review findings: address before committing. Multiple specialists run in parallel when their concerns don't overlap.

**Librarian REUSE/EXTEND mid-build**: if the librarian finds existing code that should have been reused, brief jackson to refactor before committing this phase. Don't ship the duplicate and clean up later.

### 9. External review — sebastian on diff (round 2)

After all phases are committed:

- **TINY**: skip
- **STANDARD**: default-run (skip only on sub-50-LOC mechanical diffs where the plan was trivial and internal reviewers were clean). The May-2026 multi-repo evaluation found "STANDARD external-review skipped" runs that later shipped Criticals the next audit had to catch; the prior "optional" framing trained mozart to skip-by-default, which was wrong.
- **HEAVY**: **non-negotiable** — not "mandatory" with a soft override. Skipping this stage on HEAVY is a self-detected gate failure that requires escalation, never a runtime mozart decision. "Mid-build covered it," "context pressure," and "the diff is mechanical" are not valid skip reasons. Either this review runs, or the campaign stops at `Status: stopped` with a state-file note explaining the blocker and resumes in a fresh session.

**Assert the cross-family invariant again before dispatch** (same check as stage 5 — read `.github/mozart/config/model-map.jsonc`, refuse if `roles.validation.family == roles.builders.family`).

**Pre-compute sebastian's inputs**, into `.mozart/plans/active/<slug>.counterpoint-r2-inputs/`:
- the plan path
- `diff.patch` — a pre-computed `git diff <base-commit>...HEAD` (run `git -C <worktree-path> diff <base-commit>...HEAD`, not sebastian's own tooling — it has no `execute`)
- `consumers.txt` — pre-computed consumer-audit searches against the diff's surface changes
- `installed-versions.txt` — **on the first diff-review pass of this campaign only**: the installed-dependency manifest (`npm ls --depth=0`, `pip freeze`) plus the resolved on-disk paths of every package the diff's external SDK/wire-protocol call sites touch, feeding the integration-contract sweep (check 4, required round 1)

**Brief sebastian with**: the plan path, the input-contract directory, the round (`r2-diff`), and (same as stage 5) the panel's consolidated findings so far, framed as a NET-NEW hunt.

The round-1 integration-contract sweep (check 4) exists because of the costliest observed pattern: seven-round review loops whose biggest finds — an entire SDK's egress calls using the wrong call shape, a protobuf int status compared as a string, a method treated as a list — were pre-existing, round-1-findable contract bugs hidden behind thousands of green mocked tests, surfaced only by a late ad-hoc "holistic sweep." Front-loading that sweep converts 7-round loops into ~2-round loops. **If `installed-versions.txt` is absent or empty, sebastian reports the sweep as `not performed`** rather than answering from memory — a silent degradation converted into a visible one.

Sebastian's Critical/High findings on the diff feed into reconciliation alongside valerie.

**Success detection and stage-exit contract are identical to stage 5** (attestation-based, not process-based): attestation line + cross-family confirmed + severity headers + one verdict = success; any other shape is not a clean pass. On success, simultaneously tick the stage checkbox, write the review to `.mozart/plans/active/<slug>.counterpoint-r2-diff.md`, update the state file's `Counterpoint r2 (diff)` line in `Paths`, append the attestation-ledger entry, and append the flow-sketch stage-trace entry citing the verdict and finding counts.

### 10. Validate (valerie)

- Brief valerie in **FULL** mode: plan path, diff scope (base → HEAD), original task, **the absolute path she writes her validation report to** (`<canonical-checkout>/.mozart/plans/active/<slug>.validation.md`), **and sebastian's r2 findings file when it exists**
- Valerie returns SIGNOFF or FIXES REQUIRED — and the report exists on disk at that path, not only in her return
- **Stage-exit contract, same shape as stages 5 and 9**: on return, simultaneously tick the stage checkbox AND update the state file's `Validation report` line in `Paths` to the actual artifact path AND append the flow-sketch stage-trace entry citing the verdict. A ticked stage 10 beside a `Validation report: not yet run` is the same drift class as a ticked counterpoint box beside an unwritten artifact
- **A SIGNOFF must state the disposition of every open sebastian r2 Critical/High** — resolved (with the commit), or explicitly accepted by the user. Plan-conformance SIGNOFF while cross-model correctness findings sit open is the observed rubber-stamp mode (one campaign: SIGNOFF issued while the reviewer still held six production-killing bugs; reconciliation then ran six more rounds). If sebastian's r2 hasn't converged yet, valerie's FULL pass waits for it.
- **Mechanism drift is in scope**: valerie checks that the shipped HOW matches the plan's HOW, not just that the checklist of WHATs landed. Observed miss: plan said registry-embed-at-load, shipped code did lazy-embed-per-request, signoff said "all plan steps landed." If the mechanism diverged, that's FIXES REQUIRED or an explicit user-accepted deviation — not a silent pass.
- **Verification is exhaustive-or-⛔**: valerie's Automated list must show every plan command run and passed, or recorded `⛔ environment unavailable` with a reason — a skipped command with no `⛔` record is FIXES REQUIRED, not an oversight to wave through.

### 11. Reconcile (jackson + valerie incremental)

If FIXES REQUIRED (from valerie or sebastian's r2):

- **Brief the live jackson again** (context intact if the harness supports subagent continuation — he still has the implementation diff loaded; brief-from-artifacts if it isn't) with the punch list — specific items only, no re-architecture
- Commit fixes (`fix(<slug>): address validation findings — <summary>`)
- Re-invoke valerie in **INCREMENTAL** mode — **brief the live valerie again** (context intact — she already verified the diff once) so she only re-checks the punch-list items + immediate context, not the full diff
- Cap: 3 rounds. **Increment the state file's reconciliation counter in the same step that launches each round** — never retroactively. At the cap, force the decision (ship with named residual risk, or stop); don't silently keep looping.

### 12. Documentation (scott)

After valerie's SIGNOFF, before the final report. Scott updates documentation across all three surfaces:

- **In-repo docs** — README.md, CHANGELOG.md, CONTRIBUTING.md, `docs/` — updated as part of the active branch (mozart commits scott's doc edits as a final tidy-up commit: `docs(<slug>): update README/CHANGELOG for <feature>`)
- **GitHub wiki** — depth pages for new features, updated API references
- **External wiki** (if configured via `## Documentation surfaces` in `AGENTS.md` — Wiki.js, Notion, Confluence, etc.) — runbooks, post-mortems, architectural decisions, cross-cutting context

**Publish boundary — when 12b will run, external publishing defers.** In-repo docs are unchanged: they're committed to the campaign branch before 12b so the doc commit lands inside the PR. The GitHub wiki and any external wiki are different — they're published to the world, and when a PR is about to open, the code they describe hasn't merged. So when 12b will run, **defer** those two surfaces until merge evidence arrives or the user explicitly approves publishing ahead of merge. When 12b will not run — the default, and every repo without a `## Pull requests` stanza — publish exactly as today. The asymmetry is deliberate and worth stating: with a PR there is a concrete event to wait for and a concrete artifact to point at, so the deferral is nameable and resolvable; without one, deferring would mean deferring indefinitely with no trigger.

Scott's return names the deferred surfaces, and the stage-12 line records the reason. **The reason names what actually happened, and never names a PR number unless one exists** — stage 12 runs *before* 12b, so at annotation time there is no PR number yet, and on several paths there never will be. Write the provisional form at stage 12; 12b's return rewrites it in place:

| what happened at 12b | stage-12 line after 12b returns |
|---|---|
| stanza absent or `enabled: false` | `[x] 12. Documentation — in-repo and external published` *(no deferral; the default path is unchanged)* |
| PR opened | `[x] 12. Documentation — in-repo published; external deferred: PR #<n> not yet merged` |
| 12b skipped: no `gh` / no push permission / non-GitHub remote | `[x] 12. Documentation — in-repo published; external deferred: Ship skipped (<reason>), nothing pushed — publish externally by hand or re-run after pushing` |
| 12b stopped: secret-scan hit | `[x] 12. Documentation — in-repo published; external deferred: Ship stopped on secret scan, nothing pushed` |
| stage 12 written, 12b not yet run | `[x] 12. Documentation — in-repo published; external deferred: awaiting 12b` *(provisional; 12b rewrites it)* |

A deferral whose stated cause is fictional can't be acted on by whoever reads it later, which turns the compensating control into exactly the silent drop it exists to prevent. Repeat the deferral in the final report and resolve it on the same trigger as a `pending-pr` disposition.

**When to skip scott**:
- TINY tier with no user-visible impact (pure refactor, code-style cleanup) — skip
- The diff materially changes nothing humans need to know about (renamed an internal variable) — skip
- The user explicitly said "don't document this" — skip

These skip rules govern **stage 12 only. Stage 12b runs on its own condition — see 12b.** Skipping documentation never skips Ship: a TINY refactor with no documentation surface still has a branch, and a branch still needs a merge path.

**When scott is mandatory**:
- New CLI flag, env var, or config key — README must be updated
- New public API surface — README + wiki reference
- Behavior change visible to users — CHANGELOG entry minimum
- Post-mortem-shaped DIAGNOSE → DELIVER — external wiki post-mortem (if configured)
- New service or major architectural change — external wiki runbook + decision record (if configured)

Brief scott with: slug, ticket ID, plan path, investigation/audit doc paths (if any), final commit SHAs, and the diff scope. He determines impact across all three surfaces, makes the changes, and reports back what was published where.

Scott's in-repo edits land on the active branch. Scott's wiki updates are external (GitHub wiki repo, configured external wiki API) and don't affect the branch.

### 12b. Ship (scott)

**Run condition, stated first**: 12b runs when the resolved `pull_requests.enabled` is `true` **and** the campaign has a worktree with commits **and** the remote is GitHub. Otherwise it's skipped and recorded as skipped. Always skipped for read-only flows, OPERATE, INCIDENT, and EVAL. **A repo that declares no `## Pull requests` stanza never reaches the body of this stage** — that is the default, and it is what every repo does today.

**12b's run condition is independent of stage 12's.** Scott being skipped for documentation says nothing about Ship. They share an agent, not a trigger.

**Not gated on SIGNOFF.** A FIXES-REQUIRED campaign may still want a draft PR open — signoff determines draft-vs-ready, not whether the PR exists.

**Brief scott with**: worktree path, branch, base branch, absolute plan path, absolute validation-report path, ticket ID, commit range, the post-doc-commit SHA, and the resolved stanza values including the ref they were read from. **Scott reads `.github/mozart/agents/scott/PR-AUTHORING.md` in full before running this stage** — the complete gate sequence, secret-scan discipline, template resolution, verification checklist, and grant re-validation live there, not in this summary.

**On return**: write `PR: <url> (<draft|ready>)` to the state file's `## Paths` block, rewrite the stage-12 line with the real deferral outcome (see the table in stage 12), and post the PR URL as a ticket comment.

**Failure modes, and what each one records:**
- Stanza absent or `enabled: false` → skip: `[-] 12b. Ship — skipped: no \`## Pull requests\` stanza`
- No `gh` CLI → skip, say so, print the manual command for the user
- No push permission, or a non-GitHub remote → skip, surface the reason
- Secret-scan hit → **stop**, route to jackson, do not push
- **Grant revoked since intake** (the base branch no longer carries `enabled: true`) → **stop, not skip.** Record that the authorization was withdrawn mid-campaign and leave the branch for the user. A skip line would say "this repo never opted in," which is a different fact needing a different response

### 13. Report

#### Promised-tests cross-check (before signoff, when tessa specified integration or E2E tests in the plan)

If tessa's stage-4 review or her test contract (TDD mode) named integration or E2E tests as part of the test strategy, **confirm those tests actually ran** for the merge commit before signing off. Tests that exist in the repo but are excluded from the running suite — skipped, marked with a tag that wasn't selected, in a separate CI job that didn't fire on this PR — are decoration, not verification. This is the canonical gap behind "individual components passed but the integration broke in production."

```bash
# Confirm the integration / E2E jobs ran and passed for the head SHA
gh run list --commit <head-sha> --workflow integration-tests.yml
gh run list --commit <head-sha> --workflow e2e-tests.yml

# Or, for a single-pipeline setup, confirm the promised tests were SELECTED, not merely mentioned.
# A single grep alternating over passed/skipped/deselected is NOT this check: it succeeds on its
# own failure condition, because a run whose promised tests were all skipped matches the
# "skipped" branch and exits 0. Test the two outcomes separately, in opposite directions.
gh run view <run-id> --log > /tmp/run.log
grep -qE "(skipped|deselected)" /tmp/run.log \
  && echo "GAP: promised tests were skipped or deselected in this run — not verification"
grep -qE "[0-9]+ passed" /tmp/run.log || echo "GAP: no passing test count in this run"
```

**When 12b ran, wait for the pushed commit's CI before writing the report.** Poll `gh run list --commit <head-sha> --json status,conclusion` every 30s up to the stanza's `ci_wait_minutes` (default 10). A `completed` status → record the conclusion. Still non-terminal at the bound → record `CI: still running at <n>m — status unknown, not verified` in both the report and the PR body's CI line, and leave that line unticked. **Unknown is not a pass.** Skip the wait entirely when 12b didn't run; nothing was pushed, and these checks stay as latent as they are today. This bound governs the Ship-path CI observation only — the deploy-chain rule below is stricter and unchanged, and a deploy-touching campaign does not get to time out at 10 minutes and call it done.

If a promised test class wasn't actually run for this commit: surface to the user before writing the report. Either re-run the missing job, mark the gap explicitly in the report's `Notable findings`, or — if the user accepts the trade-off — note that the promise was waived and explain why.

#### Deploy chain verification (before signoff, when the campaign touches deploy surfaces)

When the campaign modified anything that flows through a deployment chain (Dockerfiles, k8s manifests, Helm charts, CI workflows, GitOps manifest repos consumed via `kustomize ref=main`, container images), the report cannot be written until the deploy chain has reached and held a steady, healthy state. "Tests passed and valerie signed off" is necessary but not sufficient — the chain must actually deliver the bits to production and (if configured) emit a notification.

Walk every link in the chain end-to-end. The exact shape depends on the project's `AGENTS.md`; for a typical GHA + GHCR + Argo CD setup:

1. `gh run list --commit <head-sha>` — the merge commit's CI workflows are all `success`
2. The image build workflow published a tag matching `<head-sha>` (`gh api .../packages/container/.../versions` or the registry's equivalent)
3. The image-updater / GitOps writer committed an updated manifest to the consuming repo with the new tag — verify the commit + the rendered tag value in the consuming repo's kustomization
4. `kubectl -n argocd get application <name> -o jsonpath='sync={.status.sync.status} health={.status.health.status} revision={.status.sync.revision}'` — sync is `Synced`, health is `Healthy`, revision matches the new manifest commit
5. Pods on the new image: `kubectl -n <ns> get pods -o jsonpath='{range .items[?(@.status.phase=="Running")]}{.metadata.name}: {.spec.containers[0].image}{"\n"}{end}'` — every Running pod references the new tag, no leftover pods on the previous tag
6. Notification trigger fired (if configured) — for Argo: check `notified.notifications.argoproj.io` annotation or notifications-controller logs for an entry keyed by the new sync revision. For Slack/email/Telegram via webhook: check the receiving channel or logs
7. Public smoke (where applicable): an unauthenticated `curl` of a known-good endpoint returns the expected status

If any link is missing, broken, or silent, the campaign is not done. Surface the gap to the user before writing the report — and either remediate it or document it as a known follow-up. **The 2026 audit-refactor incident** where 5 phases shipped, all tests passed, valerie signed off — but Argo's app stayed `OutOfSync` for a month due to an immutable-field error and Telegram notifications were silently suppressed — is the canonical example of a campaign that passed every gate except the one that mattered.

If the project has no deployment infrastructure, note "no deploy chain — campaign produces a library only" in the final report's `Validation` block rather than skipping the section silently.

#### Finalize the flow sketch

Before writing the final report, **finalize the flow sketch** at `.mozart/plans/active/<slug>.flow.md`:
- Set `Run completed` to the current timestamp
- Fill in the **Agent participation summary** table (every agent that was invoked, with role, invocation count, outcome)
- Fill in the **Skipped agents** section with rationale for each persona that wasn't invoked
- Ensure the Mermaid diagram reflects the actual flow that ran (not the planned flow)

#### Campaign closeout (one atomic transaction)

After the final report is written, close the campaign in one sitting. A half-done closeout is the single most common defect in the field corpus (May–July 2026 evaluation: 79% of one project's finished state files still pointed at `active/` paths; 14+ files across repos sat in a finished location with a non-complete status; 28% of done campaigns still said "not yet run" beside a ticked review checkbox; three campaigns stranded their review artifacts in `active/`). The transaction:

1. **Reconcile the state file in place** (edit, don't append):
   - `Status: complete` (or `aborted`), `Current stage` final, `Last updated` stamped
   - Every stage line `[x]` or `[-] skipped: <rationale>` — no bare `[ ]` left, no duplicate stage lines
   - Iteration counters reflect the actual round counts
   - **Every commit SHA cited anywhere in the state file is reachable from HEAD** — assert it, don't eyeball it: `git -C <worktree> merge-base --is-ancestor <sha> HEAD` for each. A SHA that fails this is an orphan from a rebase, an amend, or a squashed phase, and it makes the ledger cite a commit nobody can check out (observed twice in a single campaign; prose discipline failed both times)
   - Paths block lists the ACTUAL artifact paths (no "not yet run" beside a ticked checkbox), and every internal `plans/active/` reference is rewritten to `plans/finished/`
   - Worktree line updated with the merge disposition: `merged | squash-merged | pending-pr | intentionally-unmerged | abandoned` (`pending-pr` carries the PR number and is the one value that legitimately changes after closeout — step 5 owns the resolution). Record it explicitly — squash merges make `git branch --merged` / `--is-ancestor` lie, so without this line, worktree cleanup later requires forensics (observed: three completed mobile campaigns holding unmerged code with no record of whether that was intentional)
   - **Attestation ledger is complete**: every subagent dispatched this campaign has an entry (stage, attested model, whether it matched the frontmatter-declared model)
2. **Finalize the flow sketch** — participation table, skipped-agents rationale, actual-flow mermaid, `Run completed` stamped (see `.github/mozart/manual/STATE.md`, Pipeline flow sketch)
3. **Move ALL slug artifacts by glob, not an enumerated list:**

```bash
slug="<slug>"
mkdir -p .mozart/plans/finished/
mv .mozart/plans/active/${slug}.* .mozart/plans/finished/
# Same glob per artifact root that holds lifecycle artifacts for this slug:
# investigations/, audits/, research/
```

   The enumerated three-extension loop is how sibling artifacts (`<slug>.counterpoint-r2-p0.md`, `<slug>.test-contract.md`, `<slug>.counterpoint-r1b-plan.md`) get stranded in `active/` — the glob catches everything the slug owns. The bare slug doesn't change; only the parent directory does.
4. **Close the loop upward**: if this campaign resolved another campaign's decision point (an audit whose remediation this was, a parent master-plan, a DIAGNOSE this DELIVER remediated), write a closing note into that campaign's state file now — and if this was its last open child, close the parent with this same transaction. Observed drift when skipped: a master plan sat at "plan-authored" forever while all five child campaigns shipped; an audit sat "awaiting user" for 17 days after the user's answer had already shipped as two remediation campaigns.
5. **Dispose of the worktree** (if the campaign had one):
   - Confirm the disposition you recorded in step 1 is *true*, don't assume it: `git branch --merged <base>` for a normal merge; for a squash merge, confirm the squashed commit exists on the base branch. A PR being open is not merge evidence.
   - **merged / squash-merged** → `git worktree remove <path>` (never `--force`; a dirty worktree means uncommitted work exists — surface it instead).
   - **intentionally-unmerged / abandoned** → **leave the worktree and branch in place** and name the path in the final report. A campaign the user may still salvage is not yours to delete; removing it needs their explicit go-ahead.
   - **pending-pr** → **leave the worktree and branch in place**, and name the path **and the PR number** in the final report. Same outcome as the line above, different reason: those two are decisions, this one is a wait on someone else.
   - **Resolving a `pending-pr` later.** It is the only disposition that changes after closeout, it changes in one direction, and the order is fixed. When merge evidence appears (`git branch --merged <base>`, or the squashed commit present on the base branch per this step's first bullet), **rewrite the state file's disposition line to `merged`/`squash-merged` first, and only then remove the worktree** — never the reverse. Remove first and the record still claims a PR is open, which is indistinguishable from a closeout that never finished. The resume-time sweep (`.github/mozart/manual/FLOWS.md`, Detecting an in-progress run at intake, probe 5) is what brings these back for the re-check; without it the value is write-once and the worktrees pile up.
   - Artifacts need no propagation — `.mozart/` lived in the canonical checkout the whole time (see `.github/mozart/manual/WORKTREES.md`, Artifact root), which is what makes this step a cleanup rather than a rescue. **Legacy exception**: campaigns from before that convention may hold their authoritative state inside a worktree; for those, commit or copy the finalized state/flow files back to the canonical checkout and update `Authoritative checkout` before removing anything. A final state that exists only in the worktree is invisible to the next resume — exactly how the "resume an already-merged-and-deployed campaign" hazard happens.

If any step fails, don't leave the campaign half-closed: undo the moves and surface the error rather than leaving the artifacts inconsistent.

**Corruption check after the move**: verify the invariant `Status: complete ⇔ file is in finished/`. The May-2026 multi-repo evaluation found two recurring drifts under the old prefix convention: (a) `Status: complete` state files left in `active/` (or at the legacy `active-` prefix); (b) `finished/` files with `Status: in-progress` bodies (mozart moved prematurely or the campaign never actually completed). After the move, `grep -lE '^\*?\*?Status\*?\*?: complete' .mozart/plans/active/*.state.md 2>/dev/null` should return empty, and `grep -LE '^\*?\*?Status\*?\*?: complete' .mozart/plans/finished/<slug>.state.md` should return empty. If either grep returns a result, the directory or status field disagrees with reality — fix immediately, don't ship the campaign with the discrepancy. When `scripts/mozart-lint.sh` is resolvable, run it against the repo root as the final closeout act — a clean exit (scoped to this slug's findings) is the machine check that the closeout transaction actually completed; prose checklists have twice failed to hold this invariant across evaluation cycles.

Then write the final report:

```
## <slug>: shipped (tier: <TINY|STANDARD|HEAVY>)

**Disposition**: shipped — <the merge evidence>. "shipped" is reserved for confirmed merge evidence; a campaign closing `pending-pr` titles this report `<slug>: PR open, awaiting merge` and names the PR number, branch, and worktree path here instead.
**Plan**: <path>
**Flow sketch**: .mozart/plans/<slug>.flow.md
**Counterpoint**: <r1-plan path>, <r2-diff path if run>
**Research**: <path if produced>
**Investigation** (if applicable): <path>
**Commits**: <SHAs + one-liners>
**Phases**: <count>
**Validation**: SIGNOFF (<reconciliation rounds>) — validation report: <path>
**Documentation**: <in-repo files updated, wiki URLs published, or "skipped — no user-visible impact">

### What was built
<one paragraph>

### Agents involved
<one-line summary referencing the flow sketch — e.g., "harry → bob/librarian → jackson (2 phases, ian mid-build) → valerie → scott. See flow sketch for full trace.">

### Deferred
<from plan's out-of-scope, or "none">

### Notable findings during the run
<anything reviewers / specialists / sebastian surfaced that the user should know>

### Open questions / follow-ups
<unresolved or recommended next work>
```
