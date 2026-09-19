# mozart-copilot

A multi-agent software-delivery orchestration suite for **GitHub Copilot**.

`mozart` is a senior delivery *conductor*: it doesn't write the code itself, it
decides which specialist runs, when, and in what order — then dispatches them
as Copilot subagents and drives the work end-to-end. This repo is the GitHub
Copilot port of the mozart orchestration system (originally built as a Claude
Code plugin; also ported to OpenAI Codex CLI as `mozart-codex`).

> **Status: port complete, runtime validated only mechanically.** The 22
> personas, the six-shape pipeline, the model map, the installer, and the
> validator tooling are all in place and pass their own gates — `check_agents.py`,
> `apply_models.py`, and `install-bundle.sh`'s bite tests all run green. What
> hasn't run yet is a live VS Code session: whether the agent picker shows
> only `mozart`, whether `disable-model-invocation` means what this port
> assumes, and whether a cross-model counterpoint review actually lands on a
> different model family in practice rather than only in its attestation
> line. Those are the campaign plan's Manual checklist — see
> `docs/COPILOT_PORT.md`'s "Pending manual verification" section.

## What it does

Mozart orchestrates work across six shapes:

- **DELIVER** — build a feature: research → plan → review → implement → validate → ship → document
- **AUDIT** — review against a goal: discover → fan-out → synthesize → optionally remediate
- **DIAGNOSE** — investigate a failure: intake → investigate → present findings → optionally remediate → optionally publish post-mortem
- **INCIDENT** — respond to a live outage: declare+triage → stabilize ‖ race hypotheses → converge → durable fix → verify recovery → blameless post-mortem. Mitigate first to restore service (logged + reversible), root-cause in parallel, then durable-fix with full gates restored; mozart is the incident commander, and a running timeline is the spine
- **OPERATE** — change or debug a live system: intake+context pin → recon → change plan → pre-flight (dry-run+snapshot) → apply → verify observed → record rollback. Verified empirically, reversed by a recorded rollback, not `git revert`
- **EVAL** — evaluate mozart's own field performance from past campaign artifacts and improve the configuration. No separate entry point — reached through the conductor like every other shape (D12)

At intake it **tiers** the task (TINY / STANDARD / HEAVY; SEV1/2/3 for
incidents) to right-size the gates, classifies the project (GREENFIELD /
BROWNFIELD), and recognizes when a request is genuinely a single agent's
job — routing it directly instead of imposing the full pipeline.

## The orchestra

| Agent | Role | Model role |
|---|---|---|
| **mozart** | Conductor — runs the pipeline, dispatches the rest (this is the only agent you invoke directly — D10) | `conductor` |
| harry | Planner — produces the phased implementation plan | `deep-reviewers` |
| bob | Architect reviewer — design, layering, trade-offs | `deep-reviewers` |
| ruby | UX reviewer — states, accessibility, responsive, voice; implements and verifies UI in a browser | `deep-reviewers` |
| valerie | Validator — checks implementation against the plan; runs the plan's Automated commands | `deep-reviewers` |
| jackson | Implementer — writes and reconciles code, phase by phase | `builders` |
| hank | Ops executor — applies changes to live infrastructure (OPERATE) | `builders` |
| scott | Technical writer — documentation, CHANGELOG, release notes; opens the PR when the repo opts in | `builders` |
| sarah | Technical researcher — surfaces prior art and best practices | `reviewers` |
| dexter | Code-health reviewer — duplication, complexity, naming, test seams | `reviewers` |
| xander | Security reviewer — threat model, injection, auth, secrets | `reviewers` |
| otto | Infrastructure-ops reviewer — infra, config, deployment, ops | `reviewers` |
| tessa | Test-strategy and test-quality reviewer | `reviewers` |
| percy | Performance engineer — measurement-first | `reviewers` |
| librarian | Code archaeologist — does this already exist? (BROWNFIELD only) | `reviewers` |
| ian | Change-impact analyst — ripple effects from the diff | `reviewers` |
| dick | Bug investigator — DIAGNOSE lead; reproduces, isolates, roots out. No `edit` — findings and a verdict, never a fix | `reviewers` |
| codebase-analyzer | Reads and summarizes code for higher-level agents | `support` |
| codebase-pattern-finder | Finds usage patterns across the codebase | `support` |
| web-search-researcher | Searches the web and fetches external pages | `support` |
| codebase-locator | Finds files matching a description or topic; doesn't read file contents by design | `fast-scan` |
| **sebastian** | Independent cross-model counterpoint reviewer — DELIVER stages 5 and 9. Read-only by design (D1) | `validation` — always the non-builder family (D8) |

