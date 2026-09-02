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
#      recorded canonical parent — so a parent OR ancestor swapped for a symlink
#      after install is refused rather than followed out of the namespace — then
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
