# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once it reaches `1.0.0`. Before that, `0.x` releases may include breaking changes.

## [Unreleased]

### Added
- Repo skeleton and OSS boilerplate: `LICENSE` (MIT), `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CONTRIBUTING.md`.
- Bundle namespace `.github/mozart/` and the build-time/runtime config split (repo-root `config/` vs the installable bundle).
- `config/toolsets.jsonc` — the verified Copilot tool vocabulary and the Claude-tool-noun-to-Copilot-tool mapping.
- `scripts/check_agents.py` — the mechanical persona validator (frontmatter, body-size cap, bundle-path resolution, model-map cross-checks).
- The fixture corpus under `tests/fixtures/` proving the validator actually rejects malformed personas.
- `scripts/mozart-metrics.sh` and `scripts/mozart-lint.sh`, ported from the Claude Code edition (`mozart-lint.sh` generalized to the `Counterpoint|Codex|Claude` external-review label set).
- CI workflow `.github/workflows/check.yml`, hardened (pinned actions, read-only permissions, no `pull_request_target`).
