#!/usr/bin/env bash
# install-bundle.sh — install the mozart bundle into a consuming repo, or the
# full user-scope stack (agents + bundle + CLI wrapper) into the Copilot home
# (D1/D9/D10/D11).
#
# Usage:
#   install-bundle.sh --target <dir> [--apply] [--force] [--force-clobber]
#   install-bundle.sh --user-scope [--home <dir>] [--copilot-home <dir>]
#                      [--bin-dir <dir>] [--no-bundle] [--no-wrapper]
#                      [--apply] [--force] [--force-clobber]
#
# --target <dir>       Repo scope. Copies .github/agents/*.agent.md and the
#                      whole of .github/mozart/ into <dir>. Copies NOTHING
#                      from repo-root config/, tests/, or scripts/ — those
#                      are build-time only and are never installed (D14).
#                      This reads the same membership contract
#                      --check-install enforces, so adding a manual file
#                      changes the bundle, not this script.
#
# --user-scope         Full-stack scope (D1): agent definitions, the bundle,
#                      and the CLI wrapper, all at once, by default.
#                        .github/mozart/            -> <copilot-home>/mozart/   (written first)
#                        .github/agents/*.agent.md -> <copilot-home>/agents/
#                        scripts/mozart              -> <bin-dir>/mozart
#                      --no-bundle and --no-wrapper opt out of the last two,
#                      independently and composably; passing both reproduces
#                      the agents-only install this flag used to mean.
#                      NOT an atomic operation: the bundle is written before
#                      the agents/wrapper so that an install interrupted
#                      partway (disk full, permissions) leaves old agents
#                      pointing at a new, complete bundle rather than new
#                      agents pointing at an old or missing one — the safer
#                      of the two partial states, not a rollback.
#
# Copilot-home resolution, highest precedence first (an explicit flag beats
# ambient environment — see below for why):
#   1. --copilot-home <dir>
#   2. <--home>/.copilot
#   3. $COPILOT_HOME
#   4. $HOME/.copilot                                        (the default)
# The resolved home and which rule produced it are always printed, in both
# dry-run and apply output.
#
# --home <dir>         Only valid with --user-scope. Defaults to $HOME.
#                      Exists so this mode — and its default Copilot-home
#                      rule — is testable without touching the real home
#                      directory. An explicit flag must beat ambient state:
#                      putting $COPILOT_HOME above --home would let a
#                      developer's exported $COPILOT_HOME silently defeat
#                      --home's test isolation.
#
# --copilot-home <dir> Only valid with --user-scope. Overrides Copilot-home
#                      resolution outright (rule 1).
#
# --bin-dir <dir>      Only valid with --user-scope. Where the CLI wrapper is
#                      installed. Defaults to <--home-or-$HOME>/.local/bin.
#
# --no-bundle          Only valid with --user-scope. Skip installing
#                      .github/mozart/. Refuses (exit 1), with no override
#                      flag, when <copilot-home>/mozart/VERSION already
#                      exists — updating agent definitions while leaving an
#                      older bundle in place is exactly the skew the VERSION
#                      contract exists to prevent, and it would be silent.
#
# --no-wrapper         Only valid with --user-scope. Skip installing the CLI
#                      wrapper into <bin-dir>.
#
# --apply              Write for real. Default is a dry run: prints the
#                      plan, writes nothing, exits 0.
#
# --force              Required to overwrite an installed bundle (--target's
#                      .github/mozart, or --user-scope's <copilot-home>/mozart)
#                      whose VERSION is newer than this repo's. Without it, a
#                      would-be downgrade is refused (exit 1). This is the
#                      only question --force answers: "may this bundle move
#                      backwards?"
#
# --force-clobber      Valid with --target or --user-scope. Required to
#                      overwrite a pre-existing file this installer did not
#                      write and that is not byte-identical to what would be
#                      installed
#                      — the CLI wrapper binary or an agent definition file
#                      (D11). Ownership is proven by byte-identity alone: an
#                      identical file makes the write a no-op, so nothing can
#                      be lost by proceeding; anything else might be a
#                      stranger's file, or a hand-edited one of ours, and
#                      this installer cannot tell those apart, so it asks.
#                      Every destination is checked before anything is
#                      written, so a refusal leaves the install untouched
#                      rather than half-applied. A destination that is
#                      itself a symlink is refused unconditionally (even
#                      with --force-clobber) rather than written through.
#
# --target and --user-scope are mutually exclusive: passing both exits 2.
#
# Exit: 0 success (including dry run and no-op); 1 refused (a would-be
# downgrade without --force, an inconsistent --no-bundle, or an unconsented
# collision without --force-clobber); 2 usage error.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_VERSION_FILE="$REPO_ROOT/.github/mozart/VERSION"
# Captured before argument parsing, and never reassigned: the operator's
# real home, independent of whatever --home overrides HOME_DIR to for test
# isolation. Needed by is_absurd_root below (codex r2 #2).
REAL_HOME_AMBIENT="${HOME:-}"

