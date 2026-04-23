#!/usr/bin/env python3
"""
reorganize_monorepo.py — minimal-typing monorepo consolidation.

Two phases, idempotent, git-history-preserving:

    canon   Move canon + schemas + rules + ksi from core/* into src/uiao/*
    scuba   Write top-level pyproject.toml and src/uiao/cli.py so
            `pip install -e .` + `uiao scuba ...` work

Usage (run from the monorepo root, C:\\Users\\whale\\src\\uiao):

    python scripts/reorganize_monorepo.py --phase canon --dry-run
    python scripts/reorganize_monorepo.py --phase canon
    python scripts/reorganize_monorepo.py --phase scuba --dry-run
    python scripts/reorganize_monorepo.py --phase scuba
    python scripts/reorganize_monorepo.py --phase all

Safe re-runs: every action checks source-exists and dest-free before
acting, so running twice is a no-op.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Script lives at scripts/reorganize_monorepo.py — repo root is its parent.
REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def banner(msg: str) -> None:
    print(f"\n=== {msg} ===")


def log(msg: str) -> None:
    print(f"  {msg}")


def _run(cmd: list[str], dry_run: bool) -> None:
    log(f"$ {' '.join(cmd)}")
    if not dry_run:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def ensure_dir(rel: str, dry_run: bool) -> None:
    p = REPO_ROOT / rel
    if p.exists():
        return
    log(f"mkdir -p {rel}")
    if not dry_run:
        p.mkdir(parents=True, exist_ok=True)


def git_mv(src_rel: str, dst_rel: str, dry_run: bool) -> bool:
    """git mv src_rel dst_rel (preserves history). Idempotent."""
    src = REPO_ROOT / src_rel
    dst = REPO_ROOT / dst_rel
    if not src.exists():
        log(f"skip (no source): {src_rel}")
        return False
    if dst.exists():
        log(f"skip (dest exists): {dst_rel}")
        return False
    ensure_dir(str(Path(dst_rel).parent), dry_run)
    _run(["git", "mv", src_rel, dst_rel], dry_run)
    return True


def write_text(rel: str, content: str, dry_run: bool, overwrite: bool = False) -> None:
    p = REPO_ROOT / rel
    if p.exists() and not overwrite:
        log(f"skip (exists): {rel}")
        return
    ensure_dir(str(Path(rel).parent), dry_run)
    log(f"write {rel}")
    if not dry_run:
        p.write_text(content, encoding="utf-8", newline="\n")


def touch_init(rel_dir: str, dry_run: bool) -> None:
    """Create an empty __init__.py so the dir works as a regular package
    (needed for reliable importlib.resources access to YAML/JSON files)."""
    init_path = f"{rel_dir}/__init__.py"
    p = REPO_ROOT / init_path
    if p.exists():
        return
    ensure_dir(rel_dir, dry_run)
    log(f"touch {init_path}")
    if not dry_run:
        p.write_text("", encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 1 — canon + schemas + rules + ksi
# ---------------------------------------------------------------------------
def phase_canon(dry_run: bool) -> None:
    banner("Phase 1: canon / schemas / rules / ksi → src/uiao/")

    # Canon YAML SSOT first (the user's #1 priority)
    for yml in [
        "adapter-registry.yaml",
        "document-registry.yaml",
        "image-registry.yaml",
        "modernization-registry.yaml",
        "substrate-manifest.yaml",
        "workspace-contract.yaml",
    ]:
        git_mv(f"core/canon/{yml}", f"src/uiao/canon/{yml}", dry_run)

    # Top-level canon markdown docs
    for md in [
        "UIAO-SSOT.md",
        "canonical-rules.md",
        "UIAO_002_SCuBA_Technical_Specification_v1.0.md",
        "UIAO_003_Adapter_Segmentation_Overview_v1.0.md",
    ]:
        git_mv(f"core/canon/{md}", f"src/uiao/canon/{md}", dry_run)

    # Canon subdirectories (ADRs, specs, compliance, data)
    for sub in ["adr", "specs", "compliance", "data"]:
        git_mv(f"core/canon/{sub}", f"src/uiao/canon/{sub}", dry_run)

    # Parallel top-level dirs: schemas, rules, ksi
    for top in ["schemas", "rules", "ksi"]:
        git_mv(f"core/{top}", f"src/uiao/{top}", dry_run)

    # Package markers so importlib.resources works for data files
    for pkg in [
        "src/uiao/canon",
        "src/uiao/schemas",
        "src/uiao/rules",
        "src/uiao/ksi",
    ]:
        touch_init(pkg, dry_run)

    log("\nDone with canon phase.")
    log("Note: src/uiao/ intentionally has NO __init__.py (PEP 420 namespace,")
    log("so it can share the `uiao` namespace with impl/src/uiao/impl/*).")


# ---------------------------------------------------------------------------
# Phase 2 — packaging + SCuBA callable via top-level `uiao` entry point
# ---------------------------------------------------------------------------
PYPROJECT_TOML = """\
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "uiao"
version = "0.3.0"
description = "UIAO — Unified Identity-Addressing-Overlay Architecture"
readme = "README.md"
requires-python = ">=3.10"
license = "Apache-2.0"
authors = [{ name = "WhalerMike" }]
dependencies = [
  "pydantic>=2.0",
  "pyyaml>=6.0",
  "typer>=0.9",
  "rich>=13.0",
]

