---
document_id: UIAO_137
title: "Local KSI Rules ↔ FedRAMP CR26 KSI Catalog Mapping"
version: "0.1"
status: Draft
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-10"
updated_at: "2026-05-10"
boundary: "GCC-Moderate"
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

1. **Per-rule mapping** — for each local `src/uiao/ksi/rules/KSI-NNN.yaml`,
   record the set of CR26 theme-prefixed control IDs the substrate
   asserts that rule satisfies.
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
| Local KSI rules in `src/uiao/ksi/rules/` | 10 (KSI-001 … KSI-010) |

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

Coverage summary:

- 10 of 10 local rules have at least one CR26 mapping (100% forward coverage).
- 4 of 10 are `medium` confidence — these are the rows most likely to
  shift in governance review and should be re-examined when CR26 issues
  control-level intent statements.

---

## 4. Reverse coverage — CR26 themes the local corpus addresses

The 10 local rules touch only **17 of the 46** CR26 KSI controls
(~37%). The table below lists every CR26 theme and the local rules
that contribute to it.

| CR26 theme | Title | Controls | Covered by local rules | Gap |
|---|---|---:|---|---|
| KSI-CMT | Change Management | 4 | none | **all 4 controls** — LMC · RMV · RVP · VTD |
| KSI-CNA | Cloud Native Architecture | 8 | KSI-007 (RNT), KSI-008 (MAT) | 6 controls — DFP · EIS · IBP · OFA · RVP · ULN |
| KSI-CED | Cybersecurity Education | 1 | none | **all 1 control** — RAT |
| KSI-IAM | Identity and Access Management | 6 | KSI-001 (APM, SNU), KSI-002 (APM), KSI-003 (ELP, AAM), KSI-006 (ELP), KSI-009 (ELP, JIT, SUS) | 0 controls — **theme fully covered** |
| KSI-INR | Incident Response | 3 | none | **all 3 controls** — AAR · RIR · RPI |
| KSI-MLA | Monitoring, Logging, and Auditing | 5 | KSI-005 (LET, RVL) | 3 controls — ALA · EVC · OSM |
| KSI-PIY | Policy and Inventory | 5 | none | **all 5 controls** — GIV · RES · RIS · RSD · RVD |
| KSI-RPL | Recovery Planning | 4 | none | **all 4 controls** — ABO · ARP · RRO · TRC |
| KSI-SVC | Service Configuration | 8 | KSI-004 (SNT, RUD), KSI-006 (RUD), KSI-007 (VCM), KSI-008 (VCM), KSI-010 (RUD) | 4 controls — ACM · ASM · EIS · PRR · VRI |
| KSI-SCR | Supply Chain Risk | 2 | none | **all 2 controls** — MIT · MON |

**Themes uiao currently has zero local rules for: 6 of 10** —
KSI-CMT · KSI-CED · KSI-INR · KSI-PIY · KSI-RPL · KSI-SCR.

These gaps are expected: the local KSI corpus was authored against
the SCuBA M365 assessment surface (ScubaGear) and naturally clusters
on identity, mail, sharing, and DLP. CR26 spans the full FedRAMP 20x
architecture, including change management, recovery, supply chain,
and policy/inventory — surfaces uiao has not yet wired to a SCuBA-style
evaluator. Closing these gaps is downstream work tracked separately.

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
3. **Gap labelling drives roadmap.** The 29 CR26 controls without a
   local rule are the candidates for new KSI rule authoring. Each new
   rule lands with its own row added to §3 above.

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
- [`ADR-047`](../adr/adr-047-fedramp-20x-integration.md) — FedRAMP 20x
  integration decision
- [`UIAO_133`](./fedramp-20x-integration.md) §1 — gap this document
  closes; §2 — emission contract this mapping feeds
- [`UIAO_132`](./fedramp-rfc-0026-ca7-integration.md) — CA-7
  continuous-monitoring pathway
- [`src/uiao/adapters/fedramp_cr26_catalog/`](../../adapters/fedramp_cr26_catalog/) — adapter that consumes this mapping
- [`src/uiao/ksi/rules/`](../../ksi/rules/) — local KSI rule corpus
- [`fedramp-cr26/snapshot/c31eb04…/`](../compliance/reference/fedramp-cr26/snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/) — pinned snapshot
- Upstream: <https://github.com/Palladium-Innovations/fedramp-cr26-oscal>
