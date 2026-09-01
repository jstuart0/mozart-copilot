#!/usr/bin/env python3
"""apply_models.py — stamp .github/agents/*.agent.md `model:` frontmatter
from the canonical .github/mozart/config/model-map.jsonc, or from a shipped
preset (config/model-maps/<name>.jsonc), and validate a map's invariants.

Python 3, standard library only (D11) — reuses check_agents.py's JSONC
parser, frontmatter splitter, and agent-discovery helpers rather than
duplicating them.

Usage:
    apply_models.py                          # dry run against the canonical map
    apply_models.py --apply                  # stamp for real, .bak backups
    apply_models.py --check                  # exit 1 on drift, no writes
    apply_models.py --preset claude-bulk --apply
    apply_models.py --validate-map PATH [--check-families] [--check-tiers]
    apply_models.py --check-families          # canonical map, exit 1 if same family
    apply_models.py --check-tiers             # canonical map, exit 1 on downgrade
    apply_models.py --explain                 # per-role model/family/fallback, human-readable
    apply_models.py --check --agents-dir DIR --validate-map PATH
                                               # audit an installed (out-of-tree) pair, read-only

Invariants checked by every structural validation pass (exit 1 on any):
  - the map's `agents` block covers exactly the .github/agents/*.agent.md set
  - every role's `model` is a non-empty scalar string
  - every role named in `agents` exists in `roles`
--check-families additionally asserts roles.validation.family !=
roles.builders.family (D8). --check-tiers additionally asserts no agent is
assigned a role tier below its upstream tier (tests/fixtures/upstream-tiers.tsv;
sebastian is exempt by name — net-new, no upstream row).
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_agents import (  # noqa: E402
    REPO_ROOT,
    AGENTS_DIR,
    FrontmatterError,
    agent_stem,
    discover_agent_files,
    load_jsonc,
    split_frontmatter,
)

CANONICAL_MAP = REPO_ROOT / ".github" / "mozart" / "config" / "model-map.jsonc"
PRESETS_DIR = REPO_ROOT / "config" / "model-maps"
UPSTREAM_TIERS_TSV = REPO_ROOT / "tests" / "fixtures" / "upstream-tiers.tsv"
# The r5 DATA cross-check (non-gating) reads this when present; an installed
# copy of this repo won't have the upstream source checkout, and that's
# fine — see data_cross_check_readme_vs_frontmatter().
UPSTREAM_README = Path("/Users/jaystuart/dev/mozart-orchestration/agents/README.md")

TIER_RANK = {"haiku": 0, "sonnet": 1, "opus": 2}
ROLE_TIER = {
    "conductor": "opus",
    "deep-reviewers": "opus",
    "builders": "sonnet",
    "reviewers": "sonnet",
    "support": "sonnet",
    "fast-scan": "haiku",
    # "validation" carries no upstream-tier comparison — see SEBASTIAN_EXEMPT.
}
SEBASTIAN_EXEMPT = "sebastian"
SEBASTIAN_ROLE = "validation"


# --------------------------------------------------------------------------
# Map loading + structural validation.
# --------------------------------------------------------------------------

def resolve_map_path(path_str) -> Path:
    if path_str is None:
        return CANONICAL_MAP
    p = Path(path_str)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p


def resolve_agents_dir(path_str) -> Path:
    if path_str is None:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p


def rel_or_abs(p: Path) -> str:
    """Display a path relative to REPO_ROOT when it's under the source
    checkout; absolute otherwise. An installed (out-of-tree) file — reached
    via --agents-dir or an out-of-tree --validate-map path — makes
    Path.relative_to(REPO_ROOT) raise ValueError, which this guards against
    (bob H2)."""
    return str(p.relative_to(REPO_ROOT)) if p.is_relative_to(REPO_ROOT) else str(p)


def load_map(path: Path):
    """Returns (map_dict, errors). map_dict is {} on parse failure."""
    if not path.exists():
        return {}, [f"map file not found at {path}"]
    try:
        m = load_jsonc(path)
    except (json.JSONDecodeError, OSError) as e:
        return {}, [f"could not parse {path} as JSONC: {e}"]
    if not isinstance(m, dict):
        return {}, [f"{path}: top level must be a JSON object"]
    return m, []


def validate_structure(m: dict, agents_dir: Path = None) -> list:
    """The three baseline invariants shared by every check. Returns errors.

    agents_dir (codex M2, bob H2): validate against an installed roster
    (--agents-dir) instead of .github/agents/ — without this, an
    installed-tree check would validate map coverage against the *source
    checkout's* roster and report a clean bill for the wrong tree."""
    errors = []
    roles = m.get("roles")
    agents_block = m.get("agents")
    if not isinstance(roles, dict):
        errors.append("map is missing a 'roles' object")
        roles = {}
    if not isinstance(agents_block, dict):
        errors.append("map is missing an 'agents' object")
        agents_block = {}

    for role_name, role_def in roles.items():
        model = role_def.get("model") if isinstance(role_def, dict) else None
        if not isinstance(model, str) or not model.strip():
            errors.append(f"role '{role_name}' has no non-empty 'model' scalar")

    for agent_name, role in agents_block.items():
        if role not in roles:
            errors.append(f"agent '{agent_name}' is assigned to undefined role '{role}'")

    effective_agents_dir = agents_dir if agents_dir is not None else AGENTS_DIR
    discovered = {agent_stem(f) for f in discover_agent_files(agents_dir)}
    map_agents = set(agents_block.keys())
    for missing in sorted(discovered - map_agents):
        errors.append(f"agent file '{missing}.agent.md' exists but has no entry in the map")
    for extra in sorted(map_agents - discovered):
        # bob N9: name the directory actually searched, not a hardcoded
        # '.github/agents/' — under --agents-dir that literal would send the
        # operator looking in the source checkout for a file missing from
        # the *installed* tree.
        missing_path = effective_agents_dir / f"{extra}.agent.md"
        errors.append(f"map assigns a role to '{extra}' but no {rel_or_abs(missing_path)} exists")

    return errors


