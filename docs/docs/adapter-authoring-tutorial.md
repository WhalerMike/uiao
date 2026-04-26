---
document_id: ADAPTER_TUTORIAL
title: "Adapter Authoring Tutorial: Your First UIAO Adapter"
version: "1.0"
classification: DERIVED
created_at: "2026-04-24"
updated_at: "2026-04-24"
---

# Adapter Authoring Tutorial: your first UIAO adapter

A 30-minute walkthrough from zero to a merged adapter PR, using the
shipped [ScubaGear adapter](../../src/uiao/adapters/scubagear_adapter.py)
as a mentor. By the end you will have built a minimal working
conformance adapter, passed the conformance test suite, and wired it
into the registry + CLI so `uiao adapter run <your-id>` invokes it.

This tutorial targets adapter authors. If you just want to *run* an
adapter, read [`quickstart.md`](quickstart.md) instead.

## 0. Orientation (2 min)

UIAO adapters are **read-only connectors** that pull data from external
systems, normalize it into canonical claims, and emit evidence that the
governance pipeline consumes. The registry classifies every adapter on
two independent axes:

| Axis | Values | Meaning |
|---|---|---|
| Operational class | `conformance` / `modernization` | Does it mutate the target system? |
| Mission class | `identity` / `telemetry` / `policy` / `enforcement` / `integration` | What governance domain does it serve? |

Conformance adapters live in
[`src/uiao/canon/adapter-registry.yaml`](../../src/uiao/canon/adapter-registry.yaml)
and **never mutate**. Modernization adapters live in
[`modernization-registry.yaml`](../../src/uiao/canon/modernization-registry.yaml)
and may mutate the target system under well-defined boundaries.

**You will build:** a toy `demo` conformance adapter with mission class
`policy`. Same axes as ScubaGear — it's the simplest lane to start in.

## 1. The contract (5 min)

Every adapter subclasses
[`DatabaseAdapterBase`](../../src/uiao/adapters/database_base.py) and
implements the **7 canonical responsibility domains** (per UIAO_121):

| # | Domain | Method | Returns |
|---|---|---|---|
| 2.1 | Connection & Identity | `connect()` | `ConnectionProvenance` |
| 2.2 | Schema Discovery & Mapping | `discover_schema()` | `SchemaMappingObject` |
| 2.3 | Query Normalization | `execute_query(q)` | `QueryProvenance` |
| 2.4 | Data Normalization | `normalize(rows)` | `ClaimSet` |
| 2.5 | Drift Detection | `detect_drift()` | `DriftReport` |
| 2.6 | Evidence Packaging | `collect_evidence(ksi_id)` | `EvidenceObject` |
| 2.7 | Security / Operations | `__init__(config)` + static checks | — |

The dataclasses these return are frozen contracts. Read them once:

```bash
less src/uiao/adapters/database_base.py
```

> **✓ Checkpoint 1:** you can name all 7 domains and the dataclass each
> one produces. If not, re-read `database_base.py` — everything in this
> tutorial builds on it.

## 2. File layout (3 min)

Single-file adapters live directly under `src/uiao/adapters/`:

```
src/uiao/adapters/
├── bluecat_adapter.py         ← single-file (BlueCatAdapter)
├── cyberark_adapter.py        ← single-file (CyberArkAdapter)
├── scubagear_adapter.py       ← single-file (ScubaGearAdapter)
└── terraform_adapter.py       ← single-file (TerraformAdapter)
```

Adapters with heavy supporting machinery (IR transforms, runtime
harnesses, schemas) get a subdirectory beside the single-file entry
point:

```
src/uiao/adapters/
├── scubagear_adapter.py       ← the adapter class itself
└── scuba/
    ├── ir/                    ← SCuBA → IR transformer
    ├── runtime/               ← runtime harness, PowerShell runners
    └── schemas/               ← normalized-JSON schema
```

**Rule of thumb:** start as a single file. Grow a subdirectory only
when the adapter has ≥ 3 supporting Python modules, a runtime, or a
schema.

