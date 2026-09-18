#!/usr/bin/env bash
# A17 — this port's campaign scripts against mozart-orchestration's.
#
#   scripts/mozart-lint.sh    equals the source's, modulo an allowlisted
#                             reviewer-label diff committed at
#                             tests/lint-upstream.diff (PD22)
#   scripts/mozart-metrics.sh is byte-identical to the source's
#
# Not a check.yml step: it needs a mozart-orchestration checkout, which CI
# cannot see. Same reason the fixture-corpus byte-diff runs at campaign-
# verification time rather than in CI. Run it from a copilot checkout:
#
#   bash scripts/check-lint-parity.sh /path/to/mozart-orchestration
#
# Exit 0 = parity holds. Exit 1 = a real difference. Exit 2 = usage.
#
# Residual, stated plainly: the allowlist below matches line TEXT, so a logic
# change on a line that also carries an allowlisted token would be admitted.
# This narrows the manual read; it does not replace it. A reviewer still reads
# tests/lint-upstream.diff hunk by hunk and confirms each hunk is a reviewer-
# label change rather than logic.

set -uo pipefail

SRC=${1:-}
if [ -z "$SRC" ] || [ ! -f "$SRC/scripts/mozart-lint.sh" ]; then
  echo "usage: $0 <mozart-orchestration-root>" >&2
  echo "  (needs <root>/scripts/mozart-lint.sh and mozart-metrics.sh)" >&2
  exit 2
fi

# The allowlist. Every changed line in tests/lint-upstream.diff must match one
# of these, or the diff is carrying a logic change dressed as a label change.
#
# 'codex-drift' and 'codex r[12]' are the SOURCE side of the label rename
# (codex-drift -> review-drift, 'codex r1' -> 'round 1'). They are lowercase,
# so the capitalized 'Codex' alternative does not cover them — that omission
# made this check unable to reach 0 on a correct port, i.e. unable to do its
# job at all (F46). Fixed by naming the two lowercase forms explicitly rather
# than matching case-insensitively: -i would also admit any casing of
# "claude"/"counterpoint" anywhere on a line, widening the allowlist past the
# specific strings this rename actually produces.
ALLOW_RE='REVIEW_LABEL_RE|review-drift|external-review|Counterpoint|Codex|Claude|codex-drift|codex r[12]|round [12]|PIPELINE\.md|^[<>] *#( |$)|^[<>] *$'

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
rc=0

# 1. The live diff must equal the committed allowlist file, byte for byte.
diff "$SRC/scripts/mozart-lint.sh" scripts/mozart-lint.sh > "$tmp/live.diff"
if ! diff -u tests/lint-upstream.diff "$tmp/live.diff" > "$tmp/meta.diff"; then
  echo "FAIL: scripts/mozart-lint.sh differs from the source in ways" >&2
  echo "      tests/lint-upstream.diff does not record:" >&2
  sed 's/^/      /' "$tmp/meta.diff" >&2
  rc=1
else
  echo "ok: live lint diff matches tests/lint-upstream.diff"
fi

# 2. Population floor + named member (M7). An empty or truncated allowlist file
#    would make step 3 pass while proving nothing about the label port.
changed=$(grep -cE '^[<>]' tests/lint-upstream.diff || true)
if [ "$changed" -lt 8 ]; then
  echo "FAIL: allowlist changed-line population $changed < 8 — the file is" >&2
  echo "      empty or truncated; step 3 below would pass vacuously" >&2
  rc=1
fi
if ! grep -qF 'REVIEW_LABEL_RE=' tests/lint-upstream.diff; then
  echo "FAIL: named member absent from the allowlist: REVIEW_LABEL_RE=" >&2
  rc=1
fi

# 3. Every changed line is a reviewer-label or comment change, not logic.
grep -E '^[<>]' tests/lint-upstream.diff | grep -vE "$ALLOW_RE" > "$tmp/bad" || true
n=$(grep -c . < "$tmp/bad" || true)
if [ "$n" -ne 0 ]; then
  echo "FAIL: $n non-allowlisted changed line(s) in tests/lint-upstream.diff:" >&2
  sed 's/^/      /' "$tmp/bad" >&2
  rc=1
else
  echo "ok: 0 non-allowlisted changed lines across $changed changed line(s)"
fi

# 4. Metrics is a straight copy — no allowlist, no exceptions.
if cmp "$SRC/scripts/mozart-metrics.sh" scripts/mozart-metrics.sh; then
  echo "ok: scripts/mozart-metrics.sh byte-identical to the source"
else
  echo "FAIL: scripts/mozart-metrics.sh is not byte-identical to the source" >&2
  rc=1
fi

[ "$rc" -eq 0 ] && echo "lint parity: PASS"
exit "$rc"
