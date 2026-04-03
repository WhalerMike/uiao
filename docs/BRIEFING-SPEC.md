# BRIEFING-SPEC.md — UIAO Personal Briefing Generator

**Status**: Ready for implementation
**Command**: `uiao generate-briefing`
**Assigned to**: Claude Code
**Updated**: 2026-04-03
**Owner**: whalermike

---

## Context

The project owner (Michael Stratton) needs a single human-readable document
that accurately reflects current system state at any given moment. The
20-document canon drifts from reality and is too slow to maintain manually.
This command is the owner's primary daily orientation tool — generated on
demand, never hand-edited.

---

## Quality Benchmark

The output document must meet or exceed the standard set by:

```
01_Canon/uiao-reference.docx          (34KB — canon reference architecture)
exports/docx/UIAO_Leadership_Briefing_v1.0.docx   (9.9MB — full briefing)
```

The reference architecture document uses:
- Calibri font, color #4472C4 for titles, #2B5797 for subtitles
- Audience routing tables at the front
- Hierarchical numbered sections (Part I, Section 1, 1.1, 1.2...)
- Tables with light blue header shading
- Justified body text with 1.5x line spacing
- CUI//FOUO classification banner

The briefing generator must produce documents at this visual quality level.
Use the `rich_docx.py` generator as the rendering engine — it already
implements this style. Do NOT use the plain `python-docx` approach.

---

## Mandatory Pre-Flight (Claude Code)

Before touching any file, read in this order:
1. `PROJECT-CONTEXT.md`
2. `FORMAT-CANON.md`
3. `AGENTS.md`
4. `UIAO-MEMORY.md`
5. This file

---

## Actual Repo Layout (verified from directory tree, 2026-04-03)

Key paths Claude Code must use — do not guess, these are confirmed:

```
src/uiao_core/
    cli/app.py                         ← add generate_briefing command here
    generators/
        rich_docx.py                   ← USE THIS as rendering engine
        docs.py                        ← reference for context loading
        diagrams.py                    ← reference for diagram embedding
    evidence/
        collector.py / linker.py / bundler.py
    dashboard/
        ksi.py / export.py
    monitoring/
        sentinel_hook.py / ongoing_auth.py

data/
    vendor-overlays/                   ← 9 vendor YAMLs (Big 7 + extras)
        cisco.yaml, crowdstrike.yaml, cyberark.yaml, infoblox.yaml,
        microsoft.yaml, paloalto.yaml, servicenow.yaml, splunk.yaml
    control-library/                   ← 131 control YAMLs (AC through SI)
    overlays/                          ← legacy overlays (cisco, infoblox,
                                          microsoft, okta) — do not confuse
                                          with vendor-overlays/
    parameters.yml                     ← master parameters
    control-planes.yml                 ← six plane definitions
    vendor-stack.yml                   ← vendor stack definitions

adapters/
    base_adapter.py
    cloud/  entra_id.py, intune.py, m365.py
    database/  sql_adapter.py
    government/  (stub)

assets/images/
    mermaid/                           ← 15 rendered PNGs available NOW:
        unified_arch.png               ← use on Page 2 (Stack)
        vendor_logic.png               ← use on Page 2 (Stack)
        multi_plane_integration.png    ← use on Page 2 (Stack)
        executive_dashboard_status.png ← use on Page 1 (Health)
        roadmap_gantt_visual.png       ← use on Page 5 (Priorities)
        schema_validation_flow.png     ← use on Page 4 (Pipeline)
        enforcement_pipeline_logic.png ← use on Page 4 (Pipeline)
        mgmt_plane_flow.png            ← use on Page 3 (Coverage)
    (large Gemini PNGs also available — see assets/images/*.png)

reports/
    drift-report.json                  ← live drift data
    drift-report-post-fix.json

exports/oscal/
    uiao-component-definition.json    ← OSCAL component definition
    uiao-ssp-skeleton.json            ← SSP skeleton
    uiao-poam.json                    ← current POA&M

UIAO-MEMORY.md                        ← correction log
CHANGELOG.md                          ← activity log (53KB)
PROJECT-CONTEXT.md                    ← priorities and decisions
.github/workflows/                    ← 23 CI workflows
```

---

## Implementation Steps (execute in order)

### Step 1 — Create the generator

Create `src/uiao_core/generators/briefing.py`:

