# UIAO RFC-0026 Enhancement Roadmap

**Derived from:** RFC-0026 forum review + UIAO canon (UIAO_132, ADR-043) + verified repo state
**Date:** 2026-04-23
**Status:** Working draft — dates are enforcement-clock-driven targets, not commitments
**Provenance:**
- `src/uiao/canon/specs/fedramp-rfc-0026-ca7-integration.md` (UIAO_132)
- `src/uiao/canon/adr/adr-043-fedramp-rfc-0026-ca7-integration.md`
- `src/uiao/canon/substrate-manifest.yaml` (UIAO_200)
- `docs/docs/uiao-substrate-roadmap.md` (substrate status for context)
- External forum review: FedRAMP Community Discussion #130 (RFC-0026), cisagov/ScubaConnect Discussion #27, cisagov/ScubaGear Issue #2075, Issues #2104–#2110

---

## Executive summary

RFC-0026 (CA-7 Continuous Monitoring Expectations) is already canonical in UIAO — the spec, ADR, and reference directory landed on 2026-04-21 (commit `93c0e122`). Enforcement begins **2027-01-01** and escalates via a five-strike ladder ending in certification revocation. Two adjacent deadlines from FedRAMP Notice 0009 — mandatory CCM BIR adoption by **2027-04-01** and mandatory VDR adoption by **2027-06-01** — also fall inside the enforcement window.

