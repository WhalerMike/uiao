# v0.6.1 ServiceNow — Phase 0 Plan

> **Status:** Inbox draft, 2026-05-12. Not canon. Anchored to #458 child of #447.

## Mission (one sentence)

Take the existing ServiceNow alignment adapter from "read-side DNS-style alignment with stub collector fallback" to "full tier-1 conformance" — write-side methods, OSCAL emission, KSI rules, contract fixtures, dedicated tests.

## State of tree (verified 2026-05-12 via MCP)

| Surface | Path | State |
|---|---|---|
| Adapter | `src/uiao/adapters/servicenow_adapter.py` | ✅ Real — DNS-style alignment, `connect/discover_schema/execute_query/normalize/detect_drift/collect_and_align` all implemented |
| Collector | `src/uiao/collectors/servicenow_collector.py` | ✅ Real — Table API GET with bearer token, empty-scaffold fallback for no-token CI |
| Registry entry | `modernization-registry.yaml` (service-now) | ✅ `status: active, phase: phase-1`, controls IR-4/IR-5/IR-6/CM-3 |
| Write-side methods | (adapter only has `normalize` for reads) | ❌ Missing — modernization contract needs `create_incident`, `update_incident`, `create_change_request`, `create_problem` |
| OSCAL emitter | `src/uiao/oscal/servicenow_evidence.py` | ❌ Missing |
| KSI rules | `src/uiao/rules/ksi/servicenow/*.yaml` | ❌ Missing |
| Tier-2 fixtures | `tests/fixtures/tier-2/servicenow/*.json` | ❌ Missing |
| Adapter test | `tests/test_servicenow_adapter.py` | ❌ Missing |
| Conformance test | `tests/conformance/test_servicenow_conformance.py` | ❌ Missing |
| `detect_drift()` impl | adapter line 167–179 | ⚠️ Placeholder ("scaffold — implement query comparison against canon") |

## Doctrine status

**No new ADR needed.** ADR-049 (Microsoft Adapter Coverage Expansion) + ADR-035 (per-adapter activation pattern) cover the doctrinal model.

## Batch A — 5 file-scoped workstreams

Same disjoint-file pattern as v0.6.0 HRIT productization. All parallelizable.

| WS | Branch | Scope (in) | Acceptance |
|---|---|---|---|
| **WS-A1** Write-side methods | `claude/v0.6.1-ws-a1-servicenow-write` | `src/uiao/adapters/servicenow_adapter.py`, `src/uiao/collectors/servicenow_collector.py` | `create_incident()`, `update_incident()`, `create_change_request()`, `create_problem()` on adapter; collector gains `POST`/`PATCH` helpers; empty-scaffold fallback preserved |
| **WS-A2** OSCAL emitter | `claude/v0.6.1-ws-a2-servicenow-oscal` | new `src/uiao/oscal/servicenow_evidence.py`, `tests/test_servicenow_oscal_emitter.py` | `emit_servicenow_component_definition()` produces OSCAL 1.1.2 component-definition citing IR-4/IR-5/IR-6/CM-3; golden-file regression pinned |
| **WS-A3** KSI rules | `claude/v0.6.1-ws-a3-servicenow-ksi` | `src/uiao/rules/ksi/servicenow/KSI-SNOW-001..005.yaml`, append to `uiao-control-to-ksi-mapping.yaml` | KSI-SNOW-001..005 per #458 spec; each KSI cites a NIST control + severity; mapping registry append-only |
| **WS-A4** Tier-2 fixtures | `claude/v0.6.1-ws-a4-servicenow-fixtures` | `tests/fixtures/tier-2/servicenow/` | `incident-create.json`, `incident-update.json`, `change-request-create.json`, `problem-create.json`, `query-result-empty.json`, `query-result-3-records.json`; conform to PR #304 schema |
| **WS-A5** drift impl + tests | `claude/v0.6.1-ws-a5-servicenow-drift-tests` | `src/uiao/adapters/servicenow_adapter.py` (drift only), `tests/test_servicenow_adapter.py`, `tests/conformance/test_servicenow_conformance.py` | `detect_drift()` returns real findings against canon; ≥10 tests cover read+write+drift; conformance pack passes |

## Concurrency rules

WS-A1 and WS-A5 both touch `servicenow_adapter.py` — A5 is drift-only, A1 is write-only. Merge A1 first, then A5. The other three (A2, A3, A4) are fully disjoint.

## Phase 2 integration

1. Merge order: A1 → A5 → A4 → A2 → A3
2. Wire A2's emitter to be called by A1's write methods (post-success evidence emission)
3. Wire A3's KSIs into the KSI evaluation pipeline (mapping registry already updated by A3)
4. Run full CI; tag `v0.6.1-rc1`

## Phase 4 release cut

1. Bump `__version__.py` → `0.6.1`
2. Prepend CHANGELOG `[0.6.1] — 2026-05-DD` entry
3. Tag `v0.6.1`; push tag; release.yml builds + publishes
4. Close #458; #459 (Palo Alto) becomes next

## Out of scope for v0.6.1

- ServiceNow Discovery / CMDB integration (separate adapter)
- ServiceNow ITOM / SecOps modules
- Real-tenant validation (deferred until v0.6.4 lab-tenant pass)
- Palo Alto / CyberArk completion (sibling patches: #459, #460)

## Worker-agent dispatch (when ready)

Same prompt template as v0.6.0 Batch A. Each session gets:

```
You are working on UIAO at /home/user/uiao on branch
claude/v0.6.1-ws-aN-... (already created on origin).

Read in order before any code change:
- inbox/v0.6.1-servicenow/00-phase0-plan.md §"WS-AN"
- AGENTS.md (invariants I1–I6)
- src/uiao/adapters/servicenow_adapter.py (current state)
- src/uiao/collectors/servicenow_collector.py (current state)
- src/uiao/canon/modernization-registry.yaml (service-now entry)

Execute "Deliverables" until "Acceptance" criteria are all met. Run
ruff check, mypy src/uiao, and pytest -q against your scope before
committing. Do not modify files outside your "Scope (in)" list.

Commit (conventional format). Push to origin. Do not open a PR —
Phase 2 will integrate.

If blocked, write to inbox/v0.6.1-servicenow/questions-WS-AN.md.
```
