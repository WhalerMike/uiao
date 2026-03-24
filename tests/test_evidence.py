"""Tests for uiao_core.evidence and uiao_core.models.evidence modules.

Covers:
- EvidenceArtifact, EvidenceMap, EvidenceBundle Pydantic models
- EvidenceLinker: control map, OSCAL back-matter generation, SSP injection
- EvidenceBundler: manifest, bundle model, ZIP output
- EvidenceCollector: aggregation of multiple connectors
- UIAO-MEMORY rule: every prop in back-matter carries a fresh UUIDv4 (prop:id)
"""
from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

import pytest

from uiao_core.models.evidence import EvidenceArtifact, EvidenceBundle, EvidenceMap

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_artifact() -> EvidenceArtifact:
    return EvidenceArtifact(
        uuid=str(uuid.uuid4()),
        title="Test Policy Document",
        description="Supports AC-2 and AC-3",
        file_path="exports/evidence/test_policy.pdf",
        media_type="application/pdf",
        control_refs=["ac-2", "ac-3"],
        collector="manual-upload",
    )


@pytest.fixture()
def two_artifacts() -> list[EvidenceArtifact]:
    return [
        EvidenceArtifact(
            uuid=str(uuid.uuid4()),
            title="Sentinel Logs",
            description="Audit log export",
            file_path="exports/evidence/sentinel.json",
            media_type="application/json",
            control_refs=["au-2", "au-9"],
            collector="azure-sentinel",
        ),
        EvidenceArtifact(
            uuid=str(uuid.uuid4()),
            title="Vuln Scan Report",
            description="Nessus output",
            file_path="exports/evidence/vuln_scan.xml",
            media_type="application/xml",
            control_refs=["ra-5", "si-2"],
            collector="vuln-scan",
        ),
    ]


# ---------------------------------------------------------------------------
# EvidenceArtifact model tests
# ---------------------------------------------------------------------------


class TestEvidenceArtifact:
    def test_create_minimal(self) -> None:
        art = EvidenceArtifact(uuid=str(uuid.uuid4()), title="Minimal")
        assert art.title == "Minimal"
        assert art.media_type == "application/octet-stream"
        assert art.control_refs == []

    def test_hash_sha256_valid(self) -> None:
        art = EvidenceArtifact(
            uuid=str(uuid.uuid4()),
            title="Hash Test",
            hash_sha256="a" * 64,
        )
        assert art.hash_sha256 == "a" * 64

    def test_hash_sha256_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError, match="64-character"):
            EvidenceArtifact(uuid=str(uuid.uuid4()), title="Bad Hash", hash_sha256="abc")

    def test_hash_sha256_empty_ok(self) -> None:
        art = EvidenceArtifact(uuid=str(uuid.uuid4()), title="No Hash", hash_sha256="")
        assert art.hash_sha256 == ""

    def test_collected_at_is_set(self) -> None:
        art = EvidenceArtifact(uuid=str(uuid.uuid4()), title="Timestamped")
        assert art.collected_at  # non-empty ISO timestamp

    def test_extra_fields_allowed(self) -> None:
        art = EvidenceArtifact(uuid=str(uuid.uuid4()), title="Extra", custom_field="x")
        assert art.custom_field == "x"  # type: ignore[attr-defined]

    def test_extra_fields_round_trip(self) -> None:
        """Extra fields survive model_dump/model_validate round-trip."""
        art = EvidenceArtifact(uuid=str(uuid.uuid4()), title="Round-trip", custom_field="y")
        d = art.model_dump()
        assert d["custom_field"] == "y"
        art2 = EvidenceArtifact.model_validate(d)
        assert art2.custom_field == "y"  # type: ignore[attr-defined]


class TestEvidenceMap:
    def test_create_with_artifacts(self, sample_artifact: EvidenceArtifact) -> None:
        emap = EvidenceMap(control_id="ac-2", artifacts=[sample_artifact])
        assert emap.control_id == "ac-2"
        assert len(emap.artifacts) == 1


class TestEvidenceBundle:
    def test_artifact_count(self, two_artifacts: list[EvidenceArtifact]) -> None:
        bundle = EvidenceBundle(
            bundle_id=str(uuid.uuid4()),
            artifacts=two_artifacts,
        )
        assert bundle.artifact_count() == 2

    def test_empty_bundle(self) -> None:
        bundle = EvidenceBundle(bundle_id=str(uuid.uuid4()))
        assert bundle.artifact_count() == 0