Each specialist is a Copilot subagent defined in [`.github/agents/`](.github/agents/).
Only `mozart` is `user-invocable: true` (D10); every specialist is reachable
solely through mozart's `agents:` allowlist, so intake, tiering, the
counterpoint gate, worktree isolation, ticket lifecycle, and PR
authorization can't be routed around. The upstream single-agent passthrough
survives — you can still say "have bob look at this plan," and mozart routes
it directly without imposing pipeline overhead.

## How it maps to GitHub Copilot

Mozart's architecture rests on Copilot's native `.agent.md` subagent
mechanism: the `agents:` frontmatter allowlist plus the `agent` tool cover
the dispatch mozart needs, and parallel subagent invocation covers fan-out.

The **independent cross-model reviewer** — a shelled-out `codex exec` CLI
call in the Claude Code edition — becomes a native in-process subagent
(`sebastian`) here: no process lifecycle, no stdin/kill-timer discipline, no
output-file polling. Same value (a different model family auditing the
work), a strictly simpler mechanism.

Full primitive mapping, the nine translation rules, the counterpoint
reviewer's design, and every known quirk (including the subagent
`model:`-fallback issue `## Model attestation` exists to catch):
[`docs/COPILOT_PORT.md`](docs/COPILOT_PORT.md).

### Runtime-surface scope

| surface | status |
|---|---|
| VS Code | **supported** — the only runtime this port designs and validates against |
| Copilot CLI | **loads-but-unvalidated** — the `mozart` wrapper carries the grants automatically (`--add-dir`, repo-root normalization); agent files are read and the roster appears; whether the dispatch protocol works under `/fleet`, and whether a dispatched subagent inherits the wrapper's grant, are pending manual confirmation (see "Pending manual verification" in `docs/COPILOT_PORT.md`) |
| Cloud coding agent | **out of scope** — ignores `model:`, has no subagent primitive |

## Install

**One-time, once per machine (`--user-scope`).** Installs the full stack —
agent definitions, the bundle, and a `mozart` CLI wrapper — into your
Copilot home, and prints the two settings VS Code needs. Most people only
need this.

```sh
scripts/install-bundle.sh --user-scope --apply
```

Dry-run by default (omit `--apply` to preview, writes nothing). Resolves
your Copilot home from, in order: `--copilot-home <dir>`, `--home <dir>`'s
`<dir>/.copilot`, `$COPILOT_HOME`, or the default `~/.copilot` — the
resolved value and which rule produced it are always printed. Refuses
(`--force` required) to move an installed bundle backwards; refuses
(`--force-clobber` required) to overwrite a pre-existing wrapper binary or
agent file that isn't byte-identical to what it would install, so a
hand-edited or stranger's file on your `PATH` or in `~/.copilot/agents/` is
never silently discarded. `--no-bundle`/`--no-wrapper` opt out of the
bundle or the wrapper independently.

**CLI needs zero extra settings — the wrapper carries the grants.** VS Code
needs two settings, pasted once, printed at the end of every install:

```
"chat.agentFilesLocations": ["<copilot-home>/agents"]
"chat.additionalReadAccessFolders": ["<copilot-home>/mozart"]
```

`chat.agentFilesLocations` is *discovery* — without it, `mozart` never
appears in the VS Code picker. `chat.additionalReadAccessFolders` is the
*read* grant. Reload the window after pasting.

**Pin a bundle into one specific repo instead** — vendors a version-locked
bundle into that repo rather than sharing the machine-wide one:

```sh
scripts/install-bundle.sh --target /path/to/your-repo --apply
```

Installs `.github/agents/*.agent.md` and the whole of `.github/mozart/`
into the target repo; nothing from this repo's own `config/`, `tests/`, or
`scripts/` is installed (D14). Same downgrade guard as above (`--force` to
move a pinned bundle backwards). When a repo has its own pinned bundle, it
wins over the shared user-scope one for any run rooted at that repo's root
— see Use below.

`--target` and `--user-scope` are mutually exclusive (passing both exits 2).

## Use

**Copilot CLI** — after the one-time install, from any repo:

```sh
mozart "add SSO via our IdP to the admin panel"
mozart -p "audit this repo for tech debt"
```

The wrapper resolves the git repo root (announcing the move on stderr if it
had to `cd` there from a subdirectory), grants the bundle, and execs
`copilot --agent mozart` — no `--add-dir` to type, no settings to paste.

**VS Code** — open the agent picker and select `mozart` (it's the only
agent that appears there — every specialist is `user-invocable: false`).
Hand it the task the same way:

```
add SSO via our IdP to the admin panel
audit this repo for tech debt
investigate why staging queries are slow
resume the campaign at .mozart/plans/active/<slug>.state.md
```

**Which bundle wins.** A repo's own `.github/mozart/` (installed via
`--target`) wins over the shared user-scope bundle whenever the process is
rooted at that repo's root — the CLI wrapper and VS Code both guarantee
that; a bare `copilot` launched in a subdirectory does not, and resolves
the user-scope bundle instead (D7). Mozart reports the resolved root and
that bundle's `VERSION` in its first narration line, so a stale or
unexpected bundle is visible immediately rather than inferred from
behavior.

On its first turn mozart also reads `.github/mozart/manual/INDEX.md` (the
routing table for the rest of the bundle) and `.github/mozart/manual/INTAKE.md`
(shape-boundary tests, task tiers, project context) from that resolved
root — the two mandatory boot reads. It then runs intake (shape, tier,
mode, slug), creates a state file and a flow sketch, and conducts the
pipeline, narrating each specialist dispatch so you can follow along.
Alongside those two it keeps a decisions log
(`.mozart/plans/active/<slug>.decisions.md`) from the first judgment call
onward, and records its own derived claims — a check it ran, a dispute it
settled, a fact it relied on — in the state file's `## Conductor record`,
each with the control that would have shown the claim false. If
neither bundle candidate resolves, mozart stops and names both rather than
improvising — see Install above.

**Custom `COPILOT_HOME`.** If you installed with `--copilot-home` (a
non-default Copilot home), the CLI wrapper enforces a symlink at
`~/.copilot/mozart` pointing at your configured bundle before every launch
— the installer prints the exact `ln -s` command, and the wrapper refuses
with the same remedy if the link is missing or stale. VS Code has no
equivalent pre-launch hook; the same symlink is the fix there too.

## Operating: upgrade, uninstall, troubleshoot

These three procedures cover the behavior changes the installer and the CLI
wrapper introduced. All paths below use `<copilot-home>` for your resolved
Copilot home (default `~/.copilot`).

### Upgrade

Re-running the installer no longer silently overwrites files. It **refuses**
(exit non-zero) when a destination file already exists and is not byte-identical
to what it would install — a hand-edited persona in the shared
`<copilot-home>/agents/` namespace, or a `mozart` wrapper already on your `PATH`.
A byte-identical file is a silent no-op, so a re-run that changes nothing is
always safe.

To take a deliberate upgrade that *does* change installed files, add
`--force-clobber`:

```sh
scripts/install-bundle.sh --user-scope --apply --force --force-clobber
```

