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
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_agents import (  # noqa: E402
    REPO_ROOT,
    FrontmatterError,
    agent_stem,
    check_model_ids,
    discover_agent_files,
    load_jsonc,
    rel_or_abs,
    split_frontmatter,
    validate_map_structure,
)

CANONICAL_MAP = REPO_ROOT / ".github" / "mozart" / "config" / "model-map.jsonc"
PRESETS_DIR = REPO_ROOT / "config" / "model-maps"
UPSTREAM_TIERS_TSV = REPO_ROOT / "tests" / "fixtures" / "upstream-tiers.tsv"
# The r5 DATA cross-check (non-gating) reads the upstream agents/README.md
# when a source checkout is reachable; an installed copy of this repo won't
# have that checkout, and that's fine — see
# data_cross_check_readme_vs_frontmatter(). The path is no longer hardcoded
# to one person's layout (C1): it is resolved per invocation from an
# explicit flag or the shared $MOZART_UPSTREAM_CHECKOUT env var, defaulting
# to None = skip. resolve_upstream_readme() below is the single resolver.
UPSTREAM_README_SUBPATH = "agents/README.md"


def resolve_upstream_readme(explicit: str = None):
    """Resolve the optional upstream agents/README.md for the non-gating DATA
    cross-check. Order: explicit --upstream-readme flag →
    $MOZART_UPSTREAM_CHECKOUT joined with agents/README.md → None (skip).
    None reaches data_cross_check_readme_vs_frontmatter()'s existing
    skip branch with no new code path (D-A option B)."""
    if explicit:
        return Path(explicit)
    checkout = os.environ.get("MOZART_UPSTREAM_CHECKOUT")
    if checkout:
        return Path(checkout) / UPSTREAM_README_SUBPATH
    return None

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


# validate_structure() lived here; deleted in P7 (D-B.2). Its logic — plus the
# orphan-role check cmd_map used to own — now lives in
# check_agents.validate_map_structure(), the single shared structural validator
# imported above. The import edge stays one-directional (apply_models.py ->
# check_agents.py); this module never gains a reverse dependency.


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


def data_cross_check_readme_vs_frontmatter(upstream_readme=None) -> None:
    """r5's non-gating half. tests/fixtures/upstream-tiers.tsv is
    transcribed from persona frontmatter, deliberately not from
    agents/README.md's Model column, because that column is stale for
    bob/ruby/valerie. This prints one DATA line per disagreement between
    the two sources so the staleness stays visible instead of silently
    reappearing the next time someone regenerates the TSV from the README.
    Never returns errors and never affects the caller's exit code. When no
    upstream source checkout is configured or reachable (e.g. an installed
    copy of this bundle, which never ships tests/), prints one DATA line
    saying the cross-check was skipped rather than doing nothing silently.
    `upstream_readme` is the resolve_upstream_readme() result: an explicit
    path, a $MOZART_UPSTREAM_CHECKOUT-derived path, or None."""
    if upstream_readme is None:
        print("DATA: cross-check skipped — no upstream source checkout configured "
              "(expected outside the source checkout; set --upstream-readme or "
              "$MOZART_UPSTREAM_CHECKOUT to enable)")
        return
    if not upstream_readme.exists():
        print(f"DATA: cross-check skipped — {upstream_readme} not present (expected outside the source checkout)")
        return

    readme_tiers = {}
    for line in upstream_readme.read_text(encoding="utf-8").splitlines():
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
    struct_errors = validate_map_structure(m, agents_dir)
    for e in struct_errors:
        print(f"FAIL: {e}")
    # R1 live-model-ID gate (kept separate from validate_map_structure per
    # D-B.2; absolute, not preset-relative, so safe on every map).
    model_errors = check_model_ids(m)
    for e in model_errors:
        print(f"FAIL: {e}")

    diffs, diff_errors = compute_diffs(m, agents_dir)
    for e in diff_errors:
        print(f"FAIL: {e}")
    for f, stem, old, new in diffs:
        print(f"DRIFT {rel_or_abs(f)}: model: {old} != map's {new!r} for role of '{stem}'")

    return 1 if (struct_errors or model_errors or diff_errors or diffs) else 0