def check_families(m: dict) -> list:
    roles = m.get("roles") or {}
    validation = roles.get("validation") or {}
    builders = roles.get("builders") or {}
    v_family = validation.get("family")
    b_family = builders.get("family")
    if not v_family or not b_family:
        return ["cannot check families: roles.validation.family or roles.builders.family is missing"]
    if v_family == b_family:
        return [f"roles.validation.family ({v_family!r}) == roles.builders.family ({b_family!r}) — D8 violation"]
    return []


def load_upstream_tiers() -> dict:
    tiers = {}
    for line in UPSTREAM_TIERS_TSV.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        agent, tier = line.split("\t")
        tiers[agent] = tier
    return tiers


def data_cross_check_readme_vs_frontmatter() -> None:
    """r5's non-gating half. tests/fixtures/upstream-tiers.tsv is
    transcribed from persona frontmatter, deliberately not from
    agents/README.md's Model column, because that column is stale for
    bob/ruby/valerie. This prints one DATA line per disagreement between
    the two sources so the staleness stays visible instead of silently
    reappearing the next time someone regenerates the TSV from the README.
    Never returns errors and never affects the caller's exit code. When the
    upstream source checkout isn't present (e.g. an installed copy of this
    bundle, which never ships tests/), prints one DATA line saying the
    cross-check was skipped rather than doing nothing silently."""
    if not UPSTREAM_README.exists():
        print(f"DATA: cross-check skipped — {UPSTREAM_README} not present (expected outside the source checkout)")
        return

    readme_tiers = {}
    for line in UPSTREAM_README.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(\w[\w-]*)\s*\|.*\|\s*(opus|sonnet|haiku)\s*\|", line)
        if m:
            readme_tiers[m.group(1)] = m.group(2)

    frontmatter_tiers = load_upstream_tiers()
    for agent in sorted(set(readme_tiers) & set(frontmatter_tiers)):
        if readme_tiers[agent] != frontmatter_tiers[agent]:
            print(f"DATA {agent}: README={readme_tiers[agent]} frontmatter={frontmatter_tiers[agent]}")


def check_tiers(m: dict) -> list:
    errors = []
    agents_block = m.get("agents") or {}
    upstream = load_upstream_tiers()

    for agent, upstream_tier in upstream.items():
        role = agents_block.get(agent)
        if role is None:
            errors.append(f"'{agent}' has an upstream-tiers row but no entry in the map's 'agents' block")
            continue
        role_tier = ROLE_TIER.get(role)
        if role_tier is None:
            errors.append(f"'{agent}' is assigned role '{role}', which has no tier mapping for --check-tiers")
            continue
        if upstream_tier not in TIER_RANK:
            errors.append(f"'{agent}': unknown upstream tier {upstream_tier!r} in upstream-tiers.tsv")
            continue
        if TIER_RANK[role_tier] != TIER_RANK[upstream_tier]:
            verb = "upgrade" if TIER_RANK[role_tier] > TIER_RANK[upstream_tier] else "downgrade"
            errors.append(
                f"'{agent}' is upstream tier {upstream_tier!r} but role '{role}' is tier {role_tier!r} "
                f"— a silent {verb}"
            )

    sebastian_role = agents_block.get(SEBASTIAN_EXEMPT)
    if sebastian_role is None:
        errors.append(f"'{SEBASTIAN_EXEMPT}' has no entry in the map's 'agents' block")
    elif sebastian_role != SEBASTIAN_ROLE:
        errors.append(
            f"'{SEBASTIAN_EXEMPT}' is exempt from upstream-tier comparison but must be assigned role "
            f"'{SEBASTIAN_ROLE}' (found {sebastian_role!r})"
        )

    known_agents = set(upstream) | {SEBASTIAN_EXEMPT}
    for agent in sorted(set(agents_block) - known_agents):
        errors.append(f"'{agent}' is in the map but has no upstream-tiers.tsv row and is not the named exemption")

    return errors


