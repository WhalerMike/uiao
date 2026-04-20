# Implementation Plan — Infoblox NIOS DNS/IPAM Adapter

> **Branch:** `claude/plan-next-adapter-jb76z`
> **Date:** 2026-04-18
> **Status:** draft (not canon; staging for impl PR)
> **Target canon entry:** `src/uiao/canon/modernization-registry.yaml` → `id: infoblox` (status `active`, phase-1)

## Goal

Promote the existing 121-line `infoblox_adapter.py` scaffold to a fully-built
Tier 4 adapter matching the depth of `PaloAltoAdapter` (329 lines + 138-line
parser + 265-line test file). Close the drift between canon (`status: active`)
and code (scaffold-only).

## Current state

| Artifact | Lines | State |
|---|---|---|
| `impl/src/uiao/impl/adapters/infoblox_adapter.py` | 121 | Thin scaffold — 7 DB-adapter methods + 2 extensions, all placeholder |
| `impl/src/uiao/impl/adapters/infoblox_parser.py` | — | **missing** |
| `impl/src/uiao/impl/directory_migration/adapters/ipam/infoblox/` | — | README-only (no Python; migrated from uiao-gos on 2026-04-17) |
| `impl/tests/test_infoblox_adapter.py` | — | **missing** (violates test-coverage rule) |
| `impl/tests/test_infoblox_to_oscal.py` | — | **missing** |
| `impl/tests/fixtures/infoblox-records.json` | — | Present (3 records: A + CNAME) |
| `impl/tests/data/mock_infoblox.json` | — | Present (network/subnet objects) |

## Gap analysis vs `modernization-registry.yaml` scope

Canon declares 5 scope items; current adapter only meaningfully covers 1.

| Scope item | Covered? |
|---|---|
| `dns-records` | partial (A-record path only) |
| `dhcp-scopes` | no |
| `ip-allocations` | no |
| `network-views` | no (config field exists, not queried) |
| `side-by-side-ad` | no |

Canon also declares 3 outputs; current adapter emits 1.

| Output | Covered? |
|---|---|
| `dns-change-manifest.json` | yes (`push_dns_change` stub) |
| `ipam-audit.json` | no |
| `event-stream.ndjson` | no |

## Target architecture

Mirror `paloalto_adapter.py` + `paloalto_parser.py` + `test_paloalto_adapter.py`.

```
impl/src/uiao/impl/adapters/
  infoblox_adapter.py        # ~330 lines — full DB contract + 5 extensions
  infoblox_parser.py         # ~140 lines — WAPI JSON → flat dicts per record type
impl/tests/
  test_infoblox_adapter.py   # ~260 lines — instantiation, connect, schema,
                             #   query, normalize, drift, evidence, failure modes
  test_infoblox_to_oscal.py  # ~100 lines — SC-20/SC-21/CM-8 OSCAL round-trip
  fixtures/
    infoblox-dhcp-ranges.json      # new
    infoblox-networks.json         # new (or promote mock_infoblox.json)
    infoblox-fixed-addresses.json  # new
```

## Work breakdown (ordered; each step independently mergeable)

### 1. Parser module (`infoblox_parser.py`)
- `parse_a_records(wapi_json)` → `[{name, ipv4, zone, view, ref}]`
- `parse_cname_records(wapi_json)` → `[{alias, canonical, view, ref}]`
- `parse_networks(wapi_json)` → `[{cidr, view, tags}]`
- `parse_dhcp_ranges(wapi_json)` → `[{start, end, network, view}]`
- `parse_fixed_addresses(wapi_json)` → `[{ipv4, mac, name, view}]`
- `diff_record_sets(canon, live)` → `{added, removed, modified}` (drift helper)