```python
# src/uiao_core/generators/briefing.py
"""
UIAO Personal Briefing Generator
Command: uiao generate-briefing
Owner: whalermike (Michael Stratton)
Purpose: Single human-readable DOCX reflecting current system state.
Generated from live repo sources. Never hand-edited.
Quality target: matches 01_Canon/uiao-reference.docx visual standard.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor

from uiao_core.config import Settings

# ---------------------------------------------------------------------------
# Brand colors (from uiao-reference.docx)
# ---------------------------------------------------------------------------
COLOR_TITLE = RGBColor(0x44, 0x72, 0xC4)      # #4472C4 — blue title
COLOR_SUBTITLE = RGBColor(0x2B, 0x57, 0x97)   # #2B5797 — dark blue subtitle
COLOR_HEADER_BG = "D5E8F0"                     # table header shading
COLOR_ACCENT = RGBColor(0xC0, 0x00, 0x00)      # #C00000 — red CUI banner

STATUS_EMOJI = {
    "pass": "🟢",
    "warn": "🟡",
    "fail": "🔴",
    "unknown": "⚠️",
}

# Vendor → Control Plane mapping (from data/vendor-overlays/)
PLANE_VENDOR_MAP = {
    "Identity":   ["microsoft", "entra_id", "cyberark", "okta"],
    "Network":    ["cisco"],
    "Addressing": ["infoblox"],
    "Telemetry":  ["splunk", "sentinel", "crowdstrike"],
    "Security":   ["paloalto", "crowdstrike"],
    "Management": ["servicenow", "cyberark"],
}

VENDOR_OVERLAY_NAMES = {
    "cisco": "Cisco SD-WAN",
    "crowdstrike": "CrowdStrike EDR",
    "cyberark": "CyberArk PAM",
    "infoblox": "InfoBlox DDI",
    "microsoft": "Microsoft Entra ID / M365",
    "paloalto": "Palo Alto NGFW",
    "servicenow": "ServiceNow Xanadu",
    "splunk": "Splunk SIEM",
}


# ---------------------------------------------------------------------------
# Styling helpers
# ---------------------------------------------------------------------------

def _set_cell_shading(cell, fill_hex: str) -> None:
    """Apply background shading to a table cell."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def _add_cui_banner(doc: Document) -> None:
    """Add CUI//FOUO classification banner matching reference doc style."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("CUI // FOUO")
    run.bold = True
    run.font.color.rgb = COLOR_ACCENT
    run.font.size = Pt(10)


def _add_heading(doc: Document, text: str, level: int = 1,
                 color: RGBColor | None = None) -> None:
    heading = doc.add_heading(text, level=level)
    if color:
        for run in heading.runs:
            run.font.color.rgb = color


def _add_styled_table(
    doc: Document,
    headers: list[str],
    rows: list[dict],
    keys: list[str],
    col_widths: list[float] | None = None,
) -> None:
    """Add a table matching the reference architecture visual style."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"

    # Header row with blue shading
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        cell = hdr_cells[i]
        cell.text = h
        _set_cell_shading(cell, COLOR_HEADER_BG)
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True
                run.font.color.rgb = COLOR_SUBTITLE

    # Data rows
    for row_data in rows:
        cells = table.add_row().cells
        for i, key in enumerate(keys):
            cells[i].text = str(row_data.get(key, "—"))

    doc.add_paragraph()


def _embed_diagram(doc: Document, path: Path, caption: str,
                   width_inches: float = 5.5) -> None:
    """Embed a diagram PNG or show a fallback message."""
    if path.exists():
        doc.add_picture(str(path), width=Inches(width_inches))
        p = doc.add_paragraph(caption)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].italic = True
        p.runs[0].font.size = Pt(9)
    else:
        doc.add_paragraph(
            f"⚠️  Diagram not available: {path.name}. "
            f"Run `uiao generate-diagrams` to generate."
        )


# ---------------------------------------------------------------------------
# Data collectors — all pull from live repo sources
# ---------------------------------------------------------------------------

def collect_ci_status(root: Path) -> list[dict]:
    """
    Assess CI health from workflow files and drift reports.
    Source: .github/workflows/ + reports/drift-report.json
    """
    components = [
        "CI Pipeline (ci.yml)",
        "OSCAL Validation (trestle)",
        "Drift Detection",
        "Adapter Registry",
        "Evidence Collection",
        "Security Scan",
    ]

    # Check drift report for actual status
    drift_path = root / "reports" / "drift-report.json"
    drift_status = "unknown"
    drift_note = ""
    if drift_path.exists():
        try:
            drift_data = json.loads(drift_path.read_text(encoding="utf-8"))
            issues = drift_data.get("issues", [])
            drift_status = "fail" if issues else "pass"
            drift_note = f"{len(issues)} drift issues" if issues else "Clean"
        except Exception:
            drift_status = "unknown"

    results = []
    for component in components:
        if "Drift" in component:
            results.append({
                "component": component,
                "status": STATUS_EMOJI.get(drift_status, "⚠️"),
                "last_changed": "See reports/drift-report.json",
                "notes": drift_note or "Run drift-detection workflow",
            })
        else:
            results.append({
                "component": component,
                "status": "⚠️",
                "last_changed": "Run `gh run list` to refresh",
                "notes": "Live CI status requires GitHub Actions API",
            })
    return results


def collect_memory_entries(root: Path, n: int = 3) -> list[dict]:
    """Pull last n entries from UIAO-MEMORY.md correction log."""
    memory_path = root / "UIAO-MEMORY.md"
    if not memory_path.exists():
        return [{"date": "—", "task": "MEMORY.md not found",
                 "outcome": "—", "correction": ""}]

    entries = []
    for line in memory_path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\| 20\d\d-", line):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                entries.append({
                    "date": parts[0],
                    "task": parts[1],
                    "outcome": parts[2],
                    "correction": parts[4] if len(parts) > 4 else "",
                })

    return entries[:n] or [
        {"date": "—", "task": "No entries found",
         "outcome": "—", "correction": ""}
    ]


def collect_adapter_status(root: Path) -> list[dict]:
    """
    Read vendor-overlays/ YAMLs (the Big 7 + extras).
    Source: data/vendor-overlays/*.yaml (NOT data/overlays/ — different dir)
    """
    overlays_dir = root / "data" / "vendor-overlays"
    if not overlays_dir.exists():
        return [{"plane": "—", "vendor": "data/vendor-overlays/ not found",
                 "status": "⚠️", "controls": "—", "role": "—"}]

    plane_lookup = {
        vendor: plane
        for plane, vendors in PLANE_VENDOR_MAP.items()
        for vendor in vendors
    }

    rows = []
    for yaml_file in sorted(overlays_dir.glob("*.yaml")):
        if yaml_file.stem == "example":
            continue
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            vendor_key = yaml_file.stem.lower()
            name = VENDOR_OVERLAY_NAMES.get(vendor_key, data.get("name", yaml_file.stem))
            plane = plane_lookup.get(vendor_key, "Unknown")
            controls = data.get("controls", data.get("control_families", []))
            if isinstance(controls, list):
                controls_str = ", ".join(str(c) for c in controls[:5])
                if len(controls) > 5:
                    controls_str += f" +{len(controls)-5} more"
            else:
                controls_str = str(controls) if controls else "—"
            rows.append({
                "plane": plane,
                "vendor": name,
                "status": data.get("status", "active"),
                "controls": controls_str or "—",
                "role": data.get("role", "—"),
            })
        except Exception as exc:
            rows.append({
                "plane": "Error", "vendor": yaml_file.stem,
                "status": "⚠️", "controls": str(exc)[:60], "role": "—",
            })

    return rows or [{"plane": "—", "vendor": "No overlays found",
                     "status": "⚠️", "controls": "—", "role": "—"}]


def collect_control_coverage(root: Path) -> tuple[list[dict], int, int, int]:
    """
    Read data/control-library/ YAMLs (131 controls confirmed in tree).
    Returns (rows, gold_count, covered_count, total_count).
    """
    control_dir = root / "data" / "control-library"
    if not control_dir.exists():
        return ([{"id": "—", "title": "control-library/ not found",
                  "narrative": "—", "evidence": "—", "gap": "dir missing"}],
                0, 0, 0)

    rows = []
    for yaml_file in sorted(control_dir.glob("*.yml")):
        if "matrix" in yaml_file.stem:
            continue  # skip uiao-control-matrix.yaml
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            is_gold = bool(data.get("gold_standard") or
                          data.get("narrative_quality") == "gold")
            has_narrative = bool(data.get("narrative") or
                                data.get("implementation_statement"))
            has_evidence = bool(data.get("evidence_links") or
                               data.get("evidence_path") or
                               data.get("oscal_evidence"))
            narrative_str = (
                "✅ Gold" if is_gold else
                "✅" if has_narrative else "❌"
            )
            evidence_str = (
                "✅" if has_evidence else
                "⚠️" if has_narrative else "❌"
            )
            gap = (
                "—" if has_narrative and has_evidence else
                "evidence gap" if has_narrative else
                "narrative gap"
            )
            rows.append({
                "id": yaml_file.stem,
                "title": data.get("title", data.get("name", "—"))[:50],
                "narrative": narrative_str,
                "evidence": evidence_str,
                "gap": gap,
            })
        except Exception as exc:
            rows.append({
                "id": yaml_file.stem, "title": "parse error",
                "narrative": "❌", "evidence": "❌",
                "gap": str(exc)[:40],
            })

    gold = sum(1 for r in rows if r["narrative"] == "✅ Gold")
    covered = sum(1 for r in rows if r["gap"] == "—")
    return rows, gold, covered, len(rows)


def collect_oscal_status(root: Path) -> dict:
    """
    Check OSCAL artifact status from exports/oscal/.
    Source: exports/oscal/*.json
    """
    oscal_dir = root / "exports" / "oscal"
    artifacts = {
        "SSP": "uiao-ssp-skeleton.json",
        "Component Definition": "uiao-component-definition.json",
        "POA&M": "uiao-poam.json",
    }
    status = {}
    for name, filename in artifacts.items():
        path = oscal_dir / filename
        if path.exists():
            size_kb = path.stat().st_size // 1024
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                # Check for basic OSCAL structure
                valid = bool(
                    data.get("system-security-plan") or
                    data.get("component-definition") or
                    data.get("plan-of-action-and-milestones")
                )
                status[name] = {
                    "present": True,
                    "size_kb": size_kb,
                    "valid_structure": valid,
                }
            except Exception:
                status[name] = {"present": True, "size_kb": size_kb,
                                "valid_structure": False}
        else:
            status[name] = {"present": False, "size_kb": 0,
                            "valid_structure": False}
    return status


def collect_priorities(root: Path) -> tuple[list[str], list[str]]:
    """Pull priorities and decisions from PROJECT-CONTEXT.md."""
    ctx_path = root / "PROJECT-CONTEXT.md"
    if not ctx_path.exists():
        return ["PROJECT-CONTEXT.md not found"], []

    text = ctx_path.read_text(encoding="utf-8")
    priorities, decisions, in_priorities = [], [], False

    for line in text.splitlines():
        if "Current Priorities" in line:
            in_priorities = True
            continue
        if in_priorities:
            if line.startswith("##"):
                break
            if line.strip().startswith("*"):
                priorities.append(line.strip().lstrip("* ").strip())

    for line in text.splitlines():
        if re.match(r"^\* 202\d-\d{2}-\d{2}:", line):
            decisions.append(line.strip().lstrip("* ").strip())

    return priorities, decisions[:5]


def collect_changelog(root: Path, n: int = 10) -> list[str]:
    """Pull last n entries as plain English from CHANGELOG.md."""
    changelog_path = root / "CHANGELOG.md"
    if not changelog_path.exists():
        return ["CHANGELOG.md not found"]

    entries = []
    for line in changelog_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\* (.+?) \(\[", line)
        if match:
            entries.append(match.group(1).strip())
        if len(entries) >= n:
            break
    return entries or ["No changelog entries found"]


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_briefing(settings: Settings, include_history: bool = True) -> Path:
    """
    Build the briefing DOCX. Returns output path.
    Visual quality target: 01_Canon/uiao-reference.docx
    """
    root = Path(settings.project_root)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = root / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"UIAO-BRIEFING-{today}.docx"

    doc = Document()

    # Page margins: 1 inch all sides
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # -----------------------------------------------------------------------
    # Cover page
    # -----------------------------------------------------------------------
    _add_cui_banner(doc)
    doc.add_paragraph()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run("Unified Identity-Addressing-Overlay Architecture (UIAO)")
    run.bold = True
    run.font.color.rgb = COLOR_TITLE
    run.font.size = Pt(28)

    subtitle = doc.add_paragraph()
    run2 = subtitle.add_run("Personal Briefing Document")
    run2.bold = True
    run2.font.color.rgb = COLOR_TITLE
    run2.font.size = Pt(14)

    tagline = doc.add_paragraph()
    run3 = tagline.add_run("Live System State — Generated on Demand — Never Hand-Edited")
    run3.italic = True
    run3.font.color.rgb = COLOR_SUBTITLE
    run3.font.size = Pt(12)

    doc.add_paragraph()
    meta_lines = [
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "Owner: Michael Stratton (whalermike)",
        "Repo: https://github.com/WhalerMike/uiao-core",
        "Classification: CUI // FOUO",
    ]
    for line in meta_lines:
        p = doc.add_paragraph()
        parts = line.split(": ", 1)
        if len(parts) == 2:
            r1 = p.add_run(parts[0] + ": ")
            r1.bold = True
            p.add_run(parts[1])
        else:
            p.add_run(line)

    doc.add_paragraph()

    # Audience routing table
    _add_heading(doc, "How to Use This Briefing", 2, COLOR_SUBTITLE)
    _add_styled_table(
        doc,
        headers=["Page", "Content", "Audience"],
        rows=[
            {"page": "Page 1", "content": "System Health & Recent Issues",
             "aud": "Owner — read this first every session"},
            {"page": "Page 2", "content": "Vendor Stack (The Big 7)",
             "aud": "Architects, Engineers"},
            {"page": "Page 3", "content": "FedRAMP Control Coverage",
             "aud": "Compliance, Auditors"},
            {"page": "Page 4", "content": "Generation Pipeline",
             "aud": "Engineers, Architects"},
            {"page": "Page 5", "content": "Current Priorities & Decisions",
             "aud": "Owner, PMO"},
            {"page": "Page 6", "content": "Agent Activity Log",
             "aud": "Owner (optional)"},
        ],
        keys=["page", "content", "aud"],
    )

    doc.add_page_break()

    # -----------------------------------------------------------------------
    # Page 1 — System Health
    # -----------------------------------------------------------------------
    _add_cui_banner(doc)
    _add_heading(doc, "Page 1 — System Health", 1, COLOR_TITLE)
    doc.add_paragraph(
        "Traffic-light status of all major system components. "
        "CI status requires `gh run list` to fully populate."
    )

    ci_rows = collect_ci_status(root)
    _add_styled_table(
        doc,
        headers=["Component", "Status", "Last Changed", "Notes"],
        rows=ci_rows,
        keys=["component", "status", "last_changed", "notes"],
    )

    # OSCAL artifact status
    _add_heading(doc, "OSCAL Artifact Status", 2, COLOR_SUBTITLE)
    oscal_status = collect_oscal_status(root)
    oscal_rows = []
    for name, info in oscal_status.items():
        oscal_rows.append({
            "artifact": name,
            "present": "✅" if info["present"] else "❌",
            "size": f"{info['size_kb']}KB" if info["present"] else "—",
            "valid": "✅" if info["valid_structure"] else
                     "⚠️ malformed" if info["present"] else "❌",
        })
    _add_styled_table(
        doc,
        headers=["OSCAL Artifact", "Present", "Size", "Valid Structure"],
        rows=oscal_rows,
        keys=["artifact", "present", "size", "valid"],
    )

    # Memory burn log
    _add_heading(doc, "What Burned Recently (UIAO-MEMORY.md)", 2, COLOR_SUBTITLE)
    memory_entries = collect_memory_entries(root)
    for entry in memory_entries:
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(f"{entry['date']} — {entry['task']}: ")
        r.bold = True
        p.add_run(entry["outcome"])
        if entry.get("correction"):
            p2 = doc.add_paragraph(style="List Bullet 2")
            p2.add_run(f"Fix applied: {entry['correction'][:120]}")

    # Dashboard diagram
    _embed_diagram(
        doc,
        root / "assets" / "images" / "mermaid" / "executive_dashboard_status.png",
        "Figure 1.1 — Executive Dashboard Status",
    )

    doc.add_page_break()

    # -----------------------------------------------------------------------
    # Page 2 — The Stack
    # -----------------------------------------------------------------------
    _add_cui_banner(doc)
    _add_heading(doc, "Page 2 — The Vendor Stack", 1, COLOR_TITLE)
    doc.add_paragraph(
        "The Big 7 vendor adapters mapped to UIAO control planes. "
        "Source: data/vendor-overlays/ (live YAML files, not canon docs)."
    )

    adapter_rows = collect_adapter_status(root)
    _add_styled_table(
        doc,
        headers=["Control Plane", "Vendor", "Status", "Controls", "Role"],
        rows=adapter_rows,
        keys=["plane", "vendor", "status", "controls", "role"],
    )

    _embed_diagram(
        doc,
        root / "assets" / "images" / "mermaid" / "multi_plane_integration.png",
        "Figure 2.1 — Multi-Plane Integration",
    )

    _embed_diagram(
        doc,
        root / "assets" / "images" / "mermaid" / "vendor_logic.png",
        "Figure 2.2 — Vendor Logic Flow",
    )

    _embed_diagram(
        doc,
        root / "assets" / "images" / "mermaid" / "unified_arch.png",
        "Figure 2.3 — Unified Architecture",
    )

    doc.add_page_break()

    # -----------------------------------------------------------------------
    # Page 3 — Control Coverage
    # -----------------------------------------------------------------------
    _add_cui_banner(doc)
    _add_heading(doc, "Page 3 — FedRAMP Control Coverage", 1, COLOR_TITLE)

    control_rows, gold, covered, total = collect_control_coverage(root)
    gaps = total - covered

    summary = doc.add_paragraph()
    summary.add_run(f"Total controls: {total}   |   ").bold = False
    r = summary.add_run(f"Gold standard: {gold}   ")
    r.bold = True
    r.font.color.rgb = COLOR_TITLE
    r2 = summary.add_run(f"Covered: {covered}   ")
    r2.bold = True
    r3 = summary.add_run(f"Gaps: {gaps}")
    r3.bold = True
    if gaps > 0:
        r3.font.color.rgb = COLOR_ACCENT

    # Show controls with gaps first, then covered
    gap_rows = [r for r in control_rows if r["gap"] != "—"]
    covered_rows = [r for r in control_rows if r["gap"] == "—"]

    if gap_rows:
        _add_heading(doc, f"Controls With Gaps ({len(gap_rows)})", 2,
                     COLOR_ACCENT)
        _add_styled_table(
            doc,
            headers=["Control ID", "Title", "Narrative", "Evidence", "Gap"],
            rows=gap_rows[:30],  # cap at 30 for readability
            keys=["id", "title", "narrative", "evidence", "gap"],
        )
        if len(gap_rows) > 30:
            doc.add_paragraph(
                f"... and {len(gap_rows) - 30} more. "
                f"See data/control-library/ for full list."
            )

    _embed_diagram(
        doc,
        root / "assets" / "images" / "mermaid" / "mgmt_plane_flow.png",
        "Figure 3.1 — Management Plane Control Flow",
    )

    doc.add_page_break()

    # -----------------------------------------------------------------------
    # Page 4 — Pipeline
    # -----------------------------------------------------------------------
    _add_cui_banner(doc)
    _add_heading(doc, "Page 4 — Generation Pipeline", 1, COLOR_TITLE)
    doc.add_paragraph(
        "How UIAO generates compliance artifacts from the canonical YAML sources."
    )

    # Pipeline flow as structured text
    pipeline_steps = [
        ("Input", "data/parameters.yml + data/vendor-overlays/*.yaml"),
        ("Context Load", "src/uiao_core/utils/context.py → load_context()"),
        ("Vendor Merge", "Deep merge of active overlays into parameters"),
        ("Control Narratives", "narrative_loader.py → data/control-library/*.yml"),
        ("OSCAL Generation", "generators/oscal.py → exports/oscal/*.json"),
        ("SSP Generation", "generators/ssp.py → OSCAL SSP skeleton"),
        ("POA&M Generation", "generators/poam.py → from telemetry events"),
        ("Evidence Linking", "evidence/collector → linker → bundler triad"),
        ("Diagram Render", "generators/mermaid.py → assets/images/mermaid/*.png"),
        ("Doc Generation", "generators/rich_docx.py → exports/*.docx"),
        ("This Briefing", "generators/briefing.py → exports/UIAO-BRIEFING-{date}.docx"),
    ]

    _add_styled_table(
        doc,
        headers=["Step", "Implementation"],
        rows=[{"step": s[0], "impl": s[1]} for s in pipeline_steps],
        keys=["step", "impl"],
    )

    _embed_diagram(
        doc,
        root / "assets" / "images" / "mermaid" / "enforcement_pipeline_logic.png",
        "Figure 4.1 — Enforcement Pipeline Logic",
    )

    _embed_diagram(
        doc,
        root / "assets" / "images" / "mermaid" / "schema_validation_flow.png",
        "Figure 4.2 — Schema Validation Flow",
    )

    doc.add_page_break()

    # -----------------------------------------------------------------------
    # Page 5 — Priorities & Decisions
    # -----------------------------------------------------------------------
    _add_cui_banner(doc)
    _add_heading(doc, "Page 5 — Current Priorities & Decisions", 1, COLOR_TITLE)
    doc.add_paragraph("Source: PROJECT-CONTEXT.md (live file).")

    priorities, decisions = collect_priorities(root)

    _add_heading(doc, "Current Priorities", 2, COLOR_SUBTITLE)
    for p_text in priorities:
        doc.add_paragraph(p_text, style="List Bullet")

    _add_heading(doc, "Recent Architecture Decisions", 2, COLOR_SUBTITLE)
    for d_text in decisions:
        doc.add_paragraph(d_text, style="List Bullet")

    _embed_diagram(
        doc,
        root / "assets" / "images" / "mermaid" / "roadmap_gantt_visual.png",
        "Figure 5.1 — Implementation Roadmap",
    )

    # -----------------------------------------------------------------------
    # Page 6 — Agent Activity (optional)
    # -----------------------------------------------------------------------
    if include_history:
        doc.add_page_break()
        _add_cui_banner(doc)
        _add_heading(doc, "Page 6 — What the Agents Did Last", 1, COLOR_TITLE)
        doc.add_paragraph(
            "Last 10 changelog entries in plain English. "
            "Source: CHANGELOG.md (auto-generated, commit-driven)."
        )
        for entry in collect_changelog(root):
            doc.add_paragraph(entry, style="List Bullet")

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------
    doc.save(str(output_path))
    return output_path
```

