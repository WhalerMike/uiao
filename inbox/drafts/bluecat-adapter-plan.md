# Implementation Plan — BlueCat Address Manager (BAM) Adapter

> **Branch:** `claude/bluecat-adapter-build`
> **Date:** 2026-04-19
> **Status:** draft (not canon)
> **Target canon entry:** `src/uiao/canon/modernization-registry.yaml` → `id: bluecat-address-manager` (status `active`, phase-1)

## Goal

Land the BlueCat Address Manager adapter as the second IPAM-class
modernization adapter, mirroring the just-landed `InfobloxAdapter`
structure. Closes the last canon → code drift in the IPAM family.

## Current state

| Artifact | Lines | State |
|---|---|---|
| `src/uiao/adapters/bluecat_adapter.py` | — | **missing** |
| `src/uiao/adapters/bluecat_parser.py` | — | **missing** |
| `src/uiao/directory_migration/adapters/ipam/bluecat/` | 6 | README placeholder only |
| `tests/test_bluecat_adapter.py` | — | **missing** |
| `tests/test_bluecat_to_oscal.py` | — | **missing** |
| `tests/fixtures/bluecat-*.json` | — | **missing** |
| Canon registry entry `bluecat-address-manager` | — | `status: active`, 4-item scope |

## Scope mapping (BlueCat ↔ Infoblox)

| Canon scope | Infoblox WAPI object | BlueCat BAM object |
|---|---|---|
| `dns-records` | `record:a` / `record:cname` | `HostRecord` / `AliasRecord` |
| `dhcp-scopes` | `range` | `DHCP4Range` |
| `ip-allocations` | `fixedaddress` | `IP4Address` / `MACAddress` |
| `side-by-side-ad` | event-stream.ndjson | event-stream.ndjson |
| *(no entry)* | `networkview` | *(uses "Configuration" — out of scope)* |

**Note:** canon declares 4 scope items for BlueCat (no `network-views`
— BAM uses "Configuration" which is the implicit root container, not a
queryable object per se). `SCOPE` constant therefore has 4 entries, not
5.

## Target architecture

Mirror `infoblox_adapter.py` + `infoblox_parser.py` + tests:

```
src/uiao/adapters/
  bluecat_adapter.py        # ~440 lines — full DB contract + 5 extensions
  bluecat_parser.py         # ~150 lines — BAM JSON → flat dicts per type
tests/
  test_bluecat_adapter.py   # ~260 lines — instantiation, connect, schema,
                            #   query, normalize, drift, evidence, failures
  test_bluecat_to_oscal.py  # ~100 lines — SC-20/SC-21/CM-8 OSCAL round-trip
  fixtures/
    bluecat-host-records.json
    bluecat-alias-records.json
    bluecat-dhcp-ranges.json
    bluecat-ip-addresses.json
```

## Work breakdown

### 1. Parser (`bluecat_parser.py`, ~150 lines)
- `parse_host_records(payload)` — HostRecord (A-record equivalent) → flat list.
- `parse_alias_records(payload)` — AliasRecord (CNAME equivalent).
- `parse_dhcp_ranges(payload)` — DHCP4Range.
- `parse_ip_addresses(payload)` — IP4Address objects.
- `_entity_properties(raw)` — helper: parses BAM's
  `"properties": "k1=v1|k2=v2|"` pipe-delimited string into a dict.
- `diff_record_sets(baseline, live)` — reuse the same shape as
  `infoblox_parser.diff_record_sets` (identity key from `id` field, falls
  back to `type:config:name`).

### 2. Adapter (`bluecat_adapter.py`, ~440 lines)
- `SCOPE = ["dns-records", "dhcp-scopes", "ip-allocations", "side-by-side-ad"]` (4 items).
- `connect()` — identity `bluecat:<bam_host>:<config>`, endpoint
  `<bam_host>/Services/REST/v1/` (HTTPS), mTLS defaults True.