### 2. Adapter expansion (`infoblox_adapter.py` → ~330 lines)
- Add `SCOPE = [...]` class constant matching 5 canon scope items.
- `execute_query`: branch on `canonical_query["from"]` to emit 5 WAPI URLs (not just one).
- `normalize`: dispatch to record-type-specific claim builders; per-type `claim_id` shape (e.g. `infoblox:<view>:record-a:<name>`, `infoblox:<view>:network:<cidr>`).
- `discover_schema`: vendor/canonical schema for all 5 object types.
- `detect_drift`: real three-way (canon baseline ↔ WAPI live ↔ last-collected) using `diff_record_sets`; severity from drift count.
- New extension methods:
  - `get_all_objects(scope=None, wapi_json=None)` — mirror of `get_running_config`; accepts injected JSON for tests.
  - `push_dhcp_change(scope, cidr, delta)` — DHCP sibling of `push_dns_change`.
  - `emit_event_stream(events)` — writes NDJSON to `event-stream.ndjson` (canon output).
  - `generate_ipam_evidence(records=None)` — full bundle covering SC-20, SC-21, CM-8; replaces `generate_dns_evidence`.

### 3. Fixtures
- Promote `tests/data/mock_infoblox.json` to `tests/fixtures/infoblox-networks.json` (align with existing `infoblox-records.json` naming).
- Add `infoblox-dhcp-ranges.json` and `infoblox-fixed-addresses.json` with 3 entries each.

### 4. Tests (`test_infoblox_adapter.py` ~260 lines)
Mirror `test_paloalto_adapter.py` class structure:
- `TestInstantiation` — ADAPTER_ID, SCOPE (5 items), default/custom config, `isinstance(DatabaseAdapterBase)`.
- `TestConnect` — provenance, identity contains grid_master, endpoint shape, mTLS default True.
- `TestDiscoverSchema` — all 5 vendor object types present; unmapped fields captured.
- `TestExecuteQuery` — each of the 5 `from` values produces distinct WAPI URL.
- `TestNormalize` — record-type dispatch; claim_id shape per type; empty-input safety.
- `TestDriftDetection` — drift count from injected canon vs WAPI diff; severity escalation.
- `TestExtensions` — `get_all_objects` with injected JSON, `push_dns_change`, `push_dhcp_change`, `emit_event_stream` (tmp_path), `generate_ipam_evidence`.
- `TestFailureModes` — malformed WAPI JSON, missing `view`, unknown `from`, empty record set.

### 5. OSCAL round-trip (`test_infoblox_to_oscal.py` ~100 lines)
- Feed a `generate_ipam_evidence()` output through `adapter_to_oscal.py`.
- Assert SC-20, SC-21, CM-8 control IDs surface in the OSCAL observations.

### 6. Update `impl/src/uiao/impl/adapters/__init__.py`
- Already exports `InfobloxAdapter` (confirmed via `test_adapters.py` import) — no change expected, but verify.

## Out of scope (explicitly deferred)

- Live WAPI HTTP client. Adapter remains offline-testable; production deployment
  wires a session object via the `auth_method` config path (same pattern
  PaloAlto uses for on-prem runners).
- BlueCat adapter. Identical shape, but land Infoblox first and port via a
  follow-up PR (`ADP-NNN`) once the IPAM adapter contract is proven.
- Canon changes. The registry entry is already `status: active` — no
  `UIAO_NNN` allocation or ADR needed for this work.

## Test / exit criteria

- [ ] `pytest -q impl/tests/test_infoblox_adapter.py` green (≥ 40 tests)
- [ ] `pytest -q impl/tests/test_infoblox_to_oscal.py` green
- [ ] `pytest -q` (full suite) green — no regressions in `test_adapters.py`
- [ ] `ruff check impl/` clean
- [ ] `uiao substrate walk` reports no new DRIFT findings
- [ ] `uiao substrate drift` exit 0

## Commit cadence

One commit per numbered work item above, each prefixed `[UIAO-IMPL] feat: infoblox — <subject>`. Target ~6 commits total; PR body links back to this plan file.

## Follow-ups (separate PRs)

1. **BlueCat parity** — port same structure to `bluecat_adapter.py`; reuse the IPAM test harness.
2. **Event stream wiring** — connect `emit_event_stream` to the directory-migration event bus in `impl/src/uiao/impl/directory_migration/`.
3. **Delete the `directory_migration/adapters/ipam/infoblox/README.md` stub** once the canonical adapter covers its capabilities, or convert it into a usage guide pointing at `uiao.impl.adapters.infoblox_adapter`.