# ---------------------------------------------------------------------------
# EvidenceLinker tests
# ---------------------------------------------------------------------------


class TestEvidenceLinker:
    def test_build_control_map(self, two_artifacts: list[EvidenceArtifact]) -> None:
        from uiao_core.evidence.linker import EvidenceLinker

        linker = EvidenceLinker(two_artifacts)
        cmap = linker.build_control_map()
        assert "au-2" in cmap
        assert "au-9" in cmap
        assert "ra-5" in cmap
        assert "si-2" in cmap
        assert len(cmap["au-2"].artifacts) == 1

    def test_control_map_no_duplicates(self, sample_artifact: EvidenceArtifact) -> None:
        """Same artifact should not appear twice in a control map entry."""
        from uiao_core.evidence.linker import EvidenceLinker

        linker = EvidenceLinker([sample_artifact])
        cmap = linker.build_control_map()
        assert len(cmap["ac-2"].artifacts) == 1

    def test_to_oscal_back_matter_structure(self, sample_artifact: EvidenceArtifact) -> None:
        from uiao_core.evidence.linker import EvidenceLinker

        linker = EvidenceLinker([sample_artifact])
        bm = linker.to_oscal_back_matter()

        assert "resources" in bm
        assert len(bm["resources"]) == 1
        resource = bm["resources"][0]
        assert resource["uuid"] == sample_artifact.uuid
        assert resource["title"] == sample_artifact.title
        assert "props" in resource
        assert "rlinks" in resource

    def test_every_prop_has_uuid_prop_id_rule(self, sample_artifact: EvidenceArtifact) -> None:
        """UIAO-MEMORY rule: every prop in back-matter must carry its own UUIDv4."""
        from uiao_core.evidence.linker import EvidenceLinker

        linker = EvidenceLinker([sample_artifact])
        bm = linker.to_oscal_back_matter()
        resource = bm["resources"][0]
        for prop in resource["props"]:
            assert "uuid" in prop, f"prop missing uuid: {prop}"
            # Must be a valid UUID
            uuid.UUID(prop["uuid"])

    def test_prop_id_prop_present(self, sample_artifact: EvidenceArtifact) -> None:
        """A prop with name='id' must be present in every back-matter resource."""
        from uiao_core.evidence.linker import EvidenceLinker

        linker = EvidenceLinker([sample_artifact])
        bm = linker.to_oscal_back_matter()
        resource = bm["resources"][0]
        id_props = [p for p in resource["props"] if p["name"] == "id"]
        assert len(id_props) == 1
        assert id_props[0]["value"] == sample_artifact.uuid

    def test_control_ref_props(self, sample_artifact: EvidenceArtifact) -> None:
        """Each control ref gets its own prop with a fresh UUID."""
        from uiao_core.evidence.linker import EvidenceLinker

        linker = EvidenceLinker([sample_artifact])
        bm = linker.to_oscal_back_matter()
        resource = bm["resources"][0]
        ctrl_props = [p for p in resource["props"] if p["name"] == "control-ref"]
        # sample_artifact has ac-2 and ac-3
        assert len(ctrl_props) == 2
        values = {p["value"] for p in ctrl_props}
        assert values == {"ac-2", "ac-3"}
        # Each must have its own uuid
        uuids = [p["uuid"] for p in ctrl_props]
        assert len(set(uuids)) == 2, "Each control-ref prop must have a unique UUID"

    def test_fedramp_ns_on_all_props(self, sample_artifact: EvidenceArtifact) -> None:
        """All props must carry the FedRAMP OSCAL namespace."""
        from uiao_core.evidence.linker import FEDRAMP_NS, EvidenceLinker

        linker = EvidenceLinker([sample_artifact])
        bm = linker.to_oscal_back_matter()
        for resource in bm["resources"]:
            for prop in resource["props"]:
                assert prop.get("ns") == FEDRAMP_NS, f"prop missing FedRAMP ns: {prop}"

    def test_inject_into_ssp_adds_resources(
        self, two_artifacts: list[EvidenceArtifact]
    ) -> None:
        from uiao_core.evidence.linker import EvidenceLinker

        ssp: dict = {"system-security-plan": {"metadata": {}, "back-matter": {"resources": []}}}
        linker = EvidenceLinker(two_artifacts)
        updated = linker.inject_into_ssp(ssp)
        resources = updated["system-security-plan"]["back-matter"]["resources"]
        assert len(resources) == 2

    def test_inject_into_ssp_no_duplicates(self, sample_artifact: EvidenceArtifact) -> None:
        from uiao_core.evidence.linker import EvidenceLinker

        ssp: dict = {"system-security-plan": {}}
        linker = EvidenceLinker([sample_artifact])
        linker.inject_into_ssp(ssp)
        # Inject again — same artifact should not be added twice
        linker.inject_into_ssp(ssp)
        resources = ssp["system-security-plan"]["back-matter"]["resources"]
        assert len(resources) == 1

    def test_inject_bare_ssp_dict(self, sample_artifact: EvidenceArtifact) -> None:
        """inject_into_ssp should also accept a bare SSP dict without the outer wrapper."""
        from uiao_core.evidence.linker import EvidenceLinker

        ssp: dict = {"metadata": {}}
        linker = EvidenceLinker([sample_artifact])
        linker.inject_into_ssp(ssp)
        assert "back-matter" in ssp

    def test_empty_linker_returns_empty_resources(self) -> None:
        from uiao_core.evidence.linker import EvidenceLinker

        linker = EvidenceLinker([])
        bm = linker.to_oscal_back_matter()
        assert bm["resources"] == []


