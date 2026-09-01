# Security

## Reporting a vulnerability

**Preferred**: open a [GitHub Security Advisory](https://github.com/jstuart0/mozart-copilot/security/advisories/new) on this repository. GitHub Security Advisories are private by default — the report will not be visible until you and the maintainer agree on a disclosure timeline.

**Alternate**: email `jay.stuart@agileservicesgrp.com` with "Security:" in the subject line if you prefer not to use GitHub.

Best-effort acknowledgment within 5 business days.

## Scope

This is a markdown-and-config GitHub Copilot port of mozart. It contains no compiled application code and runs no server of its own; the small amount of Python (`scripts/check_agents.py`, `scripts/apply_models.py`) and Bash (`scripts/mozart-lint.sh`, `scripts/mozart-metrics.sh`, `scripts/install-bundle.sh`) is local validation and install tooling with no network calls. Agents defined under `.github/agents/` receive the following capabilities from the Copilot harness, scoped per-agent by each file's `tools:` frontmatter:

- **Shell access** (`execute`) — an agent granted `execute` can run arbitrary shell commands in the user's environment
- **File read/search** (`read`, `search`) — an agent can read and search files in the current workspace
- **File edit** (`edit`) — an agent granted `edit` can modify files on the local filesystem
- **Web access** (`web`) — an agent granted `web` can fetch external URLs
- **Subagent dispatch** (`agent`) — only `mozart` is granted `agent`; it can spawn the specialists named in its `agents:` allowlist, each of which also receives the capabilities its own `tools:` line grants

The user is responsible for reviewing what mozart and its subagents are asked to run. Mozart's own authority constraints (no unprompted pushes to remote, no destructive shared-state operations without explicit user confirmation) are documented in `.github/mozart/PIPELINE.md` under "Authority boundaries". Those constraints are enforced by the persona instructions, not by the harness — they are behavioral, not sandboxed.

**Vulnerability classes of interest:**
- Persona instructions that can be coerced into issuing destructive commands without user confirmation
- Prompt injections that cause an agent to exfiltrate or log secrets
- Template examples that reference probeable infrastructure or real credentials
- Agent chaining patterns that bypass the authority boundaries documented in `PIPELINE.md`
- The counterpoint reviewer (`sebastian`) being granted `execute` — by design it reads adversarial content (an untrusted diff, third-party package sources) and must stay `read, search` only

## Out of scope

- Bugs in the third-party ticketing or documentation services themselves (Plane, Linear, Jira, Wiki.js, etc.)
- Bugs in the Copilot harness (VS Code, Copilot CLI) or GitHub's infrastructure
- Bugs in the consuming repo's `AGENTS.md` configuration
- Social-engineering attacks against the port's human users

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
