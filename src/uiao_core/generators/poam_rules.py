"""Rule-based POA&M gap detection engine.

Loads rule definitions from data/poam_rules.yaml and evaluates them against
the loaded UIAO context to produce POAMEntry objects.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import yaml

from uiao_core.models.poam import POAMEntry, POAMRule

# ---------------------------------------------------------------------------
# Rule loading
# ---------------------------------------------------------------------------

def load_rules(rules_path: str | Path | None = None) -> list[POAMRule]:
    """Load POA&M rules from a YAML file.

    Args:
        rules_path: Path to ``poam_rules.yaml``.  Defaults to
            ``<project_root>/data/poam_rules.yaml``.

    Returns:
        List of validated :class:`POAMRule` objects.
    """
    if rules_path is None:
        from uiao_core.utils.context import get_settings
        settings = get_settings()
        rules_path = settings.data_dir / "poam_rules.yaml"

    rules_path = Path(rules_path)
    if not rules_path.exists():
        return []

    with rules_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_rules = data.get("rules", [])
    rules: list[POAMRule] = []
    for raw in raw_rules:
        if isinstance(raw, dict):
            rules.append(POAMRule.model_validate(raw))
    return rules


# ---------------------------------------------------------------------------
# Rule evaluation helpers
# ---------------------------------------------------------------------------

def _evaluate_low_maturity(
    rule: POAMRule,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return gap dicts for matrix entries whose maturity matches the rule."""
    gaps: list[dict[str, Any]] = []
    matrix = context.get("unified_compliance_matrix", [])
    if not isinstance(matrix, list):
        return gaps

    for entry in matrix:
        if not isinstance(entry, dict):
            continue
        maturity = entry.get("cisa_maturity", "")
        if maturity == rule.condition_value:
            gaps.append({
                "category": entry.get("category", "Unknown"),
                "maturity": maturity,
                "nist_controls": entry.get("nist_controls", []),
            })
    return gaps


def _evaluate_missing_evidence(
    rule: POAMRule,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return gap dicts for KSI mappings that lack evidence."""
    gaps: list[dict[str, Any]] = []
    fedramp = context.get("fedramp_20x_config", {})
    if not isinstance(fedramp, dict):
        return gaps
    core_mappings = fedramp.get("core_mappings", [])
    if not isinstance(core_mappings, list):
        return gaps

    for m in core_mappings:
        if not isinstance(m, dict):
            continue
        evidence = m.get("evidence_source", "")
        if not evidence or str(evidence).strip() == "":
            gaps.append({
                "concept": m.get("concept", "Unknown"),
                "control": m.get("nist_rev5_control", ""),
            })
    return gaps


def _evaluate_missing_control(
    rule: POAMRule,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return a gap dict if the target control is absent from any mapping."""
    target = rule.condition_value
    if not target:
        return []

    # Collect all controls mentioned across context
    all_controls: set[str] = set()

    matrix = context.get("unified_compliance_matrix", [])
    if isinstance(matrix, list):
        for entry in matrix:
            if isinstance(entry, dict):
                for ctrl in entry.get("nist_controls", []):
                    all_controls.add(str(ctrl))

    fedramp = context.get("fedramp_20x_config", {})
    if isinstance(fedramp, dict):
        for m in fedramp.get("core_mappings", []):
            if isinstance(m, dict):
                ctrl = m.get("nist_rev5_control", "")
                if ctrl:
                    all_controls.add(str(ctrl))

    if target not in all_controls:
        return [{"control": target}]
    return []


# ---------------------------------------------------------------------------
# Main evaluation entry point
# ---------------------------------------------------------------------------

def evaluate_rules(
    context: dict[str, Any],
    rules: list[POAMRule] | None = None,
    rules_path: str | Path | None = None,
) -> list[POAMEntry]:
    """Evaluate all rules against *context* and return :class:`POAMEntry` objects.

    Args:
        context: Merged UIAO context dict (from :func:`load_context`).
        rules: Pre-loaded list of :class:`POAMRule`.  If *None*, rules are
            loaded from *rules_path*.
        rules_path: Path to the rules YAML file.  Used only when *rules* is
            ``None``.

    Returns:
        List of :class:`POAMEntry` objects, one per matched gap per rule.
    """
    if rules is None:
        rules = load_rules(rules_path)

    entries: list[POAMEntry] = []
    counter = 0

    for rule in rules:
        ctype = rule.condition_type

        if ctype == "low_maturity":
            gaps = _evaluate_low_maturity(rule, context)
            for gap in gaps:
                counter += 1
                entries.append(
                    POAMEntry(
                        uuid=str(uuid.uuid4()),
                        finding_id=f"POAM-UIAO-{counter:04d}",
                        title=f"[{rule.id}] Low maturity: {gap['category']}",
                        description=(
                            f"CISA maturity is '{gap['maturity']}' for category "
                            f"'{gap['category']}'. Controls: {gap['nist_controls']}. "
                            f"{rule.description}"
                        ),
                        risk_rating=rule.risk_rating,
                        related_controls=gap["nist_controls"],
                        responsible_party=rule.responsible_party,
                        milestone_description=rule.recommendation,
                        source="rule_engine",
                        source_finding_id=rule.id,
                    )
                )

        elif ctype == "missing_evidence":
            gaps = _evaluate_missing_evidence(rule, context)
            for gap in gaps:
                counter += 1
                controls = [gap["control"]] if gap.get("control") else []
                entries.append(
                    POAMEntry(
                        uuid=str(uuid.uuid4()),
                        finding_id=f"POAM-UIAO-{counter:04d}",
                        title=f"[{rule.id}] Missing evidence: {gap['concept']}",
                        description=(
                            f"No evidence source defined for KSI concept "
                            f"'{gap['concept']}' (control: {gap.get('control', 'N/A')}). "
                            f"{rule.description}"
                        ),
                        risk_rating=rule.risk_rating,
                        related_controls=controls,
                        responsible_party=rule.responsible_party,
                        milestone_description=rule.recommendation,
                        source="rule_engine",
                        source_finding_id=rule.id,
                    )
                )

        elif ctype == "missing_control":
            gaps = _evaluate_missing_control(rule, context)
            for gap in gaps:
                counter += 1
                entries.append(
                    POAMEntry(
                        uuid=str(uuid.uuid4()),
                        finding_id=f"POAM-UIAO-{counter:04d}",
                        title=f"[{rule.id}] Missing control: {gap['control']}",
                        description=(
                            f"Required control '{gap['control']}' is not present in any mapping. "
                            f"{rule.description}"
                        ),
                        risk_rating=rule.risk_rating,
                        related_controls=[gap["control"]],
                        responsible_party=rule.responsible_party,
                        milestone_description=rule.recommendation,
                        source="rule_engine",
                        source_finding_id=rule.id,
                    )
                )

        # Unknown / custom condition types produce no entries by default.

    return entries
