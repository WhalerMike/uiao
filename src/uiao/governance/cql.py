"""Compliance Query Language (CQL) — UIAO_108, §3.2.

CQL is the substrate's read-only query surface over its evidence
sources: the EvidenceGraph (UIAO_113), the EnforcementJournal
(UIAO_111), the Data Lake archive (UIAO_109), and the canon adapter
registries (UIAO_003 / UIAO_131). Sized as a subset of a structured
query language — not full SQL — so the implementation stays small,
deterministic, and dependency-free.

Query shape (YAML / dict):

    source: findings | enforcement | archive | adapters
    select: [field1, field2, ...]      # optional; default = all fields
    where:
      <field>: <scalar>                # equality
      <field>:
        op: in | not_in | contains | gte | lte | ne | exists
        value: ...
    order_by: <field>
    order: asc | desc                  # default asc
    limit: 100

Sources are resolved at evaluation time by an injected
:class:`CQLSourceResolver` — production wires it to live data sources
(scheduler runs, on-disk journal, archive backend, canon registries);
tests inject in-memory lists. This keeps the evaluator pure-function
over its inputs.

Example queries (canonical reference set ships in
``src/uiao/canon/queries/``):

    # Open DRIFT-AUTHZ findings sorted by severity descending
    source: findings
    where:
      drift_class: DRIFT-AUTHZ
      status: Open
    order_by: severity
    order: desc
    limit: 25

    # Enforcement actions with action=block in the last day
    source: enforcement
    where:
      action: block
    order_by: dispatched_at
    order: desc
    limit: 50
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable, Mapping, Optional

import yaml

if TYPE_CHECKING:
    from uiao.governance.feature_flags import FeatureFlagRegistry
    from uiao.governance.tenancy import Tenant, TenantContext

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUERY_DIR = REPO_ROOT / "uiao" / "canon" / "queries"


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


VALID_SOURCES = ("findings", "enforcement", "archive", "adapters")

# Operators classified by stability. v1 operators are always available;
# experimental operators require the UIAO_119 v2 feature flag
# `auditor-api.cql.experimental-ops` to be enabled for the calling
# tenant context. Default canon enables it for `internal` tenants in
# `dev` / `stage` only — agency operators see only the v1 surface so
# canon stays the contract.
V1_OPS = ("eq", "ne", "in", "not_in", "contains", "gte", "lte", "exists")
EXPERIMENTAL_OPS = ("regex",)
EXPERIMENTAL_OPS_FLAG = "auditor-api.cql.experimental-ops"


# A source resolver maps a source name to a list of dict records.
# Each record is treated as a flat dict for filtering / projection.
CQLSourceResolver = Callable[[str], list[dict[str, Any]]]


# ---------------------------------------------------------------------------
# Query data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CQLPredicate:
    """One field-level predicate in a `where:` clause."""

    field: str
    op: str  # eq | ne | in | not_in | contains | gte | lte | exists
    value: Any = None

    def matches(self, record: Mapping[str, Any]) -> bool:
        if self.op == "exists":
            return self.field in record
        actual = record.get(self.field)
        if self.op == "eq":
            return bool(actual == self.value)
        if self.op == "ne":
            return bool(actual != self.value)
        if self.op == "in":
            try:
                return bool(actual in self.value)
            except TypeError:
                return False
        if self.op == "not_in":
            try:
                return bool(actual not in self.value)
            except TypeError:
                return True
        if self.op == "contains":
            if actual is None:
                return False
            try:
                return bool(self.value in actual)  # works for str / list / set
            except TypeError:
                return False
        if self.op == "gte":
            try:
                return bool(actual >= self.value)
            except TypeError:
                return False
        if self.op == "lte":
            try:
                return bool(actual <= self.value)
            except TypeError:
                return False
        if self.op == "regex":
            # Experimental — parse-time gate ensures only callers that
            # passed the auditor-api.cql.experimental-ops flag check
            # can construct a predicate with this op. At evaluation
            # time we don't re-check the flag (that would couple the
            # evaluator to the registry); the parser is the gate.
            if actual is None:
                return False
            try:
                return re.search(self.value, str(actual)) is not None
            except (re.error, TypeError):
                return False
        return False


@dataclass(frozen=True)
class CQLQuery:
    """Parsed CQL query."""

    source: str
    select: tuple[str, ...] = ()
    where: tuple[CQLPredicate, ...] = ()
    order_by: str = ""
    order: str = "asc"
    limit: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "select": list(self.select),
            "where": [{"field": p.field, "op": p.op, "value": p.value} for p in self.where],
            "order_by": self.order_by,
            "order": self.order,
            "limit": self.limit,
        }


@dataclass(frozen=True)
class CQLResult:
    """Outcome of a CQL evaluation."""

    query: CQLQuery
    rows: tuple[dict[str, Any], ...]

    @property
    def count(self) -> int:
        return len(self.rows)

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query.as_dict(),
            "count": self.count,
            "rows": list(self.rows),
        }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class CQLParseError(ValueError):
    """Raised when a query body fails validation."""


def _parse_predicate(
    field_name: str,
    raw: Any,
    *,
    allow_experimental: bool = False,
) -> CQLPredicate:
    """Parse one `where:` entry into a :class:`CQLPredicate`.

    ``allow_experimental`` controls whether ops in
    :data:`EXPERIMENTAL_OPS` (e.g., ``regex``) are accepted. When
    ``False`` (the default), an experimental op produces a parse
    error citing the flag that gates it; agency operators see this
    error rather than ever exercising the experimental surface.
    """
    if isinstance(raw, Mapping):
        op = str(raw.get("op", "eq")).strip().lower()
        if op in V1_OPS:
            return CQLPredicate(field=field_name, op=op, value=raw.get("value"))
        if op in EXPERIMENTAL_OPS:
            if not allow_experimental:
                raise CQLParseError(
                    f"operator '{op}' on field '{field_name}' is experimental; "
                    f"enable {EXPERIMENTAL_OPS_FLAG!r} for the calling context "
                    f"or restrict the query to V1 operators ({', '.join(V1_OPS)})"
                )
            return CQLPredicate(field=field_name, op=op, value=raw.get("value"))
        raise CQLParseError(f"unknown operator '{op}' on field '{field_name}'")
    return CQLPredicate(field=field_name, op="eq", value=raw)


def parse_query(
    body: Any,
    *,
    flags: Optional[FeatureFlagRegistry] = None,
    tenant_context: Optional[TenantContext] = None,
    tenant: Optional[Tenant] = None,
) -> CQLQuery:
    """Parse a query body (dict or YAML string) into a :class:`CQLQuery`.

    UIAO_119 v2 wave 2 — when ``flags`` and ``tenant_context`` are
    both supplied, parse-time consults the
    ``auditor-api.cql.experimental-ops`` feature flag. Queries that
    use experimental operators (e.g., ``regex``) succeed only when
    the flag is enabled for the supplied context. Without
    ``flags``/``tenant_context`` experimental operators are rejected
    — the strict default keeps the v1 surface stable for agency
    operators.
    """
    if isinstance(body, str):
        try:
            body = yaml.safe_load(body)
        except yaml.YAMLError as exc:
            raise CQLParseError(f"invalid YAML: {exc}") from exc
    if not isinstance(body, Mapping):
        raise CQLParseError("query body must be a mapping")

    allow_experimental = False
    if flags is not None and tenant_context is not None:
        allow_experimental = flags.is_enabled(EXPERIMENTAL_OPS_FLAG, tenant_context, tenant)

    source = str(body.get("source", "")).strip()
    if source not in VALID_SOURCES:
        raise CQLParseError(f"unknown source '{source}'. Valid sources: {', '.join(VALID_SOURCES)}")

    select_raw = body.get("select") or []
    select: tuple[str, ...]
    if isinstance(select_raw, str):
        select = (select_raw.strip(),) if select_raw.strip() else ()
    elif isinstance(select_raw, Iterable):
        select = tuple(str(f).strip() for f in select_raw if str(f).strip())
    else:
        select = ()

    where_raw = body.get("where") or {}
    predicates: list[CQLPredicate] = []
    if isinstance(where_raw, Mapping):
        for field_name, value in where_raw.items():
            predicates.append(
                _parse_predicate(
                    str(field_name),
                    value,
                    allow_experimental=allow_experimental,
                )
            )

    order_by = str(body.get("order_by", "")).strip()
    order = str(body.get("order", "asc")).strip().lower()
    if order not in ("asc", "desc"):
        raise CQLParseError(f"order must be 'asc' or 'desc', got '{order}'")

    limit_raw = body.get("limit", 0)
    try:
        limit = int(limit_raw) if limit_raw is not None else 0
    except (TypeError, ValueError) as exc:
        raise CQLParseError(f"limit must be an integer, got {limit_raw!r}") from exc
    if limit < 0:
        raise CQLParseError(f"limit must be >= 0, got {limit}")

    return CQLQuery(
        source=source,
        select=select,
        where=tuple(predicates),
        order_by=order_by,
        order=order,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


@dataclass
class CQLEvaluator:
    """Evaluates parsed queries against a :class:`CQLSourceResolver`."""

    resolver: CQLSourceResolver

    def evaluate(self, query: CQLQuery) -> CQLResult:
        rows = self.resolver(query.source)
        # Filter
        filtered = [r for r in rows if all(p.matches(r) for p in query.where)]
        # Order
        if query.order_by:
            reverse = query.order == "desc"
            filtered.sort(
                key=lambda r: _ordering_key(r.get(query.order_by)),
                reverse=reverse,
            )
        # Limit
        if query.limit > 0:
            filtered = filtered[: query.limit]
        # Project
        if query.select:
            projected = tuple({k: r.get(k) for k in query.select} for r in filtered)
        else:
            projected = tuple(dict(r) for r in filtered)
        return CQLResult(query=query, rows=projected)


def _ordering_key(value: Any) -> tuple[int, Any]:
    """Build a sort key that tolerates None and mixed-type fields."""
    if value is None:
        return (0, "")
    if isinstance(value, (int, float, bool)):
        return (1, value)
    return (2, str(value))


# ---------------------------------------------------------------------------
# Source resolvers — wire CQL to the substrate's live data
# ---------------------------------------------------------------------------


def make_default_resolver(
    *,
    findings: Optional[list[dict[str, Any]]] = None,
    enforcement: Optional[list[dict[str, Any]]] = None,
    archive: Optional[list[dict[str, Any]]] = None,
    adapters: Optional[list[dict[str, Any]]] = None,
) -> CQLSourceResolver:
    """Build a resolver from in-memory record lists. Tests use this;
    production deployments inject live data via callable resolvers."""
    sources = {
        "findings": list(findings or []),
        "enforcement": list(enforcement or []),
        "archive": list(archive or []),
        "adapters": list(adapters or []),
    }

    def resolve(name: str) -> list[dict[str, Any]]:
        return sources.get(name, [])

    return resolve


def graph_findings_resolver(graph: Any) -> list[dict[str, Any]]:
    """Project an :class:`uiao.evidence.graph.EvidenceGraph` into the
    flat dict shape CQL operates on. Each graph FindingNode becomes one
    row.
    """
    out: list[dict[str, Any]] = []
    for node in graph.nodes_of_type("finding"):
        extra = getattr(node, "extra", {}) or {}
        out.append(
            {
                "id": getattr(node, "id", ""),
                "severity": getattr(node, "severity", ""),
                "control_id": getattr(node, "control_id", ""),
                "drift_class": getattr(node, "drift_class", ""),
                "status": getattr(node, "status", ""),
                "adapter_id": str(extra.get("adapter_id", "") or ""),
                "run_id": str(extra.get("run_id", "") or ""),
            }
        )
    return out


def journal_records_resolver(records: Iterable[Any]) -> list[dict[str, Any]]:
    """Project EnforcementJournal records (or any object with
    ``as_dict()``) into flat dicts."""
    out: list[dict[str, Any]] = []
    for r in records:
        if hasattr(r, "as_dict"):
            out.append(r.as_dict())
        elif isinstance(r, Mapping):
            out.append(dict(r))
    return out


def archive_entries_resolver(entries: Iterable[Any]) -> list[dict[str, Any]]:
    """Project ArchiveEntry records into flat dicts."""
    return journal_records_resolver(entries)


def adapters_resolver(adapter_dicts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Project canon adapter dicts into flat dicts (drops nested keys)."""
    out: list[dict[str, Any]] = []
    for raw in adapter_dicts:
        if not isinstance(raw, Mapping):
            continue
        flat: dict[str, Any] = {}
        for k, v in raw.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                flat[str(k)] = v
            elif isinstance(v, list):
                flat[str(k)] = list(v)
        out.append(flat)
    return out