# canon_path P — physically resolve P for blocklist comparison. Walks up to
# the longest existing ancestor when P itself doesn't exist yet (the normal
# case: --copilot-home/--bin-dir name a not-yet-created directory), resolves
# that ancestor with `cd && pwd -P`, then reattaches the not-yet-existing
# remainder. This is what lets a relative-looking bypass like `/usr/..` or a
# symlinked ancestor compare correctly against the blocklist below, instead
# of surviving as a distinct string (codex r2 #2).
canon_path() {
  local p="$1" rest="" cur="$1" resolved
  while [ -n "$cur" ] && [ "$cur" != "/" ] && [ ! -e "$cur" ]; do
    rest="/$(basename "$cur")$rest"
    cur="$(dirname "$cur")"
  done
  if [ -z "$cur" ]; then
    printf '%s\n' "$p"
    return
  fi
  resolved="$(cd "$cur" 2>/dev/null && pwd -P)" || { printf '%s\n' "$p"; return; }
  printf '%s%s\n' "$resolved" "$rest"
}

# Absurd install roots (xander L2): never let --copilot-home or --bin-dir
# resolve to one of these — the blast radius of scattering the bundle or the
# wrapper directly into a system or home root is out of proportion to any
# plausible intent behind passing it. Compared by physical resolution (so
# `/usr/..` can't survive as a distinct string from `/`) against the REAL
# ambient $HOME as well as $HOME_DIR (which --home may have overridden to a
# test fixture) — otherwise `--home <test-dir> --copilot-home "$HOME"` would
# smuggle the operator's actual home root past a check that only ever looked
# at the overridden $HOME_DIR (codex r2 #2).
is_absurd_root() {
  local candidate resolved_root root
  candidate="$(canon_path "$1")"
  for root in "/" "$HOME_DIR" "$REAL_HOME_AMBIENT" "/usr" "/etc"; do
    [ -z "$root" ] && continue
    resolved_root="$(canon_path "$root")"
    if [ "$candidate" = "$resolved_root" ]; then
      return 0
    fi
  done
  return 1
}