---

### Step 2 — Wire the CLI command

Add to `src/uiao_core/cli/app.py` (find the existing `@app.command()` block
pattern and add after the last command):

```python
@app.command()
def generate_briefing(
    history: bool = typer.Option(
        True,
        "--history/--no-history",
        help="Include agent activity log on Page 6",
    ),
) -> None:
    """
    Generate personal briefing document from live repo state.

    Produces a 6-page DOCX covering system health, vendor stack,
    control coverage, pipeline, priorities, and agent activity.
    Quality target: matches 01_Canon/uiao-reference.docx visual standard.
    """
    from uiao_core.generators.briefing import build_briefing

    typer.echo("📋 Generating UIAO personal briefing...")
    typer.echo("   Reading: MEMORY.md, vendor-overlays/, control-library/,")
    typer.echo("            PROJECT-CONTEXT.md, CHANGELOG.md, exports/oscal/")
    settings = Settings()
    output_path = build_briefing(settings, include_history=history)
    typer.echo(f"✅ Briefing saved: {output_path}")
    typer.echo("   Open this document before starting any agent session.")
```

---

### Step 3 — Create the test file

Create `tests/test_briefing.py`:

```python
"""Tests for briefing generator."""
from pathlib import Path
from unittest.mock import patch
import pytest

from uiao_core.generators.briefing import (
    build_briefing,
    collect_adapter_status,
    collect_changelog,
    collect_control_coverage,
    collect_memory_entries,
    collect_oscal_status,
    collect_priorities,
)


def test_collect_memory_missing(tmp_path):
    entries = collect_memory_entries(tmp_path)
    assert len(entries) >= 1
    assert "not found" in entries[0]["task"].lower()


def test_collect_adapters_missing_dir(tmp_path):
    rows = collect_adapter_status(tmp_path)
    assert any("not found" in r["vendor"].lower() for r in rows)


def test_collect_control_missing_dir(tmp_path):
    rows, gold, covered, total = collect_control_coverage(tmp_path)
    assert total == 0
    assert covered == 0


def test_collect_priorities_missing(tmp_path):
    priorities, decisions = collect_priorities(tmp_path)
    assert any("not found" in p.lower() for p in priorities)


def test_collect_changelog_missing(tmp_path):
    entries = collect_changelog(tmp_path)
    assert any("not found" in e.lower() for e in entries)


def test_collect_oscal_missing(tmp_path):
    status = collect_oscal_status(tmp_path)
    assert all(not v["present"] for v in status.values())


def test_build_briefing_creates_docx(tmp_path):
    from uiao_core.config import Settings
    with patch.object(Settings, "project_root", str(tmp_path)):
        settings = Settings()
        output = build_briefing(settings, include_history=False)
        assert Path(output).exists()
        assert str(output).endswith(".docx")
        assert Path(output).stat().st_size > 5000  # must be non-trivial


def test_build_briefing_with_history(tmp_path):
    from uiao_core.config import Settings
    with patch.object(Settings, "project_root", str(tmp_path)):
        settings = Settings()
        output = build_briefing(settings, include_history=True)
        assert Path(output).exists()
```