# ---------------------------------------------------------------------------
# Canonical query loader
# ---------------------------------------------------------------------------


def load_canonical_queries(
    query_dir: str | Path | None = None,
) -> dict[str, CQLQuery]:
    """Load reference queries from ``src/uiao/canon/queries/``.

    Each YAML file contributes one query. The file's stem becomes the
    query id (e.g. ``open-drift-authz-findings.yaml`` →
    ``open-drift-authz-findings``).
    """
    root = Path(query_dir) if query_dir else DEFAULT_QUERY_DIR
    if not root.is_dir():
        return {}
    out: dict[str, CQLQuery] = {}
    for path in sorted(root.iterdir()):
        if path.suffix not in (".yaml", ".yml"):
            continue
        try:
            body = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        try:
            out[path.stem] = parse_query(body)
        except CQLParseError:
            continue
    return out


__all__ = [
    "CQLEvaluator",
    "CQLParseError",
    "CQLPredicate",
    "CQLQuery",
    "CQLResult",
    "CQLSourceResolver",
    "EXPERIMENTAL_OPS",
    "EXPERIMENTAL_OPS_FLAG",
    "V1_OPS",
    "VALID_SOURCES",
    "adapters_resolver",
    "archive_entries_resolver",
    "graph_findings_resolver",
    "journal_records_resolver",
    "load_canonical_queries",
    "make_default_resolver",
    "parse_query",
]
