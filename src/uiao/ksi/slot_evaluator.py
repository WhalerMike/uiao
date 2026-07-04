"""KSI slot-evidence evaluator (ADR-111 evaluation engine — Plane 0.5 → Plane 2).

For each KSI rule with ``Status: active`` and a CR26 control target, evaluates
whether the AAN conformance adapter binding index contains a high-confidence
slot binding for every claimed CR26 control.

Verdict contract
----------------
pass          → every CR26 control claimed by the rule has at least one
                slot binding with ``confidence == "high"``
fail          → slot bindings exist for at least one control but none reach
                high confidence; or some controls have high bindings while
                others have only lower-confidence bindings (any miss → fail)
inconclusive  → no slot binding found for any of the CR26 controls; evidence
                not yet bound to this rule in any slot evidence YAML

This module is the bridge between the AAN slot evidence layer (slot-*.yaml
files, loaded by ``ksi_ar.build_cr26_binding_index()``) and the KSI verdict
layer.  It intentionally does not read YAML directly — the caller supplies the
pre-built binding index so the evaluator stays fast and testable in isolation.

Scaffold rules raise ``ValueError`` on evaluation: evaluability and mapping
confidence are orthogonal per ADR-111, and the error makes the mis-use
explicit at test time.
"""

from __future__ import annotations

from typing import Any

_HIGH = "high"


def evaluate_slot(
    cr26_control: str,
    binding_index: dict[str, list[dict[str, Any]]],
    *,
    require_confidence: str = _HIGH,
) -> str:
    """Return a verdict for one CR26 control against the slot binding index.

    Args:
        cr26_control:       The CR26 control ID (e.g. ``"KSI-CMT-LMC"``).
        binding_index:      Output of ``build_cr26_binding_index()`` — maps
                            control IDs to lists of slot binding dicts, each
                            with a ``"confidence"`` key.
        require_confidence: Minimum confidence for a ``"pass"`` verdict.
                            Only ``"high"`` is currently recognised.

    Returns:
        ``"pass"``, ``"fail"``, or ``"inconclusive"``.
    """
    bindings = binding_index.get(cr26_control, [])
    if not bindings:
        return "inconclusive"
    if any(b.get("confidence") == require_confidence for b in bindings):
        return "pass"
    return "fail"


def evaluate_rule(
    rule_doc: dict[str, Any],
    mapping_row: dict[str, Any],
    binding_index: dict[str, list[dict[str, Any]]],
) -> str:
    """Evaluate one KSI rule against the AAN slot binding index.

    A rule passes only if **every** CR26 control it claims has at least one
    high-confidence slot binding.  A single miss on any control returns
    ``"fail"``; all-inconclusive (no bindings whatsoever) returns
    ``"inconclusive"``.

    Args:
        rule_doc:      Parsed KSI-*.yaml dict (may be empty ``{}`` for rules
                       with no local YAML file; must not have
                       ``Status == "scaffold"`` or ``ValueError`` is raised).
        mapping_row:   One row from ``ksi-mapping.yaml["mappings"]``; must
                       supply ``cr26_controls`` (list of CR26 control IDs).
        binding_index: Output of ``build_cr26_binding_index()``.

    Returns:
        ``"pass"``, ``"fail"``, or ``"inconclusive"``.

    Raises:
        ValueError: If ``rule_doc["Status"] == "scaffold"``.
    """
    if rule_doc.get("Status") == "scaffold":
        rule_id = rule_doc.get("KSI_ID", "?")
        raise ValueError(
            f"Cannot evaluate scaffold rule {rule_id} — "
            "evaluation engine not yet wired for this rule (ADR-111). "
            "Activate the rule (Status: active, concrete Logic) first."
        )

    cr26_ids: list[str] = list(mapping_row.get("cr26_controls") or [])
    if not cr26_ids:
        return "inconclusive"

    slot_verdicts = [evaluate_slot(cid, binding_index) for cid in cr26_ids]

    if all(v == "pass" for v in slot_verdicts):
        return "pass"
    if all(v == "inconclusive" for v in slot_verdicts):
        return "inconclusive"
    return "fail"
