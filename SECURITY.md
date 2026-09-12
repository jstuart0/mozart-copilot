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

## Bundle provenance gate — what it is, and what it is not

The CLI wrapper (`scripts/mozart`) runs a **provenance gate** before launching: when the repo it is rooted in ships its own `.github/mozart` bundle, the wrapper compares that bundle against the one you installed (`~/.copilot/mozart`) and, on any difference, refuses to launch unless the repo root has been recorded as trusted (by a `--user-scope`/`--target` install, `scripts/install-bundle.sh`) or is named for that one invocation by `MOZART_TRUST_REPO_BUNDLE=<repo-root>`.

Understand the guarantee precisely. This is **consent + baseline comparison, not authenticity**: it proves *"this tree is not the one you installed from"* and makes you consent before a drifted bundle runs. It does **not** prove the tree is genuine, unmodified, or safe. Trust is keyed on user-side state (your recorded roots), never on anything the repo itself ships — a repo-content heuristic is forgeable for free, so the gate deliberately ignores repo content when deciding trust.

**Known limits (all in scope for reports, none currently fixed):**

1. **Not a universal gate.** It is bypassed entirely by a bare copilot launch, by VS Code (which never runs the wrapper), and by any already-running agent. It guards the wrapper's `exec`, nothing else.
2. **No content verification.** It performs no signature and no checksum verification of bundle contents; it is a directory *diff* against your installed baseline, not an integrity check against a trusted source.
3. **TOCTOU.** The tree is proven to match your baseline at check time, and then `exec copilot` hands a long-running agent the same bundle afterward — a swap in that window is not re-checked.
4. **Environment-injectable trust.** `MOZART_TRUST_REPO_BUNDLE` is read from the environment, so a hostile repo that ships a `.envrc`/`.env` exporting `MOZART_TRUST_REPO_BUNDLE=$PWD` self-trusts its own poisoned bundle in any shell that auto-loads it. For this reason the override is **per-invocation only**, and auto-loading it via direnv or an equivalent per-repo env mechanism is an **anti-pattern** for this variable — it teaches exactly the reflex (trusting repo-local content) the gate exists to break. Do not wire it into direnv.
5. **Path-based, not content-based.** Trust is path-based: it is recorded against a repo *root*, and contents at a trusted path are never re-authenticated — so a `git pull`, a merged pull request, or any in-place edit of a trusted checkout **inherits trust automatically**.

**Other accepted residuals** in the surrounding install/launch tooling: a symlinked *ancestor* directory above an operator-supplied install root is not resolved by `install-bundle.sh` (catching it would require an unconditional `readlink -f`/`realpath`, whose flags diverge across BSD and GNU — a portability trap the script avoids; the `[ -L ]` container and leaf checks cover every path the installer itself creates). Separately, the shipped model maps follow a same-family `fallback` convention that is **conventional, not enforced** — a cross-family fallback could converge the builder and validation roles onto one family during a provider outage; this D8 gap is documented in full in `docs/COPILOT_PORT.md`. Separately again, the documented uninstall procedure (`README.md`'s Uninstall section, `scripts/uninstall.sh`) narrows but does not eliminate a leaf-and-ancestor pathname TOCTOU between validating a file's identity and deleting it — a concurrent local actor able to mutate `<copilot-home>/agents/` or the wrapper's directory in that window is a documented, accepted residual, not a defect.

## Out of scope

- Bugs in the third-party ticketing or documentation services themselves (Plane, Linear, Jira, Wiki.js, etc.)
- Bugs in the Copilot harness (VS Code, Copilot CLI) or GitHub's infrastructure
- Bugs in the consuming repo's `AGENTS.md` configuration
- Social-engineering attacks against the port's human users

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | Yes       |
| < 0.3   | No        |
