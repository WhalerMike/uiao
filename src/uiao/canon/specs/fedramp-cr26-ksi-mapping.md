---
document_id: UIAO_137
title: "Local KSI Rules ↔ FedRAMP CR26 KSI Catalog Mapping"
version: "0.2"
status: Draft
owner: "Michael Stratton"
created_at: "2026-05-10"
updated_at: "2026-08-06"
mas-scope: "in-scope"
---

# UIAO_137 — Local KSI Rules ↔ FedRAMP CR26 KSI Catalog Mapping

> **Status: DRAFT.** Closes the catalog-version-dependent enumeration
> gap that [`UIAO_133 §1`](./fedramp-20x-integration.md) Out-of-scope
> item 3 explicitly defers:
>
> > *individual KSI IDs are catalog-version-dependent and tracked in
> > companion mappings as the catalog stabilizes.*
>
> This is the companion mapping for the CR26 catalog snapshot pinned
> at [`fedramp-cr26/snapshot/c31eb04…/`](../compliance/reference/fedramp-cr26/snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/).
> Status stays DRAFT until governance review accepts the per-rule
> assignments below.

UIAO_137 sits beside [`UIAO_132`](./fedramp-rfc-0026-ca7-integration.md)
(FedRAMP RFC-0026 CA-7 Pathway Integration) and
[`UIAO_133`](./fedramp-20x-integration.md) (FedRAMP 20x Integration).
Where UIAO_133 covers KSI **theme** emission (KSI-CNA, KSI-MLA, …),
UIAO_137 covers **per-control mapping** at the level of CR26
theme-prefixed control IDs (KSI-IAM-ELP, KSI-MLA-LET, …).

The machine-readable companion is
[`src/uiao/adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml`](../../adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml).
The substrate consumes that file via the `fedramp-cr26-catalog`
conformance adapter (ADR-061 D3); the markdown table below is its
human-readable form, and the two must stay in lockstep (drift surfaced
via the existing CI tests).

---

## 1. Scope

UIAO_137 covers three operational concerns:

1. **Per-rule mapping** — for each local `ksi/rules/KSI-NNN.yaml`
   (full `src/uiao/...` path prefix elided to avoid substrate-drift
   false-flag on the `NNN` placeholder pattern), record the set of
   CR26 theme-prefixed control IDs the substrate asserts that rule
   satisfies.
2. **Reverse coverage** — record which CR26 controls have at least one
   local rule pointing at them, and which do not.
3. **Gap labelling** — name the CR26 themes for which uiao does not yet
   carry a local rule, so the gap is visible in canon rather than
   implicit.

Out of scope for this document:

- CR26 controls outside the `KSI` group (FedRAMP CR26 also defines an
  `FRR` group — FedRAMP Requirements and Recommendations — with 15
  subgroups; FRR mapping is a separate UIAO_NNN companion when it
  matters).
- Tailoring the CR26 20x profile shell into a Low / Moderate / High
  baseline. The shell at the pinned snapshot is exactly that — a
  shell — and tailoring lives under
  `canon/compliance/reference/gcc-moderate-boundary-assessment/`.
- New local KSI rules to close the gaps. Adding rules is downstream
  work (per AGENTS.md Operating Rules: "New CLI commands ship with
  happy-path + failure-mode tests in the same PR" — same discipline
  applies to KSI rules).

---

## 2. Provenance pin

| Field | Value |
|---|---|
| CR26 snapshot SHA | `c31eb04c082d6d578a26a00de9a482707ab7a00c` |
| Catalog UUID at this SHA | `092dc25a-18ca-51d9-ab85-744e5435405e` |
| Catalog metadata.version | `0.1.0` |
| KSI themes present | 10 (KSI-CMT · KSI-CNA · KSI-CED · KSI-IAM · KSI-INR · KSI-MLA · KSI-PIY · KSI-RPL · KSI-SVC · KSI-SCR) |
| KSI controls present | 46 |
| Local KSI rules in `src/uiao/ksi/rules/` | 29 (KSI-001 … KSI-029; KSI-011…014 are KSI-CMT scaffolds per ADR-111) |