`--force-clobber` overrides the byte-identity guard on the shared
`<copilot-home>/agents/` namespace. Use it on a deliberate upgrade; do not add it
to routine commands. (`--force` alone only permits moving an installed bundle
*backwards* to an older `VERSION`; it does not authorize clobbering a modified
file — that is `--force-clobber`'s separate consent question.)

### Uninstall

The installer records every file it writes in an ownership manifest at
`<copilot-home>/mozart-manifest.txt` (mode `0600`), one line per file in the
format `<sha256>  <absolute-path>` (two spaces, checksum first), and records the
wrapper's install location in an out-of-band allowlist at
`<copilot-home>/mozart-trust/wrapper-paths` (mode `0600`). The uninstall reads
both and removes **only** the files the manifest lists, and only if each is
still byte-for-byte the file the installer wrote. It is deliberately
conservative:

- It **validates the entire manifest first and deletes nothing if any line is
  malformed** — a tampered or truncated manifest aborts the whole run, never
  "everything up to the bad line".
- It **refuses any non-absolute or non-normalized path, and any `..`
  component** — a lexical namespace test alone would accept
  `agents/../../etc/passwd`.
- It deletes an agent file only when it is a **direct child of the physically
  resolved `<copilot-home>/agents/` dir**, and the wrapper only when its
  recorded path is a **member of the installer-written allowlist** — never a
  `*/mozart` basename match against any file named `mozart` anywhere.
- Immediately before each delete it **physically resolves the file's parent and
  refuses a symlinked immediate parent, or any parent/ancestor redirect whose
  physical resolution differs from the recorded owned identity**: an agent's
  resolved parent must be the owned agents dir, and the wrapper's must equal its
  installer-recorded canonical parent, then the delete goes through that
  validated physical path.
  This narrows — but does not eliminate — a leaf-and-ancestor pathname TOCTOU: a
  concurrent local actor able to mutate those directories in the window between
  validation and the `rm` remains a known, documented residual.
- It **refuses to delete any file whose current sha256 differs from the recorded
  one** — that file was modified since install and is no longer ours to remove.
- If the manifest is missing, unreadable, or a symlink, it deletes nothing.
- It never removes the shared `<copilot-home>/agents/` directory itself, which
  may hold third-party personas.

If you still have a checkout, run `bash scripts/uninstall.sh`. Otherwise the
script is self-contained — copy the block below and run it exactly as written
(it makes no changes you did not install):

<!-- BEGIN uninstall.sh (kept byte-identical to scripts/uninstall.sh; the "README uninstall block matches scripts/uninstall.sh" CI step enforces this) -->
```sh
#!/usr/bin/env bash
# scripts/uninstall.sh — remove exactly the files this project installed under
# the user's Copilot home, and nothing else (P20, sebastian HIGH-2).
#
# It reads the ownership manifest install-bundle.sh writes (P15) and the
# wrapper-location allowlist it records (mozart-trust/wrapper-paths), then:
#   1. validates the ENTIRE manifest first — any malformed line, or any path
#      that is not provably inside the owned namespace, aborts the whole run
#      before a single delete (a bad manifest deletes NOTHING, not "everything
#      up to the bad line");
#   2. refuses any non-absolute / non-normalized path or any '..' component
#      (a lexical namespace test alone would accept 'agents/../../etc/passwd');
#   3. accepts an agent file only when it is a DIRECT child of the physical
#      <copilot-home>/agents dir, and the wrapper only when its recorded path
#      is a MEMBER of the installer-written allowlist — never a '*/mozart'
#      basename match against any file named 'mozart' anywhere;
#   4. before deleting, physically resolves each candidate's PARENT and refuses
#      a symlinked parent, an agent whose physical parent is not the owned
#      agents dir, or a wrapper whose physical parent is not its installer-
#      recorded canonical parent — so a parent OR ancestor swap that redirects
#      the physical resolution away from the recorded owned identity is refused
#      rather than followed out of the namespace — then
#      deletes through the validated physical path only when its current sha256
#      still matches the recorded one (modified-since-install is skipped, never
#      deleted). This narrows but does not eliminate a leaf-and-ancestor
#      pathname TOCTOU: a concurrent local actor able to mutate these
#      directories in the window between validation and `rm` remains a
#      documented residual.
#
# It is self-contained: run `bash scripts/uninstall.sh` from a checkout, or
# copy this block out and run it directly if the checkout is gone. Portable
# BSD/macOS + GNU: sha256 via sha256sum or shasum -a 256; no readlink -f /
# realpath (flag skew) — physical resolution is `cd && pwd -P`.
set -euo pipefail

COPILOT_HOME="${COPILOT_HOME:-$HOME/.copilot}"
manifest="$COPILOT_HOME/mozart-manifest.txt"
wrapper_allowlist="$COPILOT_HOME/mozart-trust/wrapper-paths"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" 2>/dev/null | awk '{print $1}'
  else
    shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
  fi
}

# physical_dir DIR — absolute physical path of an EXISTING directory, empty on
# failure. No readlink -f/realpath (BSD/GNU flag skew).
physical_dir() { ( cd "$1" 2>/dev/null && pwd -P ); }

if [ -L "$manifest" ]; then
  echo "REFUSED: $manifest is a symlink — refusing to treat a link as the authoritative delete list." >&2
  exit 1
fi
if [ ! -r "$manifest" ]; then
  echo "no readable ownership manifest at $manifest — nothing to uninstall" >&2
  exit 0
fi

# Physical <copilot-home> (the manifest lives inside it, so it exists). The
# owned agents namespace is exactly "<physical copilot-home>/agents/<name>",
# which is what the installer records (it canonicalizes the install root).
copilot_phys="$(physical_dir "$COPILOT_HOME")" || copilot_phys=""
if [ -z "$copilot_phys" ]; then
  echo "REFUSED: cannot physically resolve $COPILOT_HOME — refusing to uninstall against an unknown root." >&2
  exit 1
fi
agents_prefix="$copilot_phys/agents"

# Physically resolve the OWNED agents dir ONCE. The Pass-1 namespace test below
# is lexical; that alone is not enough (sebastian HIGH-2). If <copilot-home>/
# agents is itself a symlink — an attacker can swap it AFTER install to redirect
# a recorded, checksum-matching path OUT of the namespace — it is NOT our dir:
# agents_phys is left empty and no agent file becomes eligible for deletion
# (fail closed). Otherwise agents_phys is the fully-resolved directory every
# agent candidate's PHYSICAL parent must equal at delete time.
if [ -L "$copilot_phys/agents" ]; then
  agents_phys=""
else
  agents_phys="$(physical_dir "$copilot_phys/agents")" || agents_phys=""
fi

# The wrapper-location allowlist is the out-of-band authority (mode 0600, in
# the 0700 mozart-trust dir) that a tampered manifest cannot reach. Absent or
# a symlink -> no wrapper is eligible for deletion (fail closed).
wrapper_allow=""
if [ -e "$wrapper_allowlist" ] && [ ! -L "$wrapper_allowlist" ] && [ -r "$wrapper_allowlist" ]; then
  wrapper_allow="$(cat "$wrapper_allowlist")"
fi

is_allowed_wrapper() {
  local candidate="$1" line
  [ -n "$wrapper_allow" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    [ -z "$line" ] && continue
    [ "$line" = "$candidate" ] && return 0
  done <<EOF
$wrapper_allow
EOF
  return 1
}

# ---- Pass 1: validate the ENTIRE manifest. Any failure aborts before any
# delete (no partial deletes on a malformed or out-of-namespace line).
del_paths=()
del_shas=()
del_kinds=()
line_no=0
while IFS= read -r line || [ -n "$line" ]; do
  line_no=$((line_no + 1))
  [ -z "$line" ] && continue
  recorded_sha="${line%%  *}"
  path="${line#*  }"

  # (a) format: sha256 is exactly 64 lowercase hex chars, and the two-space
  # separator must actually split the line.
  case "$recorded_sha" in *[!0-9a-f]* | "") echo "REFUSED: malformed manifest line $line_no (bad sha256); deleting nothing." >&2; exit 1;; esac
  [ "${#recorded_sha}" -eq 64 ] || { echo "REFUSED: malformed manifest line $line_no (sha256 not 64 hex); deleting nothing." >&2; exit 1; }
  if [ "$path" = "$line" ]; then echo "REFUSED: malformed manifest line $line_no (missing two-space separator); deleting nothing." >&2; exit 1; fi

  # (b) path shape: absolute, normalized, no '..'/'.'/empty component. A
  # crafted 'agents/../../etc/x' can then never resolve out of the namespace.
  case "$path" in
    /*) ;;
    *) echo "REFUSED: manifest line $line_no path is not absolute ('$path'); deleting nothing." >&2; exit 1;;
  esac
  case "$path" in
    *//* | */) echo "REFUSED: manifest line $line_no path is not normalized ('$path'); deleting nothing." >&2; exit 1;;
    */../* | */.. | */./* | */.) echo "REFUSED: manifest line $line_no path has a '.' or '..' component ('$path'); deleting nothing." >&2; exit 1;;
  esac

  # (c) namespace: a DIRECT child of the physical agents dir, OR a wrapper path
  # that is a MEMBER of the installer-written allowlist. No basename globbing.
  # This is a LEXICAL classification only; Pass 2 physically re-validates the
  # candidate's parent before deleting (sebastian HIGH-2).
  owned=0
  kind=""
  case "$path" in
    "$agents_prefix"/*)
      rest="${path#"$agents_prefix"/}"
      case "$rest" in */*) : ;; *) owned=1; kind="agent" ;; esac
      ;;
  esac
  if [ "$owned" -eq 0 ] && is_allowed_wrapper "$path"; then
    owned=1; kind="wrapper"
  fi
  if [ "$owned" -eq 0 ]; then
    echo "REFUSED: manifest line $line_no path '$path' is outside the owned namespace (not a direct child of $agents_prefix and not an installer-recorded wrapper location); deleting nothing." >&2
    exit 1
  fi

  del_paths+=("$path")
  del_shas+=("$recorded_sha")
  del_kinds+=("$kind")
done < "$manifest"

# ---- Pass 2: every line validated. Delete each still-present, still-identical
# file. A checksum mismatch or a symlink is skipped (not ours), never fatal.
i=0
n=${#del_paths[@]}
while [ "$i" -lt "$n" ]; do
  path="${del_paths[$i]}"
  recorded_sha="${del_shas[$i]}"
  kind="${del_kinds[$i]}"
  i=$((i + 1))
  if [ ! -e "$path" ]; then echo "already gone: $path"; continue; fi
  if [ -L "$path" ]; then echo "REFUSED (is a symlink, not the file we installed): $path" >&2; continue; fi

  # HIGH-2: Pass 1's namespace test is LEXICAL, so a parent — or a higher
  # ancestor — swapped for a symlink AFTER install still passes it. Before
  # deleting, refuse a symlinked immediate parent outright, physically resolve
  # the parent, then require the physical parent to equal the candidate's owned
  # identity: for an agent, the owned agents dir; for a wrapper, its installer-
  # recorded canonical parent (the lexical parent of the allowlist-matched path,
  # which the installer canonicalized at record time). A swapped ancestor makes
  # the physical parent resolve elsewhere, so the equality fails and we refuse
  # rather than follow it. Delete through the VALIDATED physical path — never
  # through the lexical name whose parent may now redirect outside the namespace.
  parent="${path%/*}"
  if [ -L "$parent" ]; then
    echo "REFUSED (parent directory is a symlink, would redirect outside the owned namespace): $path" >&2
    continue
  fi
  parent_phys="$(physical_dir "$parent")" || parent_phys=""
  if [ -z "$parent_phys" ]; then
    echo "REFUSED (cannot physically resolve the parent directory, not ours to delete): $path" >&2
    continue
  fi
  if [ "$kind" = "agent" ] && { [ -z "$agents_phys" ] || [ "$parent_phys" != "$agents_phys" ]; }; then
    echo "REFUSED (physical parent '$parent_phys' is not the owned agents dir '$agents_phys', not ours to delete): $path" >&2
    continue
  fi
  if [ "$kind" = "wrapper" ] && [ "$parent_phys" != "$parent" ]; then
    echo "REFUSED (physical parent '$parent_phys' is not the installer-recorded wrapper parent '$parent' — a parent or ancestor was swapped for a symlink after install, not ours to delete): $path" >&2
    continue
  fi
  target="$parent_phys/${path##*/}"
  if [ -L "$target" ]; then echo "REFUSED (resolves to a symlink, not the file we installed): $path" >&2; continue; fi
  cur="$(sha256_of "$target")" || cur=""
  if [ -z "$cur" ] || [ "$cur" != "$recorded_sha" ]; then
    echo "REFUSED (modified since install, not ours to delete): $path" >&2
    continue
  fi
  rm -f "$target" && echo "removed: $path"
done

echo "uninstall complete. The bundle and manifest are left in place; remove them yourself if you want them gone:"
echo "  rm -rf \"$COPILOT_HOME/mozart\" \"$manifest\" \"$COPILOT_HOME/mozart-trust\""
```
<!-- END uninstall.sh -->

After the personas and wrapper are gone you may remove the bundle, manifest and
trust state yourself: `rm -rf "$COPILOT_HOME/mozart"
"$COPILOT_HOME/mozart-manifest.txt" "$COPILOT_HOME/mozart-trust"`. If you added
the VS Code settings, remove `chat.agentFilesLocations` and
`chat.additionalReadAccessFolders` too.

### Troubleshoot

**`mozart: REFUSED — bundle provenance mismatch.`** The CLI wrapper compares the
`.github/mozart` bundle the repo you launched from ships against the one you
installed, and it refused because they differ and the repo root is not a trusted
root. This proves the tree is **not the one you installed from** — it does *not*
prove the tree is malicious, and it does *not* prove it is genuine. The gate is
**consent + baseline comparison, not authenticity**: it performs no signature or
checksum verification of bundle contents (see `SECURITY.md`).

Two legitimate remedies, in order of preference:

1. **Trust the repo permanently by reinstalling from it** — this records its
   canonical root in your trust list so future launches are silent:

   ```sh
   scripts/install-bundle.sh --user-scope --apply   # run from the repo root
   ```

2. **Trust it for this one invocation** (root-scoped, never a global boolean;
   do **not** auto-load it via direnv/`.envrc` — that self-trusts a repo-local
   bundle and defeats the gate, and `SECURITY.md` lists it as an anti-pattern):

   ```sh
   MOZART_TRUST_REPO_BUNDLE="<repo-root>" mozart "<task>"
   ```

   where `<repo-root>` is the exact path the banner printed as `repo root`.

**A `--target`-only consumer with no user-scope install must use the override.**
Trust roots are recorded in the *user-side* home (`<copilot-home>/mozart-trust/
roots`). If you pinned a bundle into a repo with `--target` but never ran a
`--user-scope` install, there is no user-side home to record the root into, so
every launch from that repo hits the gate — the per-invocation
`MOZART_TRUST_REPO_BUNDLE` override is the intended path there. The `--target`
installer prints this notice when it detects no `<copilot-home>`.

The gate guards the wrapper's `exec` only: it is bypassed by a bare `copilot`
launch, by VS Code (which never runs the wrapper), and by any already-running
agent.

## Configuring your repo

Mozart adapts to your **ticketing**, **documentation**, **code-retrieval**,
**worktree**, and **pull-request** setup via stanzas in the consuming repo's
`AGENTS.md`. **See [`.github/mozart/INTEGRATION.md`](.github/mozart/INTEGRATION.md)
for the contract and per-system templates.** If a stanza is absent, the
corresponding behavior is skipped or falls back to a sensible default. The
bundle location makes this file less discoverable than a repo-root
`INTEGRATION.md` (see the divergence from the Codex edition in
`docs/COPILOT_PORT.md`) — this section exists specifically to surface it.

## Model configuration

Every agent's `model:` is stamped from `.github/mozart/config/model-map.jsonc`
— seven roles (`conductor`, `deep-reviewers`, `builders`, `reviewers`,
`support`, `fast-scan`, `validation`), 22 assignments. The headline
invariant: **`validation` always runs a different model family than
`builders`** (D8) — sebastian's counterpoint review is only worth running if
it's a genuinely different model auditing the work, not a same-family echo.
`scripts/apply_models.py --check-families` enforces this as a hard exit-1
gate, not a convention.

Two shipped presets flip the whole roster's family in one move while
preserving that invariant:

```sh
python3 scripts/apply_models.py --preset claude-bulk --apply   # builders on Anthropic, sebastian on GPT-5.6-Sol
python3 scripts/apply_models.py --preset gpt-bulk --apply      # builders on OpenAI,    sebastian on Claude Opus 5
```

Dry-run by default; `--apply` writes and backs up every changed file to
`<file>.bak` first. To tune a single role or model ID instead of switching
the whole preset, hand-edit `.github/mozart/config/model-map.jsonc` directly,
then run `apply_models.py --apply` to stamp the roster from it —
`--check` (drift), `--check-families` (D8), and `--check-tiers` (every
agent's role matches its upstream Claude-edition tier exactly — see
`docs/COPILOT_PORT.md`) all validate the result before you ship it.

## Repo layout

```
.github/agents/           specialist + conductor persona definitions (.agent.md)
.github/mozart/           the installable runtime bundle (manual/, agents/<name>/,
                           PIPELINE.md, LEARNINGS.md, INTEGRATION.md, EVAL.md,
                           config/model-map.jsonc, VERSION)
.github/workflows/        CI (check.yml)
config/                   build-time-only config: toolsets.jsonc, model-maps/
scripts/                  validator, stamper, install script, CLI wrapper, lint/metrics
tests/                    fixture corpus + coverage/runtime-read manifests
docs/                     port rationale and known quirks (COPILOT_PORT.md)
```

## Relationship to the Claude Code and Codex editions

This is a faithful port. The orchestration *methodology* — pipeline stages,
tiering, gates, state-file and flow-sketch artifacts, ticket lifecycle,
narration cadence — is harness-neutral and identical across editions. Only the
dispatch / continuation / cross-model-review plumbing differs, per
`docs/COPILOT_PORT.md`.

## License

MIT — see [LICENSE](LICENSE).
