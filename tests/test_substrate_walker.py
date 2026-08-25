"""Tests for the substrate repo-walker (src/uiao/substrate/walker.py)
and the `uiao substrate walk` / `uiao substrate drift` CLI commands.

Happy paths and failure modes. Fixtures synthesize a minimal post-ADR-032
workspace on disk at tmp_path; module names (`uiao`, `tests`, `docs`)
match the real substrate topology.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from uiao.cli.substrate import substrate_app as app
from uiao.substrate.walker import walk_substrate

runner = CliRunner()


MANIFEST_BODY = {
    "metadata": {
        "document_id": "UIAO_200",
        "title": "UIAO Substrate Manifest",
        "version": "2.0",
        "status": "Current",
        "classification": "OPERATIONAL",
        "owner": "test",
        "created_at": "2026-04-17",
        "updated_at": "2026-04-23",
        "boundary": "GCC-Moderate",
    },
    "workspace": {"root_env": "UIAO_WORKSPACE_ROOT"},
    "github": {"root": "https://example.com/test/uiao", "default_branch": "main"},
    "modules": [
        {"name": "uiao", "path": "src/uiao", "role": "package", "canon_consumer": False},
        {"name": "tests", "path": "tests", "role": "consumer", "canon_consumer": True},
        {"name": "docs", "path": "docs", "role": "consumer", "canon_consumer": True},
    ],
    "drift_scan": {
        "classes": ["DRIFT-SCHEMA", "DRIFT-PROVENANCE"],
        "roots": ["src/uiao", "tests", "docs"],
    },
    "registry_refs": {"document_registry": "src/uiao/canon/document-registry.yaml"},
}

CONTRACT_BODY = {
    "metadata": {
        "document_id": "UIAO_201",
        "title": "UIAO Workspace Contract",
        "version": "2.0",
        "status": "Current",
        "classification": "OPERATIONAL",
        "owner": "test",
        "created_at": "2026-04-17",
        "updated_at": "2026-04-23",
        "boundary": "GCC-Moderate",
    },
    "local": {"root_env": "UIAO_WORKSPACE_ROOT"},
    "remote": {"root": "https://example.com/test/uiao", "default_branch": "main"},
    "module_paths": {"uiao": "src/uiao", "tests": "tests", "docs": "docs"},
    "drift_scan_roots": ["src/uiao", "tests", "docs"],
    "build_outputs": {},
}


def _write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def _make_workspace(tmp_path: Path, *, with_contract: bool = True, doc_exists: bool = True) -> Path:
    """Synthesize a minimal valid substrate workspace on disk."""
    for mod in ("src/uiao", "tests", "docs"):
        (tmp_path / mod).mkdir(parents=True, exist_ok=True)
    _write_yaml(tmp_path / "src/uiao/canon/substrate-manifest.yaml", MANIFEST_BODY)
    if with_contract:
        _write_yaml(tmp_path / "src/uiao/canon/workspace-contract.yaml", CONTRACT_BODY)
    registry = {
        "schema-version": "1.0.0",
        "updated": "2026-04-23",
        "documents": [
            {
                "id": "UIAO_200",
                "path": "src/uiao/canon/substrate-manifest.yaml",
                "title": "UIAO Substrate Manifest",
                "status": "Current",
                "classification": "OPERATIONAL",
            }
        ],
    }
    # The contract file declares document_id UIAO_201, so it needs a registry
    # row whenever it is written: the reverse registry walk reads canon ->
    # registry and reports a declared-but-unallocated id as DRIFT-PROVENANCE.
    # Registering it unconditionally would instead trip the forward walk when
    # the fixture omits the file. In the real workspace both are registered.
    if with_contract:
        registry["documents"].append(
            {
                "id": "UIAO_201",
                "path": "src/uiao/canon/workspace-contract.yaml",
                "title": "UIAO Workspace Contract",
                "status": "Current",
                "classification": "OPERATIONAL",
            }
        )
    if not doc_exists:
        registry["documents"].append(
            {
                "id": "UIAO_999",
                "path": "src/uiao/canon/does-not-exist.md",
                "title": "Intentionally missing",
                "status": "Current",
                "classification": "OPERATIONAL",
            }
        )
    _write_yaml(tmp_path / "src/uiao/canon/document-registry.yaml", registry)
    return tmp_path


def _write_canon_doc(root: Path, rel_path: str, doc_id: str, body: str) -> Path:
    """Write a canon document and register its `document_id`.

    Every canon document that declares an id must have a registry row — that is
    the invariant the reverse registry walk enforces. Fixtures that write a doc
    without registering it would trip DRIFT-PROVENANCE on an id that is
    incidental to what the test is actually asserting, so the two writes are
    kept together here.
    """
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ndocument_id: {doc_id}\n---\n{body}")

    registry_path = root / "src/uiao/canon/document-registry.yaml"
    registry = yaml.safe_load(registry_path.read_text())
    registry["documents"].append(
        {
            "id": doc_id,
            "path": rel_path,
            "title": f"Fixture {doc_id}",
            "status": "Current",
            "classification": "CANONICAL",
        }
    )
    _write_yaml(registry_path, registry)
    return path


def test_walker_happy_path(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    report = walk_substrate(workspace_root=root)
    assert report.ok, report.findings
    assert report.manifest_present
    assert report.contract_present
    assert report.modules_checked == 3
    # Two registry rows walked forward (manifest + contract), and the same two
    # files walked back from canon to the registry.
    assert report.documents_checked == 2
    assert report.document_ids_checked == 2


def test_walker_detects_missing_module(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    # Remove a declared module path
    (root / "docs").rmdir()
    report = walk_substrate(workspace_root=root)
    assert not report.ok
    schema_findings = [f for f in report.findings if f.drift_class == "DRIFT-SCHEMA"]
    assert schema_findings, report.findings
    assert any("docs" in f.path for f in schema_findings)


def test_walker_detects_missing_canon_document(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, doc_exists=False)
    report = walk_substrate(workspace_root=root)
    assert not report.ok
    provenance = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE"]
    assert provenance
    assert any("does-not-exist" in f.path for f in provenance)


def test_walker_missing_manifest_yields_p1(tmp_path: Path) -> None:
    root = tmp_path
    report = walk_substrate(workspace_root=root)
    assert not report.manifest_present
    assert any(f.drift_class == "DRIFT-SCHEMA" and f.severity == "P1" for f in report.findings)


def test_walker_optional_contract(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, with_contract=False)
    report = walk_substrate(workspace_root=root)
    assert report.ok, report.findings
    assert report.contract_present is False


def test_cli_substrate_walk_happy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_workspace(tmp_path)
    monkeypatch.setenv("UIAO_WORKSPACE_ROOT", str(root))
    result = runner.invoke(app, ["walk"])
    assert result.exit_code == 0, result.stdout
    assert "PASS" in result.stdout


def test_cli_substrate_walk_fail(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    (root / "docs").rmdir()
    result = runner.invoke(app, ["walk", "--workspace-root", str(root)])
    assert result.exit_code == 1
    assert "FAIL" in result.stdout
    assert "DRIFT-SCHEMA" in result.stdout


def test_cli_substrate_walk_json(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    result = runner.invoke(app, ["walk", "--workspace-root", str(root), "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["modules_checked"] == 3


def test_cli_substrate_drift_passes(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    result = runner.invoke(app, ["drift", "--workspace-root", str(root)])
    assert result.exit_code == 0
    assert "PASS" in result.stdout


def test_cli_substrate_drift_fails(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, doc_exists=False)
    result = runner.invoke(app, ["drift", "--workspace-root", str(root)])
    assert result.exit_code == 1
    assert "FAIL" in result.stdout


def test_walker_detects_missing_code_reference(tmp_path: Path) -> None:
    """Canon document cites a code path (src/uiao/ or retired impl/) that
    does not exist on disk."""
    root = _make_workspace(tmp_path)
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/fake-spec.md",
        "UIAO_999",
        "# Fake spec\n\nThe implementation lives at `src/uiao/nonexistent/module.py`.\n",
    )
    report = walk_substrate(workspace_root=root)
    assert not report.ok
    prov = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE" and "nonexistent" in f.path]
    assert prov, report.findings
    assert prov[0].severity == "P2"
    assert report.code_refs_checked >= 1


def test_walker_detects_legacy_impl_reference(tmp_path: Path) -> None:
    """Any surviving `impl/...` citation in canon is dangling by definition
    post-ADR-032 and should be flagged."""
    root = _make_workspace(tmp_path)
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/legacy-spec.md",
        "UIAO_999",
        "# Legacy spec\n\nHistorical reference: `impl/src/uiao/impl/retired.py`.\n",
    )
    report = walk_substrate(workspace_root=root)
    prov = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE" and "impl/" in f.path]
    assert prov, report.findings
    assert prov[0].severity == "P2"


def test_walker_accepts_valid_code_reference(tmp_path: Path) -> None:
    """Canon reference to an existing code path under src/uiao/ is clean."""
    root = _make_workspace(tmp_path)
    real = root / "src/uiao/real_module.py"
    real.parent.mkdir(parents=True, exist_ok=True)
    real.write_text("# real module\n")
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/real-spec.md",
        "UIAO_998",
        "# Real spec\n\nSee `src/uiao/real_module.py` for the implementation.\n",
    )
    report = walk_substrate(workspace_root=root)
    prov = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE" and "real_module" in f.path]
    assert not prov, f"unexpected findings for existing code ref: {report.findings}"
    assert report.code_refs_checked >= 1


def test_walker_dedupes_same_code_ref_within_file(tmp_path: Path) -> None:
    """Multiple mentions of the same missing code path in one canon doc
    report once, not N times."""
    root = _make_workspace(tmp_path)
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/dupe-spec.md",
        "UIAO_997",
        "First mention: `src/uiao/dupe.py`\nSecond mention: `src/uiao/dupe.py`\nThird mention: `src/uiao/dupe.py`\n",
    )
    report = walk_substrate(workspace_root=root)
    prov = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE" and "dupe.py" in f.path]
    assert len(prov) == 1, [f.path for f in prov]


def test_walker_scans_markdown_links_in_canon(tmp_path: Path) -> None:
    """Markdown link syntax like [label](src/uiao/foo.py) is also scanned."""
    root = _make_workspace(tmp_path)
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/link-spec.md",
        "UIAO_996",
        "See [the module](src/uiao/missing_link.py) for details.\n",
    )
    report = walk_substrate(workspace_root=root)
    prov = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE" and "missing_link" in f.path]
    assert prov, report.findings


def test_walker_scans_docs_directory_for_dangling_refs(tmp_path: Path) -> None:
    """docs/*.md and docs/*.qmd are scanned the same way canon .md is —
    catches narrative drift outside the canon namespace.
    """
    root = _make_workspace(tmp_path)
    docs_dir = root / "docs" / "narrative"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # A .qmd file citing a nonexistent code path
    (docs_dir / "guide.qmd").write_text("---\ntitle: Guide\n---\n\nSee `src/uiao/nonexistent/helper.py`.\n")
    # A .md file citing another nonexistent path
    (docs_dir / "notes.md").write_text("Legacy code was at `impl/retired/thing.py`.\n")

    report = walk_substrate(workspace_root=root)

    docs_findings = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE" and "docs document" in f.detail]
    assert any("nonexistent/helper" in f.path for f in docs_findings), report.findings
    assert any("retired/thing" in f.path for f in docs_findings), report.findings

    # Docs findings are P2, never P1 — cleanup is editorial, not blocking
    assert all(f.severity == "P2" for f in docs_findings)


def test_walker_docs_existing_ref_resolves_clean(tmp_path: Path) -> None:
    """A docs file citing an existing code path produces no finding."""
    root = _make_workspace(tmp_path)
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    real = root / "src/uiao/docs_real.py"
    real.parent.mkdir(parents=True, exist_ok=True)
    real.write_text("# real module\n")

    (docs_dir / "guide.md").write_text("See `src/uiao/docs_real.py`.\n")

    report = walk_substrate(workspace_root=root)
    assert not [f for f in report.findings if "docs_real" in f.path], report.findings


def test_walker_report_includes_code_refs_counter(tmp_path: Path) -> None:
    """Report exposes code_refs_checked counter for operators."""
    root = _make_workspace(tmp_path)
    report = walk_substrate(workspace_root=root)
    assert hasattr(report, "code_refs_checked")
    assert report.code_refs_checked >= 0
    # JSON output must include the counter
    assert "code_refs_checked" in report.as_dict()


def test_cli_drift_passes_on_p2_only(tmp_path: Path) -> None:
    """P2-only findings (canon→code drift) do not block the drift CLI."""
    root = _make_workspace(tmp_path)
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/warn-only.md",
        "UIAO_995",
        "See `src/uiao/ghost.py`.\n",
    )
    result = runner.invoke(app, ["drift", "--workspace-root", str(root)])
    assert result.exit_code == 0, result.stdout
    assert "PASS" in result.stdout
    assert "warning" in result.stdout.lower()


def test_cli_drift_fails_on_p1(tmp_path: Path) -> None:
    """P1 blocker still fails the drift CLI."""
    root = _make_workspace(tmp_path)
    (root / "docs").rmdir()  # P1 DRIFT-SCHEMA
    result = runner.invoke(app, ["drift", "--workspace-root", str(root)])
    assert result.exit_code == 1
    assert "FAIL" in result.stdout


def test_cli_walk_shows_warnings_separately(tmp_path: Path) -> None:
    """Walk CLI displays WARN section for P2 findings, exit 0 if only P2."""
    root = _make_workspace(tmp_path)
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/warn-display.md",
        "UIAO_994",
        "See `src/uiao/phantom.py`.\n",
    )
    result = runner.invoke(app, ["walk", "--workspace-root", str(root)])
    assert result.exit_code == 0, result.stdout
    assert "WARN" in result.stdout
    assert "P2" in result.stdout


# ---------------------------------------------------------------------------
# Retired-slug detection (manifest.retired_slugs[])
# ---------------------------------------------------------------------------


def _make_workspace_with_retired_slugs(tmp_path: Path) -> Path:
    """Workspace with a single retired-slug entry: MOD_X -> UIAO_174."""
    root = _make_workspace(tmp_path)
    manifest = root / "src/uiao/canon/substrate-manifest.yaml"
    body = yaml.safe_load(manifest.read_text())
    body["retired_slugs"] = [
        {"slug": "MOD_X", "replacement": "UIAO_174", "rationale": "ADR-060 flatten"},
    ]
    _write_yaml(manifest, body)
    return root


def test_walker_retired_slug_in_canon_doc_fires_p2(tmp_path: Path) -> None:
    """Canon doc body containing a retired slug raises a P2 advisory
    naming the replacement and the rationale."""
    root = _make_workspace_with_retired_slugs(tmp_path)
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/uses-retired.md",
        "UIAO_993",
        "# Uses retired\nSee MOD_X for governance telemetry.\n",
    )
    report = walk_substrate(workspace_root=root)
    matches = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE" and "retired slug MOD_X" in f.detail]
    assert matches, report.findings
    assert matches[0].severity == "P2"
    assert matches[0].subkind == "retired-slug"
    assert "UIAO_174" in matches[0].detail
    assert "ADR-060 flatten" in matches[0].detail


def test_walker_retired_slug_in_docs_qmd_fires_p2(tmp_path: Path) -> None:
    """Docs .qmd body containing a retired slug raises a P2 advisory."""
    root = _make_workspace_with_retired_slugs(tmp_path)
    qmd = root / "docs/some-page.qmd"
    qmd.parent.mkdir(parents=True, exist_ok=True)
    qmd.write_text("# Heading\nLegacy reference: MOD_X.\n")
    report = walk_substrate(workspace_root=root)
    matches = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE" and "retired slug MOD_X" in f.detail]
    assert matches, report.findings


def test_walker_retired_slug_no_op_when_block_absent(tmp_path: Path) -> None:
    """No retired_slugs in manifest => scan is a no-op even if a doc
    contains what looks like a retired-slug-shaped string."""
    root = _make_workspace(tmp_path)  # no retired_slugs
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/looks-retired.md",
        "UIAO_992",
        "See MOD_X.\n",
    )
    report = walk_substrate(workspace_root=root)
    assert not any("retired slug" in f.detail for f in report.findings), report.findings


def test_walker_retired_slug_skips_prior_id_frontmatter(tmp_path: Path) -> None:
    """The `prior_id: "MOD_X"` frontmatter line is the canonical
    historical record and must not be flagged."""
    root = _make_workspace_with_retired_slugs(tmp_path)
    spec = root / "src/uiao/canon/UIAO_174_Demo.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(
        "---\n"
        "document_id: UIAO_174\n"
        "provenance_flatten:\n"
        '  prior_id: "MOD_X"\n'
        "---\n"
        "# Demo doc\nNo body reference to the retired slug here.\n"
    )
    report = walk_substrate(workspace_root=root)
    assert not any("retired slug" in f.detail for f in report.findings), report.findings


def test_walker_retired_slug_skips_adr_060(tmp_path: Path) -> None:
    """ADR-060 references retired slugs by construction (it's the
    source-of-truth artifact about the rename); the scan must skip it."""
    root = _make_workspace_with_retired_slugs(tmp_path)
    _write_canon_doc(
        root,
        "src/uiao/canon/adr/adr-060-mod-namespace-flatten-into-uiao-canon.md",
        "UIAO_999",
        "# ADR-060\nThis ADR retires MOD_X; the replacement is UIAO_174.\n",
    )
    report = walk_substrate(workspace_root=root)
    assert not any("retired slug" in f.detail for f in report.findings), report.findings


def test_walker_retired_slug_dedupes_per_file(tmp_path: Path) -> None:
    """Multiple occurrences of the same retired slug in one file produce
    exactly one finding."""
    root = _make_workspace_with_retired_slugs(tmp_path)
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/triple-mention.md",
        "UIAO_991",
        "# Triple\nMOD_X here. MOD_X again. And once more: MOD_X.\n",
    )
    report = walk_substrate(workspace_root=root)
    matches = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE" and "retired slug MOD_X" in f.detail]
    assert len(matches) == 1, report.findings


# ---------------------------------------------------------------------------
# `uiao substrate walk --retired-slugs-only` filter
# ---------------------------------------------------------------------------


def test_cli_walk_retired_slugs_only_filters_out_other_findings(tmp_path: Path) -> None:
    """`--retired-slugs-only` should suppress findings that aren't from the
    retired-slug scan, leaving only retired-slug advisories in the output.

    Setup: a workspace with both kinds of P2 findings — a dangling code
    citation (canon doc citing src/uiao/nonexistent/module.py) AND a
    retired slug citation (canon doc using MOD_X).
    """
    root = _make_workspace_with_retired_slugs(tmp_path)
    # Finding 1: dangling code reference (DRIFT-PROVENANCE, generic).
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/dangling.md",
        "UIAO_990",
        "See `src/uiao/nonexistent/module.py`.\n",
    )
    # Finding 2: retired slug.
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/uses-retired.md",
        "UIAO_989",
        "Legacy reference: MOD_X.\n",
    )

    # Without the filter, both findings appear.
    result_unfiltered = runner.invoke(app, ["walk", "--workspace-root", str(root), "--json"])
    assert result_unfiltered.exit_code == 0, result_unfiltered.stdout
    unfiltered = json.loads(result_unfiltered.stdout)
    assert any("nonexistent/module" in f["detail"] for f in unfiltered["findings"])
    assert any("retired slug" in f["detail"] for f in unfiltered["findings"])

    # With the filter, only the retired-slug finding remains, and every
    # surviving finding carries subkind=="retired-slug" — the filter discriminates
    # on the subkind label, not on detail-string substrings.
    result_filtered = runner.invoke(app, ["walk", "--workspace-root", str(root), "--retired-slugs-only", "--json"])
    assert result_filtered.exit_code == 0, result_filtered.stdout
    filtered = json.loads(result_filtered.stdout)
    assert len(filtered["findings"]) >= 1
    assert all(f["subkind"] == "retired-slug" for f in filtered["findings"])
    assert not any("nonexistent/module" in f["detail"] for f in filtered["findings"])
    # And in the unfiltered output, the dangling-code-ref finding has no
    # subkind tag — proving the filter wouldn't accidentally let it through
    # if the detail wording ever shifted.
    dangling = [f for f in unfiltered["findings"] if "nonexistent/module" in f["detail"]]
    assert dangling and all(f["subkind"] is None for f in dangling)


def test_cli_walk_retired_slugs_only_clean_when_no_retired_refs(tmp_path: Path) -> None:
    """`--retired-slugs-only` on a workspace with no retired-slug references
    (but other drift) reports PASS with the retired-slug-specific message."""
    root = _make_workspace_with_retired_slugs(tmp_path)
    # Plant only a non-retired-slug finding.
    _write_canon_doc(
        root,
        "src/uiao/canon/specs/dangling.md",
        "UIAO_988",
        "See `src/uiao/nonexistent/module.py`.\n",
    )

    result = runner.invoke(app, ["walk", "--workspace-root", str(root), "--retired-slugs-only"])
    assert result.exit_code == 0, result.stdout
    assert "PASS" in result.stdout
    assert "no retired-slug references" in result.stdout
    assert "filtered to --retired-slugs-only" in result.stdout


# ---------------------------------------------------------------------------
# Historical-record exemptions (CR-003): adr-060 / adr-062
# ---------------------------------------------------------------------------


def test_code_ref_scan_exempts_adr062_historical_record(tmp_path: Path) -> None:
    """adr-062's supersession note narrates intentionally-absent paths;
    the code-ref scan must not flag them (CODE_REF_EXEMPT_FILES)."""
    from uiao.substrate.walker import SubstrateReport, _scan_canon_code_refs

    canon_adr = tmp_path / "src" / "uiao" / "canon" / "adr"
    canon_adr.mkdir(parents=True)
    (canon_adr / "adr-062-orgpath-depth-extension.md").write_text(
        "Historic: `src/uiao/adapters/modernization/active_directory/orgpath.py` is intentionally absent."
    )
    (canon_adr / "adr-999-other.md").write_text("Cites `src/uiao/does/not/exist.py` and should be flagged.")

    report = SubstrateReport(workspace_root=tmp_path, manifest_present=True, contract_present=True)
    _scan_canon_code_refs(tmp_path, report)
    flagged_files = {f.detail.split(" cites ")[0] for f in report.findings}
    assert not any("adr-062" in f for f in flagged_files)
    assert any("adr-999-other.md" in f for f in flagged_files)


def test_retired_slug_scan_exempts_adr062(tmp_path: Path) -> None:
    """adr-062 is preserved for historical reference and cites MOD_*
    slugs by construction — same exemption class as adr-060."""
    from uiao.substrate.walker import SubstrateReport, _scan_retired_slugs

    canon_adr = tmp_path / "src" / "uiao" / "canon" / "adr"
    canon_adr.mkdir(parents=True)
    (canon_adr / "adr-062-orgpath-depth-extension.md").write_text("Historic MOD_A discussion.")
    (canon_adr / "adr-777-fresh.md").write_text("New doc citing MOD_A wrongly.")

    report = SubstrateReport(workspace_root=tmp_path, manifest_present=True, contract_present=True)
    _scan_retired_slugs(
        tmp_path, report, [{"slug": "MOD_A", "replacement": "UIAO_151", "rationale": "ADR-060 flatten"}]
    )
    paths = {f.path for f in report.findings}
    assert not any("adr-062" in p for p in paths)
    assert any("adr-777-fresh.md" in p for p in paths)


# ---------------------------------------------------------------------------
# Reverse registry walk: canon -> registry
# ---------------------------------------------------------------------------
#
# The forward walk asks "does every registered path exist?". These cover the
# other half — "is every declared identity recorded, and recorded here?" — which
# the forward walk structurally cannot see, because an unregistered document has
# no registry row to walk from.


def test_unallocated_document_id_fires_p1(tmp_path: Path) -> None:
    """A document declaring an id the registry does not carry is invisible to
    every registry-derived surface."""
    root = _make_workspace(tmp_path)
    spec = root / "src/uiao/canon/specs/unregistered.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("---\ndocument_id: UIAO_987\n---\n# Unregistered\n")

    report = walk_substrate(workspace_root=root)
    matches = [f for f in report.findings if f.subkind == "document-id-unallocated"]
    assert len(matches) == 1, report.findings
    assert matches[0].drift_class == "DRIFT-PROVENANCE"
    assert matches[0].severity == "P1"
    assert matches[0].path == "src/uiao/canon/specs/unregistered.md"
    assert "UIAO_987" in matches[0].detail


def test_document_id_bound_to_another_path_fires_p1(tmp_path: Path) -> None:
    """Two documents claiming one id: only one is reachable by that id."""
    root = _make_workspace(tmp_path)
    _write_canon_doc(root, "src/uiao/canon/specs/first.md", "UIAO_986", "# First\n")
    impostor = root / "src/uiao/canon/specs/second.md"
    impostor.write_text("---\ndocument_id: UIAO_986\n---\n# Second\n")

    report = walk_substrate(workspace_root=root)
    matches = [f for f in report.findings if f.subkind == "document-id-path-mismatch"]
    assert len(matches) == 1, report.findings
    assert matches[0].severity == "P1"
    assert matches[0].path == "src/uiao/canon/specs/second.md"
    # The message names the path the id actually resolves to.
    assert "src/uiao/canon/specs/first.md" in matches[0].detail


def test_correctly_registered_document_is_clean(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    _write_canon_doc(root, "src/uiao/canon/specs/registered.md", "UIAO_985", "# Registered\n")
    report = walk_substrate(workspace_root=root)
    assert not [f for f in report.findings if (f.subkind or "").startswith("document-id")], report.findings


def test_data_file_back_reference_is_allocation_checked_only(tmp_path: Path) -> None:
    """Data files under canon/data carry the id of the document they are the
    executable form of. Requiring that id to bind to the data file's own path
    would assert the opposite of what the field means there."""
    root = _make_workspace(tmp_path)
    _write_canon_doc(root, "src/uiao/canon/specs/parent.md", "UIAO_984", "# Parent\n")
    _write_yaml(
        root / "src/uiao/canon/data/companion.yaml",
        {"document_id": "UIAO_984", "profile_id": "companion"},
    )
    report = walk_substrate(workspace_root=root)
    assert not [f for f in report.findings if (f.subkind or "").startswith("document-id")], report.findings


def test_data_file_back_reference_to_unallocated_id_still_fires(tmp_path: Path) -> None:
    """Allocation is still checked: a back-reference to nothing is drift."""
    root = _make_workspace(tmp_path)
    _write_yaml(
        root / "src/uiao/canon/data/orphan.yaml",
        {"document_id": "UIAO_983", "profile_id": "orphan"},
    )
    report = walk_substrate(workspace_root=root)
    matches = [f for f in report.findings if f.subkind == "document-id-unallocated"]
    assert len(matches) == 1, report.findings
    assert matches[0].path == "src/uiao/canon/data/orphan.yaml"


def test_metadata_nested_document_id_is_read(tmp_path: Path) -> None:
    """The UIAO_200/201/202 convention nests the id under `metadata:`."""
    root = _make_workspace(tmp_path)
    _write_yaml(
        root / "src/uiao/canon/data/nested.yaml",
        {"metadata": {"document_id": "UIAO_982"}, "payload": {}},
    )
    report = walk_substrate(workspace_root=root)
    assert [f for f in report.findings if f.subkind == "document-id-unallocated"], report.findings


def test_non_uiao_namespaces_are_out_of_scope(tmp_path: Path) -> None:
    """document-registry.yaml allocates the UIAO_NNN namespace and only that.
    CHARTER-NNN and descriptive data-file slugs are governed elsewhere."""
    root = _make_workspace(tmp_path)
    charter = root / "src/uiao/canon/charter/CHARTER-001.md"
    charter.parent.mkdir(parents=True, exist_ok=True)
    charter.write_text("---\ndocument_id: CHARTER-001\n---\n# Charter\n")
    _write_yaml(
        root / "src/uiao/canon/data/slug-id.yaml",
        {"document_id": "mssql-rationalization-domain-catalog"},
    )
    report = walk_substrate(workspace_root=root)
    assert not [f for f in report.findings if (f.subkind or "").startswith("document-id")], report.findings


def test_document_without_frontmatter_is_skipped(tmp_path: Path) -> None:
    """Unparseable or frontmatter-less files belong to schema validation, not
    here — guessing at a broken file's identity produces a worse finding."""
    root = _make_workspace(tmp_path)
    bare = root / "src/uiao/canon/specs/bare.md"
    bare.parent.mkdir(parents=True, exist_ok=True)
    bare.write_text("# No frontmatter at all\n")
    broken = root / "src/uiao/canon/specs/broken.md"
    broken.write_text("---\ndocument_id: [unclosed\n---\n# Broken\n")
    report = walk_substrate(workspace_root=root)
    assert not [f for f in report.findings if (f.subkind or "").startswith("document-id")], report.findings


def test_document_ids_checked_counter_is_reported(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    _write_canon_doc(root, "src/uiao/canon/specs/counted.md", "UIAO_981", "# Counted\n")
    report = walk_substrate(workspace_root=root)
    # manifest + contract + the new doc.
    assert report.document_ids_checked == 3
    assert "document_ids_checked" in report.as_dict()


def test_live_corpus_has_no_document_id_drift() -> None:
    """Every UIAO_NNN declared in canon is allocated, and to that same path."""
    report = walk_substrate()
    matches = [f for f in report.findings if (f.subkind or "").startswith("document-id")]
    assert matches == [], "canon -> registry drift:\n" + "\n".join(f"{f.path}: {f.detail}" for f in matches)
