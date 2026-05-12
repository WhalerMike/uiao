# 01 — State of Tree: HRIT Productization Surface

> **Status:** Inbox draft. Not canon. Authored 2026-05-06 against
> `origin/main` HEAD `92ea7615`.
>
> **Renumber note (2026-05-11):** The "Next UIAO_NNN: UIAO_143" claim in
> the *Free identifier slots* section below was correct at the time of
> writing but has since been superseded. UIAO_143 was claimed by SCIM
> RFC Core Schema (PR #342). The HRIT productization spec moved to
> **UIAO_144**. The ADR-058 candidate identifier in the same section was
> also renumbered to **ADR-065** (slot collision with Microsoft Purview
> coverage ADR-058 accepted 2026-05-07). Body retained verbatim for
> historical record.

## Doctrine layer — COMPLETE

| Document | ID | Status | Path |
|---|---|---|---|
| ADR-054 | Single-ATO Reciprocity Model | Accepted 2026-05-04 | `src/uiao/canon/adr/adr-054-single-ato-reciprocity.md` |
| UIAO_140 | Single-ATO Reciprocity Model spec | Current | `src/uiao/canon/specs/single-ato-reciprocity-model.md` |
| Spec2-D6.1 | Federal HRIT Integration Runbook v0.1 | Draft | `src/uiao/canon/specs/Spec2-D6.1-FederalHRITIntegrationRunbook.md` |
| UIAO_112 | Multi-Tenant Isolation v1.1 | Amended by ADR-054 | `src/uiao/canon/specs/governance.md` |
| UIAO_141 | Customer Identity Model | Current | `src/uiao/canon/specs/customer-identity-model.md` |
| UIAO_142 | Customer KYC Runbook | Current | `src/uiao/canon/specs/customer-kyc-runbook.md` |
| ADR-051 | SAML Trust Anchor | Accepted | `adr-051-saml-trust-anchor.md` |
| ADR-052 | PIV / USAccess Adapter | Accepted (reserved slot) | `adr-052-piv-usaccess-adapter.md` |
| ADR-053 | OPM Azure APIM Adapter | Accepted (reserved slot) | `adr-053-opm-azure-apim-adapter.md` |
| ADR-056 | Login.gov Federation Activation | Accepted (Stage 2) | `adr-056-login-gov-activation-contract.md` |

Twelve federal HRIT systems are concretized in Spec2-D6.1 §2 (NFC EmpowHR,
Treasury HR Connect, DCPDS, etc.), giving the runtime a real target list.

## Schema layer — FOUNDATION IN PLACE

| Schema | Path | State |
|---|---|---|
| Reciprocal-Consumption Registry schema | `src/uiao/schemas/reciprocal-consumption/registry.schema.json` | Active, CI-validated. Required `legal_basis` field enforces ADR-055 (privacy-act-sorn-routine-use, cmppa-matching-agreement, statute, customer-consent, interagency-mou). |
| Reciprocal-Consumption Registry data | `src/uiao/canon/reciprocal-consumption-registry.yaml` | Initialized empty 2026-05-05; awaiting first entitlement entry post Privacy Officer sign-off. |
| Evidence Graph (UIAO_113) | `src/uiao/canon/specs/graph-schema.md` | v1.1 — customer-side nodes (CIR, KYC events, reciprocity-attribute-records). **Missing: `ato-decision` and `reciprocity-record` ATO-level node types.** |
| Reciprocity-Record schema | (does not exist) | Phase 0 stub; Batch A WS-A5 fills. |

## Runtime layer — SPARSE; explicitly deferred

ADR-054 §Implementation table lines 157–164 names the deferrals.

| Capability | Doctrine source | Tree state | Gap |
|---|---|---|---|
| Reciprocity-record artifact emission | UIAO_140 §7 line 53 ("one per consuming agency") | None | `src/uiao/oscal/reciprocity_record.py` does not exist |
| `ato-decision` event node type | UIAO_140 §6 lines 102–108 | Not in UIAO_113 v1.1 | Needs UIAO_113 v1.2 amendment |
| Configuration-latitude drift enforcement | UIAO_140 §5 line 91 | No CQL query, no drift rule | DRIFT-SCHEMA finding when tenant configuration not in SSP latitude table |
| 30-day draft / 45-day final SSP cadence | ADR-054 Q&A #44 / UIAO_140 §4 lines 63–65 | Orchestrator has no timer | Needs ConMon SLA tooling |
| 30-day reauthorization SLA | UIAO_140 §4 line 75 / ADR-054 Consequences line 131 | ConMon does not enforce | Needs cadence validator |
| Per-consuming-agency reciprocity bundle | Spec2-D6.1 §9 line 269 | No aggregation | Depends on emitter |
| Reciprocity acceptance CLI | Spec2-D6.1 §7 line 239 (`uiao app onboard-federal`) | No command | Needs `cli/reciprocity.py` (or extend existing sub-app) |
| Per-agency component-definition / scoped-assessment-results | UIAO_140 §7 line 132 | Generator emits one platform-scope set | Per-agency projection missing |
| Tests | ADR-054 line 163 | None | Happy-path + lapsed-ATO + configuration-latitude drift |

## Federation block touchpoints

| ADR | Function | Runtime | Phase 0 dependency? |
|---|---|---|---|
| ADR-051 | SAML 2.0 trust anchor (OPM Entra federation) | Doctrine only | **Yes, foundational.** Consuming agencies authenticate via SAML assertions per Solicitation Clause 1752.224-70(c). UIAO observes; OPM Entra issues. |
| ADR-052 | PIV / USAccess conformance adapter | Reserved slot | **Yes (delayed phase).** UIAO observes PIV cert chains, never issues. Sibling Spec2-D6.2 noted for DoD CAC. |
| ADR-053 | OPM Azure APIM gateway | Reserved slot | **Yes, critical.** Solicitation Appendix B (pp. 82, 84) mandates all OPM integrations through APIM. |
| ADR-056 | Login.gov federation | Reserved (Stage 2) | **No.** Citizen-side; out of scope for HRIT (workforce). Required for KYC block, not this theme. |

Phase 0 of HRIT productization treats ADR-051/052/053 as **observable
upstream contracts** — UIAO consumes their assertions, never issues them.

## Path collision check — all clear

| Proposed path | Exists? | Verdict |
|---|---|---|
| `src/uiao/adapters/modernization/hrit/` | No | Safe |
| `src/uiao/cli/reciprocity.py` | No | Safe |
| `src/uiao/oscal/reciprocity_record.py` | No | Safe (matches ADR-054 line 162 naming) |
| `src/uiao/schemas/reciprocity-record/` | No | Safe |
| `tests/test_reciprocity_*.py` | No | Safe |
| `tests/test_hrit_*.py` | No | Safe |
| `examples/hrit/` | No | Safe |
| `docs/docs/22_HRITProductization.qmd` | No | Safe (sequence ends at 21) |

## Free identifier slots (historical — see renumber note at top)

- **Next ADR:** ADR-058 (ADR-057 used by `adr-057-application-aware-networking-and-token-bound-transport.md` on this branch) — **superseded:** renumbered to ADR-065 (see top note)
- **Next UIAO_NNN:** UIAO_143 (highest allocated is UIAO_142; reserved range 100–199 has 56 slots free) — **superseded:** UIAO_143 now SCIM RFC; HRIT spec is UIAO_144
- **Next docs/docs/:** `22_HRITProductization.qmd`

## What's deferred but documented

ADR-054 §Implementation lines 157–164 explicitly defers:
1. `oscal/reciprocity_record.py` emitter
2. Per-agency reciprocity tests (happy-path + lapsed-ATO)
3. Evidence graph v1.2 node types
4. ConMon SLA enforcement
5. Reciprocity acceptance CLI

**This is the v0.6.0 runtime work.** The Batch A plan in `03-batch-plan.md`
is exactly these deferrals plus their schema, fixtures, docs, and KSI rules.
