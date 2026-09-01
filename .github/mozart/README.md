# The mozart bundle

**Membership contract, two classes.** Everything under this directory
(`.github/mozart/`) **installs** with the bundle (`scripts/install-bundle.sh --target`
copies the whole tree). A file not under `.github/mozart/` never installs
and no `.github/agents/*.agent.md` persona may reference it as a path to
read — that half of the contract has no exceptions.

The stronger claim — "read by an agent at runtime" — is true of *most*, not
all, of what installs. `tests/runtime-reads.tsv` is the actual enumeration:
every `(agent, path)` citation an agent body makes, generated from the
personas themselves (`check_agents.py --emit-runtime-reads`). Two files
install but are never cited by any persona and so never appear in that
manifest: this file (`README.md` — it's for the human configuring the
bundle, not for an agent to read) and `config/.gitkeep` (an empty git
placeholder, not content). Both are installed-but-not-agent-read; everything
else under this directory that ships is also a genuine runtime read, and
`--check-install`/`--check-doc-refs` verify that against the manifest, not
against this file's prose.

## Bundle resolution

Every agent resolves the bundle root once, at boot, by probing two literal
candidates in order: `.github/mozart` relative to the working directory,
then `~/.copilot/mozart` (the user-scope bundle). The first whose `VERSION`
reads wins, and every file for that run is read from that one root — mixing
roots (a manual from one, a model map from another) is a silent desync D7
exists to prevent. If neither candidate's `VERSION` reads, an agent stops
and names both rather than improvising. See `docs/COPILOT_PORT.md` for the
full rationale, including the CLI wrapper's repo-root grant (D9) and the
two-literal-path probe's documented limit (D10).

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
