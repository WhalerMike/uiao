"""ScubaDrift verdict artifact — evidence source for ScuBA-sourced KSI rules.

KSI-001..010 are ScuBA-sourced (``Source.SCuBA_Field``): the authoritative
evaluator is CISA ScubaGear run against the live M365 tenant, with ScubaDrift
(tools/scubadrift) supplying the failure *disposition* — is a failing policy
new drift, a lapsed risk-acceptance, or a governed (in-date, approved,
ticketed) exception?

Before this module existed, the OSCAL AR asserted those ten rules
unconditionally "satisfied" with no artifact behind them. Now the AR consumes
a **verdicts artifact** (``scubadrift-verdicts.json``) built by merging two
machine outputs:

1. a ScubaGear results file (all policies, pass/fail), and
2. ``scubadrift triage --json`` over that same run (dispositions for the
   failures against the risk-acceptance register).

``build_scuba_verdicts()`` produces the artifact; ``evaluate_scuba_rule()``
turns it into an OSCAL finding state:

- satisfied     : every mapped policy passes or is a governed exception
- not-satisfied : any mapped policy is actionable (new drift or lapsed
                  acceptance) — flows into AR risks and the POA&M
- other         : artifact missing, rule unmapped, or a mapped policy was
                  not assessed in the run

The artifact carries a mandatory ``provenance`` block (``tenant`` vs
``sample-fixture``) which the AR surfaces verbatim, so a reader can always
tell whether a verdict is backed by real tenant data or a demonstration
fixture.

Companion files:
  tools/scubadrift/                                    — disposition engine
  output/artifacts/ksi-bundle/scubadrift-verdicts.json — committed artifact
  src/uiao/oscal/ksi_ar.py                             — consumer
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_ID = "uiao-scuba-verdicts/1.0"

#: Default on-disk location of the committed verdicts artifact, relative to
#: the repo root (same directory as the rest of the KSI OSCAL bundle).
DEFAULT_VERDICTS_PATH = Path("output/artifacts/ksi-bundle/scubadrift-verdicts.json")

#: Dispositions (from scubadrift.triage) that demand action — they make the
#: owning KSI not-satisfied. A governed_exception does not: it is a failing
#: policy already covered by an in-date, approved, ticketed risk-acceptance.
ACTIONABLE_DISPOSITIONS = frozenset({"actionable_new_drift", "lapsed_acceptance"})

# ---------------------------------------------------------------------------
# KSI rule -> ScubaGear policy IDs
# ---------------------------------------------------------------------------

#: Which SCuBA Secure Configuration Baseline policies back each ScuBA-sourced
#: KSI rule. Policy IDs follow the CISA baselines as of SCuBA v1.5 and are
#: illustrative in the same sense as SCUBA_TO_KSI_MAP in
#: ``scubagear_adapter.py`` — confirm against the baseline version your
#: ScubaGear deployment actually assesses before relying on a verdict.
KSI_SCUBA_POLICIES: dict[str, list[str]] = {
    # MFA enforcement: phishing-resistant MFA, with the baseline's sanctioned
    # alternative-MFA fallback policy.
    "KSI-001": ["MS.AAD.3.1v1", "MS.AAD.3.2v1"],
    # Legacy authentication blocked.
    "KSI-002": ["MS.AAD.1.1v1"],
    # Global Administrator count within the 2-8 band.
    "KSI-003": ["MS.AAD.7.1v1"],
    # Automatic forwarding to external domains disabled.
    "KSI-004": ["MS.EXO.1.1v2"],
    # Mailbox auditing enabled.
    "KSI-005": ["MS.EXO.13.1v1"],
    # SharePoint/OneDrive external sharing restricted.
    "KSI-006": ["MS.SHAREPOINT.1.1v1", "MS.SHAREPOINT.1.2v1"],
    # Safe Links and Safe Attachments both ride the Defender for Office 365
    # preset-security-policy baseline entry.
    "KSI-007": ["MS.DEFENDER.1.3v1"],
    "KSI-008": ["MS.DEFENDER.1.3v1"],
    # Conditional Access enforcement: the risk-based CA policies the AAD
    # baseline mandates.
    "KSI-009": ["MS.AAD.2.1v1", "MS.AAD.2.3v1"],
    # Custom DLP policy for sensitive information types.
    "KSI-010": ["MS.DEFENDER.4.1v2"],
}


# ---------------------------------------------------------------------------
# ScubaGear results parsing (light — full alias handling lives in scubadrift)
# ---------------------------------------------------------------------------


def _iter_scuba_policy_rows(results_doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Yield raw policy-result rows from either ScubaGear results shape.

    Accepts the flat ``{metadata, results: [...]}`` shape and the full
    ``ScubaResults.json`` shape ``{MetaData, Results: {PRODUCT: [...]}}``.
    """
    flat = results_doc.get("results")
    if isinstance(flat, list):
        return [r for r in flat if isinstance(r, dict)]
    nested = results_doc.get("Results")
    if isinstance(nested, dict):
        rows: list[dict[str, Any]] = []
        for product_rows in nested.values():
            if isinstance(product_rows, list):
                rows.extend(r for r in product_rows if isinstance(r, dict))
        return rows
    return []


