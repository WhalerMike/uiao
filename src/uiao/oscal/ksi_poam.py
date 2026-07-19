"""OSCAL Plan of Action and Milestones (POA&M) generator for AAN KSI gaps.

Reads an OSCAL Assessment Results document (produced by ksi_ar.py) and
generates an OSCAL POA&M with one item per non-satisfied KSI finding.

Mapping of AR states to POA&M disposition:
  "satisfied"     → no POA&M item (control is closed)
  "not-satisfied" → open POA&M item, severity moderate, 90-day default SLA
  "other"         → open POA&M item, severity low, milestone date from theme
                    (BOD 26-04 deadline 2026-12-07 for KSI-CMT / KSI-SCR items)

The POAM can be generated standalone from bundled data (same as ksi_ar.py),
or from a previously-written AR JSON file via ``from_ar_path``.

Companion files:
  src/uiao/oscal/ksi_ar.py      (AR that feeds this POAM)
  src/uiao/oscal/ksi_ap.py      (AP that governs this POAM)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uiao.oscal.version import OSCAL_VERSION

_FEDRAMP_NS = "https://fedramp.gov/ns/oscal"
_OrgComp_NS = "https://uiao.gov/ns/oscal/aan-evidence"

# BOD 26-04 VDR/VER deadline — hard milestone for supply-chain / change-mgmt KSIs.
_BOD_2604_DEADLINE = "2026-12-07"

# Themes that carry the BOD 26-04 urgency milestone.
_BOD_THEMES = {"KSI-CMT", "KSI-SCR"}


def _item_severity(state: str, theme: str) -> str:
    if state == "not-satisfied":
        return "moderate"
    if theme in _BOD_THEMES:
        return "moderate"
    return "low"


def _milestone_date(state: str, theme: str, assessment_date: str) -> str:
    """Return an ISO 8601 date string for the POA&M scheduled-completion."""
    if theme in _BOD_THEMES:
        return _BOD_2604_DEADLINE
    # Default: 90 days from assessment for not-satisfied, 180 for other.
    from datetime import timedelta

    try:
        base = datetime.fromisoformat(assessment_date[:10])
    except ValueError:
        base = datetime.now(timezone.utc)
    days = 90 if state == "not-satisfied" else 180
    return (base + timedelta(days=days)).strftime("%Y-%m-%d")


def _finding_theme(cr26_controls: list[str]) -> str:
    """Infer KSI theme from the first CR26 control ID."""
    for ctl in cr26_controls:
        parts = ctl.split("-")
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
    return ""


def _extract_ar_gaps(ar_doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract non-satisfied findings from an OSCAL AR document.

    Returns a list of dicts with keys:
        rule_id, title, state, description, cr26_controls, confidence,
        finding_uuid, observation_uuid, assessment_date

    Note: ksi_ar.py stores ksi-id and assessment-confidence in
    ``finding["target"]["props"]``, not in ``finding["props"]``.
    The CR26 control ID is parsed from ``finding["target"]["target-id"]``
    (format: ``{cr26_control_id}_smt``).
    """
    ar = ar_doc.get("assessment-results", {})
    results = ar.get("results", [])
    if not results:
        return []

    result = results[0]
    assessment_date = result.get("start", "")[:10]
    findings = result.get("findings", [])

    gaps: list[dict[str, Any]] = []
    for finding in findings:
        target = finding.get("target", {})
        status = target.get("status", {})
        state = status.get("state", "")
        if state == "satisfied":
            continue

        # ksi-id and assessment-confidence live in target.props (see ksi_ar._build_ksi_finding).
        target_props = {p["name"]: p["value"] for p in (target.get("props", []) or [])}
        rule_id = target_props.get("ksi-id", "")
        confidence = target_props.get("assessment-confidence", "low")

        # CR26 control ID is encoded as "{control_id}_smt" in target-id.
        target_id = target.get("target-id", "")
        cr26_controls: list[str] = []
        if target_id.endswith("_smt"):
            cr26_controls = [target_id[:-4]]

        related_obs = finding.get("related-observations", [])
        obs_uuid = related_obs[0].get("observation-uuid", "") if related_obs else ""

        gaps.append(
            {
                "rule_id": rule_id,
                "title": finding.get("title", ""),
                "state": state,
                "description": finding.get("remarks", ""),
                "cr26_controls": cr26_controls,
                "confidence": confidence,
                "finding_uuid": finding.get("uuid", ""),
                "observation_uuid": obs_uuid,
                "assessment_date": assessment_date,
            }
        )
    return gaps