# --------------------------------------------------------------------------
# --explain
# --------------------------------------------------------------------------

def cmd_explain(path_str) -> int:
    path = resolve_map_path(path_str)
    m, errors = load_map(path)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    roles = m.get("roles") or {}
    print(f"map: {rel_or_abs(path)}")
    for role_name in sorted(roles):
        r = roles[role_name]
        print(f"  {role_name:16s} model={r.get('model')!r:24s} family={r.get('family')!r:10s} fallback={r.get('fallback')!r}")
    return 0


# --------------------------------------------------------------------------
# --check / --apply (stamping)
# --------------------------------------------------------------------------

def stamp_model_line(text: str, new_model: str) -> str:
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        raise FrontmatterError("missing opening '---' delimiter on line 1")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            end_idx = i
            break
    if end_idx is None:
        raise FrontmatterError("unclosed frontmatter: no closing '---' delimiter found")
    for i in range(1, end_idx):
        if lines[i].startswith("model:"):
            lines[i] = f"model: {new_model}"
            return "\n".join(lines)
    raise FrontmatterError("no top-level 'model:' key found in frontmatter")


def current_model(text: str):
    _, body = split_frontmatter(text)  # noqa: F841 — validates the delimiters
    for line in text.split("\n"):
        if line.startswith("model:"):
            return line[len("model:"):].strip()
    return None


def compute_diffs(m: dict, agents_dir: Path = None):
    """Returns (diffs, errors). diffs: list of (file, stem, old_model, new_model)."""
    roles = m.get("roles") or {}
    agents_block = m.get("agents") or {}
    diffs, errors = [], []
    for f in discover_agent_files(agents_dir):
        stem = agent_stem(f)
        role = agents_block.get(stem)
        if role is None:
            continue
        role_def = roles.get(role) or {}
        new_model = role_def.get("model")
        if not new_model:
            continue
        try:
            text = f.read_text(encoding="utf-8")
            old_model = current_model(text)
        except FrontmatterError as e:
            errors.append(f"{rel_or_abs(f)}: {e}")
            continue
        if old_model != new_model:
            diffs.append((f, stem, old_model, new_model))
    return diffs, errors


def cmd_check(path_str=None, agents_dir: Path = None) -> int:
    path = resolve_map_path(path_str)
    m, errors = load_map(path)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    struct_errors = validate_structure(m, agents_dir)
    for e in struct_errors:
        print(f"FAIL: {e}")

    diffs, diff_errors = compute_diffs(m, agents_dir)
    for e in diff_errors:
        print(f"FAIL: {e}")
    for f, stem, old, new in diffs:
        print(f"DRIFT {rel_or_abs(f)}: model: {old} != map's {new!r} for role of '{stem}'")

    return 1 if (struct_errors or diff_errors or diffs) else 0


def cmd_stamp(apply: bool, preset: str) -> int:
    if preset:
        preset_path = PRESETS_DIR / f"{preset}.jsonc"
        if not preset_path.exists():
            print(f"FAIL: no such preset {preset_path.relative_to(REPO_ROOT)}")
            return 1
        preset_map, preset_errors = load_map(preset_path)
        if preset_errors:
            for e in preset_errors:
                print(f"FAIL: {e}")
            return 1
        struct_errors = validate_structure(preset_map)
        if struct_errors:
            for e in struct_errors:
                print(f"FAIL: preset '{preset}': {e}")
            return 1
        preset_family_errors = check_families(preset_map)
        preset_tier_errors = check_tiers(preset_map)
        if preset_family_errors or preset_tier_errors:
            for e in preset_family_errors + preset_tier_errors:
                print(f"FAIL: preset '{preset}': {e}")
            print(f"refusing to stamp: preset '{preset}' fails validation (see above) — the canonical map is left unchanged")
            return 1
        if apply:
            shutil.copy2(preset_path, CANONICAL_MAP)
            print(f"copied {preset_path.relative_to(REPO_ROOT)} -> {CANONICAL_MAP.relative_to(REPO_ROOT)}")
        else:
            print(f"[dry run] would copy {preset_path.relative_to(REPO_ROOT)} -> {CANONICAL_MAP.relative_to(REPO_ROOT)}")

    m, errors = load_map(CANONICAL_MAP)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    struct_errors = validate_structure(m)
    if struct_errors:
        for e in struct_errors:
            print(f"FAIL: {e}")
        return 1

    # Refuse to stamp a map that fails an invariant, whether or not it just
    # arrived via --preset. Structural validity alone isn't enough — a
    # structurally-fine preset can still violate D8 (same-family
    # validation) or silently retier someone; catch both before any
    # frontmatter write, not after.
    family_errors = check_families(m)
    tier_errors = check_tiers(m)
    if family_errors or tier_errors:
        for e in family_errors + tier_errors:
            print(f"FAIL: {e}")
        print("refusing to stamp: the active map fails validation (see above)")
        return 1

    diffs, diff_errors = compute_diffs(m)
    for e in diff_errors:
        print(f"FAIL: {e}")
    if diff_errors:
        return 1

    if not diffs:
        print("no drift: every agent's model: already matches the active map")
        return 0

    for f, stem, old, new in diffs:
        action = "stamping" if apply else "[dry run] would stamp"
        print(f"{action} {f.relative_to(REPO_ROOT)}: model: {old} -> {new}")
        if apply:
            text = f.read_text(encoding="utf-8")
            backup = f.with_suffix(f.suffix + ".bak")
            backup.write_text(text, encoding="utf-8")
            new_text = stamp_model_line(text, new)
            f.write_text(new_text, encoding="utf-8")

    return 0


