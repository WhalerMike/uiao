"""Tests for the vendor overlay loader in scripts/generate_docs.py."""

import os
import sys

# Ensure the scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from uiao_core.generators.docs import DATA_DIR, OVERLAYS_DIR, _merge_by_key, apply_overlay
from generate_docs import load_overlays

# ---------------------------------------------------------------------------
# Unit tests: _merge_by_key
# ---------------------------------------------------------------------------


class TestMergeByKey:
    def test_updates_matching_entry(self):
        base = [{"id": "identity", "subtitle": "Generic IdP", "foo": "bar"}]
        overlay = [{"id": "identity", "subtitle": "Entra ID"}]
        result = _merge_by_key(base, overlay, "id")
        assert len(result) == 1
        assert result[0]["subtitle"] == "Entra ID"
        assert result[0]["foo"] == "bar"  # non-overlapping key preserved

    def test_appends_new_entry(self):
        base = [{"id": "identity", "subtitle": "Generic IdP"}]
        overlay = [{"id": "network", "subtitle": "Cisco SD-WAN"}]
        result = _merge_by_key(base, overlay, "id")
        assert len(result) == 2
        assert result[1]["id"] == "network"

    def test_preserves_original_order(self):
        base = [
            {"id": "identity", "subtitle": "A"},
            {"id": "network", "subtitle": "B"},
        ]
        overlay = [{"id": "network", "subtitle": "Cisco"}]
        result = _merge_by_key(base, overlay, "id")
        assert result[0]["id"] == "identity"
        assert result[1]["id"] == "network"
        assert result[1]["subtitle"] == "Cisco"

    def test_no_overlay_unchanged(self):
        base = [{"id": "identity", "subtitle": "Generic IdP"}]
        result = _merge_by_key(base, [], "id")
        assert result == base

    def test_empty_base_with_overlay(self):
        base = []
        overlay = [{"id": "identity", "subtitle": "Entra ID"}]
        result = _merge_by_key(base, overlay, "id")
        assert len(result) == 1
        assert result[0]["subtitle"] == "Entra ID"


# ---------------------------------------------------------------------------
# Unit tests: apply_overlay
# ---------------------------------------------------------------------------


class TestApplyOverlay:
    def _make_context(self):
        """Return a minimal context dict with a control_planes structure."""
        return {
            "control_planes": {
                "control_planes": [
                    {"id": "identity", "subtitle": "Identity Provider", "components": []},
                    {"id": "network", "subtitle": "SD-WAN Platform", "components": []},
                ],
                "fedramp_20x_control_plane_alignment": [
                    {"plane_id": "identity", "evidence_source": "Generic IdP logs"},
                    {"plane_id": "network", "evidence_source": "Generic network logs"},
                ],
            }
        }

    def test_control_plane_subtitle_overridden(self):
        ctx = self._make_context()
        overlay = {"control_plane_overrides": [{"id": "identity", "subtitle": "Entra ID + ICAM + Zero Trust"}]}
        apply_overlay(ctx, overlay)
        planes = ctx["control_planes"]["control_planes"]
        identity = next(p for p in planes if p["id"] == "identity")
        assert identity["subtitle"] == "Entra ID + ICAM + Zero Trust"

    def test_fedramp_evidence_overridden(self):
        ctx = self._make_context()
        overlay = {
            "fedramp_alignment_overrides": [
                {"plane_id": "identity", "evidence_source": "Microsoft Entra ID sign-in and risk logs"}
            ]
        }
        apply_overlay(ctx, overlay)
        alignment = ctx["control_planes"]["fedramp_20x_control_plane_alignment"]
        identity = next(a for a in alignment if a["plane_id"] == "identity")
        assert identity["evidence_source"] == "Microsoft Entra ID sign-in and risk logs"

    def test_overlay_meta_ignored(self):
        ctx = self._make_context()
        overlay = {
            "overlay_meta": {"vendor": "test", "product": "test"},
            "control_plane_overrides": [],
        }
        apply_overlay(ctx, overlay)
        assert "overlay_meta" not in ctx

    def test_non_overlapping_plane_unchanged(self):
        ctx = self._make_context()
        overlay = {"control_plane_overrides": [{"id": "identity", "subtitle": "Entra ID"}]}
        apply_overlay(ctx, overlay)
        planes = ctx["control_planes"]["control_planes"]
        network = next(p for p in planes if p["id"] == "network")
        assert network["subtitle"] == "SD-WAN Platform"

    def test_multiple_overlays_accumulate(self):
        ctx = self._make_context()
        overlay_a = {"control_plane_overrides": [{"id": "identity", "subtitle": "Entra ID"}]}
        overlay_b = {"control_plane_overrides": [{"id": "network", "subtitle": "Cisco SD-WAN"}]}
        apply_overlay(ctx, overlay_a)
        apply_overlay(ctx, overlay_b)
        planes = ctx["control_planes"]["control_planes"]
        assert next(p for p in planes if p["id"] == "identity")["subtitle"] == "Entra ID"
        assert next(p for p in planes if p["id"] == "network")["subtitle"] == "Cisco SD-WAN"


