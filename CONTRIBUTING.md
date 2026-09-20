# Contributing

Thank you for your interest in improving mozart-copilot. This is the GitHub
Copilot port of the mozart orchestration system — its behavior lives in
`.agent.md` persona files under `.github/agents/`, the runtime bundle under
`.github/mozart/`, and a small set of validation/install scripts under
`scripts/`. See `.github/mozart/README.md` for the bundle's membership
contract before touching anything under it.

## Persona authoring contract

Every specialist persona file (`.github/agents/*.agent.md`) must include, in
this order:

1. **YAML frontmatter** — `name`, `description`, `tools`, `model` (a scalar
   string, never a YAML sequence), `agents` (`[]` for every specialist; the
   conductor's allowlist for `mozart`), `user-invocable` (`false` for every
   specialist; `true` only for `mozart`). The `description` field is what VS
   Code's agent picker shows for `mozart` (the only user-invocable agent) and
   what a reader sees when browsing `.github/agents/` — write it for someone
   who doesn't know the pipeline. ~30–50 words. No jokes.
2. **Opening paragraph** — who the agent is, what its job is, what it
   explicitly does not do.
3. **`## Code retrieval`** — the code-aware-retrieval guidance, copied
   verbatim from an existing specialist.
   **The bundle-resolution sentence is inserted immediately before the
   persona's first `.github/mozart/` citation, wherever that citation
   actually falls** — not tied to any specific heading. For nearly every
   specialist that citation is the code-aware-retrieval paragraph itself,
   so in practice the sentence becomes `## Code retrieval`'s own first
   paragraph, as its own paragraph (one blank line before and after — see
   any existing specialist for the exact wording and pattern):
   `**Bundle resolution.** Every \`.github/mozart\` path below is a
   citation form: read it from the bundle root your brief names. If no
   root reads, stop and say so — don't answer from memory.`
   **The one documented exception**: a persona whose own `## Code
   retrieval` section makes no bundle citation at all — `sebastian`, which
   works from mozart's pre-computed inputs rather than its own retrieval —
   gets the sentence immediately before whichever later section makes its
   actual first citation instead (for `sebastian`, `## Where you fit in
   mozart's pipeline`, right before its `PIPELINE.md` reference). The rule
   is "immediately before the first read," never "inside this heading
   regardless of whether it reads anything" — a sentence placed ahead of
   a citation-free section guards nothing.
   **D13 — no path-shaped literals**: any bundle path used illustratively
   elsewhere in the body (not as a real citation) must not be path-shaped
   enough to match `BUNDLE_REF_RE` — use the bare directory
   (`` `.github/mozart` ``), never a trailing-slash-plus-filename shape. A
   path-shaped illustrative example becomes a phantom manifest row that
   `--check-doc-refs` then fails on, for a path that was never real.
4. **`## Where you fit in mozart's pipeline`** — the stage marker, a short
   "Before you / After you" list, triggers, and a "Not your lane" boundary
   statement. Close with: `See the bundled \`.github/mozart/PIPELINE.md\` for
   the full reference.` The marker's form and rules mirror the Claude Code
   edition's contract; this section appears exactly once, ahead of
   `## Field notes`.
5. **`## Default standard`** — copy the canonical paragraph verbatim from the
   `## Default standard` section of an existing specialist (cite the section,
   never a line range — the range shifts as the file above it grows). This
   paragraph is identical across every specialist.
6. **`## Core operating principles`** — role-specific principles, as specific
   subsections.
7. **`## Working mode`** — how the agent processes a task end-to-end,
   numbered steps.
8. **`## Output format`** — a fenced markdown template for the agent's output
   artifact.
9. **`## Model attestation`** — copy verbatim from `docs/COPILOT_PORT.md`
   once that section exists (Phase 2): begin every response with
   `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
10. **`## Communicate as you work`** — copy this section verbatim from an
    existing specialist. It is the same in every specialist.
11. **`## Field notes (append-only)`** — copy the stub from any existing
    specialist. Append-only; see `.github/mozart/LEARNINGS.md` for the
    protocol.

**Voice**: professional and precise. Match the density and tone of
`.github/agents/mozart.agent.md` and `.github/mozart/INTEGRATION.md`. No
emojis. No jokey lines.

## When you add a new agent, also update

- `.github/mozart/PIPELINE.md` — add the agent to the Agent roster table and
  to the appropriate reviewer/specialist trigger table
- `.github/agents/mozart.agent.md` — add the agent to its `agents:`
  allowlist (mozart is the only agent that can dispatch a specialist)
- `.github/mozart/config/model-map.jsonc` — assign the agent a role in the
  `roles` block (or reuse an existing role) and add it to the `agents` block;
  then re-stamp with `python3 scripts/apply_models.py --apply`
- `README.md` — add the agent to the orchestra table and update the agent
  count
- `tests/fixtures/upstream-tiers.tsv` (if the agent has an upstream Claude
  Code counterpart) — record its upstream model tier so
  `apply_models.py --check-tiers` can verify the port didn't silently retier
  it