[project.scripts]
uiao = "uiao.cli:main"

# This pyproject covers only src/uiao/*. The existing impl/ subtree is
# installed separately via `pip install -e impl/` and contributes
# uiao.* to the same PEP 420 `uiao` namespace at runtime.
[tool.setuptools.packages.find]
where = ["src"]
include = ["uiao*"]
namespaces = true

# Ship canon YAML / schemas / rules / KSI as package data so runtime
# code can access them via importlib.resources.
[tool.setuptools.package-data]
"uiao.canon" = ["**/*.yaml", "**/*.yml", "**/*.md", "**/*.json"]
"uiao.schemas" = ["**/*.json", "**/*.yaml", "**/*.yml"]
"uiao.rules" = ["**/*.yaml", "**/*.yml", "**/*.md"]
"uiao.ksi" = ["**/*.yaml", "**/*.yml", "**/*.json"]
"""

CLI_PY = '''\
"""uiao CLI entry point (top-level).

Thin bridge over the existing Typer app at `uiao.cli.app:app`.
As adapters migrate from `uiao.impl.*` into `uiao.*` directly, this
file can absorb those commands.

Today this enables:

    uiao --help
    uiao scuba transform --input ... --out ...
"""
from __future__ import annotations


def main() -> int:
    # Lazy import so the bridge costs nothing at package-load time.
    from uiao.cli.app import app
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def phase_scuba(dry_run: bool) -> None:
    banner("Phase 2: packaging + top-level CLI")

    # Ensure src/uiao/ exists (as PEP 420 namespace — no __init__.py here)
    ensure_dir("src/uiao", dry_run)

    # Top-level pyproject.toml (guarded: won't overwrite if it already exists)
    write_text("pyproject.toml", PYPROJECT_TOML, dry_run)

    # Top-level CLI bridge
    write_text("src/uiao/cli.py", CLI_PY, dry_run)

    log("\nDone with scuba phase.")
    log("Next, from the monorepo root:")
    log("  pip install -e .")
    log("  uiao --help")
    log("  uiao scuba transform --input <scuba.json> --out <ir.json>")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def preflight() -> None:
    # Basic sanity: are we in the expected tree?
    if not (REPO_ROOT / ".git").exists():
        print(f"ERROR: {REPO_ROOT} is not a git repo.", file=sys.stderr)
        sys.exit(2)
    if not (REPO_ROOT / "core").exists() and not (REPO_ROOT / "src" / "uiao").exists():
        print(
            f"ERROR: {REPO_ROOT} has neither core/ nor src/uiao/ — wrong directory?",
            file=sys.stderr,
        )
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--phase",
        choices=["canon", "scuba", "all"],
        required=True,
        help="Which phase to run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without touching anything.",
    )
    args = parser.parse_args()

    preflight()
    banner(f"uiao monorepo reorganization — phase={args.phase} dry_run={args.dry_run}")
    log(f"repo root: {REPO_ROOT}")

    if args.phase in {"canon", "all"}:
        phase_canon(args.dry_run)
    if args.phase in {"scuba", "all"}:
        phase_scuba(args.dry_run)

    banner("Finished.")
    if args.dry_run:
        log("Dry run only — no files changed.")
    else:
        log("Re-run safely: every step is idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    raise SystemExit(main())