This mapping is **valid only against this pinned SHA**. When the pin
advances per ADR-061 D2, this document and the YAML companion are
updated in lockstep with the snapshot-advance PR; the
`fedramp-cr26-catalog` adapter emits `DRIFT-PROVENANCE` if a CR26 ID
cited below no longer resolves in the new snapshot.

---

## 3. Forward mapping — local KSI rule → CR26 controls

Each row asserts: *the local rule, when it passes, contributes evidence
toward the cited CR26 controls.* A row with multiple CR26 IDs means the
local rule covers more than one CR26 axis (typical for cross-cutting
controls like Conditional Access). Assignment confidence is `high` when
the local rule's NIST 800-53 mapping aligns directly with the CR26
control's intent; `medium` when the rule is necessary-but-not-sufficient
for the CR26 control.

| Local rule | Local title | NIST 800-53 (local) | CR26 control(s) | Confidence | Rationale |
|---|---|---|---|---|---|
| KSI-001 | Multi-Factor Authentication Enforcement | IA-2, IA-2(1), IA-2(11) | KSI-IAM-APM · KSI-IAM-SNU | high | APM (passwordless / modern auth) is MFA's CR26 expression; SNU covers non-user (service) accounts that must authenticate without interactive MFA. |
| KSI-002 | Legacy Authentication Disabled | AC-17, IA-5 | KSI-IAM-APM | high | Disabling legacy is the negative side of enforcing modern auth — same control axis. |
| KSI-003 | Global Administrator Count | AC-2(1), AC-6 | KSI-IAM-ELP · KSI-IAM-AAM | high | ELP (Least Privilege) is the direct match; AAM (Automating Account Management) covers the lifecycle that keeps the count bounded. |
| KSI-004 | External Forwarding Restrictions | SC-7, SC-8 | KSI-SVC-SNT · KSI-SVC-RUD | medium | SNT (Securing Network Traffic) covers the egress boundary; RUD (Removing Unwanted Data) covers data-leak intent. Together they bracket the rule. |
| KSI-005 | Mailbox Auditing Enabled | AU-2, AU-12 | KSI-MLA-LET · KSI-MLA-RVL | high | LET (Logging Event Types) is the emission side; RVL (Reviewing Logs) is the review side. AU-2/AU-12 cover both. |
| KSI-006 | External Sharing Restrictions | AC-3, AC-21 | KSI-IAM-ELP · KSI-SVC-RUD | medium | ELP covers the access-control side; RUD covers the data-egress side. |
| KSI-007 | Safe Links Protection | SI-3, SI-4 | KSI-SVC-VCM · KSI-CNA-RNT | medium | VCM (Validating Communications) is the URL-validation control; RNT (Restricting Network Traffic) covers the egress-block side when a link is bad. |
| KSI-008 | Safe Attachments Protection | SI-3, SI-4 | KSI-SVC-VCM · KSI-CNA-MAT | medium | VCM covers attachment scanning; MAT (Minimizing Attack Surface) covers reducing the live-payload paths. |
| KSI-009 | Conditional Access Enforcement | AC-3, AC-17 | KSI-IAM-ELP · KSI-IAM-JIT · KSI-IAM-SUS | high | CA is the policy-enforcement layer for least privilege, just-in-time access, and suspicious-activity response — three IAM axes. |
| KSI-010 | Data Loss Prevention Enforcement | MP-4, SC-28 | KSI-SVC-RUD | high | RUD (Removing Unwanted Data) is the direct CR26 expression of DLP. |
| KSI-011 | Change Logging and Monitoring | CM-3, AU-6 | KSI-CMT-LMC | low (scaffold) | LMC requires modifications to be logged and monitored; scaffold targets substrate change-log completeness. Evidence binding pending CR26 VER. |
| KSI-012 | Immutable Redeployment over Direct Modification | CM-2, SA-10 | KSI-CMT-RMV | low (scaffold) | RMV favors version-controlled redeploy over in-place mutation; scaffold targets deployment provenance. Evidence binding pending CR26 VER. |
| KSI-013 | Change-Procedure Effectiveness Review | CM-3, CA-7 | KSI-CMT-RVP | low (scaffold) | RVP requires persistent review of change-management effectiveness; scaffold targets the ConMon review cadence. Evidence binding pending CR26 VER. |
| KSI-014 | Automated Validation Throughout Deployment | CM-3(2), SA-11 | KSI-CMT-VTD | low (scaffold) | VTD requires automated testing/validation across deployment; scaffold targets deployment-validation telemetry. Evidence binding pending CR26 VER. |
| KSI-015 | Supply Chain Risk Mitigation | SR-2, SR-3, PM-30 | KSI-SCR-MIT | high | SBOM/VDR/VEX tooling plus a CI-blocking dependency-scan gate cover identify, review, and mitigate; PM-30 is satisfied by organizational risk-appetite/charter evidence. |
| KSI-016 | Supply Chain Monitoring | SR-6, SR-8, CA-7 | KSI-SCR-MON | high | Vendor PSIRT/advisory subscriptions satisfy CR26's contractual-notification path directly; CI-gate SBOM-diff scanning on every PR adds the active-monitoring side. |
| KSI-017 | Endpoint Inventory Visibility | CM-8, RA-5, RA-5(5) | KSI-PIY-GIV | high | Authenticated vulnerability-scan coverage across every managed endpoint continuously populates the inventory GIV requires. |
| KSI-018 | Endpoint Entity State Resolution | CM-7, CM-7(1), CM-8 | KSI-PIY-RES | high | Automated policy enforcement gives on-demand resolution of any endpoint's current configuration and compliance posture. |
| KSI-019 | Endpoint Inventory State Recording | CM-8, RA-5, RA-5(2) | KSI-PIY-RIS | high | Continuous scanning tracks device onboard/offboard/reconfigure events as a change-logged inventory record. |
| KSI-020 | SDLC Security Review | SA-11, SA-15, SA-8, SR-3 | KSI-PIY-RSD | high | CI-gate SBOM/provenance scanning and container signing at build time is the automated SDLC security review RSD requires. |
| KSI-021 | Privileged Access via Defined Paths | IA-11, AC-11, AC-12, AC-6(5) | KSI-PIY-RVD | high | PIM just-in-time activation plus a PAW architecture is the single, monitored, identity-anchored privileged-access path RVD requires. |
| KSI-022 | Cybersecurity Training Effectiveness Review | AT-2, AT-2(1), AT-2(2), AT-3, AT-3(3), AT-3(5), AT-4, CP-3, IR-2 | KSI-CED-RAT | high | Role-based training matrices plus a machine-readable completion-threshold record satisfy RAT's persistent-review-across-dimensions requirement. |
| KSI-023 | Incident After Action Report Generation | IR-3, IR-4, IR-4(1), IR-8, CP-4 | KSI-INR-AAR | high | SOAR closed-loop incident records carry a mandatory AAR artifact; tabletop exercises independently produce a signed, lessons-learned AAR. |
| KSI-024 | Incident Response Procedure Effectiveness Review | IR-4, IR-6, IR-6(1), IR-6(3), IR-7, IR-7(1), IR-8, IR-8(1), SI-4(5) | KSI-INR-RIR | high | SOAR playbook review metrics plus the annual IR test's procedure-effectiveness finding log satisfy persistent review directly. |
| KSI-025 | Past Incident Pattern Review | IR-3, IR-4, IR-4(1), IR-5, IR-8 | KSI-INR-RPI | high | Continuous threat-intel correlation and hunting queries over the closed-incident corpus is the pattern-and-previously-unidentified-vulnerability review RPI requires. |
| KSI-026 | Backup Alignment with Recovery Objectives | CM-2(3), CP-6, CP-9, CP-10, CP-10(2), SI-12 | KSI-RPL-ABO | high | Backup review is anchored to BIA-derived RTO/RPO rather than an independent backup schedule — the direct ABO expression. |
| KSI-027 | Recovery Plan Alignment with Objectives | CP-2, CP-2(1), CP-2(3), CP-4(1), CP-6, CP-6(1), CP-6(3), CP-7, CP-7(1), CP-7(2), CP-7(3), CP-8, CP-8(1), CP-8(2), CP-10, CP-10(2) | KSI-RPL-ARP | high | The Contingency Plan's BIA-anchored objectives plus its technical recovery components are ARP's plan-to-objective alignment directly. |
| KSI-028 | Recovery Objective Review | CP-2(3), CP-10 | KSI-RPL-RRO | high | Annual BIA review with mission-owner sign-off is the persistent RTO/RPO re-validation RRO requires. |
| KSI-029 | Recovery Capability Testing | CP-2(1), CP-2(3), CP-4, CP-4(1), CP-6(1), CP-9(1), CP-10, IR-3, IR-3(2) | KSI-RPL-TRC | high | Tabletop exercises plus annual backup-restore testing against defined objectives is TRC's capability-testing requirement directly. |

