#!/usr/bin/env python3
"""check_agents.py — mechanical validator for mozart-copilot's .agent.md personas.

Python 3, standard library only (D11): bash+jq can't parse JSONC comments and
a regex-only frontmatter parser desynchronizes from real YAML the first time
someone writes a block list or a quoted scalar.

Body measurement uses the same two-delimiter extractor and character (not
byte) semantics as the plan's BODY() shell function:

    awk 'BEGIN{n=0} /^---$/ && n<2 {n++; next} n==2' <file> | LC_ALL=en_US.UTF-8 wc -m

`split_frontmatter()` below reproduces that extractor exactly: the first two
lines that are *exactly* "---" are delimiters; everything after the second
delimiter is body, including any further "---" lines. `len()` on the decoded
UTF-8 body text is `wc -m`'s character count under a UTF-8 locale.

Exit-code contract (shared with mozart-lint.sh / mozart-metrics.sh):
    0 = clean (WARN allowed)
    1 = findings
    2 = nothing to check (a required input file doesn't exist yet — this is
        not a vacuous pass; a missing prerequisite is reported, not ignored)

Usage:
    check_agents.py [--min-agents N]
    check_agents.py --file PATH
    check_agents.py --self-test [--forms]
    check_agents.py --map PATH
    check_agents.py --emit-runtime-reads
    check_agents.py --check-doc-refs [TSV_PATH]
    check_agents.py --check-install DIR [--layout repo|user]
    check_agents.py --check-carve TSV_PATH
    check_agents.py --check-doc-table
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Best-effort PyYAML cross-check (live-parser incident, 2026-09-01): real
# copilot CLI 1.0.82 rejected an installed mozart.agent.md — "failed to
# parse YAML frontmatter: mapping values are not allowed in this context"
# — for an unquoted description scalar containing ': ' that this repo's
# hand-rolled parser (parse_frontmatter below, which only ever looks at the
# first ':' on a line) silently accepted. When PyYAML is importable, every
# frontmatter block is additionally parsed with yaml.safe_load as a second,
# spec-accurate opinion; when it isn't, that cross-check is silently
# skipped and every caller that reports results names which mode ran, so a
# pass is attributable to one or both parsers rather than assumed.
try:
    import yaml as _pyyaml
    HAVE_PYYAML = True
except ImportError:
    _pyyaml = None
    HAVE_PYYAML = False

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".github" / "agents"

# Upstream source of truth for the manual carve (Phase 5, step 21; campaign
# plan Context section). Hardcoded here — these are the AUTHORITY;
# tests/coverage-map.tsv's own '# expected_chars=<N>' header is a
# cross-check against them, never the source of truth on its own (a header
# edited to match wrong rows must not be sufficient to pass --check-carve).
UPSTREAM_CARVE_START_LINE = 7
UPSTREAM_CARVE_END_LINE = 2400
UPSTREAM_CARVE_EXPECTED_CHARS = 241189
# The upstream mozart.md live re-derivation (below, in cmd_check_carve) reads
# this when a source checkout is reachable. The path is no longer hardcoded
# to one person's layout (C1): it is resolved per invocation from an explicit
# --upstream-mozart-md flag or the shared $MOZART_UPSTREAM_CHECKOUT env var,
# defaulting to None = skip. resolve_upstream_mozart_md() below is the single
# resolver.
UPSTREAM_MOZART_MD_SUBPATH = "agents/mozart.md"


def resolve_upstream_mozart_md(explicit: str = None):
    """Resolve the optional upstream agents/mozart.md for the carve's live
    re-derivation cross-check. Order: explicit --upstream-mozart-md flag →
    $MOZART_UPSTREAM_CHECKOUT joined with agents/mozart.md → None (skip).
    None reaches cmd_check_carve()'s existing .exists()-guarded skip branch
    with no new code path (D-A option B)."""
    if explicit:
        return Path(explicit)
    checkout = os.environ.get("MOZART_UPSTREAM_CHECKOUT")
    if checkout:
        return Path(checkout) / UPSTREAM_MOZART_MD_SUBPATH
    return None
BUNDLE_PREFIX = ".github/mozart/"
TOOLSETS_PATH = REPO_ROOT / "config" / "toolsets.jsonc"
RUNTIME_READS_TSV = REPO_ROOT / "tests" / "runtime-reads.tsv"
DOC_PORT_PATH = REPO_ROOT / "docs" / "COPILOT_PORT.md"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"

WARN_CHARS = 27000
FAIL_CHARS = 30000

CANONICAL_MODEL_MAP = ".github/mozart/config/model-map.jsonc"
# EVAL.md exists at two canonical bundle locations: the schema/reference doc
# at bundle root and the pipeline-procedure doc under manual/ (see
# .github/mozart/manual/INDEX.md's disambiguation note — both are real,
# distinct, required reads). Every other basename here has exactly one
# canonical location.
BUNDLE_DOC_VALID_PREFIXES = {
    "PIPELINE.md": [".github/mozart/"],
    "LEARNINGS.md": [".github/mozart/"],
    "INTEGRATION.md": [".github/mozart/"],
    "EVAL.md": [".github/mozart/", ".github/mozart/manual/"],
}
BUNDLE_REF_RE = re.compile(r"\.github/mozart/[A-Za-z0-9_./-]+")

# D3 — the user-scope bundle root is a legal grant target, never a legal read
# path. Two closed-form rejection regexes, used together with a bare token
# search (rule 1's acceptance is the *absence* of a rule-2/rule-3 hit, not a
# separate positive check):
#
#   rule 2 — a path component after the root. The first-character class
#   deliberately excludes '.' (bob N7): with '.' included, legal prose
#   "...the bundle at `~/.copilot/mozart/`. Then..." would fire on the
#   sentence period, contradicting rule 1's acceptance of the bare root.
USER_BUNDLE_SUFFIX_RE = re.compile(r"(\.copilot|\$\{?COPILOT_HOME\}?)/mozart/[A-Za-z0-9_-]")
#   rule 3 — the bare root token, used to test whether it co-occurs (per
#   line) with a shell verb in command position. Not anchored to end-of-
#   token, so it also matches when a rule-2 suffix is present on the line.
USER_BUNDLE_ROOT_RE = re.compile(r"~/\.copilot/mozart|\$\{?COPILOT_HOME\}?/mozart")
#   the command-position verb heuristic (bob N6/N7): trailing '\b' keeps
#   'cat' from firing on 'catalog' and 'ln' from firing on 'lnk'; the
#   leading alternation anchors to command position. 'install' is
#   deliberately absent (bob C1) — the recommended remediation is
#   `scripts/install-bundle.sh --user-scope --apply`, and a rule that fires
#   on the fix it recommends trains worse halt messages.
USER_BUNDLE_SHELL_VERB_RE = re.compile(r"(?:^|[`$;|(]|&&)\s*(?:cp|cat|rsync|ln|tar|mv|scp)\b")


# --------------------------------------------------------------------------
# JSONC (comments + trailing commas), stdlib only.
# --------------------------------------------------------------------------

def strip_jsonc_comments(text: str) -> str:
    out = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        c = text[i]
        if in_string:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def load_jsonc(path: Path):
    text = path.read_text(encoding="utf-8")
    stripped = strip_jsonc_comments(text)
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
    return json.loads(stripped)


# --------------------------------------------------------------------------
# Frontmatter: the two-delimiter extractor + a minimal YAML-subset parser.
# --------------------------------------------------------------------------

class FrontmatterError(Exception):
    pass


def split_frontmatter(text: str):
    """Return (fm_lines, body_text). Raises FrontmatterError on a missing or
    unclosed opening/closing '---' pair — never a partial parse."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines or lines[0] != "---":
        raise FrontmatterError("missing opening '---' delimiter on line 1")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            end_idx = i
            break
    if end_idx is None:
        raise FrontmatterError("unclosed frontmatter: no closing '---' delimiter found")
    fm_lines = lines[1:end_idx]
    body_lines = lines[end_idx + 1:]
    body_text = "".join(l + "\n" for l in body_lines)
    return fm_lines, body_text


