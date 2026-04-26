"""OSCAL Assessment Results (SAR) generator.

Produces a FedRAMP-aligned OSCAL Assessment Results document from a
SCuBA transform result + evidence bundle.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from uiao.evidence.bundle import EvidenceBundle
from uiao.evidence.graph import EvidenceGraph
from uiao.ir.models.core import Evidence

_FEDRAMP_NS = "https://fedramp.gov/ns/oscal"
_UIAO_GRAPH_NS = "https://uiao.gov/ns/oscal/graph"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finding_state(evidence: Evidence) -> str:
    """Map Evidence evaluation to OSCAL finding state."""
    if evidence.evaluation.get("passed"):
        return "satisfied"
    return "not-satisfied"


def _finding_risk_state(evidence: Evidence) -> str:
    if evidence.evaluation.get("passed"):
        return "closed"
    return "open"


def _severity(evidence: Evidence) -> str:
    sev = str(evidence.data.get("severity", "Medium"))
    mapping = {"Critical": "very-high", "High": "high", "Medium": "moderate", "Low": "low"}
    return mapping.get(sev, "moderate")


def _build_observation(
    evidence: Evidence,
    now: str,
    *,
    graph: Optional[EvidenceGraph] = None,
) -> Dict[str, Any]:
    """Build a single OSCAL observation from an Evidence object.

    When a UIAO_113 evidence graph is provided, graph-derived props
    (adapter run, scheduler run, top finding severity) are attached to
    the subject's prop list under the ``_UIAO_GRAPH_NS`` namespace so
    auditors can trace each observation back to its scheduler dispatch.
    """
    ksi_id = evidence.data.get("ksi_id", evidence.id)
    status = evidence.data.get("status", "UNKNOWN")
    details = evidence.data.get("details", "")

    subject_props: List[Dict[str, Any]] = [
        {"name": "ksi-id", "value": ksi_id, "ns": _FEDRAMP_NS},
        {"name": "status", "value": status, "ns": _FEDRAMP_NS},
        {
            "name": "evidence-hash",
            "value": evidence.evaluation.get("canonical_hash", "")[:16] or "n/a",
            "ns": _FEDRAMP_NS,
        },
    ]
    obs_links: List[Dict[str, Any]] = []
    if graph is not None:
        control_id = evidence.control_id or ksi_id
        graph_props = graph.sar_props_for_evidence(control_id)
        for name, value in graph_props.items():
            subject_props.append({"name": name, "value": str(value), "ns": _UIAO_GRAPH_NS})
        if graph_props:
            obs_links.append(
                {
                    "rel": "graph-evidence",
                    "href": "#" + graph.resource_uuid_for_control(control_id),
                    "media-type": "application/json",
                }
            )

    obs: Dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "title": "SCuBA Assessment: " + ksi_id,
        "description": details or ("Automated telemetry observation for " + ksi_id + "."),
        "methods": ["AUTOMATED"],
        "types": ["finding"],
        "subjects": [
            {
                "subject-uuid": str(uuid.uuid4()),
                "type": "inventory-item",
                "title": ksi_id,
                "props": subject_props,
            }
        ],
        "collected": evidence.timestamp or now,
        "expires": "",
        "remarks": "run_id="
        + str(evidence.data.get("run_id", "unknown"))
        + " | tenant="
        + str(evidence.data.get("tenant_id", "unknown")),
    }
    if obs_links:
        obs["links"] = obs_links
    return obs


def _build_finding(
    evidence: Evidence,
    observation_uuid: str,
    now: str,
) -> Dict[str, Any]:
    """Build a single OSCAL finding from an Evidence object."""
    ksi_id = evidence.data.get("ksi_id", evidence.id)
    control_id = evidence.control_id or ksi_id
    state = _finding_state(evidence)
    status_label = evidence.data.get("status", "UNKNOWN")
    return {
        "uuid": str(uuid.uuid4()),
        "title": ksi_id + ": " + status_label,
        "description": (
            "SCuBA automated assessment finding for " + ksi_id + " mapped to NIST control " + control_id + "."
        ),
        "target": {
            "type": "statement-id",
            "target-id": control_id + "_smt",
            "title": control_id,
            "props": [
                {"name": "ksi-id", "value": ksi_id, "ns": _FEDRAMP_NS},
                {"name": "assessment-status", "value": status_label, "ns": _FEDRAMP_NS},
            ],
            "status": {"state": state},
        },
        "related-observations": [{"observation-uuid": observation_uuid}],
        "collected": now,
        "props": [
            {"name": "severity", "value": _severity(evidence), "ns": _FEDRAMP_NS},
            {"name": "finding-state", "value": state, "ns": _FEDRAMP_NS},
        ],
    }


def _build_risk(evidence: Evidence, finding_uuid: str, now: str) -> Optional[Dict[str, Any]]:
    """Build an OSCAL risk entry for FAIL/WARN evidence. Returns None for PASS."""
    if evidence.evaluation.get("passed"):
        return None
    ksi_id = evidence.data.get("ksi_id", evidence.id)
    control_id = evidence.control_id or ksi_id
    severity = _severity(evidence)
    status = evidence.data.get("status", "FAIL")
    details = evidence.data.get("details", "")
    return {
        "uuid": str(uuid.uuid4()),
        "title": "Risk: " + ksi_id + " " + status,
        "description": details or ("Control " + control_id + " is not satisfied per SCuBA telemetry."),
        "statement": (
            "The assessed control " + control_id + " (" + ksi_id + ") returned status " + status + ". "
            "This represents a compliance gap requiring remediation."
        ),
        "props": [
            {"name": "ksi-id", "value": ksi_id, "ns": _FEDRAMP_NS},
            {"name": "control-id", "value": control_id, "ns": _FEDRAMP_NS},
        ],
        "status": _finding_risk_state(evidence),
        "characterizations": [
            {
                "origin": {"actors": [{"type": "tool", "actor-uuid": str(uuid.uuid4()), "title": "SCuBA"}]},
                "facets": [
                    {"name": "likelihood", "system": _FEDRAMP_NS, "value": severity},
                    {"name": "impact", "system": _FEDRAMP_NS, "value": severity},
                ],
            }
        ],
        "deadline": now,
        "related-findings": [{"finding-uuid": finding_uuid}],
    }


def _build_back_matter(
    bundle: EvidenceBundle,
    *,
    graph: Optional[EvidenceGraph] = None,
) -> Dict[str, Any]:
    """Build OSCAL back-matter with evidence resource links.

    When a UIAO_113 graph is provided, one additional resource per
    graph-covered control is appended so the per-observation
    ``links[].href = #<resource-uuid>`` references resolve.
    """
    resources = []
    for e in bundle.evidence:
        ksi_id = e.data.get("ksi_id", e.id)
        resources.append(
            {
                "uuid": str(uuid.uuid4()),
                "title": "SCuBA Evidence: " + ksi_id,
                "props": [
                    {"name": "ksi-id", "value": ksi_id, "ns": _FEDRAMP_NS, "uuid": str(uuid.uuid4())},
                    {
                        "name": "status",
                        "value": e.data.get("status", "UNKNOWN"),
                        "ns": _FEDRAMP_NS,
                        "uuid": str(uuid.uuid4()),
                    },
                    {"name": "evidence-id", "value": e.id, "ns": _FEDRAMP_NS, "uuid": str(uuid.uuid4())},
                    {
                        "name": "run-id",
                        "value": e.data.get("run_id", "unknown"),
                        "ns": _FEDRAMP_NS,
                        "uuid": str(uuid.uuid4()),
                    },
                ],
                "remarks": "Canonical hash prefix: " + (e.evaluation.get("canonical_hash", "")[:16] or "n/a"),
            }
        )
    if graph is not None:
        control_ids = [e.control_id for e in bundle.evidence if e.control_id]
        for res in graph.back_matter_resources_for_controls(control_ids).values():
            resources.append(res)
    return {"resources": resources}


def build_sar(
    bundle: EvidenceBundle,
    system_name: str = "UIAO SCuBA Assessment System",
    tenant_id: str = "",
    ap_href: str = "",
    now: Optional[str] = None,
    graph: Optional[EvidenceGraph] = None,
) -> Dict[str, Any]:
    """Build a full OSCAL Assessment Results document from an EvidenceBundle.

    Args:
        bundle:      EvidenceBundle from build_bundle_from_transform_result().
        system_name: Human-readable system name for metadata.
        tenant_id:   M365 tenant identifier.
        ap_href:     Optional href to an existing Assessment Plan.
        now:         Override assessment timestamp (ISO 8601).
        graph:       Optional UIAO_113 EvidenceGraph. When present, each
                     observation is augmented with graph-derived props
                     (adapter run, scheduler run id, top finding severity)
                     so auditors can trace each finding back through the
                     adapter dispatch that produced it.

    Returns:
        Dict with top-level key "assessment-results".
    """
    now = now or _now()
    prov_ts = bundle.provenance.timestamp or now
    agency_party_uuid = str(uuid.uuid4())

    control_ids = sorted({e.control_id for e in bundle.evidence if e.control_id})

    observations: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []

    for evidence in bundle.evidence:
        obs = _build_observation(evidence, prov_ts, graph=graph)
        observations.append(obs)
        finding = _build_finding(evidence, obs["uuid"], now)
        findings.append(finding)
        risk = _build_risk(evidence, finding["uuid"], now)
        if risk is not None:
            risks.append(risk)

    if control_ids:
        reviewed_controls: Dict[str, Any] = {
            "control-selections": [
                {
                    "description": "Controls assessed via SCuBA automated telemetry",
                    "include-controls": [{"control-id": cid} for cid in control_ids],
                }
            ]
        }
    else:
        reviewed_controls = {
            "control-selections": [
                {
                    "description": "SCuBA KSI results (controls pending NIST mapping)",
                    "include-all": {},
                }
            ]
        }

    sar: Dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": "OSCAL SAR: " + system_name + " \u2014 SCuBA Run " + bundle.run_id,
            "published": now,
            "last-modified": now,
            "version": bundle.provenance.version or "1.0",
            "oscal-version": "1.0.4",
            "props": [
                {"name": "fedramp-impact", "value": "Moderate", "ns": _FEDRAMP_NS},
                {"name": "run-id", "value": bundle.run_id, "ns": _FEDRAMP_NS},
                {"name": "tenant-id", "value": tenant_id or "unknown", "ns": _FEDRAMP_NS},
                {"name": "tool", "value": "SCuBA / UIAO-Core", "ns": _FEDRAMP_NS},
                {"name": "bundle-hash", "value": bundle.hash()[:32], "ns": _FEDRAMP_NS},
            ],
            "roles": [
                {"id": "assessor", "title": "Automated Assessor (SCuBA)"},
                {"id": "assessment-lead", "title": "UIAO Program Office"},
            ],
            "parties": [
                {
                    "uuid": agency_party_uuid,
                    "type": "organization",
                    "name": "UIAO Program Office \u2014 Automated Assessment",
                }
            ],
        },
        "import-ap": {
            "href": ap_href or "#",
            "remarks": ("Assessment Plan not yet generated. Use uiao generate-sap." if not ap_href else ""),
        },
        "results": [
            {
                "uuid": str(uuid.uuid4()),
                "title": "SCuBA Assessment Results: " + bundle.run_id,
                "description": (
                    "Automated SCuBA assessment of " + str(len(bundle.evidence)) + " KSI controls. "
                    "PASS: "
                    + str(bundle.pass_count)
                    + ", WARN: "
                    + str(bundle.warn_count)
                    + ", FAIL: "
                    + str(bundle.fail_count)
                    + "."
                ),
                "start": prov_ts,
                "end": now,
                "props": [
                    {"name": "pass-count", "value": str(bundle.pass_count), "ns": _FEDRAMP_NS},
                    {"name": "warn-count", "value": str(bundle.warn_count), "ns": _FEDRAMP_NS},
                    {"name": "fail-count", "value": str(bundle.fail_count), "ns": _FEDRAMP_NS},
                    {"name": "unmapped-ksi-count", "value": str(len(bundle.unmapped_ksi_ids)), "ns": _FEDRAMP_NS},
                ],
                "reviewed-controls": reviewed_controls,
                "observations": observations,
                "findings": findings,
                "risks": risks,
            }
        ],
        "back-matter": _build_back_matter(bundle, graph=graph),
    }

    return {"assessment-results": sar}


def build_sar_summary(sar_doc: Dict[str, Any]) -> str:
    """Return a human-readable summary of an OSCAL SAR document."""
    ar = sar_doc.get("assessment-results", {})
    meta = ar.get("metadata", {})
    results = ar.get("results", [{}])[0]
    props = {p["name"]: p["value"] for p in results.get("props", [])}
    findings = results.get("findings", [])
    risks = results.get("risks", [])
    run_id = next((p["value"] for p in meta.get("props", []) if p["name"] == "run-id"), "n/a")
    lines = [
        meta.get("title", "untitled"),
        "  Run ID      : " + run_id,
        "  PASS        : " + props.get("pass-count", "?"),
        "  WARN        : " + props.get("warn-count", "?"),
        "  FAIL        : " + props.get("fail-count", "?"),
        "  Findings    : " + str(len(findings)),
        "  Open risks  : " + str(sum(1 for r in risks if r.get("status") == "open")),
    ]
    return "\n".join(lines)


def export_sar(
    bundle: EvidenceBundle,
    output_path: str,
    system_name: str = "UIAO SCuBA Assessment System",
    tenant_id: str = "",
    ap_href: str = "",
    graph: Optional[EvidenceGraph] = None,
) -> str:
    """Build and write the OSCAL SAR JSON to output_path. Returns the path.

    Forwards the optional ``graph`` kwarg to :func:`build_sar` so the
    emitted SAR carries UIAO_113 graph-derived links when a scheduler
    run has been ingested.
    """
    sar_doc = build_sar(
        bundle,
        system_name=system_name,
        tenant_id=tenant_id,
        ap_href=ap_href,
        graph=graph,
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sar_doc, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out)
