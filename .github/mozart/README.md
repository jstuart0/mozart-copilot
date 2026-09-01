# The mozart bundle

**Membership contract**: everything under this directory (`.github/mozart/`)
is read by an agent at runtime and installs with the bundle. Nothing outside
it is a runtime read. If a file is not under `.github/mozart/`, no
`.github/agents/*.agent.md` persona may reference it as a path to read.

## Single resolution path

Every agent resolves bundle content at exactly one path:
`<workspace>/.github/mozart/`. There is no fallback and no search order in
v1 — if the bundle is absent from a workspace, an agent stops and names the
missing path rather than improvising. See `docs/COPILOT_PORT.md` (from
Phase 2 onward) for the full rationale, including why a two-step
`~/.copilot/mozart/` fallback is documented as designed-for-v2 and
unvalidated rather than shipped as behavior.

## What lives here

- `manual/` — the conductor's bundled reference manual, carved out of the
  monolithic upstream conductor persona to fit the 30,000-character body cap
  (lands Phase 5)
- `agents/<name>/` — persona-private overflow documents for personas that
  don't fit the cap on their own (e.g. `agents/scott/PR-AUTHORING.md`) (lands
  Phase 4+)
- `config/model-map.jsonc` — the canonical active model-role assignment,
  read by the conductor at runtime *and* written by
  `scripts/apply_models.py` at build time (lands Phase 6)
- `PIPELINE.md`, `LEARNINGS.md`, `INTEGRATION.md`, `EVAL.md`, `VERSION` —
  bundle-root reference documents cited from persona bodies (lands Phase 5+)

## What does not live here

Build-time-only files — the validator's tool vocabulary
(`config/toolsets.jsonc`), the shipped model-map presets
(`config/model-maps/*.jsonc`), the fixture corpus (`tests/`), and the
validation/install scripts (`scripts/`) — live at the repo root and are never
copied into an installed bundle. See the Decisions section of the campaign
plan (D14) for why the split is by *when a file is read*, not by directory
convention.
