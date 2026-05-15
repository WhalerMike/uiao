# v0.6.2 Palo Alto NGFW — Phase 0 Plan

> **Status:** Inbox draft, 2026-05-15. Not canon. Anchored to #459 child of #447.

## Mission (one sentence)

Take the existing PAN-OS XML-API alignment adapter from "schema discovery + offline XML parsing scaffold" to "full tier-1 conformance with real HTTPS XML API, OSCAL emission, KSI rules, contract fixtures, and real drift detection."

## State of tree (verified 2026-05-15 via MCP)

| Surface | Path | State |
|---|---|---|
| Adapter | `src/uiao/adapters/paloalto_adapter.py` | ✅ Real — 8 methods incl. `get_running_config`, `push_config_change`, `generate_firewall_evidence`. Scope: `security-policies`, `nat-rules`, `threat-prevention-profiles`. |
| Parser | `src/uiao/adapters/paloalto_parser.py` | ✅ Real — `parse_security_rules_xml`, `parse_nat_rules_xml` |
| Test | `tests/test_paloalto_adapter.py` | ✅ Exists |
| Registry entry | `modernization-registry.yaml` (palo-alto) | ✅ `status: active, phase: phase-1, runner-class: on-prem-self-hosted`, controls SC-7/CM-7/AC-4 |
| Real HTTPS XML API call | `get_running_config()` line "In real usage, call PAN-OS XML API here" | ❌ Stub — pulls XML from `_config["_security_rules_xml"]` mock; never makes a real HTTP request |
| `push_config_change()` real push + commit | adapter line ~210 | ⚠️ Reports drift only; never POSTs to PAN-OS or issues `<commit>` |
| OSCAL emitter | `src/uiao/oscal/paloalto_evidence.py` | ❌ Missing |
| KSI rules | `src/uiao/rules/ksi/paloalto/*.yaml` | ❌ Missing |
| Tier-2 fixtures | `tests/fixtures/tier-2/paloalto/*.xml` | ❌ Missing (PAN-OS responses are XML, not JSON) |
| Conformance test | `tests/conformance/test_paloalto_conformance.py` | ❌ Missing |
| `detect_drift()` impl | adapter line ~146 | ⚠️ Placeholder ("scaffold — implement running-config vs candidate-config vs canon baseline") |

## Doctrine status

**No new ADR needed.** ADR-049 (Microsoft Adapter Coverage Expansion) + ADR-035 (per-adapter activation pattern) cover the doctrinal model. ServiceNow v0.6.1 established the per-adapter Phase 0 → Batch A → Phase 2 → Phase 4 cadence; v0.6.2 follows it directly.

## Differences from v0.6.1 ServiceNow

| Aspect | ServiceNow (v0.6.1) | Palo Alto (v0.6.2) |
|---|---|---|
| Wire format | JSON via REST Table API | XML via PAN-OS XML API |
| Runner class | github-hosted | **on-prem-self-hosted** (PAN-OS management plane is rarely internet-reachable) |
| Auth | Bearer token | API key, mTLS preferred |
| Mutation contract | POST/PATCH per object | XML config edit + explicit `<commit>` operation |
| Existing test infrastructure | None | `test_paloalto_adapter.py` exists |
| Fixture format | JSON | XML (or JSON wrapper around XML payloads) |

## Batch A — 5 file-scoped workstreams

Same disjoint-file shape as v0.6.1 with minor adjustments for XML/PAN-OS specifics.

| WS | Branch | Scope (in) | Acceptance |
|---|---|---|---|
| **WS-A1** Real API integration | `claude/v0.6.2-ws-a1-paloalto-api` | `src/uiao/adapters/paloalto_adapter.py` (HTTP layer only), `src/uiao/collectors/paloalto_collector.py` (new) | `paloalto_collector.py` makes real `httpx` calls to PAN-OS XML API (GET running-config, POST config edit, POST commit); empty-scaffold fallback when no API key configured; `get_running_config()` and `push_config_change()` wire through collector; mTLS support honored from config |
| **WS-A2** OSCAL emitter | `claude/v0.6.2-ws-a2-paloalto-oscal` | new `src/uiao/oscal/paloalto_evidence.py`, `tests/test_paloalto_oscal_emitter.py` | `emit_paloalto_component_definition(claims, tenant_id, signer, signing_key) -> dict` producing OSCAL 1.1.2 component-definition citing SC-7 / CM-7 / AC-4; HMAC-SHA256 signing; ≥8 tests including signature round-trip + tamper detection (mirror WS-A2 pattern from v0.6.1) |
| **WS-A3** KSI rules | `claude/v0.6.2-ws-a3-paloalto-ksi` | `src/uiao/rules/ksi/paloalto/KSI-PAN-001..006.yaml`, append to `uiao-control-to-ksi-mapping.yaml` | 6 KSI-PAN rules per #459 spec (log-setting, no-any-any, threat-profile attached, decryption policy, commit approver, NAT cites security rule); mapping registry append-only |
| **WS-A4** Tier-2 fixtures | `claude/v0.6.2-ws-a4-paloalto-fixtures` | `tests/fixtures/tier-2/paloalto/` | 6 fixtures: `security-rule-create.xml`, `security-rule-update.xml`, `nat-rule-create.xml`, `threat-profile-update.xml`, `commit-success.xml`, `commit-conflict.xml`. Wrap XML payloads in a tier-2 contract JSON envelope per PR #304 schema, or emit raw XML with companion `.meta.json` siblings — WS-A4 picks the cleaner option that conforms to the existing schema. |
| **WS-A5** Drift + tests | `claude/v0.6.2-ws-a5-paloalto-drift-tests` | `src/uiao/adapters/paloalto_adapter.py` (drift method only), expand `tests/test_paloalto_adapter.py`, new `tests/conformance/test_paloalto_conformance.py` | `detect_drift()` real impl: compares running-config (collector fetch) vs candidate-config vs registry-expected scope; emits `DriftReport(drift_type="palo-alto-rule-divergence", severity="high"|"info")`; ≥15 tests covering connect / schema / query / normalize / drift / push-change-without-commit / commit; ≥6 conformance tests against WS-A4 fixtures |

## Concurrency rules

WS-A1 and WS-A5 both touch `paloalto_adapter.py` — A1 owns HTTP-call wiring (additive in collector + minimal hook in adapter), A5 owns `detect_drift()` method body only. Merge order: A1 → A5 → A4 → A2 → A3 (same as v0.6.1).

## Phase 2 integration

1. Merge order: A1 → A5 → A4 → A2 → A3
2. Cross-WS wire-up (anticipated): A5's conformance test calling A2's emitter (same shape as v0.6.1's fix)
3. Run full CI; tag `v0.6.2-rc1`

## Phase 4 release cut

Same shape as v0.6.1 (with line-ending lesson learned):

```powershell
# Use explicit LF write to avoid mixed-line-ending pre-commit hook
[IO.File]::WriteAllText(
    "src/uiao/__version__.py",
    '__version__ = "0.6.2"' + "`n",
    [Text.Encoding]::UTF8
)
```

Then commit + tag + push.

## Out of scope for v0.6.2

- Panorama (multi-NGFW management) — separate adapter
- Cortex (XSOAR / XDR) — separate adapter
- GlobalProtect VPN — separate adapter
- Cloud NGFW (AWS / Azure variants) — separate adapter
- Real-NGFW validation (deferred to v0.6.2.x lab-NGFW pass; needs on-prem-self-hosted runner with PAN-OS access)
- CyberArk completion (sibling: #460)

## Worker-agent dispatch (when ready)

Same template as v0.6.1; substitute `v0.6.2` and `paloalto` paths.
