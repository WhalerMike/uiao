"""Consistency gate: golden ScubaGear fixture vs SCUBA_TO_KSI_MAP.

Implements the local half of RFC-0026 enhancement E2 (see
docs/docs/uiao-rfc-0026-roadmap.md). The upstream tracker workflow
(.github/workflows/scubagear-upstream-track.yml) opens a canon-change
issue when cisagov/ScubaGear ships a new release that UIAO's pin has
not been reconciled against; this test module catches the *intra-PR*
case — when either SCUBA_TO_KSI_MAP or the golden fixture is edited
but the other isn't kept in sync.

The golden fixture at tests/fixtures/scubagear_golden_sample.json is
required to span every MS.* product prefix currently in
SCUBA_TO_KSI_MAP; losing coverage for a whole product family shows up
here as a test failure rather than as a silent omission in production
ConMon packs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.scuba.ir.normalize_scuba import normalize_scuba
from uiao.adapters.scubagear_adapter import SCUBA_TO_KSI_MAP

FIXTURE = Path(__file__).parent / "fixtures" / "scubagear_golden_sample.json"


def _product_prefix(policy_id: str) -> str:
    """Extract the product prefix from a ScubaGear policy ID.

    MS.AAD.1.1v1       -> MS.AAD
    MS.SHAREPOINT.3.2v1 -> MS.SHAREPOINT
    """
    parts = policy_id.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else policy_id


@pytest.fixture(scope="module")
def golden_raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestGoldenFixtureCoverage:
    def test_fixture_covers_every_product_prefix_in_map(self, golden_raw: dict) -> None:
        """Every MS.<product> prefix in SCUBA_TO_KSI_MAP must be exercised."""
        fixture_prefixes = {_product_prefix(r["PolicyId"]) for r in golden_raw["TestResults"]}
        map_prefixes = {_product_prefix(k) for k in SCUBA_TO_KSI_MAP}
        missing = map_prefixes - fixture_prefixes
        assert not missing, (
            f"Golden fixture is missing coverage for product prefixes: {sorted(missing)}. "
            "Add at least one policy from each prefix to "
            "tests/fixtures/scubagear_golden_sample.json so map drift in that "
            "family is caught by the consistency gate."
        )

    def test_every_fixture_policy_is_in_map(self, golden_raw: dict) -> None:
        """Every policy ID in the fixture must resolve via SCUBA_TO_KSI_MAP."""
        policies = [r["PolicyId"] for r in golden_raw["TestResults"]]
        unmapped = [p for p in policies if p not in SCUBA_TO_KSI_MAP]
        assert not unmapped, (
            f"Fixture references {len(unmapped)} policy IDs not in SCUBA_TO_KSI_MAP: {unmapped}. "
            "Either add the mapping to src/uiao/adapters/scubagear_adapter.py "
            "or remove the policy from the fixture."
        )


class TestNormalizeAgainstGolden:
    def test_zero_unmapped_policies(self, tmp_path: Path) -> None:
        """normalize_scuba() on the golden fixture must report zero unmapped.

        This is the gate the upstream tracker workflow also relies on:
        if SCUBA_TO_KSI_MAP loses an entry that the fixture references,
        normalize_scuba will classify it as unmapped and this assertion
        fails — catching the drift before a production ConMon pack does.
        """
        target = tmp_path / "ScubaResults.json"
        target.write_text(FIXTURE.read_text(encoding="utf-8"))
        out = normalize_scuba(target)

        meta = out["assessment_metadata"]["normalization"]
        assert meta["unmapped_count"] == 0, (
            f"normalize_scuba found {meta['unmapped_count']} unmapped policies: {meta['unmapped_policies']}"
        )

    def test_envelope_carries_tool_and_opa_version_from_golden(self, tmp_path: Path) -> None:
        """The golden fixture includes ToolVersion + OpaVersion; the envelope
        must preserve both so the DRIFT-PROVENANCE pre-flight (E3.3) can use
        them. This pins the integration between E2 and E3."""
        target = tmp_path / "ScubaResults.json"
        target.write_text(FIXTURE.read_text(encoding="utf-8"))
        out = normalize_scuba(target)

        am = out["assessment_metadata"]
        assert am["tool_version"] == "1.7.1"
        assert am["source_envelope"].get("OpaVersion") == "0.59.0"
        # The pre-flight should have run and passed against the scuba.yaml pin
        assert am["provenance_preflight"]["status"] == "ok"