Coverage summary:

- 29 of 29 local rules have at least one CR26 mapping (100% forward coverage).
- 4 of 29 are `medium` confidence (all in KSI-001…010) — these are the
  rows most likely to shift in governance review and should be
  re-examined when CR26 issues control-level intent statements.
- 4 of 29 are `low` confidence **scaffolds** (KSI-011…014, KSI-CMT theme):
  the rule files exist and carry `Status: scaffold`, but their evidence
  bindings are not yet evaluable. They finalize when the CR26 VDR/VER
  evidence contract publishes (ADR-111 ratification gate; FINDING-PGM-003 §4).
- The remaining 15 (KSI-015…029, added since this document's last
  narrative update) are all `high` confidence — each binds to a named
  evidence-contract slot (`slot-04` through `slot-08`) rather than an
  asserted mapping.

---

## 4. Reverse coverage — CR26 themes the local corpus addresses

The 29 local rules touch **32 of the 46** CR26 KSI controls
(~70%). The table below lists every CR26 theme and the local rules
that contribute to it.

| CR26 theme | Title | Controls | Covered by local rules | Gap |
|---|---|---:|---|---|
| KSI-CED | Cybersecurity Education | 1 | KSI-022 (RAT) | 0 controls — **theme fully covered** |
| KSI-CMT | Change Management | 4 | KSI-011 (LMC), KSI-012 (RMV), KSI-013 (RVP), KSI-014 (VTD) — all `scaffold` | 0 controls — **theme covered by scaffolds** (not yet evaluable; ADR-111) |
| KSI-CNA | Cloud Native Architecture | 8 | KSI-007 (RNT), KSI-008 (MAT) | 6 controls — DFP · EIS · IBP · OFA · RVP · ULN |
| KSI-IAM | Identity and Access Management | 6 | KSI-001 (APM, SNU), KSI-002 (APM), KSI-003 (ELP, AAM), KSI-006 (ELP), KSI-009 (ELP, JIT, SUS) | 0 controls — **theme fully covered** |
| KSI-INR | Incident Response | 3 | KSI-023 (AAR), KSI-024 (RIR), KSI-025 (RPI) | 0 controls — **theme fully covered** |
| KSI-MLA | Monitoring, Logging, and Auditing | 5 | KSI-005 (LET, RVL) | 3 controls — ALA · EVC · OSM |
| KSI-PIY | Policy and Inventory | 5 | KSI-017 (GIV), KSI-018 (RES), KSI-019 (RIS), KSI-020 (RSD), KSI-021 (RVD) | 0 controls — **theme fully covered** |
| KSI-RPL | Recovery Planning | 4 | KSI-026 (ABO), KSI-027 (ARP), KSI-028 (RRO), KSI-029 (TRC) | 0 controls — **theme fully covered** |
| KSI-SVC | Service Configuration | 8 | KSI-004 (SNT, RUD), KSI-006 (RUD), KSI-007 (VCM), KSI-008 (VCM), KSI-010 (RUD) | 5 controls — ACM · ASM · EIS · PRR · VRI |
| KSI-SCR | Supply Chain Risk | 2 | KSI-015 (MIT), KSI-016 (MON) | 0 controls — **theme fully covered** |