def _policy_id(row: dict[str, Any]) -> str:
    return str(row.get("policy_id") or row.get("PolicyId") or row.get("Control ID") or "").strip()


def _result(row: dict[str, Any]) -> str:
    return str(row.get("result") or row.get("Result") or "").strip().lower()


# ---------------------------------------------------------------------------
# Artifact build / load
# ---------------------------------------------------------------------------


def build_scuba_verdicts(
    results_doc: dict[str, Any],
    triage_doc: dict[str, Any],
    provenance_source: str = "tenant",
    provenance_note: str = "",
    now: str | None = None,
) -> dict[str, Any]:
    """Merge a ScubaGear results doc with a ScubaDrift triage report.

    Args:
        results_doc:       Parsed ScubaGear results JSON (flat or full shape).
        triage_doc:        Parsed output of ``scubadrift triage --json`` for
                           the same run.
        provenance_source: ``"tenant"`` for a real ScubaGear run, or
                           ``"sample-fixture"`` for demonstration data. The
                           OSCAL AR surfaces this verbatim.
        provenance_note:   Free-text provenance detail (input filenames, run
                           context).
        now:               Override the generation timestamp (ISO 8601).

    Returns:
        The verdicts artifact dict (``schema`` = ``uiao-scuba-verdicts/1.0``):
        one entry per assessed policy, failures annotated with their
        ScubaDrift disposition.
    """
    dispositions: dict[str, dict[str, Any]] = {}
    for entry in triage_doc.get("triaged", []) or []:
        pid = str(entry.get("policy_id", "")).strip()
        if pid:
            dispositions[pid] = entry

    policies: dict[str, dict[str, Any]] = {}
    for row in _iter_scuba_policy_rows(results_doc):
        pid = _policy_id(row)
        if not pid:
            continue
        result = _result(row)
        record: dict[str, Any] = {"result": "pass" if result == "pass" else "fail"}
        if record["result"] == "fail":
            triaged = dispositions.get(pid)
            if triaged is None:
                # Failing but absent from the triage report — treat as
                # ungoverned rather than silently passing it.
                record["disposition"] = "actionable_new_drift"
                record["reason"] = "failing policy absent from triage report"
            else:
                record["disposition"] = str(triaged.get("disposition", ""))
                record["reason"] = str(triaged.get("reason", ""))
                acceptance = triaged.get("acceptance")
                if isinstance(acceptance, dict):
                    record["ticket"] = str(acceptance.get("ticket", ""))
                    record["expiry_date"] = str(acceptance.get("expiry_date", ""))
        policies[pid] = record

    return {
        "schema": SCHEMA_ID,
        "generated_at": now or datetime.now(timezone.utc).isoformat(),
        "as_of": str(triage_doc.get("as_of", "")),
        "provenance": {
            "source": provenance_source,
            "note": provenance_note,
        },
        "policies": policies,
    }