# refuse_if_symlinked_containers LABEL PATH [LABEL PATH ...] — P13. Refuse,
# before any byte is written, when a destination *container directory* is
# itself a symlink, on both the --target and --user-scope branches. Every
# symlinked container in the argument list is reported, so a single run names
# them all.
#
# Distinct from the per-file [ -L ] collision matrix (below, in the
# user-scope branch, and in the --target branch as of P14): that matrix
# guards the leaf *files* being written and passes *vacuously* when the
# container is the link, because every file then lands inside the link's
# target and no per-file test ever fires. A symlinked container silently
# redirects the whole install through the link — into /etc, a sibling repo,
# anywhere it points. is_absurd_root does not catch this either: it compares
# canonicalized *strings* against a fixed blocklist, so a <copilot-home> that
# is a symlink to /etc/foo passes it and mkdir -p writes straight through.
#
# Fail closed and portable: the test is a plain POSIX [ -L ] type check with
# no path resolution, so BSD/macOS and GNU agree (deliberately NOT readlink
# -f / realpath, whose flags differ across the two). A symlink — including a
# dangling one — is refused; nothing is followed, so an inconclusive resolve
# can never be mistaken for "not a link".
refuse_if_symlinked_containers() {
  local blocks=()
  local label path
  while [ $# -gt 0 ]; do
    label="$1"; path="$2"; shift 2
    if [ -L "$path" ]; then
      blocks+=("$label: $path")
    fi
  done
  if [ "${#blocks[@]}" -gt 0 ]; then
    echo "REFUSED: a destination container directory is a symlink; refusing to write through it (P13) — this would redirect the install into the link's target. Remove it and re-run if you intend to replace what it points to:" >&2
    local b
    for b in "${blocks[@]}"; do echo "  $b" >&2; done
    exit 1
  fi
}

# --------------------------------------------------------------------------
# Ownership manifest (D-I, P15). A persistent record of every file this
# installer has ever written under the user's home, so the documented
# uninstall (P20) can delete exactly what we own — and refuse anything else.
# It lives OUTSIDE <copilot-home>/mozart/ (which `cp -R` overwrites on every
# reinstall) at <copilot-home>/mozart-manifest.txt, mode 0600.
#
# Line format: "<sha256>  <absolute-path>" (two spaces). The recorded sha256
# is what makes the uninstall safe: a file whose current hash no longer
# matches has been replaced by the user or another project and MUST be left
# alone. The manifest never shrinks (union-with-dedup) — a path an earlier
# install wrote is preserved even when a later reinstall with different flags
# (--no-wrapper, a changed --bin-dir) would not write it again. An orphaned
# entry is a *skipped* delete at uninstall, never a wrong one.
#
# Portability: sha256 via `sha256sum` (GNU) or `shasum -a 256` (BSD/macOS);
# first whitespace-delimited field via `awk`. No associative arrays (macOS
# ships bash 3.2) — dedup is done with a linear membership test.
# --------------------------------------------------------------------------

sha256_of() {
  # Hex sha256 of file "$1", or empty on failure (fail closed).
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" 2>/dev/null | awk '{print $1}'
  else
    shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
  fi
}

_path_in_list() {
  local needle="$1"; shift
  local x
  for x in "$@"; do
    [ "$x" = "$needle" ] && return 0
  done
  return 1
}

# write_manifest MANIFEST_PATH DEST_PATH... — union the paths written this run
# into any prior manifest, refreshing the checksum for every path written this
# run and preserving all prior entries whose path is not written this run.
# Refuses (exit 2) any path containing a newline BEFORE touching the manifest —
# the format is line-based and a forgeable manifest is an arbitrary-delete
# primitive at uninstall. The file is (re)written 0600 every time; its content
# is never even briefly world-readable (umask 077 around the write).
write_manifest() {
  local manifest="$1"; shift
  local nl=$'\n'
  local p
  # 1. Newline rejection — fail closed before any read or write.
  for p in "$@"; do
    if [ "$p" != "${p//$nl/}" ]; then
      echo "REFUSED: refusing to record a destination path containing a newline in the ownership manifest — it would forge the line-based format and become an arbitrary-delete primitive at uninstall: $p" >&2
      exit 2
    fi
  done
  # 2. An existing-but-unreadable manifest cannot be safely unioned; rewriting
  #    it would orphan every prior entry. Fail closed rather than shrink it.
  if [ -f "$manifest" ] && [ ! -r "$manifest" ]; then
    echo "REFUSED: existing ownership manifest $manifest is unreadable — refusing to rewrite it, which would orphan the paths a prior install recorded." >&2
    exit 2
  fi
  # 3. Preserve prior entries whose path is NOT written this run (union).
  local merged="" line ppath
  if [ -f "$manifest" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      [ -z "$line" ] && continue
      ppath="${line#*  }"
      if ! _path_in_list "$ppath" "$@"; then
        merged+="$line$nl"
      fi
    done < "$manifest"
  fi
  # 4. Fresh, checksummed entries for every path written this run.
  local sum
  for p in "$@"; do
    sum="$(sha256_of "$p")"
    if [ -z "$sum" ]; then
      echo "REFUSED: could not compute sha256 for $p — refusing to write an unverifiable ownership-manifest entry." >&2
      exit 2
    fi
    merged+="$sum  $p$nl"
  done
  # 5. Write 0600. umask keeps the content from existing world-readable even
  #    momentarily; chmod re-asserts the mode on an already-present file.
  local umask_old; umask_old="$(umask)"
  umask 077
  printf '%s' "$merged" > "$manifest"
  umask "$umask_old"
  chmod 0600 "$manifest"
}

# --------------------------------------------------------------------------
# Install-time trust roots (D-E / D-H, P16). Records the canonical repo root
# this install trusts, keyed on USER-SIDE state at
# <copilot-home>/mozart-trust/roots (dir 0700, file 0600) — deliberately
# OUTSIDE <copilot-home>/mozart/, which `cp -R` overwrites on every reinstall.
# The launch wrapper (P17) exempts its provenance gate only for a current repo
# root whose device:inode identity matches a recorded root; everything else
# fails closed.
# --------------------------------------------------------------------------

# dev_ino DIR — canonical identity of a directory as "device:inode", or empty
# on failure. Fail closed: empty output on EITHER side of a comparison is a
# NON-match (used by the wrapper, P17). Copied verbatim into scripts/mozart.
#
# ORDER IS GNU-FIRST (`stat -c`), BSD-SECOND (`stat -f`) — the REVERSE of the
# D-H illustrative snippet, and deliberately so (see the P16 report / CHANGELOG):
# on GNU coreutils `stat -f` is --file-system and '%d'/'%i' are VALID filesystem
# directives, so `stat -f '%d:%i'` SUCCEEDS with filesystem stats — identical for
# every path on one volume — and a BSD-first order would fail OPEN on Linux/CI,
# trusting any two paths on the same filesystem. GNU `stat -c` has no such
# collision and BSD `stat` rejects `-c` outright, so GNU-first resolves to the
# real device:inode and fails CLOSED on both platforms.
dev_ino() { stat -c '%d:%i' "$1" 2>/dev/null || stat -f '%d:%i' "$1" 2>/dev/null; }

# canonical_root DIR — DIR's physically-resolved absolute path, recorded in
# human-readable form so a refusal banner can name it. Computed independently
# of $REPO_ROOT (a bare logical `pwd` captured at line 102): reusing that would
# record a logical path the physical wrapper lookup can never match under a
# symlinked ancestor (macOS /tmp -> /private/tmp), refusing every launch (D-H/Y3).
# Empty on failure.
canonical_root() { ( cd "$1" 2>/dev/null && pwd -P ); }

# record_trust_root COPILOT_HOME ROOT_DIR — append the canonical form of
# ROOT_DIR to the user-side trust roots list, dedup by dev_ino identity (and by
# exact canonical string, for the rare case dev_ino yields nothing). Appending
# an already-recorded root is a no-op; ordering is not significant. Dir 0700,
# file 0600. Caller guarantees COPILOT_HOME exists.
record_trust_root() {
  local chome="$1" rootdir="$2"
  local canon; canon="$(canonical_root "$rootdir")"
  if [ -z "$canon" ]; then
    echo "WARNING: could not physically resolve '$rootdir' — not recording it as a trusted root; launches from it will need the MOZART_TRUST_REPO_BUNDLE override." >&2
    return 0
  fi
  local trustdir="$chome/mozart-trust" rootsfile="$chome/mozart-trust/roots"
  local id; id="$(dev_ino "$canon")"
  mkdir -p "$trustdir"
  chmod 0700 "$trustdir"
  if [ -f "$rootsfile" ]; then
    local existing
    while IFS= read -r existing || [ -n "$existing" ]; do
      [ -z "$existing" ] && continue
      if [ "$existing" = "$canon" ]; then chmod 0600 "$rootsfile"; return 0; fi
      if [ -n "$id" ] && [ "$(dev_ino "$existing")" = "$id" ]; then chmod 0600 "$rootsfile"; return 0; fi
    done < "$rootsfile"
  fi
  printf '%s\n' "$canon" >> "$rootsfile"
  chmod 0600 "$rootsfile"
}

usage() {
  cat >&2 <<'USAGE'
usage: install-bundle.sh --target <dir> [--apply] [--force] [--force-clobber]
       install-bundle.sh --user-scope [--home <dir>] [--copilot-home <dir>]
                          [--bin-dir <dir>] [--no-bundle] [--no-wrapper]
                          [--apply] [--force] [--force-clobber]

--target and --user-scope are mutually exclusive.
USAGE
}

# version_gt A B — true (0) iff A > B, for the truncated semver forms this
# repo's VERSION file uses (X.Y.Z or X.Y.Z-suffix). No external dependency
# (no `sort -V`, which BSD sort on macOS doesn't support) — a bare release
# outranks a same-numbered prerelease; otherwise plain numeric comparison
# of the dot-separated core.
version_gt() {
  local a="$1" b="$2"
  local a_core="${a%%-*}" b_core="${b%%-*}"
  local a_pre=0 b_pre=0
  if [ "$a" != "$a_core" ]; then a_pre=1; fi
  if [ "$b" != "$b_core" ]; then b_pre=1; fi
  local IFS=.
  local -a av=($a_core) bv=($b_core)
  local i
  for i in 0 1 2; do
    local ai="${av[$i]:-0}" bi="${bv[$i]:-0}"
    if [ "$ai" -gt "$bi" ] 2>/dev/null; then return 0; fi
    if [ "$ai" -lt "$bi" ] 2>/dev/null; then return 1; fi
  done
  if [ "$a_pre" -eq 0 ] && [ "$b_pre" -eq 1 ]; then return 0; fi
  return 1
}

TARGET=""
USER_SCOPE=0
HOME_DIR="${HOME:-}"
HOME_EXPLICIT=0
COPILOT_HOME_EXPLICIT=""
BIN_DIR_EXPLICIT=""
NO_BUNDLE=0
NO_WRAPPER=0
APPLY=0
FORCE=0
FORCE_CLOBBER=0

while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      TARGET="${2:-}"
      if [ -z "$TARGET" ]; then echo "usage error: --target requires a directory argument" >&2; usage; exit 2; fi
      shift 2 ;;
    --user-scope)
      USER_SCOPE=1; shift ;;
    --home)
      HOME_DIR="${2:-}"
      HOME_EXPLICIT=1
      if [ -z "$HOME_DIR" ]; then echo "usage error: --home requires a directory argument" >&2; usage; exit 2; fi
      shift 2 ;;
    --copilot-home)
      COPILOT_HOME_EXPLICIT="${2:-}"
      if [ -z "$COPILOT_HOME_EXPLICIT" ]; then echo "usage error: --copilot-home requires a directory argument" >&2; usage; exit 2; fi
      shift 2 ;;
    --bin-dir)
      BIN_DIR_EXPLICIT="${2:-}"
      if [ -z "$BIN_DIR_EXPLICIT" ]; then echo "usage error: --bin-dir requires a directory argument" >&2; usage; exit 2; fi
      shift 2 ;;
    --no-bundle)
      NO_BUNDLE=1; shift ;;
    --no-wrapper)
      NO_WRAPPER=1; shift ;;
    --apply)
      APPLY=1; shift ;;
    --force)
      FORCE=1; shift ;;
    --force-clobber)
      FORCE_CLOBBER=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "usage error: unrecognized argument '$1'" >&2
      usage
      exit 2 ;;
  esac