**Themes uiao currently has zero local rules for: 0 of 10.** The five
themes this document previously named as zero-coverage — KSI-CED,
KSI-INR, KSI-PIY, KSI-RPL, KSI-SCR — are now fully covered by
KSI-015…029, added since this document's narrative was last current
(§3). KSI-CMT exited zero-coverage earlier still, 2026-06-18, with the
KSI-011…014 scaffolds per ADR-111 / FINDING-PGM-003 §4 — the rules
exist but are not yet evaluable.

The remaining true gap is **14 controls across three themes**:
KSI-CNA (6 of 8 open), KSI-MLA (3 of 5 open), KSI-SVC (5 of 8 open) —
plus the 4 KSI-CMT controls mapped but not yet evaluable pending the
CR26 VDR/VER evidence contract. Where the original local KSI corpus
(KSI-001…010) was authored against the SCuBA M365 assessment surface
and naturally clustered on identity, mail, sharing, and DLP, KSI-015…029
closed the *process and lifecycle* themes — training, incident
response, recovery planning, supply chain, endpoint inventory — each
bound to its own non-SCuBA evidence source (SOAR playbooks, BIA/CP
review records, SBOM/VDR tooling, Defender vulnerability-management
scans). What remains open is deeper *infrastructure-configuration*
ground: CNA's cloud-native architecture controls (data-flow protection,
encryption-in-storage, immutable/bootstrapping practices, unsupported
component tracking), MLA's alerting/event-correlation/monitoring depth
beyond the mailbox-audit surface KSI-005 covers, and SVC's asset/
configuration/patch-response controls beyond the network-egress and
content-validation surface KSI-004/007/008/010 cover. Closing these,
and making the KSI-CMT scaffolds evaluable, is downstream work tracked
in FINDING-PGM-003 §4 and gated on the CR26 VDR/VER evidence contract.