# --------------------------------------------------------------------------
# --validate-map / --check-families / --check-tiers dispatch
# --------------------------------------------------------------------------

def run_map_checks(path_str, do_families: bool, do_tiers: bool, agents_dir: Path = None) -> int:
    path = resolve_map_path(path_str)
    m, errors = load_map(path)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1

    all_errors = list(validate_structure(m, agents_dir))
    if do_families:
        all_errors += check_families(m)
    if do_tiers:
        all_errors += check_tiers(m)
        # Non-gating: never contributes to all_errors / the exit code.
        data_cross_check_readme_vs_frontmatter()

    for e in all_errors:
        print(f"FAIL: {e}")
    if not all_errors:
        print(f"OK: {rel_or_abs(path)}")
    return 1 if all_errors else 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", action="store_true", help="write changes for real (with .bak backups); default is dry run")
    p.add_argument("--check", action="store_true", help="exit 1 if any agent's model: has drifted from the canonical map")
    p.add_argument("--preset", metavar="NAME", help="copy config/model-maps/<NAME>.jsonc over the canonical map, then stamp")
    p.add_argument("--validate-map", metavar="PATH", help="validate PATH instead of the canonical map (read-only, no stamping)")
    p.add_argument("--check-families", action="store_true", help="assert roles.validation.family != roles.builders.family (D8)")
    p.add_argument("--check-tiers", action="store_true", help="assert no agent's role sits below its upstream tier")
    p.add_argument("--explain", action="store_true", help="print each role's model/family/fallback")
    p.add_argument(
        "--agents-dir",
        metavar="DIR",
        help="validate against an installed agents directory (e.g. <copilot-home>/agents) instead of "
             ".github/agents/. Read-only — not valid with --apply.",
    )
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.check and args.apply:
        print("usage error: --check and --apply are mutually exclusive")
        return 2
    if args.preset and args.validate_map:
        print("usage error: --preset and --validate-map are mutually exclusive")
        return 2
    if args.agents_dir and args.apply:
        print("usage error: --agents-dir is read-only and not valid with --apply (--apply remains repo-only)")
        return 2

    # Every read-only check below composes in one invocation instead of a
    # first-matching-flag-wins dispatch (the same class of bug as Phase 6's
    # check_agents.py --map/--min-agents gap, found again here by codex r2).
    # --validate-map PATH selects which map every one of them runs against;
    # None means the canonical map. --agents-dir DIR does the same for which
    # agent-definitions roster every one of them validates against; None
    # means .github/agents/.
    active_map_path = args.validate_map
    active_agents_dir = resolve_agents_dir(args.agents_dir)
    ran_a_check = False
    exit_code = 0

    if args.explain:
        rc = cmd_explain(active_map_path)
        if rc != 0:
            exit_code = 1
        ran_a_check = True

    if args.validate_map or args.check_families or args.check_tiers:
        rc = run_map_checks(active_map_path, args.check_families, args.check_tiers, active_agents_dir)
        if rc != 0:
            exit_code = 1
        ran_a_check = True

    if args.check:
        rc = cmd_check(active_map_path, active_agents_dir)
        if rc != 0:
            exit_code = 1
        ran_a_check = True

    if ran_a_check:
        return exit_code

    return cmd_stamp(apply=args.apply, preset=args.preset)


if __name__ == "__main__":
    sys.exit(main())
