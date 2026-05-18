---
title: "Phase 3 — OSCAL Component Definition runtime-findings mode (PR-3b)"
status: DRAFT
date: 2026-05-15
---

# Phase 3 — `oscal.py` runtime-findings mode

This file sketches the diff applied to
[`src/uiao/generators/oscal.py`](../../../src/uiao/generators/oscal.py)
when **PR-3b** lands. (PR-3a lands the canonical DriftFinding + router
with no OSCAL change. PR-3b is the assessor-facing surface.)

## What changes

Three additions, **zero removals or signature changes**:

1. New `include_runtime_findings: bool = False` parameter on
   `build_component_definition()`. Default is False — today's bundles
   stay byte-identical.
2. When True, the function reads runtime findings from the event log
   over the same time window used for evidence assembly (Phase 1d
   path), projects each into an OSCAL Observation under
   `_UIAO_RUNTIME_NS`, and attaches them to the right
   implemented-requirement via the §6 compliance mapping.
3. CLI surface (`uiao oscal generate`) gains
   `--include-runtime-findings` boolean flag.

## What does NOT change

- The existing component-definition output (when the flag is off).
- The Evidence Graph integration (Phase 3 doesn't touch
  `_UIAO_GRAPH_NS`).
- The OSCAL schema version or any field shapes.
- The bundle hash determinism guarantee from ADR-006 — when the flag
  is off, the bundle hash matches today exactly.

## Diff sketch

```python
# src/uiao/generators/oscal.py — after Phase 3 PR-3b

# Existing constant — unchanged:
_UIAO_GRAPH_NS = "https://uiao.gov/ns/oscal/graph"

# NEW Phase 3 PR-3b — runtime findings namespace:
_UIAO_RUNTIME_NS = "https://uiao.gov/ns/oscal/runtime"

# §6 compliance mapping from 16_DriftDetectionStandard.qmd — drives
# which implemented-requirement a runtime finding attaches to.
_DRIFT_CLASS_TO_CONTROLS: dict[str, list[str]] = {
    "DRIFT-PROVENANCE": ["si-7", "au-9"],   # software integrity + audit info protection
    "DRIFT-AUTHZ":      ["ac-4", "ac-22"],  # info flow + consent
    "DRIFT-IDENTITY":   ["ia-2", "ia-8"],   # identification / non-org-user identification
    "DRIFT-SCHEMA":     ["cm-3"],           # config change control
    "DRIFT-SEMANTIC":   ["ca-7"],           # continuous monitoring
    "DRIFT-BOUNDARY":   ["sc-7"],           # boundary protection (ADR-033)
}


def build_component_definition(
    context: dict[str, Any],
    graph: EvidenceGraph | None = None,
    *,
    include_runtime_findings: bool = False,         # NEW Phase 3 PR-3b
    runtime_findings_window_hours: int = 24 * 30,   # NEW; default 30 days
) -> dict[str, Any]:
    """... (existing docstring) ...

    When ``include_runtime_findings`` is True, runtime drift findings
    from the JSONL provenance event log (per Phase 1d / ADR-071) over
    the past ``runtime_findings_window_hours`` are projected into OSCAL
    Observations under ``_UIAO_RUNTIME_NS`` and attached to the right
    implemented-requirement via the §6 compliance mapping. Default is
    False — bundles are byte-identical to pre-Phase-3 output when the
    flag is off.
    """
    # ... existing assembly logic unchanged ...

    component_def = _build_component_definition_base(context, graph)

    if include_runtime_findings:
        observations = _build_runtime_observations(
            window_hours=runtime_findings_window_hours,
        )
        _attach_runtime_observations(component_def, observations)

    return component_def


# --- NEW: project findings into OSCAL Observations ---

def _build_runtime_observations(*, window_hours: int) -> list[dict[str, Any]]:
    """Read the JSONL event log; project each runtime finding into an OSCAL Observation.

    Only `subkind="runtime"` findings are included — hygiene findings
    are CI-time and belong in the build artifacts, not the ATO package.
    """
    from uiao.telemetry.provenance import read_event_log_window
    findings = read_event_log_window(window_hours=window_hours, subkind="runtime")
    return [_finding_to_observation(f) for f in findings]


def _finding_to_observation(finding: "DriftFinding") -> dict[str, Any]:
    """One DriftFinding → one OSCAL Observation.

    Carries every §4 remediation contract field as a property so an
    assessor reading the bundle sees the full lifecycle (detected,
    routed, remediated, escalated) rather than just the detection.
    """
    return {
        "uuid": str(uuid.uuid4()),
        "title": f"{finding.drift_class} ({finding.severity}) — {finding.path}",
        "description": finding.detail,
        "methods": ["EXAMINE"],
        "collected": finding.detection_timestamp,
        "props": [
            {"ns": _UIAO_RUNTIME_NS, "name": "drift-class", "value": finding.drift_class},
            {"ns": _UIAO_RUNTIME_NS, "name": "severity", "value": finding.severity},
            {"ns": _UIAO_RUNTIME_NS, "name": "subkind", "value": finding.subkind or ""},
            {"ns": _UIAO_RUNTIME_NS, "name": "detected-by", "value": finding.detected_by},
            {"ns": _UIAO_RUNTIME_NS, "name": "remediation-action", "value": finding.remediation_action},
            {"ns": _UIAO_RUNTIME_NS, "name": "auto-remediated", "value": str(finding.auto_remediated).lower()},
            {"ns": _UIAO_RUNTIME_NS, "name": "remediation-timestamp", "value": finding.remediation_timestamp or ""},
            {"ns": _UIAO_RUNTIME_NS, "name": "remediation-evidence", "value": finding.remediation_evidence or ""},
            {"ns": _UIAO_RUNTIME_NS, "name": "escalation-path", "value": finding.escalation_path or ""},
        ],
        # Inline detail goes here so an assessor doesn't have to chase
        # back-matter resources for the basic story.
        "subjects": [
            {"type": "component", "subject-uuid": _resolve_component_uuid(finding.path)},
        ],
    }


# --- NEW: attach observations to the right implemented-requirement ---

def _attach_runtime_observations(
    component_def: dict[str, Any],
    observations: list[dict[str, Any]],
) -> None:
    """Attach each Observation to every implemented-requirement whose
    control-id is in the §6 compliance mapping for the finding's drift_class.

    A finding may attach to multiple controls (e.g., DRIFT-PROVENANCE
    maps to both SI-7 and AU-9). Each Observation is referenced by
    UUID on every relevant implemented-requirement; the Observation
    itself appears once in the assessment-results / observations array.
    """
    component_def.setdefault("observations", []).extend(observations)

    obs_by_control: dict[str, list[str]] = {}
    for obs in observations:
        drift_class = next(
            (p["value"] for p in obs["props"]
             if p["name"] == "drift-class" and p["ns"] == _UIAO_RUNTIME_NS),
            "",
        )
        for control_id in _DRIFT_CLASS_TO_CONTROLS.get(drift_class, []):
            obs_by_control.setdefault(control_id, []).append(obs["uuid"])

    for component in component_def.get("components", []):
        for cic in component.get("control-implementations", []):
            for ir in cic.get("implemented-requirements", []):
                obs_uuids = obs_by_control.get(ir.get("control-id", ""), [])
                if not obs_uuids:
                    continue
                ir.setdefault("links", []).extend([
                    {"href": f"#{uid}", "rel": "observation"} for uid in obs_uuids
                ])
```