def load_scuba_verdicts(path: Path | None = None) -> dict[str, Any] | None:
    """Load a verdicts artifact from *path*; None when absent or unreadable.

    A missing artifact is a legitimate state (no ScubaGear run has been fed
    in yet) — the caller downgrades ScuBA-sourced verdicts to "other" rather
    than failing.
    """
    p = path or DEFAULT_VERDICTS_PATH
    if not p.is_file():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("policies"), dict):
        return None
    return doc


def export_scuba_verdicts(
    output_path: str | Path,
    results_path: str | Path,
    triage_path: str | Path,
    provenance_source: str = "tenant",
    provenance_note: str = "",
) -> str:
    """Build the verdicts artifact from two input files and write it.

    Returns the written path. Raises on unreadable inputs — unlike
    :func:`load_scuba_verdicts`, generation must never silently produce an
    empty artifact.
    """
    results_doc = json.loads(Path(results_path).read_text(encoding="utf-8"))
    triage_doc = json.loads(Path(triage_path).read_text(encoding="utf-8"))
    note = provenance_note or f"results: {Path(results_path).name}; triage: {Path(triage_path).name}"
    doc = build_scuba_verdicts(
        results_doc,
        triage_doc,
        provenance_source=provenance_source,
        provenance_note=note,
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out)


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------


def evaluate_scuba_rule(
    rule_id: str,
    verdicts: dict[str, Any] | None,
) -> tuple[str, str]:
    """Return ``(state, detail)`` for one ScuBA-sourced KSI rule.

    ``state`` is an OSCAL finding target status (satisfied / not-satisfied /
    other); ``detail`` is the per-policy narrative for the AR observation,
    always ending with the artifact's provenance so a reader can tell tenant
    evidence from a demonstration fixture.
    """
    policy_ids = KSI_SCUBA_POLICIES.get(rule_id)
    if not policy_ids:
        return (
            "other",
            f"Rule {rule_id} is ScuBA-sourced but has no SCuBA policy mapping "
            "in KSI_SCUBA_POLICIES; cannot evaluate against ScubaDrift verdicts.",
        )

    if verdicts is None:
        return (
            "other",
            f"No ScubaDrift verdicts artifact found for rule {rule_id}. "
            "Generate one from a ScubaGear run with 'scubadrift triage --json' "
            "and 'uiao oscal scuba-verdicts'.",
        )

    policies: dict[str, Any] = verdicts.get("policies", {})
    provenance = verdicts.get("provenance", {}) or {}
    prov_line = (
        f" Verdict source: ScubaDrift verdicts artifact, as of {verdicts.get('as_of', '?')}, "
        f"input provenance: {provenance.get('source', 'unspecified')}."
    )

    missing = [pid for pid in policy_ids if pid not in policies]
    if missing:
        return (
            "other",
            f"SCuBA policies {missing} backing rule {rule_id} were not assessed "
            "in the supplied ScubaGear run; rule not evaluated." + prov_line,
        )

    actionable: list[str] = []
    governed: list[str] = []
    for pid in policy_ids:
        record = policies[pid]
        if record.get("result") == "pass":
            continue
        disposition = str(record.get("disposition", ""))
        reason = str(record.get("reason", ""))
        if disposition in ACTIONABLE_DISPOSITIONS:
            actionable.append(f"{pid} ({disposition}: {reason})")
        else:
            governed.append(f"{pid} ({reason})")

    if actionable:
        return (
            "not-satisfied",
            f"SCuBA policies backing rule {rule_id} require action: {'; '.join(actionable)}." + prov_line,
        )

    detail = f"All SCuBA policies backing rule {rule_id} pass ({', '.join(policy_ids)})."
    if governed:
        detail = (
            f"SCuBA policies backing rule {rule_id} pass or are governed "
            f"exceptions — failing but covered by an in-date, approved "
            f"risk-acceptance: {'; '.join(governed)}."
        )
    return ("satisfied", detail + prov_line)