Your `demo` adapter is single-file:
`src/uiao/adapters/demo_adapter.py`.

## 3. Implementation walkthrough (15 min)

The fastest path to a passing adapter is to read ScubaGear method by
method and translate each into your own. ScubaGear is deliberately
dependency-light: it loads a JSON/YAML file, maps fields, and emits
claims. That's the minimum viable shape.

Clone this shell for your `demo_adapter.py`:

```python
"""Demo adapter — read-only, policy mission class, single-file layout."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from uiao.adapters.database_base import (
    ClaimObject,
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    EvidenceObject,
    QueryProvenance,
    SchemaMappingObject,
)


class DemoAdapter(DatabaseAdapterBase):
    ADAPTER_ID = "demo"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._records: List[Dict[str, Any]] = []
```

Now walk each domain. The ScubaGear line references below point at
[`src/uiao/adapters/scubagear_adapter.py`](../../src/uiao/adapters/scubagear_adapter.py).

### 3.1 Connection & Identity (lines 190–207)

ScubaGear reads a local report file and returns
`ConnectionProvenance` tagged with the file path. You do the same,
just with your own source:

```python
    def connect(self) -> ConnectionProvenance:
        """Load demo data and return provenance."""
        # For a real adapter: open a TLS connection / API client here.
        # For demo: just seed in-memory records.
        self._records = [
            {"policy_id": "DEMO-01", "status": "PASS"},
            {"policy_id": "DEMO-02", "status": "FAIL"},
        ]
        return ConnectionProvenance(
            identity="demo:local",
            auth_method="none",
            endpoint="in-memory",
            tls_version="N/A",
            mtls_enabled=False,
            timestamp=self._now(),
        )
```

**Rules:**
- `identity` must be unique per connection attempt (use
  `<adapter_id>:<instance>`)
- `auth_method` must be non-empty (`api-token`, `mtls`, `file`, `oauth`,
  etc.)
- `timestamp` must be UTC (use `self._now()` from the base class)

### 3.2 Schema Discovery (lines 214–248)

Return a `SchemaMappingObject` that documents how the vendor's field
names map to UIAO's canonical shape. For ScubaGear: `PolicyId` →
`identity suffix + KSI lookup`. For demo:

```python
    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema = {"policy_id": "string", "status": "string"}
        canonical_schema = {
            "identity": "demo:<policy_id>",
            "evidence.source": "demo",
        }
        mapping_rules = {
            "policy_id": "identity suffix",
            "status": "pass_criteria boolean",
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=[],
            version_hash=self._hash(vendor_schema),
        )
```

**Rules:**
- `version_hash` must be deterministic — same input → same hash. Use
  `self._hash(...)`; the conformance suite tests this explicitly.
- `unmapped_fields` names the vendor fields you chose **not** to map
  (audit trail).

### 3.3 Query Normalization (lines 254–268)

Accepts a canonical query and translates it to a vendor-specific
filter. For demo, we don't have filters — return the full row count:

```python
    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=f"demo filter: {canonical_query}",
            execution_plan_hash=self._hash(canonical_query),
            row_count=len(self._records),
            timestamp=self._now(),
        )
```

### 3.4 Data Normalization (lines 274–318 in ScubaGear)

This is the adapter's real work: turn vendor-shaped rows into
`ClaimObject`s. Every claim carries a stable identity, a pass/fail
result, and a content hash.

```python
    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        claims: List[ClaimObject] = []
        for row in raw_rows or self._records:
            claim_id = f"demo:{row['policy_id']}"
            passed = row.get("status", "").upper() == "PASS"
            claims.append(
                ClaimObject(
                    identity=claim_id,
                    control_id="AC-1",           # map via your own table in real adapters
                    implementation_status="implemented" if passed else "not-implemented",
                    evidence_source="demo",
                    evidence_timestamp=self._now(),
                    record_hash=self._hash(row),
                    raw_payload=row,
                )
            )
        return ClaimSet(
            claims=claims,
            generated_at=self._now(),
            source_identity="demo:local",
            total_claims=len(claims),
        )
```