# ---------------------------------------------------------------------------
# EvidenceBundler tests
# ---------------------------------------------------------------------------


class TestEvidenceBundler:
    def test_build_manifest_structure(self, two_artifacts: list[EvidenceArtifact]) -> None:
        from uiao_core.evidence.bundler import EvidenceBundler

        bundler = EvidenceBundler(two_artifacts, control_family="au")
        manifest = bundler.build_manifest()
        assert manifest["control_family"] == "au"
        assert manifest["artifact_count"] == 2
        assert len(manifest["artifacts"]) == 2
        # bundle_id must be a valid UUID
        uuid.UUID(manifest["bundle_id"])

    def test_build_bundle_model(self, two_artifacts: list[EvidenceArtifact]) -> None:
        from uiao_core.evidence.bundler import EvidenceBundler

        bundler = EvidenceBundler(two_artifacts)
        model = bundler.build_bundle_model()
        assert isinstance(model, EvidenceBundle)
        assert model.artifact_count() == 2

    def test_write_zip_creates_file(self, two_artifacts: list[EvidenceArtifact]) -> None:
        import zipfile

        from uiao_core.evidence.bundler import EvidenceBundler

        bundler = EvidenceBundler(two_artifacts)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "test_bundle.zip"
            result = bundler.write_zip(out)
            assert result.exists()
            with zipfile.ZipFile(result) as zf:
                names = zf.namelist()
            assert "manifest.json" in names
            assert "oscal-back-matter.json" in names

    def test_zip_oscal_back_matter_has_prop_ids(
        self, two_artifacts: list[EvidenceArtifact]
    ) -> None:
        """ZIP's oscal-back-matter.json must follow the prop:id rule."""
        import zipfile

        from uiao_core.evidence.bundler import EvidenceBundler

        bundler = EvidenceBundler(two_artifacts)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "bundle.zip"
            bundler.write_zip(out)
            with zipfile.ZipFile(out) as zf:
                bm = json.loads(zf.read("oscal-back-matter.json"))
        for resource in bm["resources"]:
            for prop in resource["props"]:
                assert "uuid" in prop
                uuid.UUID(prop["uuid"])

    def test_write_zip_include_files_skips_missing(
        self, two_artifacts: list[EvidenceArtifact]
    ) -> None:
        """include_files=True silently skips non-existent files."""
        from uiao_core.evidence.bundler import EvidenceBundler

        bundler = EvidenceBundler(two_artifacts)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "bundle.zip"
            # Should not raise even though artifact files don't exist on disk
            result = bundler.write_zip(out, include_files=True)
            assert result.exists()

    def test_empty_bundler(self) -> None:
        from uiao_core.evidence.bundler import EvidenceBundler

        bundler = EvidenceBundler([])
        manifest = bundler.build_manifest()
        assert manifest["artifact_count"] == 0


# ---------------------------------------------------------------------------
# EvidenceCollector integration tests
# ---------------------------------------------------------------------------


