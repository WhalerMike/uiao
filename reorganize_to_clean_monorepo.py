#!/usr/bin/env python3
"""reorganize_to_clean_monorepo.py

Safely reorganize the UIAO repo into the clean `src/uiao/*` monorepo layout.

Default is DRY-RUN. Nothing changes until you pass --apply.

Phases:
  backup    - create a local backup branch `pre-reorg/<timestamp>` from HEAD
  canon     - move YAML/JSON SSOT from `core/data/` and
              `core/compliance/reference/` under `src/uiao/canon/`
  adapters  - move `impl/src/uiao/impl/adapters/` -> `src/uiao/adapters/`
              move `impl/src/uiao/impl/scuba/`    -> `src/uiao/adapters/scuba/`
  imports   - rewrite  uiao.impl.adapters -> uiao.adapters
                       uiao.impl.scuba    -> uiao.adapters.scuba
              across *.py *.yaml *.yml *.toml *.md *.cfg *.ini
  pyproject - add uiao.adapters to package-data globs (already covers code)
  all       - backup -> canon -> adapters -> imports -> pyproject

Usage:
    python reorganize_to_clean_monorepo.py                # dry-run everything
    python reorganize_to_clean_monorepo.py --phase canon  # dry-run one phase
    python reorganize_to_clean_monorepo.py --apply        # really do it
    python reorganize_to_clean_monorepo.py --apply --phase canon
    python reorganize_to_clean_monorepo.py --apply --no-backup  # skip safety branch

Rules:
  * Uses `git mv` so rename history is preserved. Falls back to shutil for
    untracked files.
  * Never overwrites an existing destination; logs SKIP and continues.
  * Prints every action; dry-run prefix is `[DRY]`, apply prefix is `[DO ]`.
  * Idempotent: re-running after a partial run is safe.
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
# File moves for the canon phase.
#   src (relative to repo root)  ->  dst (relative to repo root)
# Directories are moved wholesale; individual files are moved one by one.
# --------------------------------------------------------------------------- #
CANON_MOVES: list[tuple[str, str]] = [
    # Everything under core/data/ becomes src/uiao/canon/data/
    ("core/data/control-planes.yml",                 "src/uiao/canon/data/control-planes.yml"),
    ("core/data/fedramp_ssp_template_structure.yaml","src/uiao/canon/data/fedramp_ssp_template_structure.yaml"),
    ("core/data/overlay-config.yml",                 "src/uiao/canon/data/overlay-config.yml"),
    ("core/data/plantuml-config.json",               "src/uiao/canon/data/plantuml-config.json"),
    ("core/data/schema.json",                        "src/uiao/canon/data/schema.json"),
    ("core/data/style-guide.yml",                    "src/uiao/canon/data/style-guide.yml"),
    ("core/data/README.md",                          "src/uiao/canon/data/README.md"),
    ("core/data/control-library",                    "src/uiao/canon/data/control-library"),
    ("core/data/overlays",                           "src/uiao/canon/data/overlays"),
    ("core/data/vendor-overlays",                    "src/uiao/canon/data/vendor-overlays"),
    # Compliance reference mappings
    ("core/compliance/reference",                    "src/uiao/canon/compliance/reference"),
]

# --------------------------------------------------------------------------- #
# Directory moves for the adapters phase.
# --------------------------------------------------------------------------- #
ADAPTER_MOVES: list[tuple[str, str]] = [
    ("impl/src/uiao/impl/adapters", "src/uiao/adapters"),
    ("impl/src/uiao/impl/scuba",    "src/uiao/adapters/scuba"),
]

# --------------------------------------------------------------------------- #
# Import rewrite rules (ordered; longer prefixes first).
# --------------------------------------------------------------------------- #
IMPORT_REWRITES: list[tuple[str, str]] = [
    ("uiao.impl.adapters", "uiao.adapters"),
    ("uiao.impl.scuba",    "uiao.adapters.scuba"),
]

REWRITE_SUFFIXES = {".py", ".yaml", ".yml", ".toml", ".md", ".cfg", ".ini", ".json"}
REWRITE_EXCLUDE_DIRS = {".git", ".venv", "node_modules", "__pycache__",
                        "uiao.egg-info", "src/uiao.egg-info"}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def log(apply: bool, msg: str) -> None:
    tag = "[DO ]" if apply else "[DRY]"
    print(f"{tag} {msg}")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO, check=check, capture_output=True, text=True)


def is_tracked(path: Path) -> bool:
    rel = path.relative_to(REPO).as_posix()
    cp = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=REPO, capture_output=True, text=True,
    )
    return cp.returncode == 0


def ensure_parent(dst: Path, apply: bool) -> None:
    if dst.parent.exists():
        return
    log(apply, f"mkdir -p {dst.parent.relative_to(REPO)}")
    if apply:
        dst.parent.mkdir(parents=True, exist_ok=True)


def move(src_rel: str, dst_rel: str, *, apply: bool) -> None:
    src = REPO / src_rel
    dst = REPO / dst_rel
    if not src.exists():
        log(apply, f"SKIP missing {src_rel}")
        return
    if dst.exists():
        log(apply, f"SKIP dst exists {dst_rel}")
        return
    ensure_parent(dst, apply)
    if is_tracked(src):
        log(apply, f"git mv {src_rel} {dst_rel}")
        if apply:
            run(["git", "mv", src_rel, dst_rel])
    else:
        log(apply, f"mv (untracked) {src_rel} {dst_rel}")
        if apply:
            shutil.move(str(src), str(dst))


# --------------------------------------------------------------------------- #
# Phases
# --------------------------------------------------------------------------- #
def phase_backup(apply: bool) -> None:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"pre-reorg/{stamp}"
    log(apply, f"git branch {branch}  (safety snapshot of HEAD)")
    if apply:
        run(["git", "branch", branch])


def phase_canon(apply: bool) -> None:
    print("\n=== phase: canon ===")
    (REPO / "src/uiao/canon/data").mkdir(parents=True, exist_ok=True) if apply else None
    (REPO / "src/uiao/canon/compliance").mkdir(parents=True, exist_ok=True) if apply else None
    for src_rel, dst_rel in CANON_MOVES:
        move(src_rel, dst_rel, apply=apply)


def phase_adapters(apply: bool) -> None:
    print("\n=== phase: adapters ===")
    for src_rel, dst_rel in ADAPTER_MOVES:
        move(src_rel, dst_rel, apply=apply)
    # Guarantee a package marker at src/uiao/adapters/__init__.py
    init = REPO / "src/uiao/adapters/__init__.py"
    if not init.exists():
        log(apply, f"create {init.relative_to(REPO)}")
        if apply:
            init.parent.mkdir(parents=True, exist_ok=True)
            init.write_text('"""uiao.adapters — connector packages."""\n')


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
        out.append(p)
    return out


def phase_imports(apply: bool) -> None:
    print("\n=== phase: imports ===")
    files = _iter_rewrite_files()
    touched = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for old, newtok in IMPORT_REWRITES:
            new = new.replace(old, newtok)
        if new != text:
            touched += 1
            log(apply, f"rewrite {f.relative_to(REPO)}")
            if apply:
                f.write_text(new, encoding="utf-8")
    print(f"    {touched} file(s) need rewrite")


def phase_pyproject(apply: bool) -> None:
    print("\n=== phase: pyproject ===")
    pp = REPO / "pyproject.toml"
    text = pp.read_text(encoding="utf-8")
    marker = '"uiao.adapters"'
    if marker in text:
        log(apply, "pyproject already declares uiao.adapters package-data")
        return
    insertion = (
        '"uiao.adapters" = ["**/*.yaml", "**/*.yml", "**/*.json"]\n'
    )
    anchor = '[tool.setuptools.package-data]\n'
    if anchor not in text:
        log(apply, "pyproject has no [tool.setuptools.package-data]; skipping")
        return
    new_text = text.replace(anchor, anchor + insertion, 1)
    log(apply, "add uiao.adapters entry to [tool.setuptools.package-data]")
    if apply:
        pp.write_text(new_text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
PHASES = {
    "backup":   phase_backup,
    "canon":    phase_canon,
    "adapters": phase_adapters,
    "imports":  phase_imports,
    "pyproject":phase_pyproject,
}
DEFAULT_ORDER = ["backup", "canon", "adapters", "imports", "pyproject"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="actually perform changes (default: dry-run)")
    ap.add_argument("--phase", choices=list(PHASES) + ["all"], default="all",
                    help="run a single phase (default: all)")
    ap.add_argument("--no-backup", action="store_true",
                    help="skip the safety backup branch")
    args = ap.parse_args()

    if args.phase == "all":
        order = [p for p in DEFAULT_ORDER if not (p == "backup" and args.no_backup)]
    else:
        order = [args.phase]

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== UIAO monorepo reorg :: mode={mode} :: phases={order} ===")
    print(f"=== repo: {REPO} ===")

    for name in order:
        PHASES[name](args.apply)

    print("\n=== done ===")
    if not args.apply:
        print("No changes were made. Re-run with --apply to execute.")
    else:
        print("Next steps:")
        print("  1. git status            # review moves")
        print("  2. pip install -e .      # verify install works")
        print("  3. uiao --help           # verify CLI")
        print("  4. pytest -q             # run tests")
        print("  5. git commit -m 'chore: reorganize into clean src/uiao monorepo'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