## CLI surface

```bash
# Today (unchanged):
uiao oscal generate                            # snapshot, no runtime findings
uiao oscal generate --source event-log         # event-log assembly, no runtime findings

# After Phase 3 PR-3b:
uiao oscal generate --source event-log \
    --include-runtime-findings                  # NEW — runtime findings as Observations
uiao oscal generate --source event-log \
    --include-runtime-findings \
    --runtime-findings-window 720h              # NEW — custom 30-day window override
```

## Tests

| Test | What it verifies |
|---|---|
| `test_oscal_default_excludes_runtime_findings` | Default invocation produces byte-identical bundle to pre-Phase-3 output |
| `test_oscal_include_runtime_findings_adds_observations` | Flag adds Observations under `_UIAO_RUNTIME_NS` |
| `test_oscal_observation_attaches_to_correct_control` | DRIFT-PROVENANCE finding attaches to SI-7 + AU-9 implemented-requirements |
| `test_oscal_window_filters_old_findings` | Findings outside the window do not appear |
| `test_oscal_only_runtime_subkind_included` | Hygiene findings from the walker do NOT appear (they're CI-time only) |
| `test_oscal_remediation_contract_in_props` | Every Observation carries the full §4 contract as props |

## Operational note for assessors

A bundle generated with `--include-runtime-findings` is a strictly
**richer** ATO package than one without — the without-version still
satisfies the existing OSCAL Component Definition contract; the
with-version adds runtime-drift Observations that supplement (not
replace) the snapshot evidence. Agencies can opt in or out per ATO
package; the flag does not bake into canon.

This matters for sovereign-boundary deployments: a GCC-Moderate or
GCC-High agency may emit runtime findings into the JSONL log (private
to the tenant) but choose NOT to include them in the ATO package
shared with a 3PAO until the assessor is briefed on what the new
observations mean. The flag gives them that control without re-running
the assembly pipeline with different inputs.
