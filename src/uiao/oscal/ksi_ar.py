"""OSCAL Assessment Results generator for FedRAMP AAN KSI slot evidence.

Reads the KSI mapping (ksi-mapping.yaml) and the FedRAMP AAN conformance
adapter slot evidence files (slot-01..07) and produces an OSCAL
Assessment Results document with per-KSI satisfied / not-satisfied /
other (not-evaluated) verdicts.

Closes the Phase 2 gap from the Federal AAN ConMon gap roadmap:
  "OSCAL Emitter extended to produce AR with KSI verdicts"

Verdict logic
-------------
Active rules (Status: active):
  Evaluated by ``uiao.ksi.slot_evaluator.evaluate_rule()`` against the AAN
  slot binding index (ADR-111 evaluation engine wiring):
  - satisfied     : every CR26 control has a high-confidence slot binding
  - not-satisfied : slot bindings exist but no high-confidence one found
  - other         : no slot binding for any of the CR26 controls

Scaffold rules (Status: scaffold):
  Mapping-confidence-based (evidence exists but evaluation engine not yet wired
  for this rule; the remark records the pending state so auditors are not misled):
  - satisfied     : mapping confidence == "high" AND high-confidence AAN binding
  - not-satisfied : mapping confidence == "medium" OR only medium-confidence bindings
  - other         : no AAN binding found, or mapping confidence == "low"

Companion files:
  src/uiao/adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml
  src/uiao/adapters/fedramp_aan_catalog/mappings/slot-*.yaml
  src/uiao/ksi/rules/KSI-*.yaml
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

_FEDRAMP_NS = "https://fedramp.gov/ns/oscal"
_AAN_NS = "https://uiao.gov/ns/oscal/aan-evidence"

_SLOTS_PACKAGE = "uiao.adapters.fedramp_aan_catalog"
_SLOTS_SUBPATH = "mappings"


# ---------------------------------------------------------------------------
# Resource discovery
# ---------------------------------------------------------------------------


def default_slots_dir() -> Path:
    """Return the on-disk path of the AAN slot evidence mappings directory."""
    candidate = resources.files(_SLOTS_PACKAGE).joinpath(_SLOTS_SUBPATH)
    return Path(str(candidate))


def default_ksi_rules_dir() -> Path:
    """Return the on-disk path of the local KSI rule YAML files."""
    candidate = resources.files("uiao.ksi").joinpath("rules")
    return Path(str(candidate))


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_slot_files(slots_dir: Path | None = None) -> list[dict[str, Any]]:
    """Load all slot-*.yaml evidence binding files from *slots_dir*.

    Returns a list of parsed YAML dicts in slot-number order.
    """
    d = slots_dir or default_slots_dir()
    docs: list[dict[str, Any]] = []
    for path in sorted(d.glob("slot-*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict):
            docs.append(doc)
    return docs


def load_ksi_rules(rules_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load all KSI-*.yaml rule files, keyed by KSI_ID."""
    d = rules_dir or default_ksi_rules_dir()
    rules: dict[str, dict[str, Any]] = {}
    for path in sorted(d.glob("KSI-*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and "KSI_ID" in doc:
            rules[doc["KSI_ID"]] = doc
    return rules


# ---------------------------------------------------------------------------
# Binding index
# ---------------------------------------------------------------------------


def build_cr26_binding_index(
    slots: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Return ``{cr26_control_id: [binding_entry, ...]}``.

    Each *binding_entry* carries the slot context so callers can trace
    every verdict back to its source slot YAML.
    """
    index: dict[str, list[dict[str, Any]]] = {}
    for slot in slots:
        slot_id = slot.get("slot_id", "?")
        slot_name = slot.get("slot", "")
        for binding in slot.get("bindings", []) or []:
            artifact_refs = list(binding.get("artifact_refs", []) or [])
            confidence = str(binding.get("confidence", "low"))
            rationale = str(binding.get("rationale", "")).strip()
            entry: dict[str, Any] = {
                "slot_id": slot_id,
                "slot": slot_name,
                "artifact_refs": artifact_refs,
                "confidence": confidence,
                "rationale": rationale,
            }
            for cr26_ctl in binding.get("cr26_controls", []) or []:
                index.setdefault(str(cr26_ctl), []).append(entry)
    return index


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------


def _ksi_verdict(
    row: dict[str, Any],
    rule_doc: dict[str, Any],
    binding_index: dict[str, list[dict[str, Any]]],
) -> tuple[str, str, list[str]]:
    """Return ``(state, description, artifact_refs)`` for one KSI mapping row.

    ``state`` is an OSCAL finding target status:
        "satisfied"     — slot-evidence pass (active) or high-confidence mapping + binding (scaffold)
        "not-satisfied" — slot-evidence fail or medium-confidence mismatch
        "other"         — no slot binding found, or mapping confidence low (scaffold)

    ``artifact_refs`` is the sorted deduplicated list of AAN Part IDs that
    back the verdict (empty when state is "other").
    """
    from uiao.ksi.slot_evaluator import evaluate_rule as _eval_slot

    rule_id = str(row.get("local_rule", ""))
    cr26_controls: list[str] = list(row.get("cr26_controls", []) or [])
    is_scaffold = rule_doc.get("Status") == "scaffold"

    # Common binding data used by both paths.
    all_bindings: list[dict[str, Any]] = [b for cr26 in cr26_controls for b in binding_index.get(cr26, [])]
    high_bindings = [b for b in all_bindings if b.get("confidence") == "high"]
    all_artifact_refs: list[str] = sorted({ref for b in all_bindings for ref in b.get("artifact_refs", [])})
    high_artifact_refs: list[str] = sorted({ref for b in high_bindings for ref in b.get("artifact_refs", [])})
    covered_slots = sorted({b["slot_id"] for b in all_bindings})

    if not is_scaffold:
        # Active rule: delegate to the slot evaluator (ADR-111 wiring).
        slot_verdict = _eval_slot(rule_doc, row, binding_index)

        if slot_verdict == "pass":
            desc = (
                f"CR26 controls {cr26_controls} evaluated via AAN slot evidence: "
                f"artifacts {high_artifact_refs}, slot(s) {covered_slots}. "
                "Slot-evidence verdict: pass (high-confidence binding confirmed)."
            )
            return ("satisfied", desc, high_artifact_refs)

        if slot_verdict == "fail":
            desc = (
                f"CR26 controls {cr26_controls} have slot bindings "
                f"(artifacts: {all_artifact_refs}, slot(s): {covered_slots}) "
                "but no high-confidence binding confirmed. Slot-evidence verdict: fail."
            )
            return ("not-satisfied", desc, all_artifact_refs)

        # inconclusive — no slot binding for any CR26 control.
        desc = (
            f"No AAN slot evidence binding found for CR26 controls {cr26_controls}. "
            "Evidence not yet bound to this rule in any slot evidence YAML."
        )
        return ("other", desc, [])

    # Scaffold rule: mapping-confidence path (evaluation engine not yet wired).
    mapping_confidence = str(row.get("confidence", "low"))
    scaffold_note = (
        f" Rule {rule_id} carries Status: scaffold — automated evaluation engine"
        " pending; this verdict is mapping-confidence-based (ADR-111)."
    )

    if not all_bindings:
        desc = (
            f"No AAN slot evidence binding found for CR26 controls {cr26_controls}. "
            "Evidence not yet bound to this rule in any slot evidence YAML." + scaffold_note
        )
        return ("other", desc, [])

    if mapping_confidence == "high" and high_bindings:
        desc = (
            f"CR26 controls {cr26_controls} are covered by AAN artifacts "
            f"{high_artifact_refs} via slot(s) {covered_slots}. "
            f"Mapping confidence: {mapping_confidence}; slot binding confidence: high." + scaffold_note
        )
        return ("satisfied", desc, high_artifact_refs)

    if mapping_confidence in ("medium", "high"):
        desc = (
            f"Partial coverage: CR26 controls {cr26_controls} are bound with "
            f"mapping confidence {mapping_confidence}. AAN artifacts: {all_artifact_refs}; "
            f"slot(s): {covered_slots}. High-confidence slot bindings: {len(high_bindings)}." + scaffold_note
        )
        return ("not-satisfied", desc, all_artifact_refs)

    desc = (
        f"Low-confidence mapping: CR26 controls {cr26_controls}; "
        f"mapping confidence: {mapping_confidence}. AAN artifacts: {all_artifact_refs}." + scaffold_note
    )
    return ("other", desc, all_artifact_refs)


# ---------------------------------------------------------------------------
# OSCAL AR builders
# ---------------------------------------------------------------------------


def _build_ksi_observation(
    row: dict[str, Any],
    state: str,
    description: str,
    artifact_refs: list[str],
    now: str,
) -> dict[str, Any]:
    rule_id = str(row.get("local_rule", "?"))
    cr26_controls: list[str] = list(row.get("cr26_controls", []) or [])
    nist_controls: list[str] = [str(n) for n in (row.get("local_nist", []) or [])]
    method = "AUTOMATED" if state == "satisfied" else "EXAMINE"
    obs_type = "finding" if state in ("satisfied", "not-satisfied") else "not-reviewed"

    subject_props: list[dict[str, Any]] = [
        {"name": "ksi-id", "value": rule_id, "ns": _FEDRAMP_NS},
        {"name": "verdict", "value": state, "ns": _FEDRAMP_NS},
        {"name": "mapping-confidence", "value": str(row.get("confidence", "low")), "ns": _FEDRAMP_NS},
    ]
    for cr26 in cr26_controls:
        subject_props.append({"name": "cr26-control", "value": cr26, "ns": _FEDRAMP_NS})
    for nist in nist_controls:
        subject_props.append({"name": "nist-control", "value": nist, "ns": _FEDRAMP_NS})
    for art in artifact_refs:
        subject_props.append({"name": "aan-artifact", "value": art, "ns": _AAN_NS})

    return {
        "uuid": str(uuid.uuid4()),
        "title": f"KSI Assessment: {rule_id} — {row.get('local_title', '')}",
        "description": description,
        "methods": [method],
        "types": [obs_type],
        "subjects": [
            {
                "subject-uuid": str(uuid.uuid4()),
                "type": "inventory-item",
                "title": rule_id,
                "props": subject_props,
            }
        ],
        "collected": now,
        "expires": "",
        "remarks": (
            f"CR26: {', '.join(cr26_controls) or 'none'} | "
            f"NIST: {', '.join(nist_controls) or 'none'} | "
            f"AAN artifacts: {', '.join(artifact_refs) or 'none'}"
        ),
    }


def _build_ksi_finding(
    row: dict[str, Any],
    observation_uuid: str,
    state: str,
    description: str,
    now: str,
) -> dict[str, Any]:
    rule_id = str(row.get("local_rule", "?"))
    cr26_controls: list[str] = list(row.get("cr26_controls", []) or [])
    control_id = cr26_controls[0] if cr26_controls else rule_id
    confidence = str(row.get("confidence", "low"))
    return {
        "uuid": str(uuid.uuid4()),
        "title": f"{rule_id}: {state}",
        "description": (
            f"AAN evidence assessment for {rule_id} mapped to {', '.join(cr26_controls) or 'no CR26 control'}."
        ),
        "target": {
            "type": "statement-id",
            "target-id": f"{control_id}_smt",
            "title": control_id,
            "props": [
                {"name": "ksi-id", "value": rule_id, "ns": _FEDRAMP_NS},
                {"name": "assessment-confidence", "value": confidence, "ns": _FEDRAMP_NS},
            ],
            "status": {"state": state},
        },
        "related-observations": [{"observation-uuid": observation_uuid}],
        "collected": now,
        "remarks": description,
        "props": [
            {"name": "verdict", "value": state, "ns": _FEDRAMP_NS},
            {"name": "mapping-confidence", "value": confidence, "ns": _FEDRAMP_NS},
            {"name": "evidence-basis", "value": "aan-conformance-adapter", "ns": _AAN_NS},
        ],
    }


def _build_ksi_risk(
    row: dict[str, Any],
    finding_uuid: str,
    state: str,
    description: str,
    now: str,
) -> dict[str, Any] | None:
    if state == "satisfied":
        return None
    rule_id = str(row.get("local_rule", "?"))
    cr26_controls: list[str] = list(row.get("cr26_controls", []) or [])
    severity = "moderate" if state == "not-satisfied" else "low"
    risk_status = "open" if state == "not-satisfied" else "closed"
    return {
        "uuid": str(uuid.uuid4()),
        "title": f"Gap: {rule_id} — {state}",
        "description": description or f"KSI {rule_id} is not fully covered by AAN evidence.",
        "statement": (
            f"CR26 control(s) {cr26_controls} claimed by {rule_id} "
            f"are not fully satisfied by AAN slot evidence ({state})."
        ),
        "props": [
            {"name": "ksi-id", "value": rule_id, "ns": _FEDRAMP_NS},
            {"name": "cr26-controls", "value": ", ".join(cr26_controls), "ns": _FEDRAMP_NS},
        ],
        "status": risk_status,
        "characterizations": [
            {
                "origin": {
                    "actors": [
                        {
                            "type": "tool",
                            "actor-uuid": str(uuid.uuid4()),
                            "title": "UIAO AAN Conformance Adapter",
                        }
                    ]
                },
                "facets": [
                    {"name": "likelihood", "system": _FEDRAMP_NS, "value": severity},
                    {"name": "impact", "system": _FEDRAMP_NS, "value": severity},
                ],
            }
        ],
        "deadline": now,
        "related-findings": [{"finding-uuid": finding_uuid}],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_ksi_ar(
    system_name: str = "UIAO Federal AAN Assessment System",
    ap_href: str = "",
    now: str | None = None,
    slots_dir: Path | None = None,
    rules_dir: Path | None = None,
    mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a full OSCAL Assessment Results document for all KSI mapping rows.

    Args:
        system_name: Human-readable name for the assessed system.
        ap_href:     Optional href to an existing Assessment Plan.
        now:         Override the assessment timestamp (ISO 8601).
        slots_dir:   Path to the AAN slot evidence YAML directory.
                     Defaults to the bundled ``fedramp_aan_catalog/mappings/``.
        rules_dir:   Path to the local KSI rule YAML directory.
                     Defaults to the bundled ``uiao/ksi/rules/``.
        mapping:     Pre-loaded ksi-mapping.yaml dict (for testing).
                     Defaults to the bundled mapping via ``load_mapping()``.

    Returns:
        Dict with top-level key ``"assessment-results"``.
    """
    from uiao.adapters.fedramp_cr26_catalog import load_mapping as _load_mapping

    if now is None:
        now = datetime.now(timezone.utc).isoformat()

    if mapping is None:
        mapping = _load_mapping()

    slots = load_slot_files(slots_dir)
    rules = load_ksi_rules(rules_dir)
    binding_index = build_cr26_binding_index(slots)

    mapping_rows: list[dict[str, Any]] = mapping.get("mappings", []) or []

    observations: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []

    satisfied_count = 0
    not_satisfied_count = 0
    not_evaluated_count = 0

    for row in mapping_rows:
        rule_id = str(row.get("local_rule", ""))
        rule_doc = rules.get(rule_id, {})
        state, description, artifact_refs = _ksi_verdict(row, rule_doc, binding_index)

        obs = _build_ksi_observation(row, state, description, artifact_refs, now)
        observations.append(obs)

        finding = _build_ksi_finding(row, obs["uuid"], state, description, now)
        findings.append(finding)

        risk = _build_ksi_risk(row, finding["uuid"], state, description, now)
        if risk is not None:
            risks.append(risk)

        if state == "satisfied":
            satisfied_count += 1
        elif state == "not-satisfied":
            not_satisfied_count += 1
        else:
            not_evaluated_count += 1

    # Collect all CR26 control IDs for reviewed-controls.
    all_cr26: list[str] = sorted({ctl for row in mapping_rows for ctl in (row.get("cr26_controls") or [])})
    reviewed_controls: dict[str, Any] = {
        "control-selections": [
            {
                "description": "CR26 KSI controls assessed via FedRAMP AAN conformance adapter slot evidence",
                "include-controls": [{"control-id": cid} for cid in all_cr26],
            }
        ]
    }

    # Back-matter: one resource per slot file.
    back_matter_resources: list[dict[str, Any]] = []
    for slot in slots:
        slot_id = slot.get("slot_id", "?")
        slot_name = slot.get("slot", "")
        artifacts = slot.get("artifacts", []) or []
        back_matter_resources.append(
            {
                "uuid": str(uuid.uuid4()),
                "title": f"AAN Slot {slot_id}: {slot_name}",
                "props": [
                    {"name": "slot-id", "value": str(slot_id), "ns": _AAN_NS},
                    {"name": "slot-name", "value": slot_name, "ns": _AAN_NS},
                    {"name": "ksi-category", "value": str(slot.get("ksi_category", "")), "ns": _AAN_NS},
                    {"name": "nist-anchor", "value": str(slot.get("nist_anchor", "")), "ns": _AAN_NS},
                    {"name": "artifact-count", "value": str(len(artifacts)), "ns": _AAN_NS},
                ],
                "remarks": (
                    f"AAN slot {slot_id} ({slot_name}) evidence binding file. "
                    f"Parts: {', '.join(str(a.get('aan_part', '?')) for a in artifacts)}."
                ),
            }
        )

    agency_party_uuid = str(uuid.uuid4())

    ar: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": f"OSCAL AR: {system_name} — FedRAMP AAN KSI Assessment",
            "published": now,
            "last-modified": now,
            "version": str(mapping.get("version", "0.1.0")),
            "oscal-version": "1.0.4",
            "props": [
                {"name": "fedramp-impact", "value": "Moderate", "ns": _FEDRAMP_NS},
                {"name": "assessment-basis", "value": "aan-conformance-adapter", "ns": _AAN_NS},
                {"name": "mapping-snapshot-sha", "value": str(mapping.get("snapshot_sha", "")), "ns": _AAN_NS},
                {"name": "tool", "value": "UIAO AAN Conformance Adapter / ksi_ar", "ns": _FEDRAMP_NS},
                {"name": "slots-bound", "value": str(len(slots)), "ns": _AAN_NS},
            ],
            "roles": [
                {"id": "assessor", "title": "UIAO AAN Conformance Adapter (Automated)"},
                {"id": "assessment-lead", "title": "UIAO Program Office"},
            ],
            "parties": [
                {
                    "uuid": agency_party_uuid,
                    "type": "organization",
                    "name": "UIAO Program Office — AAN Conformance Assessment",
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
                "title": f"AAN KSI Assessment Results: {now[:10]}",
                "description": (
                    f"FedRAMP AAN conformance adapter assessment of {len(mapping_rows)} KSI rules "
                    f"against {len(slots)} slot evidence binding files. "
                    f"Satisfied: {satisfied_count}, "
                    f"Not-satisfied: {not_satisfied_count}, "
                    f"Not-evaluated: {not_evaluated_count}."
                ),
                "start": now,
                "end": now,
                "props": [
                    {"name": "satisfied-count", "value": str(satisfied_count), "ns": _FEDRAMP_NS},
                    {"name": "not-satisfied-count", "value": str(not_satisfied_count), "ns": _FEDRAMP_NS},
                    {"name": "not-evaluated-count", "value": str(not_evaluated_count), "ns": _FEDRAMP_NS},
                    {"name": "total-ksi-rules", "value": str(len(mapping_rows)), "ns": _FEDRAMP_NS},
                    {"name": "slots-bound", "value": str(len(slots)), "ns": _AAN_NS},
                ],
                "reviewed-controls": reviewed_controls,
                "observations": observations,
                "findings": findings,
                "risks": risks,
            }
        ],
        "back-matter": {"resources": back_matter_resources},
    }

    return {"assessment-results": ar}


def build_ksi_ar_summary(ar_doc: dict[str, Any]) -> str:
    """Return a human-readable summary of a KSI AR document."""
    ar = ar_doc.get("assessment-results", {})
    meta = ar.get("metadata", {})
    results = ar.get("results", [{}])[0]
    props = {p["name"]: p["value"] for p in results.get("props", [])}
    findings = results.get("findings", [])
    risks = results.get("risks", [])
    lines = [
        meta.get("title", "untitled"),
        "  Satisfied     : " + props.get("satisfied-count", "?"),
        "  Not-satisfied : " + props.get("not-satisfied-count", "?"),
        "  Not-evaluated : " + props.get("not-evaluated-count", "?"),
        "  Total rules   : " + props.get("total-ksi-rules", "?"),
        "  Findings      : " + str(len(findings)),
        "  Open risks    : " + str(sum(1 for r in risks if r.get("status") == "open")),
        "  Slots bound   : " + props.get("slots-bound", "?"),
    ]
    return "\n".join(lines)


def export_ksi_ar(
    output_path: str | Path,
    system_name: str = "UIAO Federal AAN Assessment System",
    ap_href: str = "",
    slots_dir: Path | None = None,
    rules_dir: Path | None = None,
) -> str:
    """Build and write the KSI OSCAL AR JSON to *output_path*. Returns the path."""
    ar_doc = build_ksi_ar(
        system_name=system_name,
        ap_href=ap_href,
        slots_dir=slots_dir,
        rules_dir=rules_dir,
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ar_doc, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out)