class TestEvidenceCollector:
    def test_import_package(self) -> None:
        from uiao_core.evidence import EvidenceBundler, EvidenceCollector, EvidenceLinker

        assert callable(EvidenceCollector)
        assert callable(EvidenceLinker)
        assert callable(EvidenceBundler)

    def test_collector_stub_returns_artifacts(self) -> None:
        from uiao_core.evidence.collector import AzureSentinelCollector, VulnScanCollector

        sentinel = AzureSentinelCollector()
        results = sentinel.collect()
        assert len(results) == 1
        assert results[0].control_refs == ["au-2", "au-9", "ir-4", "si-4"]

        vuln = VulnScanCollector()
        results2 = vuln.collect()
        assert len(results2) == 1
        assert "ra-5" in results2[0].control_refs

    def test_collector_default_runs_without_error(self) -> None:
        from uiao_core.evidence.collector import EvidenceCollector

        collector = EvidenceCollector.default()
        artifacts = collector.run()
        # Default collector has 5 connectors; ManualUpload returns [] if YAML missing
        assert isinstance(artifacts, list)
        # At minimum the 4 cloud stubs return 1 artifact each
        assert len(artifacts) >= 4

    def test_manual_upload_missing_yaml_returns_empty(self) -> None:
        from uiao_core.evidence.collector import ManualUploadCollector

        mc = ManualUploadCollector({"uploads_yaml": "/nonexistent/path/uploads.yaml"})
        results = mc.collect()
        assert results == []

    def test_collector_connector_error_does_not_propagate(self) -> None:
        """An exception in one connector should be swallowed; others still run."""
        from uiao_core.evidence.collector import BaseCollector, EvidenceCollector

        class BrokenConnector(BaseCollector):
            name = "broken"

            def collect(self) -> list[EvidenceArtifact]:
                raise RuntimeError("intentional test failure")

        class GoodConnector(BaseCollector):
            name = "good"

            def collect(self) -> list[EvidenceArtifact]:
                return [self._make_artifact(title="Good Artifact")]

        collector = EvidenceCollector(connectors=[BrokenConnector(), GoodConnector()])
        results = collector.run()
        assert len(results) == 1
        assert results[0].title == "Good Artifact"

    def test_vuln_scan_with_files(self, tmp_path: Path) -> None:
        """VulnScanCollector with real scan_files list returns one artifact per file."""
        from uiao_core.evidence.collector import VulnScanCollector

        f1 = tmp_path / "scan1.nessus"
        f1.touch()
        f2 = tmp_path / "scan2.xml"
        f2.touch()

        vc = VulnScanCollector({"scan_files": [str(f1), str(f2)]})
        results = vc.collect()
        assert len(results) == 2
        assert results[0].media_type == "application/xml"
        assert results[1].media_type == "application/xml"


# ---------------------------------------------------------------------------
# OSCAL SSP back-matter integrity test
# ---------------------------------------------------------------------------


class TestOSCALSSPBackMatter:
    def test_ssp_back_matter_has_resources(self) -> None:
        """The OSCAL SSP skeleton should now have non-empty back-matter."""
        ssp_path = Path("exports/oscal/uiao-ssp-skeleton.json")
        if not ssp_path.exists():
            pytest.skip("OSCAL SSP skeleton not found")
        with ssp_path.open() as f:
            ssp = json.load(f)
        resources = (
            ssp.get("system-security-plan", {})
            .get("back-matter", {})
            .get("resources", [])
        )
        assert len(resources) > 0, "back-matter resources should not be empty"

    def test_ssp_back_matter_props_have_uuid(self) -> None:
        """Every prop in back-matter resources must carry a UUIDv4 (prop:id rule)."""
        ssp_path = Path("exports/oscal/uiao-ssp-skeleton.json")
        if not ssp_path.exists():
            pytest.skip("OSCAL SSP skeleton not found")
        with ssp_path.open() as f:
            ssp = json.load(f)
        resources = (
            ssp.get("system-security-plan", {})
            .get("back-matter", {})
            .get("resources", [])
        )
        for resource in resources:
            for prop in resource.get("props", []):
                assert "uuid" in prop, f"prop missing uuid in resource {resource['uuid']}: {prop}"
                uuid.UUID(prop["uuid"])  # validate it is a real UUID