- `.github/workflows/check.yml` — the roster floor is pinned in **nine**
  `--min-agents N` invocations, the step name that announces it, and an
  **asserted failure-message substring** (`--min-agents requires >= N`).
  Raise the floor and leave the substring and the step fails with a message
  that says nothing about the agent you added. After the bump,
  `grep -c -- '--min-agents <old N>' .github/workflows/check.yml` must be `0`
- The **other eight** full-roster map documents besides
  `.github/mozart/config/model-map.jsonc` — `config/model-maps/*.jsonc` and
  the `tests/fixtures/map-*.jsonc` / `same-family.jsonc` corpus. Each
  enumerates the whole roster, and the fixture steps assert *exactly one*
  FAIL, so an agent file with no entry in a fixture map adds a second one and
  breaks a step that has nothing to do with your change. Deliberately
  excluded: `tests/fixtures/roster-floor-agents/` and
  `tests/fixtures/map-roster-floor.jsonc`, which exist to violate the floor,
  and the one agent `map-uncovered-agent.jsonc` omits on purpose
- `docs/COPILOT_PORT.md` — the `N of M agents are specialists` cardinality
- `.github/agents/mozart.agent.md` — the prose sentence counting specialists,
  which is a separate site from the `agents:` allowlist above

The last four are **cardinality-only**: they carry a number and never the new
agent's name, so a sweep that greps for the name finds none of them. Grep for
the outgoing count as well as the incoming name.

## Decision IDs

Design decisions carry a `D<n>` ID (`D1`, `D9b`, `D14`, ...). These IDs are
**scoped to `docs/COPILOT_PORT.md`'s Decision registry** — that table is their
one canonical definition. Cite a bare `(D9)` inline wherever it clarifies a
choice; a reader resolves it against the registry. When you make a new port-level
decision worth an ID, add its row to the registry in the same change — do not
mint an ID that resolves nowhere.

## Local testing

There is no compiled build. "Testing" means running the mechanical gates and
reading your diff carefully:

```bash
python3 -m py_compile scripts/check_agents.py
bash -n scripts/mozart-lint.sh scripts/mozart-metrics.sh
python3 scripts/check_agents.py --self-test
python3 scripts/check_agents.py --min-agents <current roster size>
```

`check_agents.py` runs every action flag you pass in one invocation and returns
the highest-priority status (`1` > `2` > `0`); `--emit-runtime-reads` is
mutually exclusive with all other actions. Modifier flags are accepted only with
the actions that consume them — `--min-agents` with `--map`/`--check-install`,
`--layout` with `--check-install`, `--upstream-mozart-md` with `--check-carve`,
and `apply_models.py`'s `--upstream-readme` with `--check-tiers` — otherwise the
run exits `2` naming both flags.

If you changed `scripts/mozart-lint.sh` or `scripts/mozart-metrics.sh`, also run
the cross-repo parity check against a mozart-orchestration checkout:

```bash
bash scripts/check-lint-parity.sh /path/to/mozart-orchestration
```

`mozart-lint.sh` must equal orchestration's modulo the allowlisted reviewer-label
diff committed at `tests/lint-upstream.diff`; `mozart-metrics.sh` must be
byte-identical. It is deliberately **not** a CI step — CI has no second checkout,
so it would be permanently red or vacuously green. It narrows the manual review of
that diff; it does not replace it. `AGENTS.md` has the full rationale.

If you changed a persona's output format, run it against a sample input and
confirm the output matches the template. If you changed
`.github/mozart/PIPELINE.md`, verify it stays consistent with
`.github/agents/mozart.agent.md` (the two must agree on shapes, tiers,
partial flows, and the agent roster).

## Commit and PR style

This project uses [Conventional Commits](https://www.conventionalcommits.org/).
Common types for this repo:

- `docs(persona):` — editing a persona file
- `feat(persona):` — new persona or new section in a persona
- `docs(pipeline):` — changes to `.github/mozart/PIPELINE.md`
- `docs(integration):` — changes to `.github/mozart/INTEGRATION.md`
- `chore(ci):` — CI or workflow changes
- `fix(persona):` — correcting an instruction that causes wrong behavior

## PR checklist

Before opening a pull request, confirm:

- No homelab fingerprints or personal infrastructure references have been
  introduced — this project is product-neutral
- Voice is consistent with `.github/agents/mozart.agent.md` and
  `.github/mozart/INTEGRATION.md` (professional, no emojis)
- If a new agent was added: `PIPELINE.md`, `mozart.agent.md`'s `agents:`
  allowlist, `README.md`, and `.github/mozart/config/model-map.jsonc` are all
  updated
- `python3 scripts/check_agents.py --self-test` and
  `python3 scripts/check_agents.py --min-agents <roster size>` both exit 0
- `CHANGELOG.md` has an entry for the change

## Field-notes protocol

The `## Field notes (append-only)` section at the bottom of each specialist
persona is an append-only log of cross-project patterns. See
`.github/mozart/LEARNINGS.md` for the protocol and the entry template. Do not
edit any other section of a persona file when adding a field note — those
sections are human-authored contracts.