> **✓ Checkpoint 2:** you can hold every `ClaimObject` field in mind
> without re-reading the dataclass. If yes, you understand the
> adapter's output contract.

### 3.5 Drift Detection (lines 324–344)

Each adapter reports its own `drift_detected` bit based on internal
consistency checks between two schemas / two runs / two baselines. For
demo, drift is always False:

```python
    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_detected=False,
            drift_severity="none",
            drift_type="none",
            affected_identities=[],
            detected_at=self._now(),
            reference_hash=self._hash("demo-v1"),
            current_hash=self._hash("demo-v1"),
        )
```

### 3.6 Evidence Packaging (ScubaGear implements via `collect_and_align`)

`collect_evidence(ksi_id)` is optional but recommended — it lets the
orchestrator pull evidence for a specific Key Security Indicator:

```python
    def collect_evidence(self, ksi_id: str) -> EvidenceObject:
        records = [r for r in self._records if r["policy_id"].startswith(ksi_id)]
        return EvidenceObject(
            ksi_id=ksi_id,
            records=records,
            source="demo",
            collected_at=self._now(),
            record_count=len(records),
            content_hash=self._hash(records),
        )
```

### 3.7 Security / Operational controls

The base class handles timestamps, hashing, and config isolation. Your
job is to refuse unsafe configurations early:

```python
    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        # Reject obviously-wrong config shapes here. Example:
        if config and "endpoint" in config and not config["endpoint"].startswith("https://"):
            raise ValueError("demo adapter requires HTTPS endpoints")
        self._records = []
```

> **✓ Checkpoint 3:** all 7 methods in your `demo_adapter.py`. It runs:
>
> ```bash
> python -c "from uiao.adapters.demo_adapter import DemoAdapter; a = DemoAdapter({}); print(a.connect()); print(a.normalize([]))"
> ```

## 4. Registry wiring (3 min)

Two separate registries. Put your entry in exactly one:

- **Read-only** (no mutation): `src/uiao/canon/adapter-registry.yaml`
- **Change-making**: `src/uiao/canon/modernization-registry.yaml`

The `demo` adapter is read-only. Add this entry to
`adapter-registry.yaml` under `adapters:` (alphabetical by `id`):

```yaml
  - id: demo
    name: Demo Adapter (tutorial fixture)
    class: conformance
    mission-class: policy
    status: reserved           # promote to 'active' in the PR that wires it up
    phase: tutorial
    vendor: UIAO-Docs
    license: Apache-2.0
    runtime: python-3.10
    runner-class: in-process
    tenancy: per-adapter
    scope:
      - tutorial
    outputs:
      - demo-claims.json
    triggers:
      - workflow_dispatch
    notes:
      purpose: "Demonstration adapter referenced from the authoring tutorial."
```

**Required fields** (see schema at
[`src/uiao/schemas/adapter-registry/adapter-registry.schema.json`](../../src/uiao/schemas/adapter-registry/adapter-registry.schema.json)):
`id`, `name`, `class`, `mission-class`, `status`, `phase`, `vendor`,
`license`, `runtime`, `runner-class`, `tenancy`, `scope`, `outputs`,
`triggers`.

**`class` and `mission-class` must match your adapter's behavior:**

| If your adapter... | `class` = | Common `mission-class` |
|---|---|---|
| Only reads / evaluates / assesses | `conformance` | `policy` (like ScubaGear), `telemetry`, `identity` |
| Changes target system state | `modernization` | `enforcement`, `integration` |

The `modernization` class has stricter invariants (documented in
`modernization-registry.yaml` preamble) — reserve it for adapters that
actually mutate.

Validate the registry change before committing:

```bash
python -m pytest tests/test_adapter_registry.py -q
uiao substrate walk
```

## 5. Conformance test (2 min)

Every registered adapter is exercised by
[`tests/test_adapter_conformance.py`](../../tests/test_adapter_conformance.py) —
the UIAO_121 responsibility-domain runner. Register your adapter there:

```python
# tests/test_adapter_conformance.py
from uiao.adapters.demo_adapter import DemoAdapter

ADAPTERS = {
    ...
    "demo": DemoAdapter({}),
}
```