def cmd_stamp(apply: bool, preset: str) -> int:
    if preset:
        # --preset names a bare map under config/model-maps/, never a path
        # (xander L3): reject any separator or parent-dir token before it can
        # reach PRESETS_DIR / f"{preset}.jsonc", or "../../some/map" escapes the
        # preset directory and, if it validates, gets stamped over the canonical
        # map. Constrain to a filename component; resolution happens after.
        if "/" in preset or "\\" in preset or ".." in preset or preset != os.path.basename(preset):
            print(f"FAIL: --preset must be a bare preset name, not a path (got '{preset}')")
            return 1
        preset_path = PRESETS_DIR / f"{preset}.jsonc"
        if not preset_path.exists():
            print(f"FAIL: no such preset {preset_path.relative_to(REPO_ROOT)}")
            return 1
        preset_map, preset_errors = load_map(preset_path)
        if preset_errors:
            for e in preset_errors:
                print(f"FAIL: {e}")
            return 1
        struct_errors = validate_map_structure(preset_map)
        if struct_errors:
            for e in struct_errors:
                print(f"FAIL: preset '{preset}': {e}")
            return 1
        preset_family_errors = check_families(preset_map)
        preset_tier_errors = check_tiers(preset_map)
        preset_model_errors = check_model_ids(preset_map)
        if preset_family_errors or preset_tier_errors or preset_model_errors:
            for e in preset_family_errors + preset_tier_errors + preset_model_errors:
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
    struct_errors = validate_map_structure(m)
    if struct_errors:
        for e in struct_errors:
            print(f"FAIL: {e}")
        return 1

    # Refuse to stamp a map that fails an invariant, whether or not it just
    # arrived via --preset. Structural validity alone isn't enough — a
    # structurally-fine preset can still violate D8 (same-family
    # validation), silently retier someone, or carry a dead / mislabeled
    # model ID (R1 / xander M1: without check_model_ids here, --preset … --apply
    # would copy a dead ID into the canonical map and stamp it into 22
    # personas while the read-path gate watched). Catch all three before any
    # frontmatter write, not after.
    family_errors = check_families(m)
    tier_errors = check_tiers(m)
    model_errors = check_model_ids(m)
    if family_errors or tier_errors or model_errors:
        for e in family_errors + tier_errors + model_errors:
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

def run_map_checks(path_str, do_families: bool, do_tiers: bool, agents_dir: Path = None, upstream_readme=None) -> int:
    path = resolve_map_path(path_str)
    m, errors = load_map(path)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1

    all_errors = list(validate_map_structure(m, agents_dir))
    # R1 live-model-ID gate — always runs (absolute validity, not a modifier),
    # so --validate-map with no flags still rejects a dead ID or a family
    # mislabel. Kept a separate function from validate_map_structure per D-B.2.
    all_errors += check_model_ids(m)
    if do_families:
        all_errors += check_families(m)
    if do_tiers:
        all_errors += check_tiers(m)
        # Non-gating: never contributes to all_errors / the exit code.
        data_cross_check_readme_vs_frontmatter(upstream_readme)

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
        "--upstream-readme",
        metavar="PATH",
        help="path to the upstream agents/README.md for the non-gating DATA cross-check "
             "(meaningful only with --check-tiers). Defaults to $MOZART_UPSTREAM_CHECKOUT/agents/README.md, "
             "or is skipped when neither is set.",
    )
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
    # sebastian HIGH-6: write actions (--apply, --preset) must PARTICIPATE in
    # the compatibility matrix, not silently lose to a first-flag-wins dispatch.
    # The read checks below (--check / --explain / --validate-map /
    # --check-families / --check-tiers) set ran_a_check and RETURN before
    # cmd_stamp is ever reached — so `--preset X --apply --check-tiers`,
    # `--preset X --check`, and `--apply --explain` used to run only the read
    # check against the CURRENT canonical map and silently ignore the requested
    # preset/write. This is the exact H1 defect class the campaign exists to
    # kill. Reject any read/write mix outright (exit 2) rather than pick a
    # surprising order: a write and a read-only assertion are different
    # intentions and combining them is always a mistake.
    write_requested = args.apply or (args.preset is not None)
    read_requested = (
        args.check
        or args.explain
        or (args.validate_map is not None)
        or args.check_families
        or args.check_tiers
    )
    if write_requested and read_requested:
        write_flag = "--apply" if args.apply else "--preset"
        read_flags = [
            name
            for name, on in (
                ("--check", args.check),
                ("--explain", args.explain),
                ("--validate-map", args.validate_map is not None),
                ("--check-families", args.check_families),
                ("--check-tiers", args.check_tiers),
            )
            if on
        ]
        print(
            f"usage error: {write_flag} (a write action) cannot be combined with "
            f"read-only check{'s' if len(read_flags) > 1 else ''} {', '.join(read_flags)} — "
            "run the write and the checks as separate invocations so neither is silently ignored"
        )
        return 2
    # P6/Y6 modifier compatibility matrix: --upstream-readme is only meaningful
    # with --check-tiers (data_cross_check_readme_vs_frontmatter runs solely
    # under do_tiers). Supplying it with any other action would accept-and-
    # discard it — the silently-ignored-modifier defect this campaign kills.
    if args.upstream_readme is not None and not args.check_tiers:
        print(
            "usage error: --upstream-readme is only meaningful with --check-tiers "
            "(the upstream README DATA cross-check runs solely under --check-tiers)"
        )
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
    active_upstream_readme = resolve_upstream_readme(args.upstream_readme)
    ran_a_check = False
    exit_code = 0

    if args.explain:
        rc = cmd_explain(active_map_path)
        if rc != 0:
            exit_code = 1
        ran_a_check = True

    if args.validate_map or args.check_families or args.check_tiers:
        rc = run_map_checks(active_map_path, args.check_families, args.check_tiers, active_agents_dir, active_upstream_readme)
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
