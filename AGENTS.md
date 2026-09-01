# AGENTS.md

This file is mozart-copilot's own base instructions for GitHub Copilot, and
the model for the stanza a consuming repo adds to its own `AGENTS.md` once
the bundle is installed (see `.github/mozart/INTEGRATION.md`, landing Phase
5).

## What this repo is

The GitHub Copilot port of the mozart multi-agent orchestration suite:
persona definitions under `.github/agents/`, the runtime bundle those
personas read from under `.github/mozart/`, and a small set of
validation/install tooling under `scripts/`. It ships no application code of
its own.

## The agent-file contract

Every file under `.github/agents/*.agent.md` must satisfy
`scripts/check_agents.py`'s checks: frontmatter present and correctly
delimited; `name` equal to the filename stem; `description` non-empty;
`tools:` explicit and every entry a member of `config/toolsets.jsonc`;
`model:` a scalar string; `agents:` present (`[]` on every specialist, an
explicit allowlist on the conductor); `agent` in `tools:` if and only if
`agents:` is non-empty; exactly one file `user-invocable: true` and it is
`mozart`; a `## Model attestation` marker in the body; the body under the
30,000-character cap (two-delimiter extractor, character not byte
semantics); and every path-like reference in the body resolving under
`.github/mozart/`. See `CONTRIBUTING.md` for the full nine-section authoring
contract new personas must follow.

## The bundle path

Every file an agent reads at runtime lives at exactly one path:
`<workspace>/.github/mozart/`. There is no fallback and no search order. If
an agent can't find a bundle path it expects, it stops and names the missing
path rather than improvising — see `.github/mozart/README.md` for the
membership contract and `docs/COPILOT_PORT.md` for the full rationale.

## How to run the checks

```bash
python3 -m py_compile scripts/check_agents.py
bash -n scripts/mozart-lint.sh scripts/mozart-metrics.sh

# Validator self-test against the fixture corpus
python3 scripts/check_agents.py --self-test --forms

# Full roster (raise --min-agents as the roster grows; see the campaign
# plan's step 8 for which phase owns each bump)
python3 scripts/check_agents.py --min-agents <current roster size>

# Cross-check the primitive-mapping doc against the tool vocabulary
python3 scripts/check_agents.py --check-doc-table

# Validate a single persona while drafting it
python3 scripts/check_agents.py --file .github/agents/<name>.agent.md
```

Once the model map exists (Phase 6): `python3 scripts/apply_models.py
--check` (drift), `--check-families` (D8's cross-family invariant), and
`--check-tiers` (upstream tier preservation).
