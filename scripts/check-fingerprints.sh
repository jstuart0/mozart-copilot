#!/usr/bin/env bash
# Guards against personal-infrastructure fingerprints (C1).
# KNOWN BLIND SPOTS (accepted, Y22): this pattern does NOT cover
# /Users/[A-Z]*, /home/[A-Z]*, hostnames, or absolute paths under a
# username other than 'jaystuart'. Widen deliberately, never silently.
# DEVIATION FROM D-J (required): this file is excluded from its own scan via
# ':!scripts/check-fingerprints.sh'. The verbatim D-J body scans '-- .' with
# only ':!.mozart', but once this script is *tracked* the search matches the
# pattern literal on its own grep line and would make the gate permanently
# red. Excluding the guard from itself is idiomatic (mirrors ':!.mozart').
# Accepted residual: a personal path added *inside this file* is not caught
# here; this file is small and code-reviewed.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
out="$(git grep -n -I -E 'jaystuart|/Users/[a-z]|/home/[a-z]|mozart-orchestration' -- . ':!.mozart' ':!scripts/check-fingerprints.sh')" && rc=0 || rc=$?
case "$rc" in
  0) printf 'FAIL: personal-infrastructure fingerprint(s) found:\n%s\n' "$out" >&2; exit 1 ;;
  1) echo "OK: no personal-infrastructure fingerprints"; exit 0 ;;
  *) echo "ERROR: git grep failed with status $rc" >&2; exit 2 ;;
esac
