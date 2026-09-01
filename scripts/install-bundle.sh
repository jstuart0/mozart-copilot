#!/usr/bin/env bash
# install-bundle.sh — install the mozart bundle into a consuming repo, or
# agent definitions into the verified Copilot CLI user-scope path (D9/D14).
#
# Usage:
#   install-bundle.sh --target <dir> [--apply] [--force]
#   install-bundle.sh --user-scope [--home <dir>] [--apply] [--force]
#
# --target <dir>   Repo scope. Copies .github/agents/*.agent.md and the whole
#                  of .github/mozart/ into <dir>. Copies NOTHING from
#                  repo-root config/, tests/, or scripts/ — those are
#                  build-time only and are never installed (D14). This reads
#                  the same membership contract --check-install enforces, so
#                  adding a manual file changes the bundle, not this script.
#
# --user-scope     Agent-definitions-only scope. Copies
#                  .github/agents/*.agent.md into <home>/.copilot/agents/ (the
#                  verified Copilot CLI harness path). Installs NO bundle —
#                  the workspace bundle install (--target) is still required
#                  per repo; this mode prints that as a warning. The
#                  corresponding ~/.copilot/mozart/ fallback read is
#                  designed-for-v2 and unvalidated (see docs/COPILOT_PORT.md)
#                  and this script never creates it.
#
# --home <dir>     Only valid with --user-scope. Defaults to $HOME. Exists so
#                  this mode is testable without touching the real home
#                  directory.
#
# --apply          Write for real. Default is a dry run: prints the plan,
#                  writes nothing, exits 0.
#
# --force          Required to overwrite an installed bundle whose
#                  .github/mozart/VERSION is newer than this repo's. Without
#                  it, a would-be downgrade is refused (exit 1).
#
# --target and --user-scope are mutually exclusive: passing both exits 2.
#
# Exit: 0 success (including dry run and no-op); 1 refused (e.g. a would-be
# downgrade without --force); 2 usage error.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_VERSION_FILE="$REPO_ROOT/.github/mozart/VERSION"

usage() {
  cat >&2 <<'USAGE'
usage: install-bundle.sh --target <dir> [--apply] [--force]
       install-bundle.sh --user-scope [--home <dir>] [--apply] [--force]

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
  [ "$a" != "$a_core" ] && a_pre=1
  [ "$b" != "$b_core" ] && b_pre=1
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
APPLY=0
FORCE=0

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
    --apply)
      APPLY=1; shift ;;
    --force)
      FORCE=1; shift ;;
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

  if [ "$APPLY" -eq 0 ]; then
    echo "[dry run] would install into $TARGET:"
    echo "  .github/agents/*.agent.md -> $TARGET/.github/agents/"
    echo "  .github/mozart/           -> $TARGET/.github/mozart/ (source VERSION $SOURCE_VERSION)"
    echo "[dry run] nothing from repo-root config/, tests/, or scripts/ is installed (D14)"
    exit 0
  fi

  mkdir -p "$TARGET/.github/agents"
  cp "$REPO_ROOT"/.github/agents/*.agent.md "$TARGET/.github/agents/"

  mkdir -p "$TARGET/.github/mozart"
  cp -R "$REPO_ROOT"/.github/mozart/. "$TARGET/.github/mozart/"

  echo "installed .github/agents (22 files) and .github/mozart (VERSION $SOURCE_VERSION) into $TARGET"
  exit 0
fi

# --------------------------------------------------------------------------
# --user-scope: agent-definitions-only install.
# --------------------------------------------------------------------------

if [ "$USER_SCOPE" -eq 1 ]; then
  if [ -z "$HOME_DIR" ]; then
    echo "usage error: --home requires a directory argument, and \$HOME is unset" >&2
    usage
    exit 2
  fi

  DEST="$HOME_DIR/.copilot/agents"

  if [ "$APPLY" -eq 0 ]; then
    echo "[dry run] would install .github/agents/*.agent.md -> $DEST"
    echo "[dry run] The mozart bundle is workspace-scoped: run \`install-bundle.sh --target <repo> --apply\` in each repo you want to orchestrate, or these agents will halt on their first read."
    exit 0
  fi

  mkdir -p "$DEST"
  cp "$REPO_ROOT"/.github/agents/*.agent.md "$DEST/"
  echo "Agent definitions installed. The mozart bundle is workspace-scoped: run \`install-bundle.sh --target <repo> --apply\` in each repo you want to orchestrate, or these agents will halt on their first read."
  exit 0
fi
