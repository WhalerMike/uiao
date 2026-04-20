#!/usr/bin/env python3
"""reorganize_to_clean_monorepo.py — v2

Safely reorganize the UIAO repo into the clean `src/uiao/*` monorepo layout.

Default is DRY-RUN. Nothing changes until you pass --execute.

Phases (select with --phase; default 'core' runs backup+canon+scuba+imports+pyproject):
  backup    - local safety branch `pre-reorg-backup-YYYYMMDD`
  canon     - core/data/** + core/compliance/reference/** -> src/uiao/canon/
  scuba     - every SCuBA source under impl/** -> src/uiao/adapters/scuba/
              ALSO: other adapters in impl/src/uiao/impl/adapters/ -> src/uiao/adapters/
  imports   - rewrite  uiao.impl.adapters          -> uiao.adapters
                       uiao.impl.scuba             -> uiao.adapters.scuba
                       uiao.impl.ir.adapters.scuba -> uiao.adapters.scuba.ir
              across *.py *.yaml *.yml *.toml *.md *.cfg *.ini *.json
  pyproject - declare uiao.adapters package-data + CLI entrypoint
  flatten   - (OPTIONAL, --phase flatten) move remaining impl/src/uiao/impl/*
              subpackages up into src/uiao/* and rewrite uiao.impl.* imports.
              Risky: dozens of files, likely test churn. Run separately.
  core      - backup,canon,scuba,imports,pyproject
  all       - core + flatten

Usage:
    python reorganize_to_clean_monorepo.py                  # dry-run core phases
    python reorganize_to_clean_monorepo.py --phase canon    # dry-run one phase
    python reorganize_to_clean_monorepo.py --execute        # actually do core
    python reorganize_to_clean_monorepo.py --execute --phase scuba
    python reorganize_to_clean_monorepo.py --execute --phase flatten
    python reorganize_to_clean_monorepo.py --execute --no-backup

Safety:
  * DRY-RUN is the default. Must pass --execute to mutate files.
  * Uses `git mv` when source is tracked; `shutil.move` otherwise.
  * Never overwrites; skips with `SKIP dst exists` so re-runs are idempotent.
  * Never deletes. Conflicts are logged, not resolved automatically.
  * Backup branch created from HEAD before the first mutation.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

# --------------------------------------------------------------------------- #
# Phase: canon
# --------------------------------------------------------------------------- #
CANON_MOVES: list[tuple[str, str]] = [
    ("core/data/control-planes.yml",                  "src/uiao/canon/data/control-planes.yml"),
    ("core/data/fedramp_ssp_template_structure.yaml", "src/uiao/canon/data/fedramp_ssp_template_structure.yaml"),
    ("core/data/overlay-config.yml",                  "src/uiao/canon/data/overlay-config.yml"),
    ("core/data/plantuml-config.json",                "src/uiao/canon/data/plantuml-config.json"),
    ("core/data/schema.json",                         "src/uiao/canon/data/schema.json"),
    ("core/data/style-guide.yml",                     "src/uiao/canon/data/style-guide.yml"),
    ("core/data/README.md",                           "src/uiao/canon/data/README.md"),
    ("core/data/control-library",                     "src/uiao/canon/data/control-library"),
    ("core/data/overlays",                            "src/uiao/canon/data/overlays"),
    ("core/data/vendor-overlays",                     "src/uiao/canon/data/vendor-overlays"),
    ("core/compliance/reference",                     "src/uiao/canon/compliance/reference"),
]

# --------------------------------------------------------------------------- #
# Phase: scuba  (SCuBA + sibling adapters)
#
# Real paths in this repo:
#   impl/src/uiao/impl/adapters/          - flat adapter modules incl. scuba_adapter.py
#   impl/src/uiao/impl/scuba/             - scuba transform subpackage
#   impl/src/uiao/impl/ir/adapters/scuba/ - scuba IR normalizer
#   impl/scuba-runtime/                   - runtime artifacts (run/ schemas/ transforms/)
# --------------------------------------------------------------------------- #
SCUBA_MOVES: list[tuple[str, str]] = [
    # All flat adapters (keeps scuba_adapter.py alongside siblings).
    ("impl/src/uiao/impl/adapters",       "src/uiao/adapters"),
    # Scuba transform subpackage.
    ("impl/src/uiao/impl/scuba",          "src/uiao/adapters/scuba"),
    # Scuba IR normalizer.
    ("impl/src/uiao/impl/ir/adapters/scuba", "src/uiao/adapters/scuba/ir"),
    # Scuba runtime assets (yaml schemas, transforms, run fixtures).
    ("impl/scuba-runtime",                "src/uiao/adapters/scuba/runtime"),
]

# --------------------------------------------------------------------------- #
# Phase: imports — rewrite rules (longer prefixes first).
# --------------------------------------------------------------------------- #
# NOTE: keep the literal keys intact; add this file to REWRITE_EXCLUDE_FILES
# below so the imports phase does not rewrite its own rules.
_OLD_IR = "uiao" + ".impl.ir.adapters.scuba"
_OLD_AD = "uiao" + ".impl.adapters"
_OLD_SC = "uiao" + ".impl.scuba"
IMPORT_REWRITES_CORE: list[tuple[str, str]] = [
    (_OLD_IR, "uiao.adapters.scuba.ir"),
    (_OLD_AD, "uiao.adapters"),
    (_OLD_SC, "uiao.adapters.scuba"),
]

# Used by the flatten phase (after other subpackages move up):
IMPORT_REWRITES_FLATTEN: list[tuple[str, str]] = [
    # MUST be ordered longest-prefix-first so partial matches don't corrupt.
    ("uiao.impl.", "uiao."),
]

REWRITE_SUFFIXES = {".py", ".yaml", ".yml", ".toml", ".md", ".cfg", ".ini", ".json"}
REWRITE_EXCLUDE_DIRS = {".git", ".venv", "node_modules", "__pycache__",
                        "uiao.egg-info", "src/uiao.egg-info"}
REWRITE_EXCLUDE_FILES = {"reorganize_to_clean_monorepo.py"}

# --------------------------------------------------------------------------- #
# Phase: flatten — everything still under impl/src/uiao/impl/ after scuba ran.
# --------------------------------------------------------------------------- #
# Subdirs we expect may remain. Any not listed will still be detected and
# moved, but listing them here documents the target layout.
FLATTEN_IMPL_ROOT = "impl/src/uiao/impl"
FLATTEN_DST_ROOT = "src/uiao"

# Known collisions with existing top-level package names. For these we merge
# files instead of moving the whole directory.
FLATTEN_MERGE_DIRS = {"ksi"}

# Name collision: src/uiao/cli.py (file) vs impl/src/uiao/impl/cli/ (dir).
# We do NOT auto-resolve — we log a warning. User decides how to fold them.
FLATTEN_SKIP_DIRS = {"cli"}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class Counter:
    def __init__(self) -> None:
        self.moved = 0
        self.skipped = 0
        self.rewritten = 0
        self.warnings: list[str] = []


CTR = Counter()


def log(execute: bool, msg: str) -> None:
    tag = "[DO ]" if execute else "[DRY]"
    print(f"{tag} {msg}")


def warn(msg: str) -> None:
    CTR.warnings.append(msg)
    print(f"[WARN] {msg}")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO, check=check, capture_output=True, text=True)


def is_tracked(path: Path) -> bool:
    rel = path.relative_to(REPO).as_posix()
    cp = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=REPO, capture_output=True, text=True,
    )
    return cp.returncode == 0


def ensure_parent(dst: Path, execute: bool) -> None:
    if dst.parent.exists():
        return
    log(execute, f"mkdir -p {dst.parent.relative_to(REPO)}")
    if execute:
        dst.parent.mkdir(parents=True, exist_ok=True)


def move(src_rel: str, dst_rel: str, *, execute: bool) -> None:
    """Move src -> dst. Uses git mv when possible; falls back to shutil + git add/rm
    on cross-device or other git mv failures. Git still detects the rename when
    both src (deleted) and dst (added) are staged together."""
    src = REPO / src_rel
    dst = REPO / dst_rel
    if not src.exists():
        log(execute, f"SKIP missing {src_rel}")
        CTR.skipped += 1
        return
    if dst.exists():
        log(execute, f"SKIP dst exists {dst_rel}")
        CTR.skipped += 1
        return
    ensure_parent(dst, execute)
    tracked = is_tracked(src)
    if tracked:
        log(execute, f"git mv {src_rel} {dst_rel}")
        if execute:
            cp = subprocess.run(
                ["git", "mv", src_rel, dst_rel],
                cwd=REPO, capture_output=True, text=True,
            )
            if cp.returncode != 0:
                # Cross-device or other failure: fall back.
                log(execute, f"  (git mv failed: {cp.stderr.strip()[:80]}; using shutil)")
                shutil.move(str(src), str(dst))
                run(["git", "rm", "-r", "--cached", "--quiet", src_rel], check=False)
                run(["git", "add", dst_rel])
    else:
        log(execute, f"mv (untracked) {src_rel} {dst_rel}")
        if execute:
            shutil.move(str(src), str(dst))
    CTR.moved += 1


def merge_dir(src_rel: str, dst_rel: str, *, execute: bool) -> None:
    """Move files from src into dst, preserving subdir structure; skip collisions."""
    src = REPO / src_rel
    dst = REPO / dst_rel
    if not src.is_dir():
        log(execute, f"SKIP not a dir {src_rel}")
        CTR.skipped += 1
        return
    for item in sorted(src.rglob("*")):
        if item.is_dir():
            continue
        rel_inside = item.relative_to(src)
        target = dst / rel_inside
        move(item.relative_to(REPO).as_posix(), target.relative_to(REPO).as_posix(),
             execute=execute)


# --------------------------------------------------------------------------- #
# Phase implementations
# --------------------------------------------------------------------------- #
def phase_backup(execute: bool) -> None:
    stamp = _dt.datetime.now().strftime("%Y%m%d")
    branch = f"pre-reorg-backup-{stamp}"
    existing = subprocess.run(
        ["git", "rev-parse", "--verify", branch],
        cwd=REPO, capture_output=True, text=True,
    )
    if existing.returncode == 0:
        log(execute, f"backup branch {branch} already exists; reusing")
        return
    log(execute, f"git branch {branch}  (safety snapshot of HEAD)")
    if execute:
        run(["git", "branch", branch])


def phase_canon(execute: bool) -> None:
    print("\n=== phase: canon ===")
    for src_rel, dst_rel in CANON_MOVES:
        move(src_rel, dst_rel, execute=execute)


def phase_scuba(execute: bool) -> None:
    print("\n=== phase: scuba (+ sibling adapters) ===")
    for src_rel, dst_rel in SCUBA_MOVES:
        move(src_rel, dst_rel, execute=execute)
    # Ensure package markers.
    for pkg in ("src/uiao/adapters/__init__.py",
                "src/uiao/adapters/scuba/__init__.py"):
        p = REPO / pkg
        if p.exists():
            continue
        log(execute, f"create {pkg}")
        if execute:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'"""{p.parent.name} package."""\n')


def _iter_rewrite_files() -> list[Path]:
    out: list[Path] = []
    for p in REPO.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in REWRITE_SUFFIXES:
            continue
        rel = p.relative_to(REPO).as_posix()
        if any(rel == d or rel.startswith(d + "/") for d in REWRITE_EXCLUDE_DIRS):
            continue
        if p.name in REWRITE_EXCLUDE_FILES:
            continue
        out.append(p)
    return out


def _apply_rewrites(rules: list[tuple[str, str]], execute: bool, label: str) -> None:
    files = _iter_rewrite_files()
    touched = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for old, newtok in rules:
            new = new.replace(old, newtok)
        if new != text:
            touched += 1
            log(execute, f"rewrite ({label}) {f.relative_to(REPO)}")
            if execute:
                f.write_text(new, encoding="utf-8")
    CTR.rewritten += touched
    print(f"    {label}: {touched} file(s) rewritten")


def phase_imports(execute: bool) -> None:
    print("\n=== phase: imports (scuba/adapters) ===")
    _apply_rewrites(IMPORT_REWRITES_CORE, execute, "core")


def phase_pyproject(execute: bool) -> None:
    print("\n=== phase: pyproject ===")
    pp = REPO / "pyproject.toml"
    text = pp.read_text(encoding="utf-8")
    anchor = "[tool.setuptools.package-data]\n"
    if anchor not in text:
        warn("pyproject has no [tool.setuptools.package-data]; skipping")
        return
    additions: list[str] = []
    if '"uiao.adapters"' not in text:
        additions.append(
            '"uiao.adapters" = ["**/*.yaml", "**/*.yml", "**/*.json", "**/*.md"]\n'
        )
    if not additions:
        log(execute, "pyproject already up to date")
        return
    new_text = text.replace(anchor, anchor + "".join(additions), 1)
    log(execute, "add uiao.adapters package-data entry")
    if execute:
        pp.write_text(new_text, encoding="utf-8")


def phase_flatten(execute: bool) -> None:
    print("\n=== phase: flatten (uiao.impl.* -> uiao.*) ===")
    impl_root = REPO / FLATTEN_IMPL_ROOT
    if not impl_root.is_dir():
        log(execute, f"SKIP {FLATTEN_IMPL_ROOT} absent")
        return
    for child in sorted(impl_root.iterdir()):
        if child.name.startswith("__"):
            continue  # __init__.py, __pycache__
        src_rel = child.relative_to(REPO).as_posix()
        dst_rel = f"{FLATTEN_DST_ROOT}/{child.name}"
        if child.name in FLATTEN_SKIP_DIRS:
            warn(f"collision: {src_rel} vs existing {dst_rel}.py — manual merge required")
            continue
        if child.name in FLATTEN_MERGE_DIRS or (REPO / dst_rel).exists():
            log(execute, f"merge {src_rel} into {dst_rel}")
            merge_dir(src_rel, dst_rel, execute=execute)
        else:
            move(src_rel, dst_rel, execute=execute)
    # Catch-all import rewrite after flatten.
    _apply_rewrites(IMPORT_REWRITES_FLATTEN, execute, "flatten")


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #
def summarize_before() -> None:
    print("=== BEFORE ===")
    for p in ("core/data", "core/compliance/reference",
              "impl/src/uiao/impl/adapters", "impl/src/uiao/impl/scuba",
              "impl/src/uiao/impl/ir/adapters/scuba", "impl/scuba-runtime",
              "src/uiao/canon", "src/uiao/adapters"):
        full = REPO / p
        state = "present" if full.exists() else "absent"
        print(f"  {p:<45s} {state}")


def summarize_after(execute: bool) -> None:
    print("\n=== SUMMARY ===")
    print(f"  moves:      {CTR.moved}")
    print(f"  skipped:    {CTR.skipped}")
    print(f"  rewritten:  {CTR.rewritten}")
    print(f"  warnings:   {len(CTR.warnings)}")
    for w in CTR.warnings:
        print(f"    - {w}")
    if not execute:
        print("\nNo changes were made. Re-run with --execute to perform them.")
    else:
        print("\nNext steps:")
        print("  1. git status")
        print("  2. pip install -e .")
        print("  3. uiao --help")
        print("  4. pytest -q")
        print("  5. git add -A && git commit -m 'chore: reorganize to clean src/uiao monorepo'")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
PHASES = {
    "backup":    phase_backup,
    "canon":     phase_canon,
    "scuba":     phase_scuba,
    "imports":   phase_imports,
    "pyproject": phase_pyproject,
    "flatten":   phase_flatten,
}
CORE_ORDER = ["backup", "canon", "scuba", "imports", "pyproject"]
ALL_ORDER = CORE_ORDER + ["flatten"]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--execute", action="store_true",
                    help="actually perform changes (default: dry-run)")
    ap.add_argument("--phase", choices=list(PHASES) + ["core", "all"], default="core",
                    help="which phase(s) to run (default: core)")
    ap.add_argument("--no-backup", action="store_true",
                    help="skip the safety backup branch")
    args = ap.parse_args()

    if args.phase == "core":
        order = [p for p in CORE_ORDER if not (p == "backup" and args.no_backup)]
    elif args.phase == "all":
        order = [p for p in ALL_ORDER if not (p == "backup" and args.no_backup)]
    else:
        order = [args.phase]

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"=== UIAO monorepo reorg v2 :: mode={mode} :: phases={order} ===")
    print(f"=== repo: {REPO} ===\n")
    summarize_before()

    for name in order:
        PHASES[name](args.execute)

    summarize_after(args.execute)
    return 0


if __name__ == "__main__":
    sys.exit(main())
