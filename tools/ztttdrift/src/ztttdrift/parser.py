"""Load ``ztttdrift-input/1.0`` payloads and exception registers into the model.

Unlike ScubaGear (whose JSON export is a published, observable artifact),
there is no verified sample of Microsoft ZTTT's export format available here —
so ZTTTdrift deliberately does **not** guess at vendor field names. Instead it
defines its own small, versioned input contract, ``ztttdrift-input/1.0``, and
validates it strictly: unknown schema versions, unknown stages, and unknown
pillars are rejected rather than coerced. A thin converter maps a real
assessment export (ZTTT, CISA ZTMM self-assessment worksheet, ...) onto this
contract; writing one is out of scope pending a verified sample.

Everything here is stdlib-only; YAML exception registers are supported when
``PyYAML`` happens to be installed, but JSON always works.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .models import MaturityItem, MaturityRun, RiskAcceptance, Stage, normalize_pillar

#: The one input schema this version of ZTTTdrift accepts.
SCHEMA = "ztttdrift-input/1.0"


class ParseError(ValueError):
    """Raised when input cannot be parsed into the ZTTTdrift model."""


def _item_from_row(row: dict) -> MaturityItem:
    item_id = str(row.get("item_id") or "").strip()
    if not item_id:
        raise ParseError(f"item is missing an 'item_id': {row!r}")
    try:
        pillar = normalize_pillar(str(row.get("pillar") or ""))
        stage = Stage.parse(str(row.get("stage") or ""))
        raw_target = row.get("target_stage")
        target = Stage.parse(str(raw_target)) if raw_target is not None else None
    except ValueError as exc:
        raise ParseError(f"item '{item_id}': {exc}") from exc
    return MaturityItem(
        item_id=item_id,
        pillar=pillar,
        stage=stage,
        title=str(row.get("title") or ""),
        target_stage=target,
    )


def parse_run(payload: dict) -> MaturityRun:
    """Parse one ``ztttdrift-input/1.0`` payload (already-decoded JSON)."""
    if not isinstance(payload, dict):
        raise ParseError("ztttdrift input must be a JSON object")
    schema = payload.get("schema")
    if schema != SCHEMA:
        raise ParseError(f"unsupported input schema {schema!r} (this version accepts only {SCHEMA!r})")
    try:
        assessed_at = date.fromisoformat(str(payload.get("assessed_at")))
    except ValueError as exc:
        raise ParseError(f"'assessed_at' must be YYYY-MM-DD, got {payload.get('assessed_at')!r}") from exc
    rows = payload.get("items")
    if not isinstance(rows, list):
        raise ParseError("'items' must be a list of assessment items")

    items: list[MaturityItem] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ParseError(f"each item must be an object, got {type(row).__name__}")
        item = _item_from_row(row)
        if item.item_id in seen:
            raise ParseError(f"duplicate item_id '{item.item_id}' in run")
        seen.add(item.item_id)
        items.append(item)

    return MaturityRun(
        assessed_at=assessed_at,
        source=str(payload.get("source") or ""),
        items=tuple(items),
    )


def load_run(path: str | Path) -> MaturityRun:
    """Load a ``ztttdrift-input/1.0`` file (JSON) from disk."""
    p = Path(path)
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ParseError(f"assessment file not found: {p}") from exc
    except json.JSONDecodeError as exc:
        raise ParseError(f"{p} is not valid JSON: {exc}") from exc
    return parse_run(payload)


def _acceptance_from_row(row: dict) -> RiskAcceptance:
    try:
        item_id = str(row["item_id"]).strip()
        return RiskAcceptance(
            item_id=item_id,
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
                f"{path} is YAML but PyYAML is not installed; install `ztttdrift[yaml]` or use a .json register"
            ) from exc
        return yaml.safe_load(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"{path} is not valid JSON: {exc}") from exc


def load_exceptions(path: str | Path) -> list[RiskAcceptance]:
    """Load a risk-acceptance register (JSON or, if PyYAML present, YAML).

    Accepts either a bare list of acceptances or an object with an
    ``acceptances`` / ``exceptions`` key. Raises on duplicate item ids so a
    register can never silently carry two conflicting acceptances.
    """
    p = Path(path)
    try:
        raw = _decode_register_text(p.read_text(encoding="utf-8"), p)
    except FileNotFoundError as exc:
        raise ParseError(f"exception register not found: {p}") from exc
    if isinstance(raw, dict):
        raw = raw.get("acceptances", raw.get("exceptions", []))
    if not isinstance(raw, list):
        raise ParseError(f"{p} must contain a list of acceptances")

    acceptances: list[RiskAcceptance] = []
    seen: set[str] = set()
    for row in raw:
        if not isinstance(row, dict):
            raise ParseError(f"each acceptance must be an object, got {type(row).__name__}")
        acc = _acceptance_from_row(row)
        if acc.item_id in seen:
            raise ParseError(f"duplicate risk-acceptance for item '{acc.item_id}'")
        seen.add(acc.item_id)
        acceptances.append(acc)
    return acceptances