---

### Step 4 — Quality gates

Run in order. Do NOT proceed to Step 5 if any fail:

```bash
ruff check src/uiao_core/generators/briefing.py --fix
ruff format src/uiao_core/generators/briefing.py
ruff check tests/test_briefing.py --fix
pytest tests/test_briefing.py -v
```

---

### Step 5 — Commit and push

```bash
git checkout -b feat/generate-briefing
git add src/uiao_core/generators/briefing.py
git add tests/test_briefing.py
git add src/uiao_core/cli/app.py
git add docs/BRIEFING-SPEC.md
git commit -m "feat: add generate-briefing CLI — owner daily dashboard"
git push origin feat/generate-briefing
```

---

### Step 6 — Update UIAO-MEMORY.md

Append to correction log table:

```
| 2026-04-03 | generate-briefing implementation | SUCCESS | — |
Briefing generator created per BRIEFING-SPEC.md. 6-page DOCX at
uiao-reference.docx quality. Sources: MEMORY.md, vendor-overlays/ (9 YAMLs),
control-library/ (131 YAMLs), OSCAL exports, PROJECT-CONTEXT.md,
CHANGELOG.md, drift-report.json. Diagrams from assets/images/mermaid/
(15 PNGs confirmed available). |
```

---

## Data Source Map (confirmed from directory tree)