Independent of the regulatory timeline, the upstream ScubaGear **Qwilfish** release (due **2026-06-30**) will add an MS.SECURITYSUITE policy group (issues #2104–#2110) and surface an OPA version dependency fix (#2075) that UIAO's adapter pipeline depends on. Coverage updates for Qwilfish must be in flight before it ships.

This roadmap sequences eight enhancements by enforcement-clock risk × implementation cost. Each line item is grounded in a verified file path or registry entry — external-analysis claims that failed verification (e.g. "35 adapters in registry" — actual is 8; "163 KSIs" — actual is 166) have been corrected.

---

## Status snapshot (2026-04-23)

| Area | Verified state |
|---|---|
| RFC-0026 canon integration | ✅ Complete (UIAO_132, ADR-043, reference dir) |
| `conmon-aggregate.yml` workflow | ✅ Exists |
| `gcc-boundary-gap-registry.yaml` | ✅ Exists (2026-04-20) |
| Connect.gov POA&M submission | 🟥 Manual — UIAO_132 Open Item O1, flagged before 2027-01-01 |
| Multi-agency distribution layer | 🟥 No registry, no distribution receipts |
| ScubaGear upstream tracking | 🟥 No automated watch; SCUBA_TO_KSI_MAP already has SECURITYSUITE stub entries (correction to prior analysis) |
| OPA version pre-flight | 🟥 Absent — `normalize_scuba.py` hardcodes `tool_version`; `scuba.yaml` has no OPA pin |
| PIM-for-Groups gap (ScubaGear #2072) | 🟥 Not in `gcc-boundary-gap-registry.yaml` |
| Pathway-1 BIR migration gates | 🟥 Not in enforcement timeline |
| Scan redaction pipeline | 🟥 No ADR, no implementation |

---

## Enforcement timeline (annotated)

| Date | Event | UIAO deliverables required by |
|---|---|---|
| 2026-06-30 | ScubaGear Qwilfish ships (SECURITYSUITE + OPA fix) | E2, E3 must be live |
| 2026-11-01 | 60-day pre-enforcement readiness window opens | E1, E5, E6 must be live |
| **2027-01-01** | **RFC-0026 enforcement begins (strike 1 eligible)** | Tier 1 complete |
| 2027-04-01 | CCM BIR adoption mandatory (Notice 0009) | E8 Pathway-1 migration ready |
| 2027-06-01 | VDR adoption mandatory (Notice 0009) | E8 Pathway-1 migration complete |

---

## Tier 1 — Before 2027-01-01 enforcement

### E1 · Connect.gov POA&M submission automation · UIAO_132 Open Item O1
**Target:** 2026-10-31 (60-day buffer before enforcement)
**Risk:** Missing a monthly upload after 2027-01-01 triggers strike 1 even if evidence was generated.
**Tasks:**
- [ ] T1.1 — Confirm Connect.gov upload API (REST vs SFTP; auth scheme; endpoint)
- [ ] T1.2 — Build `conmon-submit-poam` workflow as post-step of `conmon-aggregate.yml`
- [ ] T1.3 — Receipt verification; write `evidence/submissions/<yyyy-mm>/connect-gov-receipt.json`
- [ ] T1.4 — Failure path: open governance issue with SLA identical to UIAO_132 §2.2 72-hour critical-finding rule
- [ ] T1.5 — Dry-run mode for pre-enforcement testing
- [ ] T1.6 — Update UIAO_132 §2.3 to mark O1 closed

### E5 · Multi-agency artifact distribution layer
**Target:** 2026-11-30
**Risk:** RFC-0026 requires demonstrable distribution to *all* agency customers; today there's no mechanism to enumerate agencies or record distribution events.
**Tasks:**
- [ ] T5.1 — New canon file `agency-customer-registry.yaml` (pattern: `adapter-registry.yaml`)
- [ ] T5.2 — Schema: agency-id, ConMon contact, delivery channel (Connect.gov folder / email / OSCAL feed), ATO date, ConMon agreement date
- [ ] T5.3 — Extend `conmon-aggregate.yml` to iterate registry and emit per-agency distribution receipts (HMAC-SHA256 signed, same chain as evidence bundles)
- [ ] T5.4 — Receipts land in `evidence/distribution/<agency-id>/<yyyy-mm>/`
- [ ] T5.5 — Registry schema validation added to CI gate
- [ ] T5.6 — Cross-reference to UIAO_132 §3.2 / §3.3

---

## Tier 2 — Before Qwilfish ships (2026-06-30)

### E3 · OPA version pre-flight in ScubaGear adapter *(IN PROGRESS)*
**Target:** 2026-05-15
**Risk:** OPA version skew in upstream ScubaGear runs silently corrupts UIAO drift detection inputs; ScubaGear #2075 will expose the version field once Qwilfish ships, and UIAO needs to consume it on day one.
**Tasks:**
- [x] T3.0 — Verify drift module exposes `DRIFT_PROVENANCE` constant (`src/uiao/governance/drift.py:56`)
- [x] T3.0a — Confirm `scuba.yaml` has no OPA pin today (`src/uiao/canon/data/vendor-overlays/scuba.yaml:131`)
- [x] T3.0b — Confirm `normalize_scuba.py` hardcodes `tool_version` (`src/uiao/adapters/scuba/ir/normalize_scuba.py:302`)
- [x] T3.1 — Add `opa_version_minimum` pin to `scuba.yaml` under `uiao_extensions` *(PR 1)*
- [x] T3.2 — Extend `normalize_scuba.py` to preserve ScubaGear top-level metadata envelope (ToolVersion, OpaVersion when present, AssessmentDate) instead of discarding it — *(PR 1: `discover_scuba_input` / `_load_single_file` now return a 3-tuple with source_metadata; envelope surfaces in `assessment_metadata.source_envelope`; `tool_version` now reflects real `ToolVersion` when present, falling back to `ScubaGear-normalized` for backward compat)*
- [x] T3.5 — Run full scuba test suite (`test_scuba_transform_plane.py`, `test_scuba_transformer_determinism.py`, `test_scubagear_adapter.py`) — 59/59 passing after PR 1
- [x] T3.3 — Pre-flight check: if OPA version is absent, emit DRIFT-PROVENANCE warning; if below pin, emit DRIFT-PROVENANCE unauthorized classification *(PR 2: `_preflight_opa_provenance` + `_load_scuba_overlay` + `_parse_version` in `normalize_scuba.py`; result attached to `assessment_metadata.provenance_preflight`)*
- [x] T3.4 — Unit tests in `tests/test_normalize_scuba_provenance.py` — five status paths (ok / missing / below_pin / unparseable / skipped) plus integration tests via `normalize_scuba` *(PR 2: 21 new tests, 80/80 green)*
- [ ] T3.6 — Post Response C on cisagov/ScubaGear #2075 citing the implementation *(after PR 2 merges)*

### E2 · ScubaGear release tracking + mapping drift CI gate
**Target:** 2026-06-15 (two weeks before Qwilfish)
**Risk:** When Qwilfish lands new SECURITYSUITE policy IDs, UIAO's current SCUBA_TO_KSI_MAP (22 SECURITYSUITE entries already present at `scubagear_adapter.py:131-154`) will either miss new IDs or carry stale ones; Risk G-1 in UIAO_002 documents this failure mode.
**Correction from external analysis:** SECURITYSUITE is *already* populated in `SCUBA_TO_KSI_MAP` (22 entries, lines 131-154) — the "pre-populate now" sub-task is **done**. Remaining work is the release tracker and upstream diff.
**Tasks:**
- [ ] T2.1 — Create `.github/workflows/scubagear-upstream-track.yml` — watches cisagov/ScubaGear releases feed
- [ ] T2.2 — On new tag, diff ScubaResults JSON schema against pinned golden fixture
- [ ] T2.3 — Run `uiao scuba transform` against golden fixture; fail the gate on new unmapped KSI IDs
- [ ] T2.4 — Auto-open canon-change issue listing new policies + inferred NIST control family
- [ ] T2.5 — When Qwilfish ships, reconcile shipped SECURITYSUITE IDs against the 22 pre-populated entries; update map if vendor IDs differ
- [ ] T2.6 — Update UIAO_002 Appendix C with any reconciliation delta

---

## Tier 3 — Before Notice 0009 deadlines (2027-04-01 / 2027-06-01)

### E8 · Pathway-1 (VDR/CCM BIR) migration readiness gates
**Target:** 2027-02-15 (45-day buffer before CCM BIR deadline)
**Risk:** Notice 0009 mandates Pathway-1 by 2027-06-01 regardless of whether RFC-0026 ever formally compels migration; ADR-043 currently places UIAO on Pathway 2.
**Tasks:**
- [ ] T8.1 — Add Notice 0009 deadlines to ADR-043 enforcement timeline
- [ ] T8.2 — Create `vdr_adapter.py` skeleton in `src/uiao/adapters/` (stub, registered in `adapter-registry.yaml` with `status: reserved`)
- [ ] T8.3 — Create `ccm_bir_adapter.py` skeleton (same pattern)
- [ ] T8.4 — Add 90-day pre-deadline readiness check to `conmon-aggregate.yml` that opens a governance issue if migration hasn't started
- [ ] T8.5 — Update UIAO_132 §2.4 / §3.4 with migration milestone dates

---

## Tier 4 — High-value, softer deadline

### E4 · PIM-for-Groups escalation gap (ScubaGear #2072) as agency-specific desired state
**Target:** 2026-08-31
**Risk:** MS.AAD.7.4v1 maps to AU-6 in SCUBA_TO_KSI_MAP but the password-reset escalation path via PIM for Groups actually implicates AC-2 / AC-6; ScubaGear baseline doesn't yet warn. This is exactly the category UIAO's agency-specific desired-state layer exists for.
**Tasks:**
- [ ] T4.1 — Add entry to `gcc-boundary-gap-registry.yaml` documenting the PIM-for-Groups escalation risk
- [ ] T4.2 — Create desired-state rule (Rego or KSI supplemental) evaluating whether PIM-for-Groups is active on any group with password-reset permissions for privileged accounts
- [ ] T4.3 — Wire rule to `entra_policy_targeting.py` adapter
- [ ] T4.4 — Register as DRIFT-AUTHZ-class finding
- [ ] T4.5 — Document in UIAO_132 as an agency-specific-above-minimum example

### E6 · ATO onboarding workflow (depends on E5)
**Target:** 2026-12-15
**Risk:** acloudcj's RFC-0026 comment flagged ambiguity about when the collaborative ConMon obligation triggers for new agency ATOs; UIAO needs an auditable onboarding trail.
**Tasks:**
- [ ] T6.1 — Extend `src/uiao/onboarding/` with `ato-onboarding` workflow
- [ ] T6.2 — Accept new agency ATO event (manual trigger initially)
- [ ] T6.3 — PR-with-review flow to append to `agency-customer-registry.yaml` (requires E5)
- [ ] T6.4 — Welcome packet to designated ConMon contact (Connect.gov path + OSCAL feed URL)
- [ ] T6.5 — Auto-add to next monthly meeting invite

---

## Tier 5 — Needs design before code

### E7 · Scan redaction pipeline *(Design pending — ADR required)*
**Target:** 2026-09-30 (draft ADR) / 2026-12-31 (implementation)
**Risk:** RFC-0026 traditional pathway (UIAO's path per ADR-043) requires monthly distribution of OS/DB/web/container scans to all agency customers; raw unredacted scans in a GCC Moderate tenant are operationally impractical and broaden attack surface (CSP-AB / cb-axon thread).
**Tasks:**
- [ ] T7.1 — Draft new ADR: *Scan artifact redaction policy for multi-agency distribution*
- [ ] T7.2 — Define redaction profile — preserve: risk level, control family, CSP tracking ID, finding state; remove: plugin IDs, CVE identifiers, exploit path details
- [ ] T7.3 — `evidence/raw/` (restricted — 3PAO + FedRAMP corrective action only)
- [ ] T7.4 — `evidence/distribution/<agency-id>/` (redacted)
- [ ] T7.5 — Align principles with VDR-RPT-NID responsible-disclosure language

---

## Forum response tracker

| # | Venue | Status | Gating on |
|---|---|---|---|
| A | FedRAMP Community #130 | ⏸ Blocked — claims E7 + meeting spec that don't exist yet | E5, E7 land |
| B | cisagov/ScubaConnect #27 | ⏳ Pending one OSCAL version fact-check in `adapter_to_oscal.py` | Fact-check pass |
| C | cisagov/ScubaGear #2075 | ⏳ Ready after E3 | E3 complete |
| D | cisagov/ScubaGear (new issue — policy manifest) | ⏳ Queue for ~1 week after C | Response C posted |

**Posting order:** C → D → A (refined) → B (updated).

---

## Corrections log (vs. external analysis)

| Claim | Reality |
|---|---|
| "35 adapters in `adapter-registry.yaml`" | 8 adapters (scubagear, vuln-scan, stig-compliance, patch-state, intune, pki-ca, siem, uiao-git-server) |
| "163 cryptographically signed KSIs" | 166 YAML files at `src/uiao/rules/ksi/`; signing status unverified |
| "UIAO_200 defines 5 active drift classes" | Six literals exist in `drift.py:47-53`; substrate-manifest.yaml actively scans 2 (DRIFT-SCHEMA, DRIFT-PROVENANCE); DRIFT-AUTHZ/IDENTITY classifiers exist but not yet wired into the manifest |
| "Pre-populate SECURITYSUITE in SCUBA_TO_KSI_MAP" | Already populated (22 entries in `scubagear_adapter.py:131-154`) — remaining work is Qwilfish reconciliation |
| "Drift lives in `drift/` subpackage" | Lives at `src/uiao/governance/drift.py` + `drift_engine.py` |
| `scuba.yaml` OPA pin | No pin exists today; E3 adds one |

---

## Change control

This roadmap is a working document. Material changes (tier moves, date slips crossing enforcement milestones, new enhancement additions) should land via PR with a line in this file's changelog.

### Changelog
- 2026-04-23 — Initial draft (W.M.) covering E1–E8 + forum response plan.