def strip_yaml_comment(line: str) -> str:
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or line[i - 1].isspace():
                return line[:i].rstrip()
    return line.rstrip()


def is_quoted_yaml_scalar(s: str) -> bool:
    return len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'"))


def require_no_unquoted_colon_space(s: str, context: str) -> None:
    """Hard-fail rule (live-parser incident, 2026-09-01): a plain (unquoted)
    YAML scalar containing ': ' (colon-space) is invalid — real YAML treats
    an unescaped colon-space as the start of a nested mapping, ambiguous
    with plain scalar content. copilot CLI 1.0.82 rejected an installed
    mozart.agent.md with exactly this — "failed to parse YAML frontmatter:
    mapping values are not allowed in this context" — because this repo's
    own parser (which only ever splits on the first ':' on a line) silently
    accepted what real YAML refuses. Quoted scalars are exempt: real YAML
    allows ': ' freely inside a quoted string."""
    if is_quoted_yaml_scalar(s):
        return
    if ": " in s:
        raise FrontmatterError(
            f"{context} is an unquoted value containing ': ' (colon-space), which real "
            f"YAML forbids in a plain scalar (ambiguous with a nested mapping key) — "
            f"quote the whole value (e.g. \"...\") to fix. This is the live-parser "
            f"incident: copilot CLI 1.0.82 rejected an installed mozart.agent.md with "
            f"'mapping values are not allowed in this context' for exactly this shape."
        )


def parse_yaml_scalar(s: str):
    s = s.strip()
    if is_quoted_yaml_scalar(s):
        return s[1:-1]
    return s


def parse_inline_list(s: str, context: str = "inline list item"):
    s = s.strip()
    assert s.startswith("[") and s.endswith("]")
    inner = s[1:-1].strip()
    if not inner:
        return []
    items = [x.strip() for x in inner.split(",")]
    for item in items:
        require_no_unquoted_colon_space(item, context)
    return [parse_yaml_scalar(x) for x in items]


def parse_frontmatter(fm_lines):
    """Minimal top-level YAML mapping parser: bare/quoted scalars, inline
    lists ([a, b]), block lists (- item), trailing '# comment' stripping.
    Returns (data: dict, kinds: dict[str, 'scalar'|'list'])."""
    data, kinds = {}, {}
    i, n = 0, len(fm_lines)
    while i < n:
        raw = fm_lines[i]
        line = strip_yaml_comment(raw)
        if not line.strip():
            i += 1
            continue
        if line.strip().startswith("- "):
            raise FrontmatterError(f"unexpected list item with no preceding key: {raw!r}")
        if ":" not in line:
            raise FrontmatterError(f"malformed frontmatter line (no ':'): {raw!r}")
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            block_items = []
            j = i + 1
            while j < n:
                nxt_raw = fm_lines[j]
                nxt = strip_yaml_comment(nxt_raw)
                if nxt.strip() == "":
                    j += 1
                    continue
                indent = len(nxt_raw) - len(nxt_raw.lstrip(" "))
                stripped = nxt.strip()
                if stripped.startswith("- ") and indent > 0:
                    item = stripped[2:].strip()
                    require_no_unquoted_colon_space(item, f"key {key!r} list item")
                    block_items.append(parse_yaml_scalar(item))
                    j += 1
                    continue
                break
            if block_items:
                data[key] = block_items
                kinds[key] = "list"
            else:
                data[key] = ""
                kinds[key] = "scalar"
            i = j
            continue
        if rest.startswith("["):
            data[key] = parse_inline_list(rest, context=f"key {key!r} list item")
            kinds[key] = "list"
        else:
            require_no_unquoted_colon_space(rest, f"key {key!r}")
            data[key] = parse_yaml_scalar(rest)
            kinds[key] = "scalar"
        i += 1
    return data, kinds


