"""Load ScubaGear output and exception registers into the ScubaDrift model.

ScubaGear's ``ScubaResults.json`` has shifted field names across versions and
nests per-product result arrays. The parser is deliberately tolerant: it
accepts either the flat ``{metadata, results:[...]}`` shape or the full
``{MetaData, Results:{PRODUCT:[...]}}`` shape, and it resolves common field
aliases (``PolicyId`` / ``Control ID``, ``PolicyDescription`` / ``Requirement``).
Everything here is stdlib-only; YAML exception registers are supported when
``PyYAML`` happens to be installed, but JSON always works.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .models import PolicyResult, Result, RiskAcceptance, ScubaRun


class ParseError(ValueError):
    """Raised when input cannot be parsed into the ScubaDrift model."""


def _first(d: dict, *keys: str, default: Any = "") -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _policy_from_row(row: dict) -> PolicyResult:
    policy_id = str(_first(row, "PolicyId", "PolicyID", "Control ID", "ControlID", "policy_id")).strip()
    if not policy_id:
        raise ParseError(f"result row is missing a policy id: {row!r}")
    return PolicyResult(
        policy_id=policy_id,
        result=Result.parse(str(_first(row, "Result", "result"))),
        criticality=str(_first(row, "Criticality", "criticality")),
        description=str(_first(row, "PolicyDescription", "Requirement", "Description", "description")),
        details=str(_first(row, "Details", "ReportDetails", "details")),
    )


def _extract_rows(payload: dict) -> list[dict]:
    results = _first(payload, "results", "Results", default=None)
    if results is None:
        raise ParseError("payload has no 'results'/'Results' key")
    if isinstance(results, list):
        return list(results)
    if isinstance(results, dict):
        # Full ScubaResults.json shape: {PRODUCT: [rows...], ...}
        rows: list[dict] = []
        for product_rows in results.values():
            if isinstance(product_rows, list):
                rows.extend(product_rows)
        return rows
    raise ParseError(f"'results' must be a list or a product->list mapping, got {type(results).__name__}")


def parse_run(payload: dict) -> ScubaRun:
    """Parse one ScubaGear result payload (already-decoded JSON) into a ScubaRun."""
    if not isinstance(payload, dict):
        raise ParseError("ScubaGear payload must be a JSON object")
    meta = _first(payload, "metadata", "MetaData", "Metadata", default={})
    if not isinstance(meta, dict):
        meta = {}
    rows = _extract_rows(payload)
    results = tuple(_policy_from_row(r) for r in rows if isinstance(r, dict))
    return ScubaRun(
        product=str(_first(meta, "ProductName", "Product", default="")),
        tenant_id=str(_first(meta, "TenantId", "Tenant", default="")),
        timestamp=str(_first(meta, "Timestamp", "TimeStamp", default="")),
        scubagear_version=str(_first(meta, "ScubaGearVersion", "ToolVersion", default="")),
        baseline_version=str(_first(meta, "BaselineVersion", default="")),
        results=results,
    )


def load_run(path: str | Path) -> ScubaRun:
    """Load a ScubaGear result file (JSON) from disk."""
    p = Path(path)
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ParseError(f"ScubaGear results file not found: {p}") from exc
    except json.JSONDecodeError as exc:
        raise ParseError(f"{p} is not valid JSON: {exc}") from exc
    return parse_run(payload)


def _acceptance_from_row(row: dict) -> RiskAcceptance:
    try:
        policy_id = str(row["policy_id"]).strip()
        return RiskAcceptance(
            policy_id=policy_id,
            justification=str(row.get("justification", "")),
            approved_by=str(row.get("approved_by", "")),
            approved_date=date.fromisoformat(str(row["approved_date"])),
            expiry_date=date.fromisoformat(str(row["expiry_date"])),
            ticket=str(row.get("ticket", "")),
        )
    except KeyError as exc:
        raise ParseError(f"risk-acceptance is missing required field {exc}: {row!r}") from exc
    except ValueError as exc:
        raise ParseError(f"risk-acceptance has a malformed date: {exc} in {row!r}") from exc


def _decode_register_text(text: str, path: Path) -> Any:
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise ParseError(
                f"{path} is YAML but PyYAML is not installed; install `scubadrift[yaml]` or use a .json register"
            ) from exc
        return yaml.safe_load(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"{path} is not valid JSON: {exc}") from exc


def load_exceptions(path: str | Path) -> list[RiskAcceptance]:
    """Load a risk-acceptance register (JSON or, if PyYAML present, YAML).

    Accepts either a bare list of acceptances or an object with an
    ``acceptances`` / ``exceptions`` key. Raises on duplicate policy ids so a
    register can never silently carry two conflicting acceptances.
    """
    p = Path(path)
    try:
        raw = _decode_register_text(p.read_text(encoding="utf-8"), p)
    except FileNotFoundError as exc:
        raise ParseError(f"exception register not found: {p}") from exc
    if isinstance(raw, dict):
        raw = _first(raw, "acceptances", "exceptions", default=[])
    if not isinstance(raw, list):
        raise ParseError(f"{p} must contain a list of acceptances")

    acceptances: list[RiskAcceptance] = []
    seen: set[str] = set()
    for row in raw:
        if not isinstance(row, dict):
            raise ParseError(f"each acceptance must be an object, got {type(row).__name__}")
        acc = _acceptance_from_row(row)
        if acc.policy_id in seen:
            raise ParseError(f"duplicate risk-acceptance for policy '{acc.policy_id}'")
        seen.add(acc.policy_id)
        acceptances.append(acc)
    return acceptances
