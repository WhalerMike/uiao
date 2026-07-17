"""The KSI rule-library index must agree with the rule files on disk.

Regen-and-diff gate for ``src/uiao/rules/ksi/index.yaml`` (see
``scripts/rebuild_ksi_index.py``): the hand-maintained predecessor drifted in
both directions — 173 indexed entries against 191 rule files, with four whole
category directories missing and phantom entries pointing at removed rules.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "rebuild_ksi_index.py"
INDEX = REPO_ROOT / "src" / "uiao" / "rules" / "ksi" / "index.yaml"


def test_index_matches_rules_on_disk():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, f"KSI index drift:\n{result.stderr}\nRegenerate: python scripts/rebuild_ksi_index.py"


def test_every_indexed_path_exists():
    index = yaml.safe_load(INDEX.read_text(encoding="utf-8"))
    src_root = REPO_ROOT / "src" / "uiao"
    missing = [e["ksi_id"] for e in index["ksis"] if not (src_root / e["path"]).is_file()]
    assert not missing, f"index entries point at missing rule files: {missing}"


def test_stats_are_internally_consistent():
    index = yaml.safe_load(INDEX.read_text(encoding="utf-8"))
    entries = index["ksis"]
    stats = index["stats"]
    assert stats["total_ksis"] == len(entries)
    assert stats["enabled"] == sum(1 for e in entries if e["enabled"])
    assert sum(stats["categories"].values()) == len(entries)
    ids = [e["ksi_id"] for e in entries]
    assert len(ids) == len(set(ids)), "duplicate ksi_id in index"
