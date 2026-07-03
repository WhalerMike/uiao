"""OSCAL Assessment Plan generator for FedRAMP AAN KSI coverage.

Produces an OSCAL 1.0.4 Assessment Plan (AP) that describes what will be
assessed, how, and when for the AAN KSI conformance corpus.  The AP UUID
is written into the output file; pass ``--ap-href`` to ``uiao oscal ksi-ar``
to link AR documents back to this AP.

Companion files:
  src/uiao/adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml
  src/uiao/adapters/fedramp_aan_catalog/mappings/slot-*.yaml
  src/uiao/oscal/ksi_ar.py (AR generator that consumes the AP href)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_FEDRAMP_NS = "https://fedramp.gov/ns/oscal"
_AAN_NS = "https://uiao.gov/ns/oscal/aan-evidence"

_MAPPING_PACKAGE = "uiao.adapters.fedramp_cr26_catalog"
_MAPPING_FILE = "mappings/ksi-mapping.yaml"

_KSI_THEMES = ["KSI-CMT", "KSI-CNA", "KSI-IAM", "KSI-MLA", "KSI-PIY", "KSI-RPL", "KSI-SCR", "KSI-SVC"]


def _load_mapping(mapping_path: Path | None = None) -> dict[str, Any]:
    if mapping_path is not None:
        return dict(yaml.safe_load(mapping_path.read_text(encoding="utf-8")))
    from importlib import resources

    candidate = resources.files(_MAPPING_PACKAGE).joinpath(_MAPPING_FILE)
    return dict(yaml.safe_load(Path(str(candidate)).read_text(encoding="utf-8")))


def build_ksi_ap(
    system_name: str = "UIAO Federal AAN Assessment System",
    ssp_href: str = "",
    now: str | None = None,
    mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a full OSCAL Assessment Plan document for the KSI corpus.

    Args:
        system_name: Human-readable name for the system being assessed.
        ssp_href:    Optional href to the system's SSP (OSCAL import-ssp).
        now:         Override the plan timestamp (ISO 8601).
        mapping:     Pre-loaded ksi-mapping.yaml dict (for testing).

    Returns:
        Dict with top-level key ``"assessment-plan"``.
    """
    if now is None:
        now = datetime.now(timezone.utc).isoformat()

    if mapping is None:
        mapping = _load_mapping()

    mapping_rows: list[dict[str, Any]] = mapping.get("mappings", []) or []

    # All CR26 control IDs across all mapping rows.
    all_cr26: list[str] = sorted({ctl for row in mapping_rows for ctl in (row.get("cr26_controls") or [])})

    # Build one assessment task per KSI theme.
    tasks: list[dict[str, Any]] = []
    for theme in _KSI_THEMES:
        theme_controls = [
            r for r in mapping_rows if any(ctl.startswith(theme) for ctl in (r.get("cr26_controls") or []))
        ]
        if not theme_controls:
            continue
        tasks.append(
            {
                "uuid": str(uuid.uuid4()),
                "type": "action",
                "title": f"Assess {theme} KSI controls via AAN slot evidence",
                "description": (
                    f"Evaluate {len(theme_controls)} local KSI rule(s) mapped to the {theme} theme "
                    "by reading AAN conformance adapter slot evidence bindings and "
                    "computing mapping-confidence-based verdicts per ksi_ar.py."
                ),
                "props": [
                    {"name": "ksi-theme", "value": theme, "ns": _FEDRAMP_NS},
                    {"name": "rule-count", "value": str(len(theme_controls)), "ns": _FEDRAMP_NS},
                ],
                "associated-activities": [
                    {
                        "activity-uuid": str(uuid.uuid4()),
                        "subjects": [
                            {
                                "type": "component",
                                "description": f"AAN slot evidence for {theme}",
                            }
                        ],
                    }
                ],
            }
        )

    ap_uuid = str(uuid.uuid4())
    tool_party_uuid = str(uuid.uuid4())
    assessor_party_uuid = str(uuid.uuid4())

    ap: dict[str, Any] = {
        "uuid": ap_uuid,
        "metadata": {
            "title": f"OSCAL AP: {system_name} — FedRAMP AAN KSI Assessment Plan",
            "published": now,
            "last-modified": now,
            "version": str(mapping.get("version", "0.1.0")),
            "oscal-version": "1.0.4",
            "props": [
                {"name": "fedramp-impact", "value": "Moderate", "ns": _FEDRAMP_NS},
                {"name": "assessment-basis", "value": "aan-conformance-adapter", "ns": _AAN_NS},
                {"name": "mapping-snapshot-sha", "value": str(mapping.get("snapshot_sha", "")), "ns": _AAN_NS},
                {"name": "tool", "value": "UIAO AAN Conformance Adapter / ksi_ap", "ns": _FEDRAMP_NS},
                {"name": "ksi-rule-count", "value": str(len(mapping_rows)), "ns": _FEDRAMP_NS},
            ],
            "roles": [
                {"id": "assessor", "title": "UIAO AAN Conformance Adapter (Automated)"},
                {"id": "assessment-lead", "title": "UIAO Program Office"},
            ],
            "parties": [
                {
                    "uuid": tool_party_uuid,
                    "type": "tool",
                    "name": "UIAO AAN Conformance Adapter",
                    "remarks": (
                        "Automated conformance adapter that maps AAN slot evidence to "
                        "CR26 KSI controls and computes OSCAL verdicts."
                    ),
                },
                {
                    "uuid": assessor_party_uuid,
                    "type": "organization",
                    "name": "UIAO Program Office",
                    "remarks": "Assessment lead responsible for AAN evidence governance.",
                },
            ],
        },
        "import-ssp": {
            "href": ssp_href or "#",
            "remarks": "System Security Plan reference. Use uiao oscal generate to produce SSP."
            if not ssp_href
            else "",
        },
        "local-definitions": {
            "remarks": (
                "Assessment conducted via the UIAO AAN Conformance Adapter, reading "
                "ksi-mapping.yaml and slot evidence YAML files to compute per-KSI verdicts."
            )
        },
        "terms-and-conditions": {
            "parts": [
                {
                    "name": "assessment-basis",
                    "title": "Assessment Methodology",
                    "prose": (
                        "This assessment uses mapping-confidence-based verdicts derived from "
                        "the UIAO AAN Conformance Adapter (ADR-061). Evidence is sourced from "
                        f"{len([s for s in range(1, 7)])} AAN conformance adapter surface slots "
                        "(Parts 1–14). A 'satisfied' verdict requires mapping confidence 'high' "
                        "AND a high-confidence AAN slot evidence binding for the CR26 control(s). "
                        "Scaffold rules (Status: scaffold) are assessed identically; the finding "
                        "remark records the pending evaluation-engine state (ADR-111)."
                    ),
                }
            ]
        },
        "reviewed-controls": {
            "control-selections": [
                {
                    "description": "CR26 KSI controls assessed via FedRAMP AAN conformance adapter",
                    "include-controls": [{"control-id": cid} for cid in all_cr26],
                }
            ]
        },
        "assessment-subjects": [
            {
                "type": "component",
                "description": f"{system_name} — FedRAMP AAN KSI evidence corpus",
                "include-all": {},
                "props": [
                    {"name": "assessment-scope", "value": "fedramp-20x-gcc-moderate", "ns": _FEDRAMP_NS},
                    {"name": "aan-series-parts", "value": "1-14", "ns": _AAN_NS},
                ],
            }
        ],
        "assessment-assets": {
            "assessment-platforms": [
                {
                    "uuid": str(uuid.uuid4()),
                    "title": "UIAO AAN Conformance Adapter",
                    "props": [
                        {"name": "tool-name", "value": "uiao oscal ksi-ar / ksi-ap / ksi-poam", "ns": _AAN_NS},
                        {"name": "tool-version", "value": str(mapping.get("version", "0.1.0")), "ns": _AAN_NS},
                    ],
                    "uses-components": [],
                }
            ]
        },
        "tasks": tasks,
        "back-matter": {
            "resources": [
                {
                    "uuid": str(uuid.uuid4()),
                    "title": "FedRAMP 20x CR26 KSI Catalog",
                    "props": [
                        {"name": "catalog-uuid", "value": str(mapping.get("catalog_uuid", "")), "ns": _FEDRAMP_NS},
                        {
                            "name": "catalog-version",
                            "value": str(mapping.get("catalog_version", "")),
                            "ns": _FEDRAMP_NS,
                        },
                        {"name": "snapshot-sha", "value": str(mapping.get("snapshot_sha", "")), "ns": _FEDRAMP_NS},
                    ],
                    "remarks": "Pinned FedRAMP CR26 KSI catalog snapshot (see ksi-mapping.yaml).",
                },
                {
                    "uuid": str(uuid.uuid4()),
                    "title": "UIAO_137 KSI Mapping Companion",
                    "props": [
                        {"name": "governing-doc", "value": str(mapping.get("governing_doc", "")), "ns": _AAN_NS},
                        {"name": "adr", "value": str(mapping.get("adr", "")), "ns": _AAN_NS},
                    ],
                    "remarks": "Machine-readable KSI mapping companion (ksi-mapping.yaml) per ADR-061.",
                },
            ]
        },
    }

    return {"assessment-plan": ap}


def build_ksi_ap_summary(ap_doc: dict[str, Any]) -> str:
    """Return a one-line human-readable summary of an AP document."""
    ap = ap_doc.get("assessment-plan", {})
    meta = ap.get("metadata", {})
    tasks = ap.get("tasks", [])
    controls = ap.get("reviewed-controls", {}).get("control-selections", [{}])
    n_controls = len((controls[0] if controls else {}).get("include-controls", []))
    title = meta.get("title", "Unknown AP")
    published = meta.get("published", "")[:10]
    return f"{title} | {len(tasks)} themes | {n_controls} CR26 controls | {published}"


def export_ksi_ap(
    output_path: str | Path = "output/artifacts/ksi-ap.json",
    system_name: str = "UIAO Federal AAN Assessment System",
    ssp_href: str = "",
    mapping: dict[str, Any] | None = None,
) -> str:
    """Generate and write a KSI Assessment Plan JSON file.

    Returns the absolute path of the written file.
    """
    ap_doc = build_ksi_ap(system_name=system_name, ssp_href=ssp_href, mapping=mapping)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ap_doc, indent=2), encoding="utf-8")
    return str(out)
