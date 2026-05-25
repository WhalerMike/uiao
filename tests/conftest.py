"""Shared pytest fixtures for uiao tests."""

from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

from canon_paths import CANON_ROOT, DATA_DIR, GENERATION_INPUTS_DIR


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --update-golden flag to pytest CLI (used by orgtree_evidence golden tests)."""
    with contextlib.suppress(ValueError):
        parser.addoption(
            "--update-golden",
            action="store_true",
            default=False,
            help="Overwrite golden fixture files with current emitter output.",
        )


@pytest.fixture
def project_root() -> Path:
    """Return the uiao project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def canon_root() -> Path:
    """Return the resolved canon root (uiao checkout)."""
    return CANON_ROOT


@pytest.fixture
def canon_dir() -> Path:
    """Return the generation-inputs/ directory from canon."""
    return GENERATION_INPUTS_DIR


@pytest.fixture
def data_dir() -> Path:
    """Return the data/ directory from canon."""
    return DATA_DIR


@pytest.fixture
def exports_dir(project_root: Path, tmp_path: Path) -> Path:
    """Return a temporary exports directory for test output."""
    out = tmp_path / "exports" / "oscal"
    out.mkdir(parents=True)
    return out


@pytest.fixture
def sample_canon_entry() -> dict:
    """Return a minimal canon-like dict for unit tests."""
    return {
        "id": "test-entry-001",
        "name": "Test Canon Entry",
        "description": "A test entry for unit testing.",
        "category": "testing",
    }


# ---------------------------------------------------------------------------
# Canonical 10-facet OrgPath Codebook fixture (ADR-084 §C6)
#
# Built programmatically (no YAML I/O) so all 5 Phase 5 consumers'
# tests share an offline-testable, deterministic Codebook. Per-consumer
# tests parameterize against this fixture rather than constructing their
# own — guarantees consistent semantics across consumers.
# ---------------------------------------------------------------------------


