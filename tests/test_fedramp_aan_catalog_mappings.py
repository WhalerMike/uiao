"""
Tests for the FedRAMP AAN catalog adapter's evidence-binding mappings.

File: tests/test_fedramp_aan_catalog_mappings.py

Every `path:` in mappings/slot-0N-*.yaml points at an AAN book that is the
evidence for a surface slot. All 19 of them dangled: they named
`Book_NN_Federal_Application_Aware_Networking_*.qmd` from a numbering generation
that predates the reorganisation into volumes, so the current corpus has no such
file. Nothing noticed — the Adapter Conformance suite passed 330/330 throughout,
because nothing resolved these strings against the disk.

An evidence binding that points at no file is not evidence. These tests make the
pointer load-bearing.

Note the numbers in those old names were NOT a reliable key: git records
`Book_02` as Network_Access_Control_802_1X, while the mappings used
`Book_02_..._Network_Modernization` — a pairing that never existed in the
generation git recorded. The descriptive suffix identifies the document; the
number does not. Repointing by number would have silently bound the wrong books
to the wrong slots.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = REPO_ROOT / "src" / "uiao" / "adapters" / "fedramp_aan_catalog" / "mappings"
PATH_RE = re.compile(r'^\s*path:\s*["\']?([^"\'\n]+)', re.M)


def mapping_files() -> list[Path]:
    return sorted(MAPPINGS.glob("slot-0*-*.yaml"))


def declared_paths(f: Path) -> list[str]:
    return [m.group(1).strip() for m in PATH_RE.finditer(f.read_text(encoding="utf-8"))]


def test_mappings_exist() -> None:
    """The eight surface slots each ship a mapping file."""
    assert len(mapping_files()) == 8, "expected one mapping per surface slot"


@pytest.mark.parametrize("mapping", mapping_files(), ids=lambda p: p.name)
def test_mapping_is_valid_yaml(mapping: Path) -> None:
    assert yaml.safe_load(mapping.read_text(encoding="utf-8")) is not None


@pytest.mark.parametrize("mapping", mapping_files(), ids=lambda p: p.name)
def test_every_declared_path_resolves(mapping: Path) -> None:
    """An evidence pointer that resolves to nothing is not evidence.

    This is the regression that shipped: all 19 paths named books from a
    superseded numbering generation and every one was dead.
    """
    missing = [p for p in declared_paths(mapping) if not (REPO_ROOT / p).exists()]
    assert not missing, f"{mapping.name} declares {len(missing)} evidence path(s) that do not exist on disk: {missing}"


@pytest.mark.parametrize("mapping", mapping_files(), ids=lambda p: p.name)
def test_declared_paths_are_current_series_books(mapping: Path) -> None:
    """Guard the specific way these went stale: the pre-volume flat numbering.

    A path naming `Book_NN_Federal_Application_Aware_Networking_*` is from the
    superseded generation even if some file happens to sit there.
    """
    stale = [p for p in declared_paths(mapping) if "Book_" in p and "_Federal_Application_Aware_Networking_" in p]
    assert not stale, (
        f"{mapping.name} uses pre-volume book names: {stale}. The current series is "
        f"Vol_<V>_Book_<NN>_FedAAN_<Name>.qmd; match on the descriptive suffix, never "
        f"on the book number."
    )
