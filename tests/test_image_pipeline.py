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
        "# Title\n\nSee [IMAGE-03: schematic of the pipeline].\n\n"
        "And reuse [IMAGE-REF: UIAO-FIG-007].\n",
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
    assert errors == [], "\n".join(
        f"{list(e.absolute_path)}: {e.message}" for e in errors
    )


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
    assert errors == [], "\n".join(
        f"{list(e.absolute_path)}: {e.message}" for e in errors
    )


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
    return _wrap(entries[0]) if len(entries) == 1 else {
        **_wrap(entries[0]),
        "images": list(entries),
    }


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