# --------------------------------------------------------------------------
# Toolset vocabulary.
# --------------------------------------------------------------------------

def load_toolset_vocab():
    if not TOOLSETS_PATH.exists():
        raise FileNotFoundError(f"{TOOLSETS_PATH} not found — required by every check")
    data = load_jsonc(TOOLSETS_PATH)
    vocab = set(data.get("copilot_tool_sets", [])) | set(data.get("copilot_standalone_tools", []))
    wildcard_re = re.compile(data.get("mcp_wildcard_pattern", r"^[A-Za-z0-9_.-]+/\*$"))
    return vocab, wildcard_re


def is_valid_tool(tool: str, vocab, wildcard_re) -> bool:
    return tool in vocab or bool(wildcard_re.match(tool))


# --------------------------------------------------------------------------
# Bundle-path references (D9 / D14 / P8).
# --------------------------------------------------------------------------

def find_bundle_refs(body_text: str):
    refs = set()
    for m in BUNDLE_REF_RE.finditer(body_text):
        token = m.group(0).rstrip(".,;:)`'\"")
        refs.add(token)
    return refs


def find_outside_bundle_violations(body_text: str):
    violations = set()
    # D3 rule 2: a path component cited under the user-scope root. Exact at
    # the token level — see USER_BUNDLE_SUFFIX_RE's comment for the excluded
    # '.' first-char case.
    for m in USER_BUNDLE_SUFFIX_RE.finditer(body_text):
        violations.add(
            f"cites a path under the user-scope bundle root ({m.group(0)!r}) — "
            "the canonical citation form is '.github/mozart/<file>' (D2); "
            "the user-scope root ('~/.copilot/mozart' or '$COPILOT_HOME/mozart') may "
            "be named as a grant target only, never as a read path"
        )
    # D3 rule 3: the bare root on a line that also shells a copy verb in
    # command position — the copilot-cli#2173 self-bootstrap idiom.
    for line in body_text.splitlines():
        if USER_BUNDLE_ROOT_RE.search(line) and USER_BUNDLE_SHELL_VERB_RE.search(line):
            violations.add(
                "shell-copies from the user-scope bundle root at command position "
                "(github/copilot-cli#2173 — no agent-side self-bootstrap from the "
                "user-scope root; run `scripts/install-bundle.sh --user-scope --apply` "
                "instead)"
            )
    if re.search(r"(^|[^/])docs/manual/", body_text):
        violations.add(
            "references the retired r0 path 'docs/manual/' "
            "(manual docs live under .github/mozart/manual/)"
        )
    for m in re.finditer(r"[\w./~-]*model-map[\w./-]*", body_text):
        # rstrip only — trailing punctuation from prose ("...jsonc.", "...jsonc)").
        # A leading '.' is meaningful here (".github/...") and must never be stripped;
        # the capture class already excludes backtick/quote, so nothing wrapping needs it.
        token = m.group(0).rstrip(".,;:)")
        if token != CANONICAL_MODEL_MAP:
            violations.add(
                f"references 'model-map' outside the canonical bundle path "
                f"({token!r} != {CANONICAL_MODEL_MAP!r})"
            )
    for name, valid_prefixes in BUNDLE_DOC_VALID_PREFIXES.items():
        for m in re.finditer(re.escape(name), body_text):
            start = m.start()
            if not any(
                body_text[max(0, start - len(prefix)):start] == prefix
                for prefix in valid_prefixes
            ):
                violations.add(f"references '{name}' without the '.github/mozart/' bundle prefix")
    return sorted(violations)


# --------------------------------------------------------------------------
# Single-file validation.
# --------------------------------------------------------------------------

@dataclass
class ValidationResult:
    path: Path
    ok: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    data: dict = field(default_factory=dict)
    kinds: dict = field(default_factory=dict)
    body_chars: int = 0


def pyyaml_crosscheck(fm_lines) -> list:
    """Best-effort second opinion (live-parser incident, 2026-09-01): when
    PyYAML is importable, re-parse the frontmatter block with the real,
    spec-accurate parser instead of this file's hand-rolled subset. Returns
    a list of error strings (empty when PyYAML is unavailable or the block
    parses cleanly) — never raises, so a missing PyYAML dependency never
    turns into a validator crash."""
    if not HAVE_PYYAML:
        return []
    try:
        _pyyaml.safe_load("\n".join(fm_lines))
    except _pyyaml.YAMLError as e:
        return [f"PyYAML cross-check: frontmatter is not valid YAML: {e}"]
    return []


def yaml_crosscheck_mode_note() -> str:
    """One line naming which frontmatter parser(s) ran, printed by every
    entry point that validates a file — so a pass is attributable to the
    hand-rolled parser alone or to both, never assumed (live-parser
    incident, 2026-09-01)."""
    if HAVE_PYYAML:
        return "frontmatter validation mode: hand-rolled parser + PyYAML cross-check (both ran)"
    return "frontmatter validation mode: hand-rolled parser only (PyYAML not importable — cross-check skipped)"


def agent_stem(path: Path) -> str:
    name = path.name
    if name.endswith(".agent.md"):
        return name[: -len(".agent.md")]
    return path.stem