@pytest.fixture
def codebook_model_c():
    """Return the canonical 10-facet Model C Codebook fixture.

    Mirrors the slot-to-facet bindings declared in ADR-078 (1=Region,
    2=Department, 3=Division, 4=Role, 5=CostCenter, 6=Classification,
    7=HireDate typed, 8=TermDate typed allow_empty, 9=ClearanceLevel,
    10=AccountType) and ships small starter enumerations + one
    deprecated value (Division.OldCyber -> CyberOps) for Phantom Drift
    coverage. Slot 11 is reserved (test C7 reserved-facet rejection).
    """
    from uiao.modernization.orgtree.codebook import (
        Codebook,
        DeprecatedFacetValue,
        Facet,
        FacetValue,
    )

    def _enum(*values: tuple[str, str]) -> dict[str, FacetValue]:
        return {v: FacetValue(value=v, description=d) for v, d in values}

    region = Facet(
        name="region",
        attribute="extensionAttribute1",
        description="Geographic region",
        kind="enumerated",
        enumeration=_enum(
            ("NCR", "National Capital Region"),
            ("EASTUS", "Eastern United States"),
            ("WESTUS", "Western United States"),
            ("EMEA", "Europe / Middle East / Africa"),
        ),
    )
    department = Facet(
        name="department",
        attribute="extensionAttribute2",
        description="Business unit",
        kind="enumerated",
        enumeration=_enum(
            ("IT", "Information Technology"),
            ("HR", "Human Resources"),
            ("Finance", "Finance"),
            ("Legal", "Legal"),
        ),
    )
    division = Facet(
        name="division",
        attribute="extensionAttribute3",
        description="Sub-unit within department",
        kind="enumerated",
        enumeration=_enum(
            ("CyberOps", "Cybersecurity Operations"),
            ("InfraOps", "Infrastructure Operations"),
            ("AppDev", "Application Development"),
        ),
        deprecated={
            "OldCyber": DeprecatedFacetValue(
                value="OldCyber",
                replaced_by="CyberOps",
                deprecated_at="2026-01-01",
                reason="Renamed; consolidated under CyberOps",
            ),
        },
    )
    role = Facet(
        name="role",
        attribute="extensionAttribute4",
        description="Job role",
        kind="enumerated",
        enumeration=_enum(
            ("Analyst", "Analyst"),
            ("Engineer", "Engineer"),
            ("Manager", "Manager"),
            ("Director", "Director"),
        ),
    )
    cost_center = Facet(
        name="cost_center",
        attribute="extensionAttribute5",
        description="Cost center code",
        kind="enumerated",
        enumeration=_enum(
            ("CC-4100", "CC-4100"),
            ("CC-5200", "CC-5200"),
            ("CC-BAL", "Baltimore"),
        ),
    )
    classification = Facet(
        name="classification",
        attribute="extensionAttribute6",
        description="Employment classification",
        kind="enumerated",
        enumeration=_enum(
            ("Employee", "Full-time employee"),
            ("Contractor", "Contractor"),
            ("Intern", "Intern"),
            ("Executive", "Executive"),
        ),
    )
    hire_date = Facet(
        name="hire_date",
        attribute="extensionAttribute7",
        description="ISO 8601 hire date",
        kind="typed",
        value_type="date",
        value_pattern=r"^\d{4}-\d{2}-\d{2}$",
        allow_empty=False,
    )
    term_date = Facet(
        name="term_date",
        attribute="extensionAttribute8",
        description="ISO 8601 termination date; empty = active",
        kind="typed",
        value_type="date",
        value_pattern=r"^\d{4}-\d{2}-\d{2}$",
        allow_empty=True,
    )
    clearance_level = Facet(
        name="clearance_level",
        attribute="extensionAttribute9",
        description="Clearance level",
        kind="enumerated",
        enumeration=_enum(
            ("None", "No clearance"),
            ("PublicTrust", "Public Trust"),
            ("Secret", "Secret"),
            ("TopSecret", "Top Secret"),
            ("TS_SCI", "TS/SCI"),
        ),
    )
    account_type = Facet(
        name="account_type",
        attribute="extensionAttribute10",
        description="Account type",
        kind="enumerated",
        enumeration=_enum(
            ("Standard", "Standard"),
            ("Privileged", "Privileged"),
            ("Service", "Service account"),
            ("Guest", "B2B guest"),
        ),
    )
    reserved_11 = Facet(
        name="reserved_11",
        attribute="extensionAttribute11",
        description="Reserved for tenant-declared facet",
        kind="reserved",
    )

    facets = {
        f.name: f
        for f in (
            region,
            department,
            division,
            role,
            cost_center,
            classification,
            hire_date,
            term_date,
            clearance_level,
            account_type,
            reserved_11,
        )
    }
    return Codebook(
        schema_version="2.0.0",
        document_id="codebook-fixture-model-c",
        parent_canon="UIAO_151",
        model="C",
        adoption_tier_min=3,
        facets=facets,
    )


# ---------------------------------------------------------------------------
# Auto-skip canon-dependent modules when generation-inputs/ is not available.
# Canon lives in uiao; generation-inputs/ was not migrated in the split
# (tracked in issue #2). These modules re-activate automatically once canon
# is restored in uiao.
# ---------------------------------------------------------------------------
from canon_paths import GENERATION_INPUTS_DIR as _GEN_INPUTS_DIR

_CANON_DEPENDENT_MODULES = {
    "test_diagrams",
    "test_mover_logic",
    "test_generators",
    "test_models",
    "test_overlay_loader",
    "test_ssp_inject",
    # Note: test_scuba_transformer_determinism was previously listed here
    # but it uses tests/fixtures/scuba_normalized_sample.json, not
    # generation-inputs/. Removed so the 16 SCuBA transformer tests
    # actually run.
}


def pytest_collection_modifyitems(config, items):
    """Skip tests depending on canon files not yet migrated to uiao."""
    if _GEN_INPUTS_DIR.exists():
        return
    skip_marker = pytest.mark.skip(reason="canon generation-inputs/ not migrated to uiao yet (issue #2)")
    for item in items:
        module_name = item.module.__name__.rsplit(".", 1)[-1]
        if module_name in _CANON_DEPENDENT_MODULES:
            item.add_marker(skip_marker)