# ---------------------------------------------------------------------------
# Integration test: all overlays active → original vendor names restored
# ---------------------------------------------------------------------------


class TestOverlayIntegration:
    def test_all_overlays_restore_vendor_names(self):
        """With all default overlays active, vendor-specific names should be present.

        Uses control-planes.yml loaded directly (as generate_atlas.py does) so
        the context structure is ``{"control_planes": {full dict}}`` rather than
        being overwritten by program.yml's spread keys.
        """
        import yaml as _yaml

        with open(DATA_DIR / "control-planes.yml", encoding="utf-8") as fh:
            content = _yaml.safe_load(fh)

        # Mirror generate_atlas.py's loading style
        context = {"control_planes": content}
        context = load_overlays(context)

        cp_dict = context.get("control_planes", {})
        assert isinstance(cp_dict, dict), "control_planes key should be a dict"

        planes = {p["id"]: p for p in cp_dict.get("control_planes", [])}

        # Microsoft Entra ID overlay should restore identity plane subtitle
        assert planes["identity"]["subtitle"] == "Entra ID + ICAM + Zero Trust"
        # First identity component should be Microsoft Entra ID
        identity_names = [c["name"] for c in planes["identity"].get("components", [])]
        assert "Microsoft Entra ID" in identity_names

        # Cisco SD-WAN overlay should restore network plane subtitle
        assert planes["network"]["subtitle"] == "Cisco Catalyst SD-WAN (Viptela/vManage)"
        network_names = [c["name"] for c in planes["network"].get("components", [])]
        assert "vManage" in network_names

        # Infoblox overlay should restore addressing plane subtitle
        assert planes["addressing"]["subtitle"] == "InfoBlox IPAM"
        addressing_names = [c["name"] for c in planes["addressing"].get("components", [])]
        assert "InfoBlox IPAM" in addressing_names

        # Sentinel overlay should restore telemetry SIEM component
        telemetry_names = [c["name"] for c in planes["telemetry"].get("components", [])]
        assert "Splunk / Sentinel" in telemetry_names

    def test_fedramp_alignment_updated_via_top_level_key(self):
        """Overlay should update fedramp_20x_control_plane_alignment at the top level.

        This covers the generate_docs.py context where data.update() spreads
        control-planes.yml's keys at the top level of the context dict.
        """
        import yaml as _yaml

        with open(DATA_DIR / "control-planes.yml", encoding="utf-8") as fh:
            content = _yaml.safe_load(fh)
        # Simulate generate_docs.py: spread keys at top level
        context = dict(content)
        context = load_overlays(context)

        alignment = {a["plane_id"]: a for a in context["fedramp_20x_control_plane_alignment"]}
        assert alignment["identity"]["evidence_source"] == "Microsoft Entra ID sign-in and risk logs"
        assert alignment["addressing"]["evidence_source"] == "Infoblox BloxOne DDI API - deterministic IP inventory"
        assert alignment["network"]["evidence_source"] == "Cisco Catalyst SD-WAN telemetry + Microsoft INR feed"

    def test_no_overlays_uses_generic_names(self, tmp_path, monkeypatch):
        """With no overlays active, generic placeholder names should be used."""
        # Write a config with empty overlay list
        cfg = tmp_path / "overlay-config.yml"
        cfg.write_text("active_overlays: []\n", encoding="utf-8")

        import generate_docs as gd

        original_data_dir = gd.DATA_DIR
        monkeypatch.setattr(gd, "DATA_DIR", tmp_path)
        import uiao_core.generators.docs as _docs_mod
        monkeypatch.setattr(_docs_mod, "OVERLAYS_DIR", tmp_path / "overlays")

        # Load control-planes.yml directly and apply empty overlays
        import yaml as _yaml

        real_cp = original_data_dir / "control-planes.yml"
        with real_cp.open("r", encoding="utf-8") as fh:
            content = _yaml.safe_load(fh)
        context = {"control_planes": content}

        context = gd.load_overlays(context)

        planes = {p["id"]: p for p in context["control_planes"]["control_planes"]}
        # Without microsoft overlay, identity subtitle should be generic
        assert planes["identity"]["subtitle"] == "Identity Provider + ICAM + Zero Trust"
        # Without cisco overlay, network subtitle should be generic
        assert planes["network"]["subtitle"] == "SD-WAN Platform"
        # Without infoblox overlay, addressing subtitle should be generic
        assert planes["addressing"]["subtitle"] == "IPAM Platform"
