"""Unit tests for docs/generate_images.py — the unified image pipeline.

Scoped to pure functions: hash utilities, placeholder parsing, fence
detection, and registry-schema integrity. Network-calling paths (Gemini
API) are out of scope; those are exercised manually via the image-gen
workflow.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATOR_PATH = REPO_ROOT / "docs" / "generate_images.py"
REGISTRY_PATH = REPO_ROOT / "src" / "uiao" / "canon" / "image-registry.yaml"
SCHEMA_PATH = REPO_ROOT / "src" / "uiao" / "schemas" / "image-registry" / "image-registry.schema.json"


@pytest.fixture(scope="module")
def generator():
    """Import docs/generate_images.py as a module for direct function access."""
    spec = importlib.util.spec_from_file_location("generate_images", GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generate_images"] = mod
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────
# Hash utilities
# ─────────────────────────────────────────────────────────────────────


def test_sha256_bytes_deterministic(generator):
    a = generator.sha256_bytes(b"hello")
    b = generator.sha256_bytes(b"hello")
    assert a == b
    assert len(a) == 64
    assert all(c in "0123456789abcdef" for c in a)


def test_sha256_text_normalizes_line_endings(generator):
    unix = generator.sha256_text("alpha\nbeta\n")
    windows = generator.sha256_text("alpha\r\nbeta\r\n")
    old_mac = generator.sha256_text("alpha\rbeta\r")
    assert unix == windows == old_mac, "LF/CRLF/CR variants must produce identical hashes"


def test_sha256_text_sensitive_to_content(generator):
    assert generator.sha256_text("alpha") != generator.sha256_text("beta")


def test_sha256_file_matches_bytes(generator, tmp_path):
    p = tmp_path / "sample.bin"
    payload = b"UIAO-FIG-000 probe"
    p.write_bytes(payload)
    assert generator.sha256_file(p) == generator.sha256_bytes(payload)


# ─────────────────────────────────────────────────────────────────────
# Fence detection — placeholders inside ``` fences must not be harvested
# ─────────────────────────────────────────────────────────────────────


def test_fenced_code_ranges_finds_balanced_fence(generator):
    text = "before\n```\nfence body\n```\nafter\n"
    ranges = generator._fenced_code_ranges(text)
    assert len(ranges) == 1
    start, end = ranges[0]
    assert text[start:end].startswith("```")
    assert "fence body" in text[start:end]


def test_fenced_code_ranges_handles_unclosed_fence(generator):
    text = "before\n```\nunclosed tail\n"
    ranges = generator._fenced_code_ranges(text)
    assert len(ranges) == 1
    assert ranges[0][1] == len(text)  # extends to EOF


def test_fenced_code_ranges_no_fences(generator):
    assert generator._fenced_code_ranges("plain text only\n") == []


# ─────────────────────────────────────────────────────────────────────
# Placeholder scanner
# ─────────────────────────────────────────────────────────────────────


def _write_doc(dir_: Path, name: str, body: str) -> Path:
    p = dir_ / name
    p.write_text(body, encoding="utf-8")
    return p


def test_scan_placeholders_local_and_ref(generator, tmp_path):
    doc = _write_doc(
        tmp_path,
        "doc.qmd",
        "# Title\n\nSee [IMAGE-03: schematic of the pipeline].\n\nAnd reuse [IMAGE-REF: UIAO-FIG-007].\n",
    )
    locals_, refs = generator.scan_placeholders([doc])
    assert len(locals_) == 1
    assert locals_[0].placeholder_id == "IMAGE-03"
    assert "schematic" in locals_[0].body
    assert not locals_[0].is_auto
    assert len(refs) == 1
    assert refs[0].canon_id == "UIAO-FIG-007"


def test_scan_placeholders_skips_fenced_examples(generator, tmp_path):
    doc = _write_doc(
        tmp_path,
        "example.md",
        "Prose before.\n\n```\n[IMAGE-09: illustrative — not harvested]\n```\n\n"
        "Real placeholder: [IMAGE-04: a real prompt here].\n",
    )
    locals_, refs = generator.scan_placeholders([doc])
    assert len(locals_) == 1
    assert locals_[0].placeholder_id == "IMAGE-04"
    assert refs == []


def test_scan_placeholders_auto_marker(generator, tmp_path):
    doc = _write_doc(tmp_path, "auto.qmd", "Body: [IMAGE-11: AUTO]\n")
    locals_, _ = generator.scan_placeholders([doc])
    assert len(locals_) == 1
    assert locals_[0].is_auto is True


def test_scan_placeholders_tolerates_diagram_and_figure(generator, tmp_path):
    doc = _write_doc(
        tmp_path,
        "mixed.md",
        "[DIAGRAM-02: flow].\n[FIGURE-05: table].\n[IMAGE-06: scene].\n",
    )
    locals_, _ = generator.scan_placeholders([doc])
    placeholder_ids = {p.placeholder_id for p in locals_}
    assert placeholder_ids == {"DIAGRAM-02", "FIGURE-05", "IMAGE-06"}


def test_scan_placeholders_ignores_ref_in_local_regex(generator, tmp_path):
    # The local regex could structurally match [IMAGE-...: UIAO-FIG-NNN];
    # the scanner must filter that out so it's only counted as a ref.
    doc = _write_doc(tmp_path, "ref.md", "Use [IMAGE-REF: UIAO-FIG-042] here.\n")
    locals_, refs = generator.scan_placeholders([doc])
    assert locals_ == []
    assert len(refs) == 1


# ─────────────────────────────────────────────────────────────────────
# Exclusion filter — session-logs, _site, etc. must not be walked
# ─────────────────────────────────────────────────────────────────────


def test_is_excluded_skips_session_logs(generator):
    p = Path("docs/docs/session-logs/2026-04-14-plan.md")
    assert generator._is_excluded(p)


def test_is_excluded_accepts_customer_documents(generator):
    p = Path("docs/customer-documents/executive-briefs/governance-os-overview.md")
    assert not generator._is_excluded(p)


# ─────────────────────────────────────────────────────────────────────
# Registry integrity — canonical image registry must parse + validate
# ─────────────────────────────────────────────────────────────────────


def test_registry_yaml_parses():
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "images" in data and isinstance(data["images"], list)


def test_registry_validates_against_schema():
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(data))
    assert errors == [], "\n".join(f"{list(e.absolute_path)}: {e.message}" for e in errors)


# ─────────────────────────────────────────────────────────────────────
# Reuse-metadata schema additions must be accepted
# ─────────────────────────────────────────────────────────────────────


def _sample_entry(**overrides):
    entry = {
        "id": "UIAO-FIG-001",
        "slug": "drift-engine-overview",
        "title": "Drift Engine Overview",
        "description": "High-level schematic of the drift detection loop.",
        "status": "current",
        "version": "1.0",
        "prompt_file": "src/uiao/canon/image-prompts/UIAO-FIG-001.md",
        "prompt_sha256": "a" * 64,
        "generator": "gemini-2.5-flash-image",
        "file": "docs/images/canonical/UIAO-FIG-001-drift-engine-overview.png",
        "file_sha256": "b" * 64,
        "generated_at": "2026-04-23T12:00:00Z",
        "dimensions": {"width": 1920, "height": 1080},
        "aspect": "16:9",
        "used_by": [],
    }
    entry.update(overrides)
    return entry


def _wrap(entry):
    return {
        "metadata": {
            "document_id": "UIAO_202",
            "title": "UIAO Image Registry",
            "version": "1.0",
            "status": "Current",
            "classification": "OPERATIONAL",
            "owner": "test",
            "created_at": "2026-04-23",
            "updated_at": "2026-04-23",
            "boundary": "GCC-Moderate",
        },
        "schema-version": "1.0.0",
        "updated": "2026-04-23",
        "images": [entry],
    }


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_accepts_full_reuse_metadata(schema):
    entry = _sample_entry(
        tags=["drift", "evidence-chain"],
        audience=["executive", "technical"],
        document_types=["executive-brief", "architecture-series"],
        visual_style="pipeline-flow",
        themes=["drift detection", "certificate anchoring"],
        keywords=["Gemini", "Nano Banana", "SHA-256"],
        alt_text="Flow diagram showing three stages of drift detection.",
        caption="Drift engine, end to end.",
        related=["UIAO-FIG-002"],
        license="Apache-2.0",
        reuse_score=3,
    )
    errors = list(Draft202012Validator(schema).iter_errors(_wrap(entry)))
    assert errors == [], "\n".join(f"{list(e.absolute_path)}: {e.message}" for e in errors)


def test_schema_rejects_unknown_visual_style(schema):
    entry = _sample_entry(visual_style="not-a-real-style")
    errors = list(Draft202012Validator(schema).iter_errors(_wrap(entry)))
    assert errors, "unknown visual_style must be rejected"


def test_schema_rejects_bad_tag_format(schema):
    entry = _sample_entry(tags=["CamelCase"])
    errors = list(Draft202012Validator(schema).iter_errors(_wrap(entry)))
    assert errors, "non-kebab tags must be rejected"


def test_schema_rejects_unknown_audience(schema):
    entry = _sample_entry(audience=["president"])
    errors = list(Draft202012Validator(schema).iter_errors(_wrap(entry)))
    assert errors, "unknown audience must be rejected"


def test_schema_rejects_bad_related_id(schema):
    entry = _sample_entry(related=["UIAO-FIG-9"])  # 1 digit instead of 3
    errors = list(Draft202012Validator(schema).iter_errors(_wrap(entry)))
    assert errors, "related IDs must match UIAO-FIG-NNN pattern"


# ─────────────────────────────────────────────────────────────────────
# image_registry_search.py — discovery CLI
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def search_tool():
    path = REPO_ROOT / "scripts" / "tools" / "image_registry_search.py"
    spec = importlib.util.spec_from_file_location("image_registry_search", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["image_registry_search"] = mod
    spec.loader.exec_module(mod)
    return mod


def _registry_data(*entries):
    return (
        _wrap(entries[0])
        if len(entries) == 1
        else {
            **_wrap(entries[0]),
            "images": list(entries),
        }
    )


def test_search_ranks_tag_hits_above_description_hits(search_tool):
    a = _sample_entry(
        id="UIAO-FIG-010",
        tags=["zero-trust"],
        description="unrelated prose",
    )
    b = _sample_entry(
        id="UIAO-FIG-011",
        tags=["drift"],
        description="this mentions zero-trust in passing",
    )
    data = _registry_data(a, b)
    matches = search_tool.search(data, "zero-trust", None, None, None, "current")
    assert [m.entry["id"] for m in matches] == ["UIAO-FIG-010", "UIAO-FIG-011"]


def test_search_hard_filter_audience(search_tool):
    a = _sample_entry(id="UIAO-FIG-020", audience=["executive"], tags=["boundary"])
    b = _sample_entry(id="UIAO-FIG-021", audience=["technical"], tags=["boundary"])
    data = _registry_data(a, b)
    matches = search_tool.search(data, "boundary", "executive", None, None, "current")
    assert [m.entry["id"] for m in matches] == ["UIAO-FIG-020"]


def test_search_hard_filter_doc_type(search_tool):
    a = _sample_entry(id="UIAO-FIG-030", document_types=["whitepaper"], tags=["evidence"])
    b = _sample_entry(id="UIAO-FIG-031", document_types=["adapter-spec"], tags=["evidence"])
    data = _registry_data(a, b)
    matches = search_tool.search(data, "evidence", None, "whitepaper", None, "current")
    assert [m.entry["id"] for m in matches] == ["UIAO-FIG-030"]


def test_search_list_mode_returns_all_current(search_tool):
    a = _sample_entry(id="UIAO-FIG-040", status="current")
    b = _sample_entry(id="UIAO-FIG-041", status="deprecated", superseded_by="UIAO-FIG-040")
    data = _registry_data(a, b)
    matches = search_tool.search(data, None, None, None, None, "current")
    assert [m.entry["id"] for m in matches] == ["UIAO-FIG-040"]


def test_search_tie_breaks_on_reuse_score(search_tool):
    a = _sample_entry(id="UIAO-FIG-050", tags=["drift"], reuse_score=1)
    b = _sample_entry(id="UIAO-FIG-051", tags=["drift"], reuse_score=10)
    data = _registry_data(a, b)
    matches = search_tool.search(data, "drift", None, None, None, "current")
    assert [m.entry["id"] for m in matches] == ["UIAO-FIG-051", "UIAO-FIG-050"]


def test_search_no_query_no_filters_is_error_in_cli(search_tool, capsys, monkeypatch):
    """The CLI requires a query or --list; bare invocation prints usage."""
    monkeypatch.setattr(sys, "argv", ["image_registry_search.py"])
    rc = search_tool.main()
    assert rc == 2


# ─────────────────────────────────────────────────────────────────────
# Registry audit — surfaces missing reuse metadata per entry
# ─────────────────────────────────────────────────────────────────────


def test_audit_entry_reports_all_missing_when_minimal(search_tool):
    minimal = _sample_entry()  # no reuse metadata populated
    report = search_tool.audit_entry(minimal)
    assert report["complete"] is False
    assert set(report["populated"]) == set()
    assert set(report["missing"]) == set(search_tool.REUSE_METADATA_FIELDS)
    assert report["coverage"] == "0/8"


def test_audit_entry_reports_all_populated_when_rich(search_tool):
    rich = _sample_entry(
        tags=["drift"],
        audience=["executive"],
        document_types=["executive-brief"],
        visual_style="schematic",
        themes=["drift detection"],
        keywords=["Gemini"],
        alt_text="A diagram",
        caption="Figure 1",
    )
    report = search_tool.audit_entry(rich)
    assert report["complete"] is True
    assert report["missing"] == []
    assert report["coverage"] == "8/8"


def test_audit_entry_empty_list_counts_as_missing(search_tool):
    entry = _sample_entry(
        tags=[],  # present but empty — not "populated"
        audience=["executive"],
        document_types=["whitepaper"],
        visual_style="",
        themes=["x"],
        keywords=["y"],
        alt_text="alt",
        caption="cap",
    )
    report = search_tool.audit_entry(entry)
    assert "tags" in report["missing"]
    assert "visual_style" in report["missing"]
    assert report["complete"] is False


def test_audit_registry_sorts_worst_coverage_first(search_tool):
    full = _sample_entry(
        id="UIAO-FIG-100",
        tags=["a"],
        audience=["executive"],
        document_types=["whitepaper"],
        visual_style="schematic",
        themes=["b"],
        keywords=["c"],
        alt_text="d",
        caption="e",
    )
    empty = _sample_entry(id="UIAO-FIG-101")  # no reuse metadata at all
    data = _registry_data(full, empty)
    reports = search_tool.audit_registry(data)
    # Worst first.
    assert reports[0]["id"] == "UIAO-FIG-101"
    assert reports[1]["id"] == "UIAO-FIG-100"


def test_audit_registry_status_filter(search_tool):
    current = _sample_entry(id="UIAO-FIG-110", status="current")
    draft = _sample_entry(id="UIAO-FIG-111", status="draft")
    data = _registry_data(current, draft)
    reports = search_tool.audit_registry(data, status_filter="draft")
    assert [r["id"] for r in reports] == ["UIAO-FIG-111"]


def test_is_populated(search_tool):
    assert search_tool._is_populated("text")
    assert not search_tool._is_populated("")
    assert not search_tool._is_populated("   ")
    assert search_tool._is_populated(["a"])
    assert not search_tool._is_populated([])
    assert not search_tool._is_populated(None)


# ─────────────────────────────────────────────────────────────────────
# Top-level manifest aggregator
# ─────────────────────────────────────────────────────────────────────


def test_manifest_has_expected_top_level_keys(generator):
    manifest = generator.build_manifest([], [])
    assert manifest["schema_version"] == generator.MANIFEST_SCHEMA_VERSION
    assert "generated_at" in manifest
    assert manifest["registry"]["total_entries"] == 0
    assert manifest["doc_local"] == []
    assert manifest["canon_refs"] == []
    assert manifest["stats"]["doc_local_count"] == 0
    assert manifest["stats"]["canon_refs_count"] == 0


def test_manifest_registry_status_breakdown(generator):
    e1 = generator.RegistryEntry(
        id="UIAO-FIG-200",
        slug="a",
        status="current",
        prompt_file=Path("/x"),
        file=Path("/x"),
        prompt_sha256="a" * 64,
        file_sha256="b" * 64,
        version="1.0",
        generator="g",
        used_by=[],
    )
    e2 = generator.RegistryEntry(
        id="UIAO-FIG-201",
        slug="b",
        status="draft",
        prompt_file=Path("/x"),
        file=Path("/x"),
        prompt_sha256="c" * 64,
        file_sha256="d" * 64,
        version="1.0",
        generator="g",
        used_by=[],
    )
    manifest = generator.build_manifest([e1, e2], [])
    assert manifest["registry"]["total_entries"] == 2
    assert manifest["registry"]["by_status"] == {"current": 1, "draft": 1}


def test_manifest_resolves_canon_refs(generator, tmp_path):
    doc = tmp_path / "doc.qmd"
    doc.write_text("[IMAGE-REF: UIAO-FIG-300]\n", encoding="utf-8")
    entry = generator.RegistryEntry(
        id="UIAO-FIG-300",
        slug="s",
        status="current",
        prompt_file=Path("/x"),
        file=Path("/x/canonical.png"),
        prompt_sha256="a" * 64,
        file_sha256="b" * 64,
        version="1.0",
        generator="g",
        used_by=[],
    )
    ref = generator.CanonRefPlaceholder(
        document=doc,
        canon_id="UIAO-FIG-300",
        line_number=1,
    )
    manifest = generator.build_manifest([entry], [ref])
    assert manifest["stats"]["canon_refs_count"] == 1
    assert manifest["canon_refs"][0]["canon_id"] == "UIAO-FIG-300"
    assert manifest["canon_refs"][0]["status"] == "current"
    assert manifest["stats"]["unique_canon_images_referenced"] == 1
    assert manifest["stats"]["canon_refs_missing_count"] == 0


def test_manifest_flags_missing_canon_refs(generator, tmp_path):
    doc = tmp_path / "doc.qmd"
    doc.write_text("[IMAGE-REF: UIAO-FIG-404]\n", encoding="utf-8")
    ref = generator.CanonRefPlaceholder(
        document=doc,
        canon_id="UIAO-FIG-404",
        line_number=1,
    )
    manifest = generator.build_manifest([], [ref])
    assert manifest["canon_refs"][0]["status"] == "missing"
    assert manifest["stats"]["canon_refs_missing_count"] == 1


def test_manifest_doc_local_picks_up_sidecars(generator, tmp_path, monkeypatch):
    """Sidecars on disk must roll into manifest.doc_local."""
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    sidecar = image_dir / "sample.png.json"
    payload = {
        "document": "docs/customer-documents/executive-briefs/x.md",
        "placeholder_id": "IMAGE-03",
        "canonical_id": None,
        "slug": "sample",
        "prompt_sha256": "a" * 64,
        "generator": "gemini-2.5-flash-image",
        "generated_at": "2026-04-23T10:00:00Z",
        "sha256": "b" * 64,
        "version": "1.0",
        "aspect": "16:9",
        "used_by": [],
    }
    sidecar.write_text(json.dumps(payload), encoding="utf-8")
    # Also write the PNG stub so build_manifest sees a valid pair.
    (image_dir / "sample.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "CANONICAL_OUTPUT_DIR", image_dir)
    # Point the scanner at our tmp dir.
    monkeypatch.setattr(
        generator,
        "_iter_sidecars",
        lambda: [sidecar],
    )

    manifest = generator.build_manifest([], [])
    assert len(manifest["doc_local"]) == 1
    entry = manifest["doc_local"][0]
    assert entry["placeholder_id"] == "IMAGE-03"
    assert entry["prompt_sha256"] == "a" * 64
    assert entry["sha256"] == "b" * 64


def test_write_manifest_produces_valid_json(generator, tmp_path):
    target = tmp_path / "out" / "manifest.json"
    manifest = generator.build_manifest([], [])
    result_path = generator.write_manifest(manifest, target)
    assert result_path == target
    roundtrip = json.loads(target.read_text(encoding="utf-8"))
    assert roundtrip["schema_version"] == generator.MANIFEST_SCHEMA_VERSION


# ─────────────────────────────────────────────────────────────────────
# IMAGE-PROMPTS.md heading-style harvester (Option 2 of the dialects)
# ─────────────────────────────────────────────────────────────────────


def _write_image_prompts(folder: Path, blocks: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / "IMAGE-PROMPTS.md"
    p.write_text(blocks, encoding="utf-8")
    return p


def test_is_todo_body_detects_scaffold_variants(generator):
    assert generator._is_todo_body("")
    assert generator._is_todo_body("   \n  ")
    assert generator._is_todo_body("_TODO — describe the intended illustration._")
    assert generator._is_todo_body("*TODO* fill in later")
    assert generator._is_todo_body("TBD")
    assert generator._is_todo_body("<placeholder>")
    # Real content — even one substantive line — is not TODO.
    assert not generator._is_todo_body("A 16:9 schematic of the pipeline.")
    assert not generator._is_todo_body("_TODO — ignore this note._\n\nA real prompt paragraph follows.")


def test_extract_heading_blocks_basic(generator):
    text = "# Image Prompts\n\n## IMAGE-01\n\nFirst prompt body.\n\n## IMAGE-02 — Second\n\nSecond prompt body.\n"
    blocks = generator._extract_heading_blocks(text)
    ids = [b[0] for b in blocks]
    titles = [b[1] for b in blocks]
    bodies = [b[2] for b in blocks]
    assert ids == ["IMAGE-01", "IMAGE-02"]
    assert titles == ["", "Second"]
    assert "First prompt body." in bodies[0]
    assert "Second prompt body." in bodies[1]


def test_extract_heading_blocks_image_n_dialect(generator):
    """The `## Image 1: Title` dialect (docs/visuals/IMAGE-PROMPTS-SCUBA.md)
    normalizes to IMAGE-01 so filenames stay consistent."""
    text = "## Image 1: Four-Plane Pipeline\n\n**Prompt:**\nA wide schematic.\n"
    blocks = generator._extract_heading_blocks(text)
    assert len(blocks) == 1
    placeholder_id, title, body, _ = blocks[0]
    assert placeholder_id == "IMAGE-01"
    assert title == "Four-Plane Pipeline"
    assert "A wide schematic." in body


def test_extract_heading_blocks_strips_placement_and_prompt_markers(generator):
    text = (
        "## IMAGE-03\n\n"
        "**Placement:** Section 4, after the architecture paragraph.\n\n"
        "**Prompt:**\n"
        "A clean infographic showing the four planes.\n"
    )
    blocks = generator._extract_heading_blocks(text)
    assert len(blocks) == 1
    body = blocks[0][2]
    assert "Placement" not in body
    assert body.startswith("A clean infographic")


def test_find_companion_document_folder_named(generator, tmp_path):
    folder = tmp_path / "cyberark"
    folder.mkdir()
    (folder / "cyberark.qmd").write_text("# CyberArk\n", encoding="utf-8")
    (folder / "IMAGE-PROMPTS.md").write_text("## IMAGE-01\n\nbody.\n", encoding="utf-8")
    prompts = folder / "IMAGE-PROMPTS.md"
    companion = generator._find_companion_document(prompts)
    assert companion == folder / "cyberark.qmd"


def test_find_companion_document_single_sibling(generator, tmp_path):
    folder = tmp_path / "custom"
    folder.mkdir()
    (folder / "oddly-named-doc.qmd").write_text("# Doc\n", encoding="utf-8")
    (folder / "IMAGE-PROMPTS.md").write_text("## IMAGE-01\n\nbody.\n", encoding="utf-8")
    companion = generator._find_companion_document(folder / "IMAGE-PROMPTS.md")
    assert companion == folder / "oddly-named-doc.qmd"


def test_find_companion_document_none_when_ambiguous(generator, tmp_path):
    folder = tmp_path / "multi"
    folder.mkdir()
    (folder / "a.qmd").write_text("a", encoding="utf-8")
    (folder / "b.qmd").write_text("b", encoding="utf-8")
    (folder / "IMAGE-PROMPTS.md").write_text("## IMAGE-01\n\nbody.\n", encoding="utf-8")
    companion = generator._find_companion_document(folder / "IMAGE-PROMPTS.md")
    assert companion is None


def test_find_companion_document_ignores_readme_and_index(generator, tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "README.md").write_text("readme", encoding="utf-8")
    (folder / "index.qmd").write_text("index", encoding="utf-8")
    (folder / "actual-doc.qmd").write_text("real", encoding="utf-8")
    (folder / "IMAGE-PROMPTS.md").write_text("## IMAGE-01\n\nbody.\n", encoding="utf-8")
    companion = generator._find_companion_document(folder / "IMAGE-PROMPTS.md")
    assert companion == folder / "actual-doc.qmd"


def test_scan_image_prompts_files_attaches_to_companion(generator, tmp_path):
    folder = tmp_path / "cyberark"
    folder.mkdir()
    companion = folder / "cyberark.qmd"
    companion.write_text("# CyberArk\n", encoding="utf-8")
    prompts = _write_image_prompts(
        folder,
        "## IMAGE-01\n\nA 16:9 schematic of the rotation flow.\n\n## IMAGE-02\n\n_TODO — describe second._\n",
    )
    out = generator.scan_image_prompts_files([prompts])
    # Only IMAGE-01 (real body) should be harvested; IMAGE-02 is TODO.
    assert len(out) == 1
    assert out[0].document == companion
    assert out[0].placeholder_id == "IMAGE-01"
    assert "rotation flow" in out[0].body


def test_scan_image_prompts_files_skips_missing_companion(generator, tmp_path, capsys):
    folder = tmp_path / "publication"
    folder.mkdir()
    # Only .docx sibling (common for the publications/ tree); no .qmd/.md.
    (folder / "UIAO-Brief.docx").write_bytes(b"fake")
    prompts = _write_image_prompts(folder, "## IMAGE-01\n\nreal body.\n")
    out = generator.scan_image_prompts_files([prompts])
    assert out == []
    captured = capsys.readouterr()
    assert "no companion" in captured.out.lower()


def test_merge_placeholders_inline_wins_on_conflict(generator, tmp_path):
    doc = tmp_path / "doc.qmd"
    doc.write_text("", encoding="utf-8")
    inline = [
        generator.DocLocalPlaceholder(
            document=doc,
            placeholder_id="IMAGE-01",
            body="INLINE body",
            line_number=10,
            is_auto=False,
        ),
    ]
    sidecar = [
        generator.DocLocalPlaceholder(
            document=doc,
            placeholder_id="IMAGE-01",
            body="SIDECAR body",
            line_number=42,
            is_auto=False,
        ),
        generator.DocLocalPlaceholder(
            document=doc,
            placeholder_id="IMAGE-02",
            body="new from sidecar",
            line_number=55,
            is_auto=False,
        ),
    ]
    merged = generator.merge_placeholders(inline, sidecar)
    assert len(merged) == 2
    by_id = {p.placeholder_id: p for p in merged}
    assert by_id["IMAGE-01"].body == "INLINE body"
    assert by_id["IMAGE-02"].body == "new from sidecar"


def test_merge_placeholders_stable_sort(generator, tmp_path):
    a = tmp_path / "a.qmd"
    a.write_text("", encoding="utf-8")
    b = tmp_path / "b.qmd"
    b.write_text("", encoding="utf-8")
    placeholders = [
        generator.DocLocalPlaceholder(document=b, placeholder_id="IMAGE-02", body="", line_number=5, is_auto=False),
        generator.DocLocalPlaceholder(document=a, placeholder_id="IMAGE-01", body="", line_number=3, is_auto=False),
    ]
    merged = generator.merge_placeholders(placeholders, [])
    assert [p.document for p in merged] == [a, b]