Run the suite:

```bash
python -m pytest tests/test_adapter_conformance.py -q
```

You'll see roughly 40 parametrized cases run against your adapter
(seven domain classes × five-to-seven assertions each). All must pass
before merge.

> **✓ Checkpoint 4:** `demo` appears in the pytest output with all
> domain tests green. If a test fails, the error message names the
> domain (`TestDomain23QueryNormalization::test_row_count_non_negative`
> etc.) — go back to the matching section of §3.

## 6. CLI invocation (2 min)

Your adapter is now reachable through the `uiao` CLI without further
work. The orchestrator enumerates it:

```bash
uiao orchestrator list --status active
```

And `uiao adapter run` dispatches to it by id (requires
`src/uiao/cli/adapter.py` to know about the class — for adapters
beyond the existing four, add an entry to the
`adapter_registry` dict in `cli/adapter.py:adapter_run`):

```bash
uiao adapter run demo
```

If you flipped the registry `status` from `reserved` to `active`, the
orchestrator's nightly scheduler will start dispatching to it. See
[`.github/workflows/orchestrator-scheduler.yml`](../../.github/workflows/orchestrator-scheduler.yml).

## 7. Submit the PR (1 min)

Your PR checklist:

- [ ] `src/uiao/adapters/<your_id>_adapter.py` — the adapter class
- [ ] `src/uiao/adapters/__init__.py` — export added alphabetically
- [ ] `src/uiao/canon/adapter-registry.yaml` **or**
      `modernization-registry.yaml` — entry added
- [ ] `tests/test_adapter_conformance.py` — adapter added to
      `ADAPTERS` dict
- [ ] `tests/test_<your_id>_adapter.py` — behavioral tests beyond
      conformance (recommended; see
      [`tests/test_scubagear_adapter.py`](../../tests/test_scubagear_adapter.py)
      as a shape reference)
- [ ] `ruff check` + `ruff format --check` clean
- [ ] `mypy src/uiao` — no new errors
- [ ] `pytest tests/test_adapter_conformance.py` — all green
- [ ] `uiao substrate walk` — no drift introduced

PR title convention: `feat(adapters): <adapter-id> adapter — <one-line purpose>`.

That's it. Merge-ready adapter in 30 minutes.

## Next steps

- **More complex adapters:** see
  [`terraform_adapter.py`](../../src/uiao/adapters/terraform_adapter.py)
  (remote-state ingestion), [`cyberark_adapter.py`](../../src/uiao/adapters/cyberark_adapter.py)
  (API client with auth), or
  [`m365_adapter.py`](../../src/uiao/adapters/m365_adapter.py)
  (multi-endpoint orchestration).
- **Modernization adapters:** the invariants differ — read
  [`modernization-registry.yaml`](../../src/uiao/canon/modernization-registry.yaml)
  preamble before starting. Look at
  [`src/uiao/adapters/modernization/active_directory/`](../../src/uiao/adapters/modernization/active_directory/)
  for the worked example.
- **Adapter framework reference:** [`adapter-framework.qmd`](adapter-framework.qmd)
  covers the full design rationale and the architectural invariants.
- **Historical guide:** [`adapter-development-guide.md`](adapter-development-guide.md)
  predates the `DatabaseAdapterBase` ABC and uses the older
  `ComplianceAdapter` / `NormalizedClaim` shape; consult for background
  but do not copy the interface.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'DemoAdapter'` | Missing export | Add import to `src/uiao/adapters/__init__.py` |
| Conformance test fails `test_version_hash_deterministic` | Non-deterministic input to `self._hash(...)` | Ensure inputs are dict / list / str (no timestamps or UUIDs inside the hashed payload) |
| `substrate walk` flags DRIFT-PROVENANCE | Docs reference a code path that doesn't exist | Fix the reference, or if the file was intentionally renamed, add the mapping to substrate-manifest |
| Registry validation fails | Missing required field | Check `schemas/adapter-registry/adapter-registry.schema.json` — it lists every required field with constraints |
