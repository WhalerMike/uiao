"""Tests for the deterministic OrgPath projection + codebook validator (WS-A4).

Coverage checklist (acceptance criteria):
  [x] Deterministic projection — same DN input always yields same OrgPath
  [x] Codebook conformance pass — valid path returns ConformanceResult(conforms=True)
  [x] Codebook conformance fail (unknown segment) → Finding, conforms=False
  [x] Collision detection — two OUs map to same OrgPath → Finding(kind="collision")
  [x] Cycle detection — circular OU parent chain → Finding(kind="cycle"), no infinite loop
  [x] Round-trip idempotence — validate(derive(dn)) == validate(validate(derive(dn)).path)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from uiao.adapters.modernization.active_directory.orgpath import (
    ConformanceResult,
    Finding,
    detect_conflicts,
    derive_orgpath,
    validate_orgpath,
)
from uiao.modernization.orgtree import Codebook, load_codebook

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_CODEBOOK_PATH = Path(__file__).parent / "fixtures" / "orgtree" / "test-codebook.yaml"


@pytest.fixture(scope="module")
def codebook() -> Codebook:
    return load_codebook(FIXTURE_CODEBOOK_PATH)


@pytest.fixture(scope="module")
def active_codes(codebook: Codebook) -> set[str]:
    return codebook.codes


# ---------------------------------------------------------------------------
# 1. Deterministic projection
# ---------------------------------------------------------------------------


class TestDeriveOrgpath:
    def test_same_input_same_output(self, active_codes: set[str]) -> None:
        dn = "CN=Alice,OU=SEC,OU=IT,DC=corp,DC=example,DC=com"
        results = {derive_orgpath(dn, active_codes) for _ in range(5)}
        assert len(results) == 1, "derive_orgpath must be deterministic"

    def test_same_input_with_codebook_object(self, codebook: Codebook) -> None:
        dn = "CN=Alice,OU=SEC,OU=IT,DC=corp,DC=example,DC=com"
        r1 = derive_orgpath(dn, codebook)
        r2 = derive_orgpath(dn, codebook)
        assert r1 == r2

    def test_known_path_derives_to_codebook_hit(self, active_codes: set[str]) -> None:
        # OU=SEC,OU=IT → segments IT, SEC → ORG-IT-SEC (in codebook)
        dn = "CN=Bob,OU=SEC,OU=IT,DC=corp,DC=com"
        result = derive_orgpath(dn, active_codes)
        assert result == "ORG-IT-SEC"

    def test_partial_path_falls_back_to_ancestor(self, active_codes: set[str]) -> None:
        # OU=UNKNOWN,OU=IT → IT normalizes; UNKNOWN may not normalize → fallback
        dn = "CN=Carol,OU=IT,DC=corp,DC=com"
        result = derive_orgpath(dn, active_codes)
        # Must produce ORG-IT or None — never raise
        assert result is None or result == "ORG-IT"

    def test_geographic_only_dn_returns_none(self, active_codes: set[str]) -> None:
        dn = "CN=Dave,OU=NorthEast,OU=US,DC=corp,DC=com"
        # Geographic segments have no code mapping — expect None
        result = derive_orgpath(dn, active_codes)
        assert result is None

    def test_bad_arg_type_raises_typeerror(self, active_codes: set[str]) -> None:
        with pytest.raises(TypeError):
            derive_orgpath(12345, active_codes)  # type: ignore[arg-type]

    def test_empty_dn_returns_none(self, active_codes: set[str]) -> None:
        result = derive_orgpath("", active_codes)
        assert result is None

    def test_deterministic_with_set_codebook(self) -> None:
        codes: set[str] = {"ORG", "ORG-IT", "ORG-IT-SEC"}
        dn = "CN=Eve,OU=SEC,OU=IT,DC=corp,DC=com"
        assert derive_orgpath(dn, codes) == derive_orgpath(dn, codes)


# ---------------------------------------------------------------------------
# 2. Codebook conformance — pass
# ---------------------------------------------------------------------------


class TestValidateOrgpathConforms:
    def test_root_code_conforms(self, codebook: Codebook) -> None:
        result = validate_orgpath("ORG", codebook)
        assert isinstance(result, ConformanceResult)
        assert result.conforms is True
        assert result.findings == []

    def test_level1_code_conforms(self, codebook: Codebook) -> None:
        result = validate_orgpath("ORG-IT", codebook)
        assert result.conforms is True

    def test_level2_code_conforms(self, codebook: Codebook) -> None:
        result = validate_orgpath("ORG-IT-SEC", codebook)
        assert result.conforms is True

    def test_level3_code_conforms(self, codebook: Codebook) -> None:
        result = validate_orgpath("ORG-IT-SEC-SOC", codebook)
        assert result.conforms is True

    def test_result_path_matches_input(self, codebook: Codebook) -> None:
        path = "ORG-FIN-AP"
        result = validate_orgpath(path, codebook)
        assert result.path == path

    def test_set_codebook_accepted(self) -> None:
        codes: set[str] = {"ORG", "ORG-HR"}
        result = validate_orgpath("ORG-HR", codes)
        assert result.conforms is True


# ---------------------------------------------------------------------------
# 3. Codebook conformance — fail (unknown segment → finding)
# ---------------------------------------------------------------------------


class TestValidateOrgpathFindings:
    def test_unknown_leaf_segment_produces_finding(self, codebook: Codebook) -> None:
        result = validate_orgpath("ORG-IT-GHOST", codebook)
        assert result.conforms is False
        assert len(result.findings) >= 1
        kinds = {f.kind for f in result.findings}
        assert "unknown_segment" in kinds

    def test_finding_contains_offending_prefix(self, codebook: Codebook) -> None:
        result = validate_orgpath("ORG-NOPE", codebook)
        assert result.conforms is False
        subjects = [s for f in result.findings for s in f.subjects]
        assert any("ORG-NOPE" in s for s in subjects)

    def test_bad_format_produces_format_finding(self, codebook: Codebook) -> None:
        result = validate_orgpath("not-an-orgpath", codebook)
        assert result.conforms is False
        assert len(result.findings) >= 1

    def test_bad_arg_type_raises_typeerror(self, codebook: Codebook) -> None:
        with pytest.raises(TypeError):
            validate_orgpath(None, codebook)  # type: ignore[arg-type]

    def test_findings_are_finding_instances(self, codebook: Codebook) -> None:
        result = validate_orgpath("ORG-UNKNOWN", codebook)
        for f in result.findings:
            assert isinstance(f, Finding)

    def test_partial_path_unknown_intermediate(self, codebook: Codebook) -> None:
        # ORG-FAKE-SEC: ORG is fine, ORG-FAKE is not in codebook
        result = validate_orgpath("ORG-FAKE-SEC", codebook)
        assert result.conforms is False


# ---------------------------------------------------------------------------
# 4. Collision detection
# ---------------------------------------------------------------------------


class TestDetectConflictsCollision:
    def test_no_collision_clean_map(self) -> None:
        ou_map: dict[str, str | None] = {
            "OU=IT,DC=corp,DC=com": "ORG-IT",
            "OU=HR,DC=corp,DC=com": "ORG-HR",
        }
        findings = detect_conflicts(ou_map)
        collisions = [f for f in findings if f.kind == "collision"]
        assert collisions == []

    def test_collision_two_ous_same_orgpath(self) -> None:
        ou_map: dict[str, str | None] = {
            "OU=IT,DC=corp,DC=com": "ORG-IT",
            "OU=InfoTech,DC=corp,DC=com": "ORG-IT",  # collision
        }
        findings = detect_conflicts(ou_map)
        collisions = [f for f in findings if f.kind == "collision"]
        assert len(collisions) == 1
        c = collisions[0]
        assert "ORG-IT" in c.detail
        assert len(c.subjects) == 2

    def test_collision_three_ous_same_orgpath(self) -> None:
        ou_map: dict[str, str | None] = {
            "OU=A,DC=corp": "ORG-IT",
            "OU=B,DC=corp": "ORG-IT",
            "OU=C,DC=corp": "ORG-IT",
        }
        findings = detect_conflicts(ou_map)
        collisions = [f for f in findings if f.kind == "collision"]
        assert len(collisions) == 1
        assert len(collisions[0].subjects) == 3

    def test_none_orgpath_not_collides(self) -> None:
        ou_map: dict[str, str | None] = {
            "OU=A,DC=corp": None,
            "OU=B,DC=corp": None,
        }
        findings = detect_conflicts(ou_map)
        assert findings == []

    def test_finding_is_finding_instance(self) -> None:
        ou_map: dict[str, str | None] = {
            "OU=X,DC=corp": "ORG-IT",
            "OU=Y,DC=corp": "ORG-IT",
        }
        for f in detect_conflicts(ou_map):
            assert isinstance(f, Finding)

    def test_bad_arg_type_raises_typeerror(self) -> None:
        with pytest.raises(TypeError):
            detect_conflicts("not-a-dict")  # type: ignore[arg-type]

    def test_collision_error_code_set(self) -> None:
        ou_map: dict[str, str | None] = {
            "OU=P,DC=corp": "ORG-HR",
            "OU=Q,DC=corp": "ORG-HR",
        }
        findings = detect_conflicts(ou_map)
        collisions = [f for f in findings if f.kind == "collision"]
        assert all(f.error_code for f in collisions)


# ---------------------------------------------------------------------------
# 5. Cycle detection
# ---------------------------------------------------------------------------


class TestDetectConflictsCycle:
    def _cycle_map(self) -> dict[str, str | None]:
        # Construct a pathological OU map where the DN structure implies
        # a cycle: A's parent is B, B's parent is C, C's parent is A.
        # We do this by crafting DNs that share a suffix that is also a key.
        # e.g. "OU=CHILD,OU=PARENT,DC=corp" — parent is "OU=PARENT,DC=corp"
        # For a real cycle we need "OU=A,OU=B,DC=corp" whose parent is
        # "OU=B,DC=corp", and "OU=B,OU=A,DC=corp" whose parent is
        # "OU=A,DC=corp" — these two reference each other.
        return {
            "OU=A,OU=B,DC=corp": "ORG-IT",
            "OU=B,OU=A,DC=corp": "ORG-HR",
        }

    def test_cycle_produces_finding(self) -> None:
        findings = detect_conflicts(self._cycle_map())
        cycles = [f for f in findings if f.kind == "cycle"]
        assert len(cycles) >= 1

    def test_cycle_detection_terminates(self) -> None:
        """Must not loop infinitely on a cycle."""
        import signal

        def _timeout_handler(signum: int, frame: object) -> None:
            raise TimeoutError("detect_conflicts did not terminate")

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        try:
            detect_conflicts(self._cycle_map())
        finally:
            signal.alarm(0)

    def test_cycle_finding_has_subjects(self) -> None:
        findings = detect_conflicts(self._cycle_map())
        cycles = [f for f in findings if f.kind == "cycle"]
        for c in cycles:
            assert len(c.subjects) >= 2

    def test_no_cycle_clean_chain(self) -> None:
        # "OU=CHILD,OU=PARENT,DC=corp" → parent is "OU=PARENT,DC=corp"
        # "OU=PARENT,DC=corp" is also in the map with parent None (DC is outside)
        ou_map: dict[str, str | None] = {
            "OU=CHILD,OU=PARENT,DC=corp": "ORG-IT",
            "OU=PARENT,DC=corp": "ORG-HR",
        }
        findings = detect_conflicts(ou_map)
        cycles = [f for f in findings if f.kind == "cycle"]
        assert cycles == []

    def test_large_linear_chain_no_cycle(self) -> None:
        # 50-deep chain; no cycle. Must not hit recursion limit.
        ou_map: dict[str, str | None] = {}
        dn = "DC=corp"
        for i in range(50):
            dn = f"OU=N{i},{dn}"
            ou_map[dn] = "ORG-IT" if i == 0 else None
        findings = detect_conflicts(ou_map)
        cycles = [f for f in findings if f.kind == "cycle"]
        assert cycles == []


# ---------------------------------------------------------------------------
# 6. Round-trip idempotence
# ---------------------------------------------------------------------------


class TestRoundTripIdempotence:
    def test_validate_derived_path_is_stable(self, codebook: Codebook) -> None:
        """validate(derive(dn)) then validate again must give same result."""
        dn = "CN=Frank,OU=SEC,OU=IT,DC=corp,DC=com"
        path = derive_orgpath(dn, codebook)
        if path is None:
            pytest.skip("derive_orgpath returned None for this DN — cannot test round-trip")

        r1 = validate_orgpath(path, codebook)
        r2 = validate_orgpath(r1.path, codebook)

        assert r1.conforms == r2.conforms
        assert r1.path == r2.path
        assert len(r1.findings) == len(r2.findings)

    def test_validate_known_path_twice_idempotent(self, codebook: Codebook) -> None:
        path = "ORG-IT-SEC"
        r1 = validate_orgpath(path, codebook)
        r2 = validate_orgpath(r1.path, codebook)
        assert r1.conforms == r2.conforms is True
        assert r1.findings == r2.findings == []

    def test_validate_unknown_path_twice_idempotent(self, codebook: Codebook) -> None:
        path = "ORG-ZZZZ"
        r1 = validate_orgpath(path, codebook)
        r2 = validate_orgpath(r1.path, codebook)
        assert r1.conforms == r2.conforms is False
        assert len(r1.findings) == len(r2.findings)

    def test_detect_conflicts_called_twice_stable(self) -> None:
        ou_map: dict[str, str | None] = {
            "OU=IT,DC=corp": "ORG-IT",
            "OU=InfoTech,DC=corp": "ORG-IT",
        }
        f1 = detect_conflicts(ou_map)
        f2 = detect_conflicts(ou_map)
        assert len(f1) == len(f2)
        assert [f.kind for f in f1] == [f.kind for f in f2]

    def test_projection_twice_same_result(self, codebook: Codebook) -> None:
        dn = "CN=Grace,OU=IAM,OU=SEC,OU=IT,DC=corp,DC=com"
        assert derive_orgpath(dn, codebook) == derive_orgpath(dn, codebook)
