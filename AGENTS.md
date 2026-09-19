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
`.github/mozart/`. See `CONTRIBUTING.md` for the full eleven-section
authoring contract new personas must follow.

## The bundle path

Every `.github/mozart` path an agent body cites is a citation form, not a
fixed location — resolved once at boot against two literal candidates, in
order: the workspace bundle (`.github/mozart/`, when the working directory
is the repo root) and, when that candidate has no `VERSION`, the user-scope
bundle (`~/.copilot/mozart/`). If neither resolves, an agent stops and names
both candidates rather than improvising — see `.github/mozart/README.md`
for the membership contract and `docs/COPILOT_PORT.md` for the full
rationale.

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

# Conductor-corpus behaviour loop (the local equivalent of check.yml's
# "Conductor corpus" steps). Lint runs under the fixture-date override, so
# the corpus's 2099-dated campaigns land post-adoption; the control run
# below must NOT print the override-visibility line.
MOZART_LINT_CONDUCTOR_SINCE=2099-06-01 \
  bash scripts/mozart-lint.sh tests/fixtures/campaign/conductor/lint   # expect exit 1
bash scripts/mozart-lint.sh tests/fixtures/campaign/conductor/lint     # control
for c in metrics-placeholder metrics-conductor metrics-vacuity; do
  bash scripts/mozart-metrics.sh "tests/fixtures/campaign/conductor/$c"  # expect exit 0
done
```

Each corpus case carries its own `expected.tsv`; `check.yml` asserts the full
set equality, the override-visibility line in both directions, and the
section-scoped prose sites. Run those step bodies verbatim to reproduce CI.
The corpus is a byte copy of mozart-orchestration's
`tests/fixtures/conductor/` — `diff -r` between the two is the cross-repo
check, and it runs at campaign-verification time, not in CI.

The campaign scripts have a matching cross-repo check, for the same reason
off CI:

```bash
bash scripts/check-lint-parity.sh /path/to/mozart-orchestration
```

`scripts/mozart-lint.sh` must equal the source's modulo the allowlisted
reviewer-label diff committed at `tests/lint-upstream.diff`, and
`scripts/mozart-metrics.sh` must be byte-identical to it. The script also
guards against a vacuous pass (an empty or truncated allowlist file) with a
changed-line floor and a named member. It narrows the manual review of that
diff; it does not replace it.

`check_agents.py` is an **aggregating** dispatcher: pass several action flags in
one invocation and it runs every one, returning the highest-priority status
(a real failure `1` outranks a nothing-to-check `2` outranks a clean `0`).
`--emit-runtime-reads` is the one exception — it is mutually exclusive with all
other actions (its stdout is the generated `tests/runtime-reads.tsv`).

Modifier flags are only accepted with the actions that consume them, otherwise
the run exits `2` naming both flags: `--min-agents` with `--map`/`--check-install`
(or the bare roster check), `--layout` with `--check-install` only, and
`--upstream-mozart-md` with `--check-carve` only. The same rule governs
`apply_models.py`'s `--upstream-readme`, which is meaningful only with
`--check-tiers`.

Once the model map exists (Phase 6): `python3 scripts/apply_models.py
--check` (drift), `--check-families` (D8's cross-family invariant), and
`--check-tiers` (upstream tier preservation).
