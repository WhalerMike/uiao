"""UIAO Compliance Query Language (CQL) engine — UIAO_108."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class CQLQuery:
    query_type: str
    filters: list
    for_control: Optional[str] = None
    since: Optional[str] = None
    order_by: Optional[str] = None
    order_dir: str = "ASC"
    raw: str = ""


class CQLParseError(ValueError):
    pass


class CQLExecutionError(RuntimeError):
    pass


_SHOW_RE = re.compile(
    r"SHOW\s+(CONTROLS|EVIDENCE|DRIFT|POAM)"
    r"(?:\s+FOR\s+CONTROL\s+'([^']+)')?"
    r"(?:\s+WHERE\s+(.+?))?"
    r"(?:\s+SINCE\s+'([^']+)')?"
    r"(?:\s+ORDER\s+BY\s+(\w+)(?:\s+(ASC|DESC))?)?$",
    re.IGNORECASE,
)
_FILTER_RE = re.compile(r"(\w+)\s*(=|!=|>=|<=|>|<|LIKE)\s*'([^']*)'", re.IGNORECASE)
_AND_SPLIT = re.compile(r"\s+AND\s+", re.IGNORECASE)

_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4, "p4": 1, "p3": 2, "p2": 3, "p1": 4}


def parse(cql: str) -> CQLQuery:
    cql = cql.strip().rstrip(";")
    m = _SHOW_RE.match(cql)
    if not m:
        raise CQLParseError(f"Cannot parse CQL: {cql!r}")
    query_type = m.group(1).upper()
    for_control = m.group(2)
    where_clause = m.group(3)
    since = m.group(4)
    order_by = m.group(5)
    order_dir = (m.group(6) or "ASC").upper()
    filters: list = []
    if where_clause:
        for clause in _AND_SPLIT.split(where_clause):
            clause = clause.strip()
            fm = _FILTER_RE.match(clause)
            if fm:
                filters.append((fm.group(1).lower(), fm.group(2), fm.group(3)))
            else:
                raise CQLParseError(f"Cannot parse filter: {clause!r}")
    return CQLQuery(query_type=query_type, filters=filters, for_control=for_control,
                    since=since, order_by=order_by.lower() if order_by else None,
                    order_dir=order_dir, raw=cql)


def _compare(actual: Any, op: str, expected: str) -> bool:
    if actual is None:
        return False
    a, e = str(actual).lower(), expected.lower()
    if op == "=": return a == e
    if op == "!=": return a != e
    if op == "LIKE": return e.replace("%", "") in a
    ar = _SEVERITY_RANK.get(a, 0); er = _SEVERITY_RANK.get(e, 0)
    if ar and er:
        if op == ">=": return ar >= er
        if op == "<=": return ar <= er
        if op == ">": return ar > er
        if op == "<": return ar < er
    if op == ">=": return a >= e
    if op == "<=": return a <= e
    if op == ">": return a > e
    if op == "<": return a < e
    return False


def _matches(record: dict, filters: list) -> bool:
    for f, op, val in filters:
        actual = record.get(f) or record.get(f.replace("_", "-"))
        if not _compare(actual, op, val):
            return False
    return True


def _apply_since(records: list, since: str, ts_field: str = "generated_at") -> list:
    try:
        cutoff = datetime.fromisoformat(since.replace("Z", "+00:00")); cutoff = cutoff.replace(tzinfo=timezone.utc) if cutoff.tzinfo is None else cutoff
        result = []
        for r in records:
            ts = r.get(ts_field, "")
            try:
                if not ts or datetime.fromisoformat(ts.replace("Z", "+00:00")) >= cutoff:
                    result.append(r)
            except ValueError:
                result.append(r)
        return result
    except ValueError:
        return records


def _sort(records: list, order_by: str, order_dir: str) -> list:
    def key(r):
        v = r.get(order_by, "")
        rank = _SEVERITY_RANK.get(str(v).lower(), 0)
        return rank if rank else str(v).lower()
    return sorted(records, key=key, reverse=(order_dir == "DESC"))


@dataclass
class CQLResult:
    query_type: str
    records: list
    total: int
    cql: str
    executed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {"query_type": self.query_type, "total": self.total,
                "records": self.records, "cql": self.cql, "executed_at": self.executed_at}


class CQLEngine:
    def __init__(self, controls=None, evidence=None, drift=None, poam=None):
        self._controls = controls or []
        self._evidence = evidence or []
        self._drift = drift or []
        self._poam = poam or []

    def execute(self, cql: str) -> CQLResult:
        q = parse(cql)
        if q.query_type == "CONTROLS":
            records = [r for r in self._controls if _matches(r, q.filters)]
            if q.since: records = _apply_since(records, q.since, "last_assessed")
        elif q.query_type == "EVIDENCE":
            records = self._evidence
            if q.for_control:
                records = [r for r in records if r.get("control_id","").upper() == q.for_control.upper()]
            records = [r for r in records if _matches(r, q.filters)]
            if q.since: records = _apply_since(records, q.since, "generated_at")
        elif q.query_type == "DRIFT":
            records = [r for r in self._drift if _matches(r, q.filters)]
            if q.since: records = _apply_since(records, q.since)
        elif q.query_type == "POAM":
            records = [r for r in self._poam if _matches(r, q.filters)]
            if q.since: records = _apply_since(records, q.since, "detected_at")
        else:
            raise CQLExecutionError(f"Unknown query type: {q.query_type}")
        if q.order_by:
            records = _sort(records, q.order_by, q.order_dir)
        return CQLResult(query_type=q.query_type, records=records, total=len(records), cql=cql)