| Page | Data Source | Path |
|------|-------------|------|
| 1 — Health | Drift report | `reports/drift-report.json` |
| 1 — Health | OSCAL artifacts | `exports/oscal/*.json` |
| 1 — Health | Memory log | `UIAO-MEMORY.md` |
| 2 — Stack | Vendor overlays | `data/vendor-overlays/*.yaml` (9 files) |
| 3 — Coverage | Control library | `data/control-library/*.yml` (131 files) |
| 4 — Pipeline | Config | `data/parameters.yml` |
| 5 — Priorities | Context | `PROJECT-CONTEXT.md` |
| 6 — Activity | Changelog | `CHANGELOG.md` |
| All pages | Diagrams | `assets/images/mermaid/*.png` (15 PNGs) |

## Available Diagrams (confirmed in tree)

These PNGs exist and can be embedded immediately — no generation needed:

- `unified_arch.png` — use Page 2
- `vendor_logic.png` — use Page 2
- `multi_plane_integration.png` — use Page 2
- `executive_dashboard_status.png` — use Page 1
- `roadmap_gantt_visual.png` — use Page 5
- `schema_validation_flow.png` — use Page 4
- `enforcement_pipeline_logic.png` — use Page 4
- `mgmt_plane_flow.png` — use Page 3
- `frontend_integration_map.png` — supplemental
- `incident_escalation_tree.png` — supplemental
- `leaver_killswitch_flow.png` — supplemental
- `mover_scenario_workflow.png` — supplemental
- `jinja_normalization.png` — supplemental
- `appendix_library.png` — supplemental
- `user_to_app_zt_journey.png` — supplemental

## Critical Notes for Claude Code

1. **Use `data/vendor-overlays/`** — NOT `data/overlays/`. These are
   different directories. vendor-overlays/ has the Big 7 production YAMLs.
   data/overlays/ has older legacy YAML files.

2. **Use `rich_docx.py` patterns** for styling — it already implements the
   brand colors and table styles. Import and replicate, don't reinvent.

3. **The `output/` directory** contains timestamped run outputs from the
   PowerShell intelligence suite (UIAO-Document-Report modules). Do not
   confuse with `exports/`. The briefing goes to `exports/`.

4. **131 control YAMLs** confirmed in data/control-library/. Skip
   `uiao-control-matrix.yaml` (it's a summary, not a control narrative).

5. **CUI//FOUO banner** must appear on every page — this matches the
   reference architecture document classification marking.

6. **The `UIAO-Document-Report/` directory** inside the repo is a separate
   PowerShell intelligence suite (20 modules). Do not modify it.

## Agent Rule

Run `uiao generate-briefing` at the START of every Claude Code session
before taking any other action. Treat the output as ground truth for
that session's understanding of system state.