done

if [ -n "$TARGET" ] && [ "$USER_SCOPE" -eq 1 ]; then
  echo "usage error: --target and --user-scope are mutually exclusive" >&2
  usage
  exit 2
fi

if [ "$HOME_EXPLICIT" -eq 1 ] && [ "$USER_SCOPE" -eq 0 ]; then
  echo "usage error: --home is only valid with --user-scope" >&2
  usage
  exit 2
fi
if [ -n "$COPILOT_HOME_EXPLICIT" ] && [ "$USER_SCOPE" -eq 0 ]; then
  echo "usage error: --copilot-home is only valid with --user-scope" >&2
  usage
  exit 2
fi
if [ -n "$BIN_DIR_EXPLICIT" ] && [ "$USER_SCOPE" -eq 0 ]; then
  echo "usage error: --bin-dir is only valid with --user-scope" >&2
  usage
  exit 2
fi
if [ "$NO_BUNDLE" -eq 1 ] && [ "$USER_SCOPE" -eq 0 ]; then
  echo "usage error: --no-bundle is only valid with --user-scope" >&2
  usage
  exit 2
fi
if [ "$NO_WRAPPER" -eq 1 ] && [ "$USER_SCOPE" -eq 0 ]; then
  echo "usage error: --no-wrapper is only valid with --user-scope" >&2
  usage
  exit 2