- `discover_schema()` — vendor schema for HostRecord, AliasRecord,
  DHCP4Range, IP4Address.
- `execute_query()` — dispatch on `from` ∈ SCOPE to distinct BAM REST paths
  (`getEntitiesByName`, `getDHCP4Ranges`, `getIP4Address`).
- `normalize()` — per-object-type dispatch via `_claim_fields` helper.
- `detect_drift()` — real diff via `bluecat_parser.diff_record_sets`
  sourcing baseline + live from config; safe scaffold when absent.
- Extensions:
  - `get_all_objects(scope, bam_json)` — mirror of infoblox's.
  - `push_dns_change(record_type, name, data)` — DriftReport warning.
  - `push_dhcp_change(scope_type, identifier, data)` — same.
  - `emit_event_stream(events, output_path)` — NDJSON writer (identical
    to infoblox's; consider extracting to a shared helper in a follow-up).
  - `generate_ipam_evidence(scope, bam_json)` — KSI bundle for SC-20/SC-21/CM-8.
- `collect_and_align()` — calls `get_all_objects()`, returns vendor
  metadata dict.

### 3. Fixtures (3 new files)
- `bluecat-host-records.json` — 3 entries with BAM shape (`id`, `name`,
  `type: "HostRecord"`, `properties: "absoluteName=...|addresses=..."`).
- `bluecat-dhcp-ranges.json` — 3 DHCP4Range entries.
- `bluecat-ip-addresses.json` — 3 IP4Address entries (one STATIC, one
  DHCP_RESERVED, one DHCP_FREE).
- *No* alias-records fixture — covered by the host-records fixture
  including CNAME-style test rows.

### 4. Tests (`test_bluecat_adapter.py`, ~260 lines)
Mirror `test_infoblox_adapter.py`'s 11 test classes, adjusted for:
- 4-item SCOPE (not 5)
- BAM-specific identity shape
- BAM pipe-delimited properties parsing verification

### 5. OSCAL roundtrip (`test_bluecat_to_oscal.py`, ~100 lines)
Mirror `test_infoblox_to_oscal.py` — 8 tests covering claims → bundle →
SAR, all three SC-20/SC-21/CM-8 controls wired into bundle.controls and
bundle.policies.

### 6. Export
- `src/uiao/adapters/__init__.py` — add `BlueCatAdapter` to
  imports and `__all__`.
- `tests/test_adapters.py` — verify the registry entry resolves.

## Out of scope

- Live BAM HTTP client — offline testability pattern matches infoblox.
- Shared NDJSON writer extraction — flagged as a follow-up refactor
  once a third adapter needs it.
- Canon changes — `bluecat-address-manager` is already `status: active`.
- `directory_migration/adapters/ipam/bluecat/README.md` stub — same
  decision as infoblox's: repoint to the new code or delete. Deferred.

## Test / exit criteria

- [ ] `pytest tests/test_bluecat_adapter.py` green (≥ 40 tests)
- [ ] `pytest tests/test_bluecat_to_oscal.py` green (8 tests)
- [ ] `pytest tests/test_adapters.py` still 31 passed / 1 skipped
- [ ] Full regression: no new failures in paloalto / infoblox / m365 /
      terraform / scuba suites
- [ ] `ruff check` clean on all new files
- [ ] `uiao substrate walk` reports no new DRIFT findings

## Commit cadence

One commit per numbered step, prefixed `[UIAO-IMPL] feat|test: bluecat —`.
Target ~6 commits. PR body links this plan and the infoblox sibling PR.

## Follow-ups (separate PRs)

1. **Extract shared NDJSON emitter** — `emit_event_stream` is now
   identical across infoblox and bluecat; move to
   `adapters/_ipam_common.py` or similar.
2. **BAM properties parser in common module** — `_entity_properties`
   may also serve other BAM integrations.
3. **Delete or repoint** the `directory_migration/adapters/ipam/bluecat/README.md`
   placeholder now that the canonical adapter exists.
