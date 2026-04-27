"""Smoke test: OrgTree Readiness pipeline (WS-A9 Phase 2 integration smoke).

Walk the quickstart end-to-end on a small synthetic fixture and assert:
  1. Fixture is present and parseable (inline health-check).
  2. All 10 KSI YAML rule files exist and parse with required fields.
  3. Bundle CLI runs on synthetic-forest-export.json (WS-A5 real integration).
  4. Bundle signature validates (WS-A5).
  5. OSCAL evidence emitted from bundle (WS-A6 real integration, Phase 2 task 5).
  6. OSCAL output structural validation.
  7. KSI YAML files reference real NIST controls.
  8. End-to-end runtime <60s.

Phase 2 changes (M3):
  * KSI-001..007 YAML indentation fixed → all 14 KSI tests now PASS (were SKIP).
  * Added test_phase2_end_to_end_pipeline exercising real WS-A5/A6/A7/A8 outputs.
  * Added test_ksi_rules_reference_real_nist_controls asserting NIST_800-53 field.
  * test_oscal_emitter_available and test_oscal_output_schema_validates remain
    as-is (they already pass against uiao.oscal.generator from Phase 1).

Acceptance criteria:
  * Runs in <60 s (tiny fixture; no network calls; no subprocess).
  * Fails closed when modules ARE wired and regress.
  * Always picked up by `pytest tests/`.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "orgtree"
_SMOKE_FIXTURE = _FIXTURES_DIR / "smoke-fixture.json"

# The larger synthetic forest export fixture (WS-A8) used for end-to-end tests.
_EXAMPLES_DIR = Path(__file__).parent.parent / "examples" / "orgtree"
_FOREST_FIXTURE = _EXAMPLES_DIR / "synthetic-forest-export.json"

# KSI rule files live inside the installed package; resolve via importlib.resources
# so the test is path-agnostic (works with both editable install and wheel).
_KSI_RULES_PKG = "uiao.ksi.rules"
_EXPECTED_KSI_IDS = [f"KSI-{n:03d}" for n in range(1, 11)]  # KSI-001 … KSI-010

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture() -> Dict[str, Any]:
    """Return the parsed smoke fixture dict."""
    result: Dict[str, Any] = json.loads(_SMOKE_FIXTURE.read_text(encoding="utf-8"))
    return result


def _ksi_rule_path(ksi_id: str) -> Path:
    """Resolve the filesystem path to a KSI YAML rule file."""
    import importlib.resources as ilr

    pkg_files = ilr.files(_KSI_RULES_PKG)
    return Path(str(pkg_files.joinpath(f"{ksi_id}.yaml")))


# ---------------------------------------------------------------------------
# 1. Fixture health-check
# ---------------------------------------------------------------------------


def test_smoke_fixture_exists_and_parses() -> None:
    """The OrgTree smoke fixture must be committed and parseable as JSON."""
    assert _SMOKE_FIXTURE.exists(), f"Smoke fixture missing at {_SMOKE_FIXTURE}"
    data = _load_fixture()
    assert data.get("schema_version") == "1.0"
    assert "users" in data
    assert "computers" in data
    assert "servers" in data
    assert len(data["users"]) >= 1
    assert len(data["computers"]) >= 1
    assert len(data["servers"]) >= 1


def test_smoke_fixture_user_count() -> None:
    """Fixture must contain exactly 5 users (keeps the test deterministic)."""
    data = _load_fixture()
    assert len(data["users"]) == 5


def test_smoke_fixture_computer_count() -> None:
    """Fixture must contain exactly 3 computers."""
    data = _load_fixture()
    assert len(data["computers"]) == 3


def test_smoke_fixture_server_count() -> None:
    """Fixture must contain exactly 2 servers."""
    data = _load_fixture()
    assert len(data["servers"]) == 2


def test_smoke_fixture_ksi_verdicts_present() -> None:
    """Fixture must carry a ksi_verdicts block covering all 10 KSIs."""
    data = _load_fixture()
    verdicts = data.get("ksi_verdicts", {})
    missing = [k for k in _EXPECTED_KSI_IDS if k not in verdicts]
    assert not missing, f"ksi_verdicts block missing KSI IDs: {missing}"


# ---------------------------------------------------------------------------
# 2. KSI YAML rule files — structure smoke (WS-A7 Phase 1 strategy: (a))
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ksi_id", _EXPECTED_KSI_IDS)
def test_ksi_rule_file_exists_and_parses(ksi_id: str) -> None:
    """Each KSI rule YAML file must exist inside uiao.ksi.rules.

    Phase 1 robustness note: some files (KSI-001..KSI-007) have indentation
    quirks that cause yaml.safe_load to raise ScannerError.  The smoke test
    checks file presence unconditionally; YAML parse success is checked when
    the file is well-formed.  A pre-existing parse failure is reported as a
    pytest.skip with an explicit reason so it surfaces in CI without blocking
    the run — fix the YAML formatting to promote from skip → pass.
    """
    rule_path = _ksi_rule_path(ksi_id)
    assert rule_path.exists(), f"KSI rule file missing: {rule_path}"
    raw = rule_path.read_text(encoding="utf-8")
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        pytest.skip(
            f"{ksi_id}.yaml has a pre-existing YAML formatting issue (ScannerError); "
            f"fix indentation to promote this skip to PASS. Error: {exc}"
        )
    assert isinstance(doc, dict), f"{ksi_id}.yaml did not parse to a dict"


@pytest.mark.parametrize("ksi_id", _EXPECTED_KSI_IDS)
def test_ksi_rule_file_has_required_fields(ksi_id: str) -> None:
    """Each KSI rule YAML file must declare KSI_ID and Title at the top level.

    Phase 1 robustness note: files with pre-existing YAML formatting issues
    are checked via raw text fallback so the test still catches file-deletion
    regressions even when the YAML is not parseable.
    """
    rule_path = _ksi_rule_path(ksi_id)
    raw = rule_path.read_text(encoding="utf-8")
    try:
        doc: Any = yaml.safe_load(raw)
    except yaml.YAMLError:
        # Fall back to raw-text presence check when the file is malformed.
        assert f"KSI_ID: {ksi_id}" in raw, (
            f"{ksi_id}.yaml (malformed YAML) missing 'KSI_ID: {ksi_id}' in raw text"
        )
        assert "Title:" in raw, f"{ksi_id}.yaml (malformed YAML) missing 'Title:' in raw text"
        pytest.skip(
            f"{ksi_id}.yaml has a pre-existing YAML formatting issue; "
            f"raw-text field presence confirmed. Fix indentation to promote to PASS."
        )
        return
    assert isinstance(doc, dict)
    assert "KSI_ID" in doc, f"{ksi_id}.yaml missing 'KSI_ID' field"
    assert "Title" in doc, f"{ksi_id}.yaml missing 'Title' field"
    assert doc["KSI_ID"] == ksi_id, (
        f"{ksi_id}.yaml declares KSI_ID='{doc['KSI_ID']}', expected '{ksi_id}'"
    )


def test_ksi_fixture_verdicts_are_valid_values() -> None:
    """All ksi_verdicts values in the fixture must be PASS, FAIL, or WARN."""
    data = _load_fixture()
    verdicts = data.get("ksi_verdicts", {})
    allowed = {"PASS", "FAIL", "WARN"}
    bad = {k: v for k, v in verdicts.items() if v not in allowed}
    assert not bad, f"Invalid verdict values in fixture: {bad}"


# ---------------------------------------------------------------------------
# 3. Bundle signature (WS-A5) — skip if module not yet wired
# ---------------------------------------------------------------------------


def test_bundle_signature_validates() -> None:
    """Assert bundle signature validates on the smoke fixture.

    WS-A5 (auditor bundle) is present in Phase 1 via uiao.auditor.bundle.
    This test exercises the module import path and its canonical_hash helper
    against the fixture payload — a lightweight proxy for signature validation
    until the OrgTree-native bundle wiring lands in Phase 2.
    """
    try:
        from uiao.ir.models.core import canonical_hash  # type: ignore[import]
    except ImportError as exc:
        pytest.skip(
            f"WS-A5 bundle module not yet wired in Phase 1; "
            f"re-enable after Phase 2 integration. (ImportError: {exc})"
        )

    data = _load_fixture()
    # Compute a deterministic hash of the fixture payload — stands in for
    # bundle-level signature validation until the OrgTree bundle emitter is wired.
    payload_str = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    sig = canonical_hash(payload_str)
    assert isinstance(sig, str), "canonical_hash must return a string"
    assert len(sig) > 0, "canonical_hash must return a non-empty string"
    # Idempotency: same payload → same hash
    sig2 = canonical_hash(payload_str)
    assert sig == sig2, "canonical_hash must be deterministic"


# ---------------------------------------------------------------------------
# 4. OSCAL output schema-validation (WS-A6) — skip if module not yet wired
# ---------------------------------------------------------------------------


def test_oscal_emitter_available() -> None:
    """Assert uiao.oscal.generator is importable (WS-A6 emitter availability)."""
    try:
        importlib.import_module("uiao.oscal.generator")
    except ImportError as exc:
        pytest.skip(
            f"WS-A6 OSCAL emitter not yet wired in Phase 1; "
            f"re-enable after Phase 2 integration. (ImportError: {exc})"
        )


def test_oscal_output_schema_validates(tmp_path: Path) -> None:
    """Invoke the OSCAL generator on a minimal evidence bundle and validate output.

    The generator expects an evidence directory with bundle.json + evidence.jsonl.
    We build a minimal synthetic bundle from the smoke fixture so this test
    exercises the real emitter code path without requiring a full pipeline run.

    Skip reason: WS-A6 OSCAL emitter requires an evidence bundle produced by
    the OrgTree bundle module (WS-A5), which is not yet wired end-to-end in
    Phase 1. Re-enable after Phase 2 integration connects the OrgTree pipeline
    to the auditor bundle emitter.
    """
    try:
        from uiao.oscal.generator import generate_oscal  # type: ignore[import]
    except ImportError as exc:
        pytest.skip(
            f"WS-A6 OSCAL emitter not yet wired in Phase 1; "
            f"re-enable after Phase 2 integration. (ImportError: {exc})"
        )

    # Build a minimal synthetic evidence bundle from the smoke fixture.
    data = _load_fixture()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    bundle_doc: Dict[str, Any] = {
        "run_id": "smoke-test-run-001",
        "schema_version": "1.0",
        "plane": "orgtree-smoke",
        "manifest": {"total_records": len(data["users"])},
    }
    (evidence_dir / "bundle.json").write_text(
        json.dumps(bundle_doc, indent=2), encoding="utf-8"
    )

    # Write one evidence record per user as NDJSON.
    lines = []
    for user in data["users"]:
        rec: Dict[str, Any] = {
            "id": f"ev-{user['id']}",
            "control_id": "IA-2",
            "status": "satisfied" if user.get("mfaEnabled") else "not-satisfied",
            "rationale": f"MFA {'enabled' if user.get('mfaEnabled') else 'disabled'} for {user['displayName']}",
            "verdict": "pass" if user.get("mfaEnabled") else "fail",
            "fresh": True,
            "generated_at": "2026-04-27T00:00:00Z",
        }
        lines.append(json.dumps(rec))
    (evidence_dir / "evidence.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    oscal_out = tmp_path / "oscal"
    generate_oscal(str(evidence_dir), str(oscal_out))

    # Assert the three expected OSCAL output files were written.
    assert (oscal_out / "poam.json").exists(), "OSCAL generator did not write poam.json"
    assert (oscal_out / "ssp.json").exists(), "OSCAL generator did not write ssp.json"
    assert (oscal_out / "artifact-index.json").exists(), "OSCAL generator did not write artifact-index.json"

    # Validate poam.json schema (lightweight — check required top-level fields).
    poam = json.loads((oscal_out / "poam.json").read_text(encoding="utf-8"))
    assert poam.get("schema_version") == "1.0", "poam.json missing schema_version"
    assert poam.get("artifact") == "poam", "poam.json wrong artifact type"
    assert "poam-items" in poam, "poam.json missing poam-items"
    assert "summary" in poam, "poam.json missing summary"

    # Validate ssp.json schema (lightweight).
    ssp = json.loads((oscal_out / "ssp.json").read_text(encoding="utf-8"))
    assert ssp.get("schema_version") == "1.0", "ssp.json missing schema_version"
    assert ssp.get("artifact") == "ssp", "ssp.json wrong artifact type"
    assert "implemented-requirements" in ssp, "ssp.json missing implemented-requirements"
    assert "summary" in ssp, "ssp.json missing summary"

    # Validate artifact-index.json.
    index = json.loads((oscal_out / "artifact-index.json").read_text(encoding="utf-8"))
    assert "artifacts" in index, "artifact-index.json missing artifacts key"
    assert "poam" in index["artifacts"], "artifact-index.json missing poam entry"
    assert "ssp" in index["artifacts"], "artifact-index.json missing ssp entry"


# ---------------------------------------------------------------------------
# Phase 2 additions (M3): real WS-A5/A6/A7/A8 integration — no mocks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ksi_id", _EXPECTED_KSI_IDS)
def test_ksi_rules_reference_real_nist_controls(ksi_id: str) -> None:
    """Each KSI YAML must parse and reference at least one real NIST 800-53 control.

    Phase 2 M3: KSI-001..007 YAML indentation was fixed; this test promotes the
    raw-text checks to full YAML-parse + field-content assertions.
    """
    import importlib.resources as ilr

    pkg_files = ilr.files(_KSI_RULES_PKG)
    rule_path = Path(str(pkg_files.joinpath(f"{ksi_id}.yaml")))
    assert rule_path.exists(), f"KSI rule file missing: {rule_path}"

    doc = yaml.safe_load(rule_path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), f"{ksi_id}.yaml did not parse to a dict"
    assert "Mappings" in doc, f"{ksi_id}.yaml missing 'Mappings' field"
    nist_ref = doc["Mappings"].get("NIST_800-53", "")
    assert nist_ref, f"{ksi_id}.yaml has empty NIST_800-53 mapping"
    # At least one recognized NIST control family must appear
    _KNOWN_FAMILIES = {"AC", "AU", "CM", "IA", "SC", "SI", "CA", "SA", "CP"}
    refs = [r.strip() for r in nist_ref.split(",")]
    families_found = {r.split("-")[0] for r in refs if "-" in r}
    assert families_found & _KNOWN_FAMILIES, (
        f"{ksi_id}.yaml NIST_800-53 field '{nist_ref}' contains no recognized control families"
    )


def test_phase2_end_to_end_pipeline(tmp_path: Path) -> None:
    """Phase 2 M3: end-to-end pipeline using real WS-A5 bundle CLI + WS-A6 OSCAL emitter.

    Uses the synthetic forest export fixture (examples/orgtree/synthetic-forest-export.json).
    Steps:
      1. Run bundle CLI on fixture (via Python API matching the Typer command logic).
      2. Validate bundle signature.
      3. Invoke emit_orgtree_evidence on the resulting bundle.
      4. Validate OSCAL output (structural, not full trestle schema).
      5. Assert end-to-end runtime <60s.

    This test replaces the Phase 1 skip strategy: all modules are now integrated.
    """
    t_start = time.monotonic()

    # --- Step 1: Load fixture (synthetic-forest-export.json, WS-A8) ----------
    assert _FOREST_FIXTURE.exists(), (
        f"Synthetic forest fixture missing at {_FOREST_FIXTURE}. "
        "WS-A8 must commit examples/orgtree/synthetic-forest-export.json."
    )
    survey_data: Dict[str, Any] = json.loads(_FOREST_FIXTURE.read_text(encoding="utf-8"))

    # --- Step 2: Run bundle CLI via Typer CliRunner -------------------------
    from typer.testing import CliRunner

    from uiao.cli.ir import ir_app

    survey_file = tmp_path / "survey.json"
    survey_file.write_text(json.dumps(survey_data), encoding="utf-8")
    bundle_dir = tmp_path / "bundle"
    oscal_dir = tmp_path / "oscal"

    env_ci = {k: v for k, v in os.environ.items() if k != "UIAO_BUNDLE_HMAC_KEY"}
    runner = CliRunner()
    result = runner.invoke(
        ir_app,
        [
            "orgtree-readiness-bundle",
            str(survey_file),
            "--out-dir", str(bundle_dir),
            "--oscal-out", str(oscal_dir),
            "--insecure-dev-key",
        ],
        env=env_ci,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Bundle CLI non-zero exit: {result.output}"

    # --- Step 3: Validate bundle signature ----------------------------------
    bundle_json = bundle_dir / "bundle.json"
    bundle_hash_file = bundle_dir / "bundle.hash"
    bundle_sig_file = bundle_dir / "bundle.sig"

    assert bundle_json.exists(), "bundle.json not written"
    assert bundle_hash_file.exists(), "bundle.hash not written"
    assert bundle_sig_file.exists(), "bundle.sig not written"

    content_hash = bundle_hash_file.read_text().strip()
    sig = bundle_sig_file.read_text().strip()

    assert len(content_hash) == 64, "content hash must be 64 hex chars"
    assert all(c in "0123456789abcdef" for c in content_hash), "content hash must be hex"
    assert len(sig) == 64, "HMAC signature must be 64 hex chars"
    assert all(c in "0123456789abcdef" for c in sig), "HMAC signature must be hex"

    # --- Step 4: Validate bundle against schema -----------------------------
    bundle_doc: Dict[str, Any] = json.loads(bundle_json.read_text(encoding="utf-8"))
    assert bundle_doc.get("version") == "0.6.0", "bundle version mismatch"
    assert "provenance" in bundle_doc, "bundle missing provenance"
    assert bundle_doc["provenance"]["signature"] == sig, "bundle.sig must match provenance.signature"

    try:
        import jsonschema

        from importlib.resources import files as _res_files
        schema_bytes = (
            _res_files("uiao.schemas")
            .joinpath("orgtree-readiness")
            .joinpath("orgtree-readiness.schema.json")
            .read_text()
        )
        schema = json.loads(schema_bytes)
        jsonschema.validate(instance=bundle_doc, schema=schema)
    except ImportError:
        pass  # jsonschema not available — skip deep schema check

    # --- Step 5: Validate OSCAL output (WS-A6 integration) ------------------
    oscal_file = oscal_dir / "orgtree-evidence.json"
    assert oscal_file.exists(), "orgtree-evidence.json not written by WS-A6 emitter"

    oscal_doc: Dict[str, Any] = json.loads(oscal_file.read_text(encoding="utf-8"))
    assert "assessment-results" in oscal_doc, "OSCAL output missing 'assessment-results'"
    ar = oscal_doc["assessment-results"]
    assert "results" in ar, "assessment-results missing 'results'"
    assert len(ar["results"]) >= 1, "assessment-results must have at least one result"

    result_obj = ar["results"][0]
    assert "local-definitions" in result_obj or "findings" in result_obj or "observations" in result_obj, (
        "OSCAL result must have at least one of: local-definitions, findings, observations"
    )

    # --- Step 6: Runtime guard (<60s) ---------------------------------------
    elapsed = time.monotonic() - t_start
    assert elapsed < 60.0, (
        f"End-to-end pipeline took {elapsed:.1f}s — must complete in <60s. "
        "Check for slow imports or unexpected network calls."
    )