def validate_agent_file(path: Path) -> ValidationResult:
    result = ValidationResult(path=path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        result.ok = False
        result.errors.append(f"could not read file: {e}")
        return result

    try:
        fm_lines, body_text = split_frontmatter(text)
    except FrontmatterError as e:
        result.ok = False
        result.errors.append(str(e))
        return result

    try:
        data, kinds = parse_frontmatter(fm_lines)
    except FrontmatterError as e:
        result.ok = False
        result.errors.append(f"frontmatter parse error: {e}")
        return result

    result.data = data
    result.kinds = kinds
    result.body_chars = len(body_text)

    stem = agent_stem(path)
    errors = result.errors

    # PyYAML cross-check (best-effort, silent-skip when unavailable — see
    # HAVE_PYYAML / pyyaml_crosscheck above). Runs even though our own
    # hand-rolled parser already succeeded above: the two parsers accept
    # different subsets, and this is specifically the second opinion that
    # would have caught the live-parser incident before install.
    errors.extend(pyyaml_crosscheck(fm_lines))

    # name == filename stem
    name = data.get("name")
    if not name:
        errors.append("frontmatter 'name' is missing or empty")
    elif name != stem:
        errors.append(f"frontmatter name {name!r} does not match filename stem {stem!r}")

    # description present and non-empty
    description = data.get("description")
    if not description or (isinstance(description, str) and not description.strip()):
        errors.append("frontmatter 'description' is missing or empty")

    # tools: present, non-empty list, every entry in the vocabulary
    tools = None
    if "tools" not in data:
        errors.append("frontmatter 'tools' is missing")
    elif kinds.get("tools") != "list":
        errors.append("frontmatter 'tools' must be a YAML list")
    elif not data["tools"]:
        errors.append("frontmatter 'tools' is present but empty")
    else:
        tools = data["tools"]
        try:
            vocab, wildcard_re = load_toolset_vocab()
        except FileNotFoundError as e:
            errors.append(str(e))
            vocab, wildcard_re = set(), re.compile(r"$^")
        for t in tools:
            if not is_valid_tool(t, vocab, wildcard_re):
                errors.append(f"tools entry {t!r} is not a member of config/toolsets.jsonc")

    # model: present, scalar string, explicit failure on a YAML sequence
    if "model" not in data:
        errors.append("frontmatter 'model' is missing")
    elif kinds.get("model") == "list":
        errors.append(
            "frontmatter 'model' is a YAML sequence, not a scalar string "
            "(github/copilot-cli#2133 — subagent model: silently falls back to the parent's)"
        )
    elif not data["model"]:
        errors.append("frontmatter 'model' is present but empty")

    # agents: present as a list ([] for every non-conductor)
    agents_list = None
    if "agents" not in data:
        errors.append("frontmatter 'agents' is missing (use '[]' for a non-conductor specialist)")
    elif kinds.get("agents") != "list":
        errors.append("frontmatter 'agents' must be a YAML list ('[]' when empty)")
    else:
        agents_list = data["agents"]

    # user-invocable: present, boolean scalar
    user_invocable = None
    if "user-invocable" not in data:
        errors.append("frontmatter 'user-invocable' is missing")
    elif kinds.get("user-invocable") != "scalar" or data["user-invocable"] not in ("true", "false"):
        errors.append("frontmatter 'user-invocable' must be the scalar 'true' or 'false'")
    else:
        user_invocable = data["user-invocable"] == "true"
        result.data["user-invocable"] = user_invocable  # normalize to bool for callers

    # agent ∈ tools iff agents non-empty — both directions
    if tools is not None and agents_list is not None:
        agent_in_tools = "agent" in tools
        agents_nonempty = len(agents_list) > 0
        if agents_nonempty and not agent_in_tools:
            errors.append(
                "frontmatter 'agents' is non-empty but 'agent' is not in 'tools' "
                "(dispatch requires the agent tool)"
            )
        if agent_in_tools and not agents_nonempty:
            errors.append(
                "'agent' is in 'tools' but frontmatter 'agents' is empty "
                "(the agent tool is granted but nothing is dispatchable)"
            )

        # D10: dispatch authority is mozart's alone. mozart must actually
        # hold it — not merely be permitted to by the correlation check
        # above — and every other agent must not, even if its own agents:
        # / tools: pairing is internally self-consistent.
        if stem == "mozart":
            if not agent_in_tools or not agents_nonempty:
                errors.append(
                    "'mozart' must have the 'agent' tool and a non-empty 'agents:' allowlist "
                    "— it's the conductor (D10)"
                )
        else:
            if agent_in_tools:
                errors.append(
                    f"'{stem}' holds the 'agent' tool, but only 'mozart' may dispatch subagents (D10)"
                )
            if agents_nonempty:
                errors.append(
                    f"'{stem}' has a non-empty 'agents:' allowlist, but only 'mozart' may dispatch subagents (D10)"
                )

    # only mozart may be user-invocable: true (D10)
    if user_invocable is True and stem != "mozart":
        errors.append("frontmatter 'user-invocable: true' is set, but only 'mozart' may be user-invocable")

    # MODEL-ATTESTATION marker present
    if "MODEL-ATTESTATION" not in body_text:
        errors.append("body has no 'MODEL-ATTESTATION' marker")

    # body size cap / warn band (two-delimiter extractor, character semantics)
    if result.body_chars > FAIL_CHARS:
        errors.append(f"body is {result.body_chars} chars, exceeds the {FAIL_CHARS}-char cap")
    elif result.body_chars > WARN_CHARS:
        result.warnings.append(
            f"body is {result.body_chars} chars (WARN band: > {WARN_CHARS}, cap {FAIL_CHARS})"
        )

    # every path-like reference resolves under .github/mozart/
    for v in find_outside_bundle_violations(body_text):
        errors.append(v)

    result.ok = len(errors) == 0
    return result


# --------------------------------------------------------------------------
# --self-test
# --------------------------------------------------------------------------

def run_self_test(forms: bool) -> int:
    print(yaml_crosscheck_mode_note())
    ok = True

    def check_accept(p: Path, expect_warn: bool = False) -> bool:
        nonlocal ok
        if not p.exists():
            print(f"MISSING fixture: {p.relative_to(REPO_ROOT)}")
            ok = False
            return False
        r = validate_agent_file(p)
        if not r.ok:
            print(f"FAIL (expected ACCEPT): {p.relative_to(REPO_ROOT)} — {'; '.join(r.errors)}")
            ok = False
            return False
        if expect_warn and not r.warnings:
            print(f"FAIL (expected WARN): {p.relative_to(REPO_ROOT)} — accepted with no warning")
            ok = False
            return False
        tag = " (WARN)" if r.warnings else ""
        print(f"accept: {p.relative_to(REPO_ROOT)}{tag}")
        return True

    def check_reject(p: Path) -> bool:
        nonlocal ok
        if not p.exists():
            print(f"MISSING fixture: {p.relative_to(REPO_ROOT)}")
            ok = False
            return False
        r = validate_agent_file(p)
        if r.ok:
            print(f"FAIL (expected REJECT): {p.relative_to(REPO_ROOT)} — validator accepted it")
            ok = False
            return False
        print(f"reject: {p.relative_to(REPO_ROOT)} — {'; '.join(r.errors)}")
        return True

    check_accept(FIXTURES_DIR / "valid.agent.md")
    check_accept(FIXTURES_DIR / "warn-band.agent.md", expect_warn=True)

    invalid_fixtures = sorted(FIXTURES_DIR.glob("invalid-*.agent.md"))
    if not invalid_fixtures:
        print("FAIL: no tests/fixtures/invalid-*.agent.md fixtures found")
        ok = False
    for p in invalid_fixtures:
        check_reject(p)

    if forms:
        forms_dir = FIXTURES_DIR / "forms"
        form_fixtures = sorted(forms_dir.glob("*.agent.md")) if forms_dir.exists() else []
        if not form_fixtures:
            print("FAIL: no tests/fixtures/forms/*.agent.md fixtures found")
            ok = False
        for p in form_fixtures:
            check_accept(p)
        # unclosed '---' rejected — reuses the shared negative fixture
        check_reject(FIXTURES_DIR / "invalid-unclosed-frontmatter.agent.md")

    print(f"\nself-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# --------------------------------------------------------------------------
# --file
# --------------------------------------------------------------------------

def cmd_file(path_str: str) -> int:
    print(yaml_crosscheck_mode_note())
    p = Path(path_str)
    if not p.is_absolute():
        p = REPO_ROOT / p
    r = validate_agent_file(p)
    for w in r.warnings:
        print(f"WARN {p}: {w}")
    for e in r.errors:
        print(f"FAIL {p}: {e}")
    if r.ok:
        print(f"OK {p}")
        return 0
    return 1


# --------------------------------------------------------------------------
# Default: validate the whole .github/agents/ roster.
# --------------------------------------------------------------------------

def discover_agent_files(agents_dir: Path = None):
    d = agents_dir if agents_dir is not None else AGENTS_DIR
    if not d.exists():
        return []
    return sorted(d.glob("*.agent.md"))


def cmd_validate_all(min_agents) -> int:
    print(yaml_crosscheck_mode_note())
    files = discover_agent_files()
    any_fail = False
    invocable_true = []

    for f in files:
        r = validate_agent_file(f)
        rel = f.relative_to(REPO_ROOT)
        for w in r.warnings:
            print(f"WARN {rel}: {w}")
        for e in r.errors:
            print(f"FAIL {rel}: {e}")
        if not r.ok:
            any_fail = True
        if r.data.get("user-invocable") is True:
            invocable_true.append(f)

    if len(invocable_true) == 0:
        print("FAIL roster: no agent is user-invocable: true — 'mozart' (the conductor) must be (D10)")
        any_fail = True
    elif len(invocable_true) > 1:
        names = ", ".join(f.name for f in invocable_true)
        print(f"FAIL roster: more than one agent is user-invocable: true: {names}")
        any_fail = True
    elif agent_stem(invocable_true[0]) != "mozart":
        print(
            f"FAIL roster: the one user-invocable: true agent must be 'mozart', "
            f"found '{agent_stem(invocable_true[0])}' (D10)"
        )
        any_fail = True

    if min_agents is not None and len(files) < min_agents:
        print(f"FAIL roster: {len(files)} agent file(s) found under .github/agents/, --min-agents requires >= {min_agents}")
        any_fail = True

    print(f"\nvalidated {len(files)} agent file(s) under .github/agents/")
    return 1 if any_fail else 0


# --------------------------------------------------------------------------
# --map
# --------------------------------------------------------------------------

def cmd_map(path_str: str, min_agents=None) -> int:
    p = Path(path_str)
    if not p.is_absolute():
        p = REPO_ROOT / p
    if not p.exists():
        print(f"NOTHING TO CHECK: map file not found at {p}")
        return 2

    try:
        m = load_jsonc(p)
    except (json.JSONDecodeError, OSError) as e:
        print(f"FAIL: could not parse {p} as JSONC: {e}")
        return 1

    errors = []
    roles = m.get("roles")
    agents_block = m.get("agents")
    if not isinstance(roles, dict):
        errors.append("map is missing a 'roles' object")
        roles = {}
    if not isinstance(agents_block, dict):
        errors.append("map is missing an 'agents' object")
        agents_block = {}

    used_roles = set(agents_block.values())
    for role in roles:
        if role not in used_roles:
            errors.append(f"role '{role}' is defined but assigned to no agent (orphan role)")
    for agent_name, role in agents_block.items():
        if role not in roles:
            errors.append(f"agent '{agent_name}' is assigned to undefined role '{role}'")

    discovered = {agent_stem(f) for f in discover_agent_files()}
    if min_agents is not None and len(discovered) < min_agents:
        errors.append(
            f"roster: {len(discovered)} agent file(s) found under .github/agents/, "
            f"--min-agents requires >= {min_agents}"
        )
    map_agents = set(agents_block.keys())
    for missing in sorted(discovered - map_agents):
        errors.append(f"agent file '{missing}.agent.md' exists but has no entry in the map")
    for extra in sorted(map_agents - discovered):
        errors.append(f"map assigns a role to '{extra}' but no .github/agents/{extra}.agent.md exists")

    for f in discover_agent_files():
        stem = agent_stem(f)
        role = agents_block.get(stem)
        if role is None or role not in roles:
            continue
        r = validate_agent_file(f)
        role_model = roles[role].get("model") if isinstance(roles[role], dict) else None
        file_model = r.data.get("model")
        if role_model is not None and file_model is not None and role_model != file_model:
            errors.append(
                f"'{stem}' is stamped model {file_model!r} but its role '{role}' maps to {role_model!r}"
            )

    mozart_file = AGENTS_DIR / "mozart.agent.md"
    if mozart_file.exists():
        r = validate_agent_file(mozart_file)
        mozart_agents = set(r.data.get("agents") or [])
        specialists = discovered - {"mozart"}
        missing_from_allowlist = specialists - mozart_agents
        extra_in_allowlist = mozart_agents - specialists
        for a in sorted(missing_from_allowlist):
            errors.append(f"'{a}' is a specialist file but is missing from mozart's agents: allowlist")
        for a in sorted(extra_in_allowlist):
            errors.append(f"mozart's agents: allowlist names '{a}', which is not a specialist file")

    for e in errors:
        print(f"FAIL: {e}")
    return 1 if errors else 0


# --------------------------------------------------------------------------
# --emit-runtime-reads
# --------------------------------------------------------------------------

def emit_runtime_reads_rows():
    rows = []
    for f in discover_agent_files():
        stem = agent_stem(f)
        try:
            text = f.read_text(encoding="utf-8")
            _, body_text = split_frontmatter(text)
        except FrontmatterError:
            continue
        for ref in sorted(find_bundle_refs(body_text)):
            rows.append((stem, ref))
    return sorted(set(rows))


def cmd_emit_runtime_reads() -> int:
    for agent, ref in emit_runtime_reads_rows():
        print(f"{agent}\t{ref}")
    return 0


# --------------------------------------------------------------------------
# --check-doc-refs
# --------------------------------------------------------------------------

def load_runtime_reads_tsv(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise ValueError(f"malformed row (expected 2 tab-separated fields): {line!r}")
        rows.append((parts[0], parts[1]))
    return rows


def cmd_check_doc_refs(path_str=None) -> int:
    if path_str is None:
        tsv_path = RUNTIME_READS_TSV
    else:
        tsv_path = Path(path_str)
        if not tsv_path.is_absolute():
            tsv_path = REPO_ROOT / tsv_path

    if not tsv_path.exists():
        label = tsv_path.relative_to(REPO_ROOT) if tsv_path.is_relative_to(REPO_ROOT) else tsv_path
        print(f"NOTHING TO CHECK: {label} not found — generated in Phase 5 (step 22)")
        return 2

    try:
        committed = load_runtime_reads_tsv(tsv_path)
    except ValueError as e:
        print(f"FAIL: {e}")
        return 1

    fresh = emit_runtime_reads_rows()
    committed_set, fresh_set = set(committed), set(fresh)

    errors = []
    for agent, ref in sorted(committed_set - fresh_set):
        errors.append(f"stale row (no longer emitted): {agent}\t{ref}")
    for agent, ref in sorted(fresh_set - committed_set):
        errors.append(f"missing row (emitted but not committed): {agent}\t{ref}")
    for agent, ref in committed:
        if not (REPO_ROOT / ref).exists():
            errors.append(f"row resolves to a path that does not exist in this repo: {agent}\t{ref}")

    for e in errors:
        print(f"FAIL: {e}")
    return 1 if errors else 0


# --------------------------------------------------------------------------
# --check-install
# --------------------------------------------------------------------------

INSTALL_LAYOUTS = ("repo", "user")


def _installed_agents_dir(install_dir: Path, layout: str) -> Path:
    """Where the installed agent bodies live, per layout."""
    if layout == "repo":
        return install_dir / ".github" / "agents"
    return install_dir / "agents"


def _installed_ref_path(install_dir: Path, ref: str, layout: str) -> Path:
    """Row -> on-disk path, so no caller hand-builds ``DIR/mozart/...``.

    'repo' (today's shape): the manifest row (``.github/mozart/<rest>``) is
    the path relative to DIR, verbatim.
    'user' (the Copilot CLI user-scope shape, no ``.github/`` component):
    the row's leading ``.github/`` is stripped, so ``.github/mozart/<rest>``
    resolves under ``DIR/mozart/<rest>``.
    """
    if layout == "repo":
        return install_dir / ref
    assert ref.startswith(".github/"), f"manifest row does not start with '.github/': {ref!r}"
    return install_dir / ref[len(".github/"):]


def cmd_check_install(dir_str: str, layout: str = "repo") -> int:
    if not RUNTIME_READS_TSV.exists():
        print(f"NOTHING TO CHECK: {RUNTIME_READS_TSV.relative_to(REPO_ROOT)} not found — generated in Phase 5 (step 22)")
        return 2

    install_dir = Path(dir_str)
    if not install_dir.is_absolute():
        install_dir = REPO_ROOT / install_dir
    if not install_dir.exists():
        print(f"NOTHING TO CHECK: installed directory not found at {install_dir}")
        return 2

    try:
        rows = load_runtime_reads_tsv(RUNTIME_READS_TSV)
    except ValueError as e:
        print(f"FAIL: {e}")
        return 1

    errors = []
    for agent, ref in rows:
        if ref.startswith(".mozart/"):
            errors.append(f"manifest row points under .mozart/ (campaign artifact, must never enter the bundle manifest): {agent}\t{ref}")
            continue
        if not ref.startswith(BUNDLE_PREFIX):
            errors.append(f"manifest row resolves outside the bundle: {agent}\t{ref}")
            continue
        if not _installed_ref_path(install_dir, ref, layout).exists():
            errors.append(f"row not found in installed copy ({layout} layout): {agent}\t{ref}")

    # The manifest-row check above only walks rows *this repo* already
    # knows about. A file planted directly into the installed copy's own
    # agent-definitions directory — never indexed into this repo's
    # runtime-reads.tsv — would otherwise pass unnoticed. Re-scan the
    # installed copy's own agent bodies for outside-bundle references.
    # Single-sourced across both layouts (bob M-7): the D3 rule can never be
    # enforced on one install shape and not the other.
    installed_agents_dir = _installed_agents_dir(install_dir, layout)
    if installed_agents_dir.exists():
        for f in sorted(installed_agents_dir.glob("*.agent.md")):
            rel = f.relative_to(install_dir)
            try:
                text = f.read_text(encoding="utf-8")
                _, body_text = split_frontmatter(text)
            except FrontmatterError as e:
                errors.append(f"{rel}: {e}")
                continue
            for v in find_outside_bundle_violations(body_text):
                errors.append(f"{rel}: {v}")

    for e in errors:
        print(f"FAIL: {e}")
    return 1 if errors else 0


# --------------------------------------------------------------------------
# --check-carve
#
# tests/coverage-map.tsv format (created Phase 5, step 21): a TSV with
# optional leading '#'-comment lines, one of which must be
# "# expected_chars=<N>", followed by data rows
#   start_line<TAB>end_line<TAB>chars<TAB>destination
# (1-based, inclusive line ranges, both ends inclusive). The union of ranges
# must be contiguous with no gap and no overlap, and the sum of the 'chars'
# column must equal <N>.
# --------------------------------------------------------------------------

def cmd_check_carve(tsv_path_str: str, upstream_mozart_md=None) -> int:
    p = Path(tsv_path_str)
    if not p.is_absolute():
        p = REPO_ROOT / p
    if not p.exists():
        print(f"NOTHING TO CHECK: coverage-map.tsv not found at {p} — created in Phase 5 (step 21)")
        return 2

    header_expected_chars = None
    rows = []
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            m = re.match(r"#\s*expected_chars\s*=\s*(\d+)", line.strip())
            if m:
                header_expected_chars = int(m.group(1))
            continue
        parts = line.split("\t")
        if len(parts) != 4:
            print(f"FAIL: {p}:{lineno}: expected 4 tab-separated fields (start,end,chars,destination), got {len(parts)}")
            return 1
        try:
            start, end, chars = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            print(f"FAIL: {p}:{lineno}: start/end/chars must be integers: {line!r}")
            return 1
        rows.append((start, end, chars, parts[3]))

    if not rows:
        print(f"FAIL: {p} has no data rows")
        return 1
    if header_expected_chars is None:
        print(f"FAIL: {p} has no '# expected_chars=<N>' header")
        return 1

    # The header is a cross-check against the hardcoded upstream constants
    # below, never the authority on its own — a header edited to agree with
    # wrong rows must not be sufficient to pass.
    errors = []
    if header_expected_chars != UPSTREAM_CARVE_EXPECTED_CHARS:
        errors.append(
            f"{p} header 'expected_chars={header_expected_chars}' disagrees with the "
            f"hardcoded upstream constant {UPSTREAM_CARVE_EXPECTED_CHARS}"
        )

    rows.sort(key=lambda r: r[0])
    prev_end = None
    for start, end, chars, dest in rows:
        if end < start:
            errors.append(f"row {dest!r}: end {end} < start {start}")
        if prev_end is not None and start != prev_end + 1:
            errors.append(f"gap or overlap between line {prev_end} and line {start} (before {dest!r})")
        prev_end = end

    if rows[0][0] != UPSTREAM_CARVE_START_LINE:
        errors.append(
            f"carve starts at line {rows[0][0]}, not the hardcoded upstream start "
            f"{UPSTREAM_CARVE_START_LINE}"
        )
    if rows[-1][1] != UPSTREAM_CARVE_END_LINE:
        errors.append(
            f"carve ends at line {rows[-1][1]}, not the hardcoded upstream end "
            f"{UPSTREAM_CARVE_END_LINE}"
        )

    total_chars = sum(r[2] for r in rows)
    if total_chars != UPSTREAM_CARVE_EXPECTED_CHARS:
        errors.append(
            f"row character sum {total_chars} != the hardcoded upstream constant "
            f"{UPSTREAM_CARVE_EXPECTED_CHARS}"
        )

    # When the upstream source checkout is reachable, independently re-derive
    # its line count and character count (same convention: lines
    # UPSTREAM_CARVE_START_LINE-UPSTREAM_CARVE_END_LINE, each joined by '\n'
    # plus a trailing '\n', matching `sed -n '7,2400p' | wc -m`) and
    # cross-check that live measurement against the hardcoded constants too
    # — if upstream itself has drifted, this port's own carve assumption is
    # stale, and that should surface here rather than only in a wrong TSV.
    # upstream_mozart_md is the resolve_upstream_mozart_md() result: an
    # explicit path, a $MOZART_UPSTREAM_CHECKOUT-derived path, or None (skip).
    if upstream_mozart_md is not None and upstream_mozart_md.exists():
        upstream_lines = upstream_mozart_md.read_text(encoding="utf-8").splitlines()
        if len(upstream_lines) != UPSTREAM_CARVE_END_LINE:
            errors.append(
                f"{upstream_mozart_md} has {len(upstream_lines)} lines, not the hardcoded "
                f"{UPSTREAM_CARVE_END_LINE}"
            )
        else:
            measured = "\n".join(upstream_lines[UPSTREAM_CARVE_START_LINE - 1:UPSTREAM_CARVE_END_LINE]) + "\n"
            if len(measured) != UPSTREAM_CARVE_EXPECTED_CHARS:
                errors.append(
                    f"{upstream_mozart_md} lines {UPSTREAM_CARVE_START_LINE}-{UPSTREAM_CARVE_END_LINE} "
                    f"measure {len(measured)} chars, not the hardcoded {UPSTREAM_CARVE_EXPECTED_CHARS}"
                )

    for e in errors:
        print(f"FAIL: {e}")
    if not errors:
        print(f"carve is total: lines {rows[0][0]}-{rows[-1][1]}, {total_chars} chars across {len(rows)} row(s)")
    return 1 if errors else 0


# --------------------------------------------------------------------------
# --check-doc-table
# --------------------------------------------------------------------------

def extract_doc_mapping_table(doc_text: str):
    """Find the primitive-mapping table in docs/COPILOT_PORT.md: the first
    pipe-table whose header row contains both 'Claude' and 'Copilot'."""
    lines = doc_text.splitlines()
    rows = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not in_table:
            if stripped.startswith("|") and "claude" in stripped.lower() and "copilot" in stripped.lower():
                in_table = True
            continue
        if not stripped.startswith("|"):
            break
        if re.match(r"^\|[\s:-]+\|", stripped):
            continue  # separator row
        cells = [c.strip().strip("`") for c in stripped.strip("|").split("|")]
        if len(cells) >= 2:
            rows.append((cells[0], cells[1]))
    return rows


def cmd_check_doc_table() -> int:
    if not DOC_PORT_PATH.exists():
        print(f"NOTHING TO CHECK: {DOC_PORT_PATH.relative_to(REPO_ROOT)} not found — created in Phase 2 (step 9)")
        return 2
    if not TOOLSETS_PATH.exists():
        print(f"NOTHING TO CHECK: {TOOLSETS_PATH.relative_to(REPO_ROOT)} not found")
        return 2

    toolsets = load_jsonc(TOOLSETS_PATH)
    vocab_pairs = {
        (row["claude"], row["copilot"] if row["copilot"] is not None else "(no analog)")
        for row in toolsets.get("claude_to_copilot", [])
    }

    doc_text = DOC_PORT_PATH.read_text(encoding="utf-8")
    doc_pairs = set(extract_doc_mapping_table(doc_text))

    if not doc_pairs:
        print(f"FAIL: no Claude/Copilot mapping table found in {DOC_PORT_PATH.relative_to(REPO_ROOT)}")
        return 1

    missing_in_doc = vocab_pairs - doc_pairs
    extra_in_doc = doc_pairs - vocab_pairs
    errors = []
    for pair in sorted(missing_in_doc):
        errors.append(f"config/toolsets.jsonc has {pair} but docs/COPILOT_PORT.md's table does not")
    for pair in sorted(extra_in_doc):
        errors.append(f"docs/COPILOT_PORT.md's table has {pair} but config/toolsets.jsonc does not")

    for e in errors:
        print(f"FAIL: {e}")
    return 1 if errors else 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", metavar="PATH", help="validate a single agent file")
    p.add_argument("--self-test", action="store_true", help="run the fixture corpus")
    p.add_argument("--forms", action="store_true", help="with --self-test: also check the frontmatter-form fixtures")
    p.add_argument("--min-agents", type=int, default=None, help="floor on the .github/agents/ roster size")
    p.add_argument("--map", metavar="PATH", help="cross-check a model-map.jsonc against the agent-file set")
    p.add_argument("--emit-runtime-reads", action="store_true", help="print the (agent, bundle-path) manifest")
    p.add_argument(
        "--check-doc-refs",
        nargs="?",
        const=True,
        default=False,
        metavar="TSV_PATH",
        help="validate a runtime-reads.tsv is fresh (defaults to the committed tests/runtime-reads.tsv; "
             "pass a path to check a scratch copy instead, e.g. for a staleness bite test)",
    )
    p.add_argument("--check-install", metavar="DIR", help="validate an installed bundle copy against the manifest")
    p.add_argument(
        "--layout",
        choices=INSTALL_LAYOUTS,
        default="repo",
        help="with --check-install: 'repo' (default, .github/agents + .github/mozart) or "
             "'user' (agents/ + mozart/, the Copilot CLI user-scope shape)",
    )
    p.add_argument("--check-carve", metavar="TSV_PATH", help="validate a coverage-map.tsv is total")
    p.add_argument(
        "--upstream-mozart-md",
        metavar="PATH",
        help="path to the upstream agents/mozart.md for the carve's live re-derivation cross-check "
             "(meaningful only with --check-carve). Defaults to $MOZART_UPSTREAM_CHECKOUT/agents/mozart.md, "
             "or is skipped when neither is set.",
    )
    p.add_argument("--check-doc-table", action="store_true", help="validate docs/COPILOT_PORT.md against config/toolsets.jsonc")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.forms and not args.self_test:
        print("usage error: --forms requires --self-test")
        return 2

    if args.self_test:
        return run_self_test(args.forms)
    if args.file:
        return cmd_file(args.file)
    if args.map:
        return cmd_map(args.map, args.min_agents)
    if args.emit_runtime_reads:
        return cmd_emit_runtime_reads()
    if args.check_doc_refs:
        path = None if args.check_doc_refs is True else args.check_doc_refs
        return cmd_check_doc_refs(path)
    if args.check_install:
        return cmd_check_install(args.check_install, args.layout)
    if args.check_carve:
        return cmd_check_carve(args.check_carve, resolve_upstream_mozart_md(args.upstream_mozart_md))
    if args.check_doc_table:
        return cmd_check_doc_table()
    return cmd_validate_all(args.min_agents)


if __name__ == "__main__":
    sys.exit(main())