def build_ksi_poam(
    ar_doc: dict[str, Any] | None = None,
    system_name: str = "UIAO Federal AAN Assessment System",
    ap_href: str = "",
    ar_href: str = "",
    now: str | None = None,
    slots_dir: Path | None = None,
    rules_dir: Path | None = None,
    mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a full OSCAL POA&M from AR gap findings.

    If ``ar_doc`` is provided, gaps are extracted from it directly.
    Otherwise a fresh AR is built from bundled data (same as ``build_ksi_ar``).

    Args:
        ar_doc:      Pre-built OSCAL AR dict (from ``build_ksi_ar``).
        system_name: Human-readable name for the system.
        ap_href:     Href to the Assessment Plan (OSCAL import-ap).
        ar_href:     Href to the Assessment Results (back-matter reference).
        now:         Override the POA&M timestamp (ISO 8601).
        slots_dir:   Path to AAN slot evidence YAML directory (if building fresh AR).
        rules_dir:   Path to local KSI rule YAML directory (if building fresh AR).
        mapping:     Pre-loaded ksi-mapping.yaml dict (for testing).

    Returns:
        Dict with top-level key ``"plan-of-action-and-milestones"``.
    """
    if now is None:
        now = datetime.now(timezone.utc).isoformat()

    if ar_doc is None:
        from uiao.oscal.ksi_ar import build_ksi_ar

        ar_doc = build_ksi_ar(
            system_name=system_name,
            ap_href=ap_href,
            now=now,
            slots_dir=slots_dir,
            rules_dir=rules_dir,
            mapping=mapping,
        )

    gaps = _extract_ar_gaps(ar_doc)

    poam_items: list[dict[str, Any]] = []
    for gap in gaps:
        rule_id = gap["rule_id"]
        state = gap["state"]
        cr26_controls = gap["cr26_controls"]
        theme = _finding_theme(cr26_controls)
        severity = _item_severity(state, theme)
        deadline = _milestone_date(state, theme, gap["assessment_date"])

        item: dict[str, Any] = {
            "uuid": str(uuid.uuid4()),
            "title": f"Gap: {rule_id} — {state.replace('-', ' ')} ({', '.join(cr26_controls) or 'no CR26 control'})",
            "description": gap["description"]
            or (
                f"KSI rule {rule_id} mapped to CR26 {', '.join(cr26_controls)} "
                f"is {state} in the AAN conformance adapter assessment."
            ),
            "props": [
                {"name": "ksi-id", "value": rule_id, "ns": _FEDRAMP_NS},
                {"name": "state", "value": state, "ns": _FEDRAMP_NS},
                {"name": "severity", "value": severity, "ns": _FEDRAMP_NS},
                {"name": "ksi-theme", "value": theme, "ns": _FEDRAMP_NS},
                {"name": "mapping-confidence", "value": gap["confidence"], "ns": _FEDRAMP_NS},
            ],
            "related-findings": [{"finding-uuid": gap["finding_uuid"]}] if gap.get("finding_uuid") else [],
            "related-observations": [{"observation-uuid": gap["observation_uuid"]}]
            if gap.get("observation_uuid")
            else [],
            "origins": [
                {
                    "actors": [
                        {
                            "type": "tool",
                            "actor-uuid": str(uuid.uuid4()),
                            "title": "UIAO AAN Conformance Adapter / ksi_poam",
                        }
                    ]
                }
            ],
            "risk-links": [
                {
                    "risk-uuid": str(uuid.uuid4()),
                    "response": (
                        "Remediation: fulfill the AAN evidence contract for the affected "
                        f"CR26 control(s) ({', '.join(cr26_controls)}) and re-run the "
                        "conformance adapter assessment to close this POA&M item."
                        + (f" BOD 26-04 milestone: complete by {_BOD_2604_DEADLINE}." if theme in _BOD_THEMES else "")
                    ),
                }
            ],
            "scheduled-completion": deadline,
            "milestones": [
                {
                    "uuid": str(uuid.uuid4()),
                    "title": (
                        f"BOD 26-04 VDR/VER deadline — {rule_id} must satisfy {theme}"
                        if theme in _BOD_THEMES
                        else f"90-day remediation milestone — {rule_id}"
                    ),
                    "description": (
                        f"Scheduled completion: {deadline}."
                        + (
                            " This milestone is driven by BOD 26-04 (December 7, 2026) "
                            "requiring SBOM/VDR evidence for KSI-CMT and KSI-SCR controls."
                            if theme in _BOD_THEMES
                            else ""
                        )
                    ),
                    "scheduled-completion": deadline,
                }
            ],
            "remarks": (
                f"CR26: {', '.join(cr26_controls) or 'none'} | Theme: {theme} | Severity: {severity} | State: {state}"
            ),
        }

        poam_items.append(item)

    system_party_uuid = str(uuid.uuid4())

    poam: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": f"OSCAL POA&M: {system_name} — FedRAMP AAN KSI Gap Remediation",
            "published": now,
            "last-modified": now,
            "version": "0.1.0",
            "oscal-version": OSCAL_VERSION,
            "props": [
                {"name": "fedramp-impact", "value": "Moderate", "ns": _FEDRAMP_NS},
                {"name": "assessment-basis", "value": "aan-conformance-adapter", "ns": _OrgComp_NS},
                {"name": "tool", "value": "UIAO AAN Conformance Adapter / ksi_poam", "ns": _FEDRAMP_NS},
                {"name": "open-items", "value": str(len(poam_items)), "ns": _FEDRAMP_NS},
            ],
            "roles": [
                {"id": "remediation-lead", "title": "UIAO Program Office"},
            ],
            "parties": [
                {
                    "uuid": system_party_uuid,
                    "type": "organization",
                    "name": "UIAO Program Office — AAN Evidence Remediation",
                }
            ],
        },
        "import-ssp": {"href": "#"},
        "system-id": {"identifier-type": "https://fedramp.gov/", "id": system_name},
        "local-definitions": {
            "remarks": (
                "POA&M items derived from OSCAL AR produced by the UIAO AAN "
                "Conformance Adapter. Each item corresponds to a KSI rule whose "
                "verdict is not-satisfied or other (not-evaluated) in the AR."
            )
        },
        "poam-items": poam_items,
        "back-matter": {
            "resources": [
                {
                    "uuid": str(uuid.uuid4()),
                    "title": "Source Assessment Results",
                    "props": [
                        {"name": "type", "value": "oscal-ar", "ns": _OrgComp_NS},
                    ],
                    "rlinks": [{"href": ar_href or "#"}] if ar_href else [],
                    "remarks": "The OSCAL AR document from which these POA&M items were derived.",
                },
                {
                    "uuid": str(uuid.uuid4()),
                    "title": "BOD 26-04 VDR/VER Requirements",
                    "props": [
                        {"name": "type", "value": "external-reference", "ns": _OrgComp_NS},
                        {"name": "deadline", "value": _BOD_2604_DEADLINE, "ns": _OrgComp_NS},
                    ],
                    "remarks": (
                        "Binding Operational Directive 26-04: SBOM/VDR/VER submission "
                        "deadline December 7, 2026. Drives milestones for KSI-CMT and KSI-SCR items."
                    ),
                },
            ]
        },
    }

    return {"plan-of-action-and-milestones": poam}


def build_ksi_poam_summary(poam_doc: dict[str, Any]) -> str:
    """Return a one-line human-readable summary of a POA&M document."""
    poam = poam_doc.get("plan-of-action-and-milestones", {})
    meta = poam.get("metadata", {})
    items = poam.get("poam-items", [])
    bod_items = [
        i for i in items if any(p["value"] in _BOD_THEMES for p in (i.get("props", [])) if p["name"] == "ksi-theme")
    ]
    title = meta.get("title", "Unknown POA&M")
    published = meta.get("published", "")[:10]
    return f"{title} | {len(items)} open items ({len(bod_items)} BOD 26-04) | {published}"


def export_ksi_poam(
    output_path: str | Path = "output/artifacts/ksi-poam.json",
    system_name: str = "UIAO Federal AAN Assessment System",
    ap_href: str = "",
    ar_href: str = "",
    ar_doc: dict[str, Any] | None = None,
    slots_dir: Path | None = None,
    rules_dir: Path | None = None,
    mapping: dict[str, Any] | None = None,
) -> str:
    """Generate and write a KSI POA&M JSON file.

    Returns the absolute path of the written file.
    """
    poam_doc = build_ksi_poam(
        ar_doc=ar_doc,
        system_name=system_name,
        ap_href=ap_href,
        ar_href=ar_href,
        slots_dir=slots_dir,
        rules_dir=rules_dir,
        mapping=mapping,
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(poam_doc, indent=2), encoding="utf-8")
    return str(out)