---

## 5. Operational consequences

1. **`fedramp:ksi-mapping-source` props** emitted by substrate code (per
   `UIAO_133 §2.1`) may now resolve to CR26 control IDs by way of
   this document and the YAML companion. The authoritative source
   remains the local rule (and the UIAO_NNN row that names it); the
   CR26 ID is a navigational aid, not the authority — per ADR-061 D1.
2. **Adapter drift surface.** The `fedramp-cr26-catalog` adapter
   (ADR-061 D3) consumes
   `src/uiao/adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml`
   and emits `DRIFT-PROVENANCE` when a CR26 ID cited there is not
   present in the pinned snapshot. This is the test that keeps this
   document honest as the catalog evolves.
3. **Gap labelling drives roadmap.** The 14 CR26 controls without a
   local rule (§4) are the candidates for new KSI rule authoring. Each
   new rule lands with its own row added to §3 above.

---

## 6. Open questions (for governance review)

1. The 4 `medium`-confidence rows in §3 — should they be split into
   separate rules to clarify the contribution boundary, or kept
   composite with explicit `confidence: medium` carried into the
   emitted prop?
2. Should the local `KSI-NNN.yaml` files gain a `cr26_mapping:` key
   that pins the CR26 IDs at the rule level, mirroring the table in
   §3? That would localize the mapping next to the rule but introduces
   a maintenance edge (two places to update). Current draft: keep the
   mapping centralized here and in the YAML companion; revisit if the
   rule corpus exceeds ~30 entries.
3. The KSI-SCR theme (supply chain) has zero coverage and FedRAMP
   intent here is rapidly evolving. Do we wait for upstream stability
   or seed a placeholder local rule keyed to the existing
   `compliance/reference/sbom*/` tooling?

---

## 7. References

- [`ADR-061`](../adr/adr-061-fedramp-cr26-catalog-vendoring.md) — CR26
  catalog vendoring policy
- [`ADR-106`](../adr/adr-106-fedramp-20x-integration.md) — FedRAMP 20x
  integration decision (this document previously cited "ADR-047," a
  different, unrelated ADR — corrected)
- [`UIAO_133`](./fedramp-20x-integration.md) §1 — gap this document
  closes; §2 — emission contract this mapping feeds
- [`UIAO_132`](./fedramp-rfc-0026-ca7-integration.md) — CA-7
  continuous-monitoring pathway
- [`src/uiao/adapters/fedramp_cr26_catalog/`](../../adapters/fedramp_cr26_catalog/) — adapter that consumes this mapping
- [`src/uiao/ksi/rules/`](../../ksi/rules/) — local KSI rule corpus
- [`fedramp-cr26/snapshot/c31eb04…/`](../compliance/reference/fedramp-cr26/snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/) — pinned snapshot
- Upstream: <https://github.com/Palladium-Innovations/fedramp-cr26-oscal>