fi
if [ "$FORCE_CLOBBER" -eq 1 ] && [ -z "$TARGET" ] && [ "$USER_SCOPE" -eq 0 ]; then
  # --force-clobber is valid with either scope (P12 widened it to --target so
  # the documented reinstall command survives P13/P14's collision detection).
  # It is meaningless with no scope at all; the required-scope guard below
  # gives the clearer message, so only guard the truly-nonsensical case here.
  echo "usage error: --force-clobber requires --target or --user-scope" >&2
  usage
  exit 2
fi

if [ -z "$TARGET" ] && [ "$USER_SCOPE" -eq 0 ]; then
  echo "usage error: one of --target or --user-scope is required" >&2
  usage
  exit 2
fi

# --------------------------------------------------------------------------
# --target: repo-scope bundle install.
# --------------------------------------------------------------------------

if [ -n "$TARGET" ]; then
  SOURCE_VERSION="$(cat "$SOURCE_VERSION_FILE" 2>/dev/null || echo "unknown")"
  DEST_VERSION_FILE="$TARGET/.github/mozart/VERSION"

  if [ -f "$DEST_VERSION_FILE" ]; then
    DEST_VERSION="$(cat "$DEST_VERSION_FILE" 2>/dev/null || echo "unknown")"
    if version_gt "$DEST_VERSION" "$SOURCE_VERSION" && [ "$FORCE" -eq 0 ]; then
      echo "REFUSED: $TARGET already has .github/mozart VERSION $DEST_VERSION, newer than this repo's $SOURCE_VERSION. Pass --force to overwrite anyway." >&2
      exit 1
    fi
  fi

  # P13 — refuse before any write when any of the four --target containers is
  # a symlink (Y19a adds $TARGET itself and .github/agents to r1's two).
  refuse_if_symlinked_containers \
    "target repo root" "$TARGET" \
    "target .github" "$TARGET/.github" \
    "target bundle dir (.github/mozart)" "$TARGET/.github/mozart" \
    "target agents dir (.github/agents)" "$TARGET/.github/agents"

  if [ "$APPLY" -eq 0 ]; then
    echo "[dry run] would install into $TARGET:"
    echo "  .github/agents/*.agent.md -> $TARGET/.github/agents/"
    echo "  .github/mozart/           -> $TARGET/.github/mozart/ (source VERSION $SOURCE_VERSION)"
    echo "[dry run] nothing from repo-root config/, tests/, or scripts/ is installed (D14)"
    exit 0
  fi

  # P14 — collision matrix for the shared <target>/.github/agents/ namespace,
  # the --target twin of the user-scope matrix below. The collision namespace
  # is the *target repo's* agents dir, NOT <copilot-home>/agents. The bundle
  # subtree under .github/mozart/ is this project's own and governed by the
  # VERSION downgrade guard above; agent files share a name any install could
  # also write, so each is checked by byte-identity before anything is
  # written. A dest that is itself a symlink is refused unconditionally (the
  # container check covers the dir; this covers a leaf file). A non-identical
  # existing file refuses unless --force-clobber (widened to --target in P12);
  # a byte-identical file is a silent no-op.
  T_SYMLINK_BLOCKS=()
  T_COLLISIONS=()
  for f in "$REPO_ROOT"/.github/agents/*.agent.md; do
    d="$TARGET/.github/agents/$(basename "$f")"
    if [ -L "$d" ]; then
      T_SYMLINK_BLOCKS+=("$d")
    elif [ -e "$d" ] && ! cmp -s "$f" "$d"; then
      T_COLLISIONS+=("$d")
    fi
  done
  if [ "${#T_SYMLINK_BLOCKS[@]}" -gt 0 ]; then
    echo "REFUSED: the following destinations are symlinks; refusing to write through them — remove them and re-run if you intend to replace what they point to:" >&2
    for p in "${T_SYMLINK_BLOCKS[@]}"; do echo "  $p" >&2; done
    exit 1
  fi
  if [ "${#T_COLLISIONS[@]}" -gt 0 ] && [ "$FORCE_CLOBBER" -eq 0 ]; then
    echo "REFUSED: the following destinations already exist in $TARGET/.github/agents and are not byte-identical to what this install would write — pass --force-clobber to overwrite them (this discards their current contents):" >&2
    for p in "${T_COLLISIONS[@]}"; do echo "  $p" >&2; done
    exit 1
  fi

  mkdir -p "$TARGET/.github/agents"
  cp "$REPO_ROOT"/.github/agents/*.agent.md "$TARGET/.github/agents/"

  # P13/Y19b — this cp -R is a *merge* into an existing tree, so a nested
  # pre-existing symlink inside the destination bundle (e.g. .github/mozart/
  # config) would otherwise survive a reinstall and be written through.
  # Remove the destination bundle directory first — that path only, never
  # $TARGET, never .github — so the bundle is always rewritten from a clean
  # slate. The container check above already refused if .github/mozart itself
  # is the link; this handles links *inside* it.
  rm -rf "$TARGET/.github/mozart"
  mkdir -p "$TARGET/.github/mozart"
  cp -R "$REPO_ROOT"/.github/mozart/. "$TARGET/.github/mozart/"

  # P14/Y17 — honest roster count: report the number of agent files actually
  # present in the destination after the copy, computed here, never a
  # hardcoded constant that silently lies as personas are added or dropped.
  # `wc -l | tr -d ' '` because BSD wc right-pads its count while GNU does not.
  N_AGENTS=$(ls "$TARGET"/.github/agents/*.agent.md 2>/dev/null | wc -l | tr -d ' ')
  echo "installed .github/agents ($N_AGENTS files) and .github/mozart (VERSION $SOURCE_VERSION) into $TARGET"

  # P16/D-E (Y4) — a --target install trusts the TARGET repo root, but the
  # trust list is USER-SIDE state, not repo content. Append the canonical
  # $TARGET to ${COPILOT_HOME:-$HOME/.copilot}/mozart-trust/roots when that
  # home exists. When it does not (a consumer with no user-scope install),
  # print the per-invocation override explicitly rather than silently leaving
  # every launch from this repo refused — r1's "silent for --target" promise
  # was false; it is now either recorded or told exactly why not.
  USER_COPILOT_HOME="${COPILOT_HOME:-$REAL_HOME_AMBIENT/.copilot}"
  if [ -d "$USER_COPILOT_HOME" ]; then
    record_trust_root "$USER_COPILOT_HOME" "$TARGET"
    echo "recorded $(canonical_root "$TARGET") as a trusted repo root in $USER_COPILOT_HOME/mozart-trust/roots"
  else
    echo "NOTE: no Copilot home at $USER_COPILOT_HOME, so this repo was NOT added to the trust roots list. To launch mozart from it without the provenance gate refusing, pass the per-invocation override each time: MOZART_TRUST_REPO_BUNDLE=\"$(canonical_root "$TARGET")\" mozart \"<task>\" — or run a --user-scope install first. See docs."
  fi
  exit 0
fi

# --------------------------------------------------------------------------
# --user-scope: full-stack install (agents + bundle + CLI wrapper), D1.
# --------------------------------------------------------------------------

if [ -z "$HOME_DIR" ]; then
  echo "usage error: --home requires a directory argument, and \$HOME is unset" >&2
  usage
  exit 2
fi

DEFAULT_COPILOT_HOME="$HOME_DIR/.copilot"

# Copilot-home resolution (step 5) — explicit flags beat ambient
# environment, and $COPILOT_HOME (a plain env-var read, guarded for `set -u`)
# is deliberately checked *after* --home so a developer's exported
# $COPILOT_HOME cannot silently defeat --home's test isolation.
if [ -n "$COPILOT_HOME_EXPLICIT" ]; then
  RESOLVED_COPILOT_HOME="$COPILOT_HOME_EXPLICIT"
  RESOLVED_COPILOT_HOME_SOURCE="--copilot-home"
elif [ "$HOME_EXPLICIT" -eq 1 ]; then
  RESOLVED_COPILOT_HOME="$HOME_DIR/.copilot"
  RESOLVED_COPILOT_HOME_SOURCE="--home (<home>/.copilot)"
elif [ -n "${COPILOT_HOME:-}" ]; then
  RESOLVED_COPILOT_HOME="$COPILOT_HOME"
  RESOLVED_COPILOT_HOME_SOURCE='$COPILOT_HOME'
else
  RESOLVED_COPILOT_HOME="$DEFAULT_COPILOT_HOME"
  RESOLVED_COPILOT_HOME_SOURCE='default ($HOME/.copilot)'
fi

if [ -n "$BIN_DIR_EXPLICIT" ]; then
  BIN_DIR="$BIN_DIR_EXPLICIT"
else
  BIN_DIR="$HOME_DIR/.local/bin"
fi

if is_absurd_root "$RESOLVED_COPILOT_HOME"; then
  echo "usage error: refusing to resolve the Copilot home to '$RESOLVED_COPILOT_HOME' — this looks like a system or home root, not an install directory" >&2
  exit 2
fi
if is_absurd_root "$BIN_DIR"; then
  echo "usage error: refusing to install the wrapper into '$BIN_DIR' — this looks like a system or home root, not an install directory" >&2
  exit 2
fi

echo "Resolved Copilot home: $RESOLVED_COPILOT_HOME (source: $RESOLVED_COPILOT_HOME_SOURCE)"

# P13 — refuse before any write when a user-scope container is a symlink
# (Y19a adds <copilot-home> itself and <copilot-home>/agents to r1's two).
# Only containers this invocation will actually write into are checked: the
# bundle dir is skipped under --no-bundle, the wrapper bin dir under
# --no-wrapper — refusing on a container we never touch would be a spurious
# lockout, not a safety property. <copilot-home> and its agents dir are
# always written (agents land there even under --no-bundle), so both are
# always checked.
CONTAINER_CHECKS=(
  "Copilot home" "$RESOLVED_COPILOT_HOME"
  "agents dir (<copilot-home>/agents)" "$RESOLVED_COPILOT_HOME/agents"
)
if [ "$NO_BUNDLE" -eq 0 ]; then
  CONTAINER_CHECKS+=("bundle dir (<copilot-home>/mozart)" "$RESOLVED_COPILOT_HOME/mozart")
fi
if [ "$NO_WRAPPER" -eq 0 ]; then
  CONTAINER_CHECKS+=("wrapper bin dir" "$BIN_DIR")
fi
refuse_if_symlinked_containers "${CONTAINER_CHECKS[@]}"

SOURCE_VERSION="$(cat "$SOURCE_VERSION_FILE" 2>/dev/null || echo "unknown")"
DEST_BUNDLE_VERSION_FILE="$RESOLVED_COPILOT_HOME/mozart/VERSION"

# Downgrade guard (step 7), extended from --target to the user bundle: a
# user-scope install downgrades every repo on the machine at once, a
# strictly larger blast radius than the --target case this guard was
# originally written for.
if [ "$NO_BUNDLE" -eq 0 ] && [ -f "$DEST_BUNDLE_VERSION_FILE" ]; then
  DEST_BUNDLE_VERSION="$(cat "$DEST_BUNDLE_VERSION_FILE" 2>/dev/null || echo "unknown")"
  if version_gt "$DEST_BUNDLE_VERSION" "$SOURCE_VERSION" && [ "$FORCE" -eq 0 ]; then
    echo "REFUSED: $RESOLVED_COPILOT_HOME/mozart already has VERSION $DEST_BUNDLE_VERSION, newer than this repo's $SOURCE_VERSION. Pass --force to overwrite anyway." >&2
    exit 1
  fi
fi

# --no-bundle over an existing bundle is refused unconditionally — no
# override flag at all (step 7, bob N8). This is a third consent question
# distinct from --force ("move backwards?") and --force-clobber ("overwrite
# something that isn't mine?"): "may I leave this install internally
# inconsistent?" A flag whose only product is a knowingly-broken install
# isn't worth documenting, so there isn't one.
if [ "$NO_BUNDLE" -eq 1 ] && [ -f "$DEST_BUNDLE_VERSION_FILE" ]; then
  DEST_BUNDLE_VERSION="$(cat "$DEST_BUNDLE_VERSION_FILE" 2>/dev/null || echo "unknown")"
  echo "REFUSED: --no-bundle would leave $RESOLVED_COPILOT_HOME/mozart (VERSION $DEST_BUNDLE_VERSION) installed while updating agent definitions to $SOURCE_VERSION — an internally inconsistent install. Drop --no-bundle to update both, or remove $RESOLVED_COPILOT_HOME/mozart first to genuinely install agents only." >&2
  exit 1
fi

if [ "$APPLY" -eq 0 ]; then
  echo "[dry run] would install into $RESOLVED_COPILOT_HOME:"
  echo "  .github/agents/*.agent.md -> $RESOLVED_COPILOT_HOME/agents/"
  if [ "$NO_BUNDLE" -eq 0 ]; then
    echo "  .github/mozart/           -> $RESOLVED_COPILOT_HOME/mozart/ (source VERSION $SOURCE_VERSION)"
  else
    echo "  (--no-bundle: .github/mozart/ is not installed)"
  fi
  if [ "$NO_WRAPPER" -eq 0 ]; then
    echo "  scripts/mozart            -> $BIN_DIR/mozart"
  else
    echo "  (--no-wrapper: the CLI wrapper is not installed)"
  fi
  exit 0
fi

# --------------------------------------------------------------------------
# Collision policy (D11), byte-identity only. Every destination this
# invocation would write into the shared global namespaces — the wrapper
# binary on $PATH, and an agent-definitions file under a name any other
# install could also use — is checked *before* anything is written, so a
# refusal leaves the install untouched rather than half-applied. Bundle
# files under <copilot-home>/mozart/ are exclusively this project's own
# subtree (nothing else writes there) and are governed by the VERSION
# downgrade guard above instead — that is a different question ("is this
# bundle moving backwards?") from ownership of a shared name.
# --------------------------------------------------------------------------

DEST_PATHS=()
SRC_PATHS=()
for f in "$REPO_ROOT"/.github/agents/*.agent.md; do
  DEST_PATHS+=("$RESOLVED_COPILOT_HOME/agents/$(basename "$f")")
  SRC_PATHS+=("$f")
done
if [ "$NO_WRAPPER" -eq 0 ]; then
  DEST_PATHS+=("$BIN_DIR/mozart")
  SRC_PATHS+=("$REPO_ROOT/scripts/mozart")
fi

SYMLINK_BLOCKS=()
COLLISIONS=()
for i in "${!DEST_PATHS[@]}"; do
  d="${DEST_PATHS[$i]}"
  s="${SRC_PATHS[$i]}"
  if [ -L "$d" ]; then
    SYMLINK_BLOCKS+=("$d")
  elif [ -e "$d" ] && ! cmp -s "$s" "$d"; then
    COLLISIONS+=("$d")
  fi
done

if [ "${#SYMLINK_BLOCKS[@]}" -gt 0 ]; then
  echo "REFUSED: the following destinations are symlinks; refusing to write through them (xander L3) — remove them and re-run if you intend to replace what they point to:" >&2
  for p in "${SYMLINK_BLOCKS[@]}"; do echo "  $p" >&2; done
  exit 1
fi

if [ "${#COLLISIONS[@]}" -gt 0 ] && [ "$FORCE_CLOBBER" -eq 0 ]; then
  echo "REFUSED: the following destinations already exist and are not byte-identical to what this install would write — pass --force-clobber to overwrite them (this discards their current contents):" >&2
  for p in "${COLLISIONS[@]}"; do echo "  $p" >&2; done
  exit 1
fi

# --------------------------------------------------------------------------
# Write. Bundle first, agents and the wrapper last (codex r2 #1) — this is
# a best-effort ordering, not a transaction: nothing here rolls back a
# partial failure, and no earlier step in this script claims otherwise. If
# a later step fails partway (disk full, permissions), the ordering decides
# which half is left in place, and bundle-first is the safer half to lose
# last: an interrupted install then leaves OLD agent definitions pointing
# at a NEW, complete bundle. Old agents still resolve every bundle read via
# the VERSION probe (D7) — stale instructions, but no broken reads. The
# reverse order (agents-first) would risk the opposite: NEW agent bodies,
# which may cite bundle content only the new bundle has, left pointing at
# an old or missing bundle.
# --------------------------------------------------------------------------

if [ "$NO_BUNDLE" -eq 0 ]; then
  # P13/Y19b — merge copy; remove the destination bundle dir first (that path
  # only, never <copilot-home>) so a nested pre-existing symlink inside it
  # cannot survive a reinstall and be written through. The container check
  # above already refused if <copilot-home>/mozart itself is the link.
  rm -rf "$RESOLVED_COPILOT_HOME/mozart"
  mkdir -p "$RESOLVED_COPILOT_HOME/mozart"
  cp -R "$REPO_ROOT"/.github/mozart/. "$RESOLVED_COPILOT_HOME/mozart/"
fi

mkdir -p "$RESOLVED_COPILOT_HOME/agents"
if [ "$NO_WRAPPER" -eq 0 ]; then
  mkdir -p "$BIN_DIR"
fi
for i in "${!DEST_PATHS[@]}"; do
  cp "${SRC_PATHS[$i]}" "${DEST_PATHS[$i]}"
done
if [ "$NO_WRAPPER" -eq 0 ]; then
  chmod 0755 "$BIN_DIR/mozart"
fi

# P15/D-I — record ownership of exactly the shared-namespace files written
# this run (agent definitions and, unless --no-wrapper, the CLI wrapper). The
# bundle subtree under <copilot-home>/mozart/ is deliberately NOT tracked
# here: it is this project's own directory, removed wholesale at uninstall,
# never a per-file delete constrained by checksum. write_manifest unions with
# any prior manifest, so a --no-wrapper or changed --bin-dir reinstall cannot
# make an earlier-written path unrecoverable.
write_manifest "$RESOLVED_COPILOT_HOME/mozart-manifest.txt" "${DEST_PATHS[@]}"

# P16/D-E — record the SOURCE checkout as a trusted repo root, so the launch
# wrapper's provenance gate (P17) exempts it. The recorded value is the
# PHYSICAL resolution of $REPO_ROOT (via canonical_root), never $REPO_ROOT
# itself — $REPO_ROOT is a bare logical `pwd` and the wrapper looks roots up
# physically, so recording the logical form would refuse every launch under a
# symlinked ancestor (D-H/Y3). The user-scope home was just created, so it
# always exists here.
record_trust_root "$RESOLVED_COPILOT_HOME" "$REPO_ROOT"

# --------------------------------------------------------------------------
# Post-install output — the grants, exactly (step 9).
# --------------------------------------------------------------------------

echo ""
echo "1. Resolved Copilot home: $RESOLVED_COPILOT_HOME (source: $RESOLVED_COPILOT_HOME_SOURCE)"
if [ "$NO_BUNDLE" -eq 0 ]; then
  echo "   Installed VERSION: $SOURCE_VERSION"
else
  echo "   --no-bundle: no bundle installed"
fi

if [ "$NO_WRAPPER" -eq 0 ]; then
  echo ""
  echo "2. CLI — zero settings needed, the wrapper carries the grants:"
  echo "     mozart \"<task>\""
  case ":$PATH:" in
    *":$BIN_DIR:"*) : ;;
    *) echo "   NOTE: $BIN_DIR is not on your \$PATH. Add it, e.g.: export PATH=\"$BIN_DIR:\$PATH\"" ;;
  esac
  SHADOW="$(command -v mozart 2>/dev/null || true)"
  if [ -n "$SHADOW" ] && [ "$SHADOW" != "$BIN_DIR/mozart" ]; then
    echo "   WARNING: 'command -v mozart' resolves to $SHADOW, not the file just installed at $BIN_DIR/mozart — check your \$PATH order, or the wrong 'mozart' will run."
  fi
else
  echo ""
  echo "2. CLI — --no-wrapper: no wrapper installed; the CLI grant (--add-dir) must be supplied manually."
fi

echo ""
echo "3. VS Code — two settings, pasted once into settings.json, then reload the window:"
echo "     \"chat.agentFilesLocations\": [\"$RESOLVED_COPILOT_HOME/agents\"]"
if [ "$NO_BUNDLE" -eq 0 ]; then
  echo "     \"chat.additionalReadAccessFolders\": [\"$RESOLVED_COPILOT_HOME/mozart\"]"
fi

if [ "$NO_BUNDLE" -eq 0 ] && [ "$RESOLVED_COPILOT_HOME" != "$DEFAULT_COPILOT_HOME" ]; then
  echo ""
  echo "4. Custom Copilot home in use ($RESOLVED_COPILOT_HOME != $DEFAULT_COPILOT_HOME) — required step (D10), not a tip: the CLI wrapper will refuse to launch until you run"
  echo "     ln -s \"$RESOLVED_COPILOT_HOME/mozart\" \"$DEFAULT_COPILOT_HOME/mozart\""
  echo "   VS Code has no equivalent enforcement, but the same symlink is the remedy there too."
fi

echo ""
echo "5. To pin a bundle into one specific repo instead: install-bundle.sh --target <repo> --apply"

exit 0
