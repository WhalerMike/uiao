---
adr_id: adr-088
title: "HR System of Record as the Authoritative Source for Organizational Placement"
status: ACCEPTED
decided: 2026-06-01
deciders: Michael Stratton
updated: 2026-06-01
next_review: 2026-12-01
review_trigger: A workforce-system-of-record vertical other than the federal OPM HRIT instantiation is onboarded; the inherited OU estate is proposed as a remediation target rather than a decommissioning target; ADR-003 (API-driven inbound provisioning) or ADR-035 (codebook binding) is revised
impact: 'Establishes that the workforce HR system of record is the authoritative upstream source for the assignment of persons to OrgTree nodes, and that the OrgTree change-request workflow is the governance gate over HR-supplied deltas rather than an independent origin of organizational truth. Resolves the unstated source question left open by the OrgPath Narrative (Book_02 Chapter 3, Book_03 Chapter 4) and the canonical OrgTree specification (UIAO_007). Establishes the doctrine that an inherited Active Directory OU estate that has drifted from the true organizational structure is overlaid by HR-sourced OrgPath and decommissioned, not realigned. Federal scope (OPM HRIT) is one vertical instantiation per ADR-085 and Spec2-D6.1; the source slot is swapped for a commercial HCM in other verticals without architectural change.'
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-088-hr-as-orgtree-truth-source.html
---

# ADR-088: HR System of Record as the Authoritative Source for Organizational Placement

## Status

**ACCEPTED** — 2026-06-01.

This ADR is doctrine. It names the upstream source of organizational truth and fixes how an inherited, drifted OU estate is treated during the transition to OrgTree and OrgPath. It does not change any runtime behavior, schema, or registry entry; it makes explicit a source relationship that the OrgPath substrate already assumes but never states.

## Context

The OrgPath substrate is built on a registry-and-attribute closed loop. OrgTree is the versioned, schema-validated registry of organizational structure; OrgPath is the validated attribute, derived from the registry, stamped on every identity and resource object ([UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md); Book_03 of the OrgPath Narrative). The narrative establishes two things very precisely and leaves a third unstated:

1. **The registry is the authority over the attribute.** Authority runs from OrgTree outward to the stamped OrgPath value; individual object edits are not authoritative (Book_02 Chapter 3, "The Hierarchy Itself Must Be a Governed Artifact").
2. **The change-request workflow governs registry mutation.** Renames, merges, moves, and archivals enter through a reviewed, version-controlled change request (Book_03 Chapters 2 and 4).
3. **What it does not say:** where the *content* of those change requests originates — who is the authoritative source for the fact that a given person now sits under a given node.

In a well-run enterprise that fact is not invented by a directory administrator. It is recorded first in the workforce **HR system of record** (HRIS / HCM) — the system that owns hire, position, reporting-line, cost-center, location, and separation events as a matter of business authority. Active Directory's Organizational Unit estate was, historically, a *downstream projection* of that truth that drifted over years of reorganizations, mergers, and ad-hoc container moves. The common end state — and the explicit premise of the OrgPath architecture — is an OU tree that no longer reflects the organization it was built to model (Book_02 Chapter 2; Book_04 Chapter 1, which requires "an authoritative description of the organization's own structure, independent of any current state in Active Directory").

Two questions therefore need a doctrinal answer, because both are load-bearing for every downstream consumer (dynamic groups per [ADR-036](adr-036-dynamic-group-provisioning.md), administrative units per [ADR-037](adr-037-admin-unit-provisioning.md), policy targeting per [ADR-039](adr-039-policy-targeting.md), the mover lifecycle per Spec2-D2.2):

- **Q1 — Source:** What is the authoritative upstream source that populates OrgTree's personnel placement, and what is the change-request workflow's role relative to it?
- **Q2 — Inheritance:** When the inherited OU estate has drifted from the true structure, does the transition *remediate* the OUs into alignment, or does it *overlay* the truth as an attribute and retire the OU estate?

ADR-003 already chose the *transport* for HR data — API-driven inbound provisioning via Microsoft Graph `bulkUpload`, HR-system-agnostic — but it does not assert the *doctrine* that HR is the authoritative source of organizational placement, nor does it speak to OU remediation. This ADR closes that gap.

## Decision

### D1. The HR system of record is the authoritative source for organizational placement

The workforce HR system of record is the authoritative upstream source for the assignment of a person to an OrgTree node, and for the identity and lifecycle of that person as a worker. Two distinct authorities are recognized, and HR holds both:

- **Identity authority** — who the worker is: the immutable correlation anchor (`employeeId`), legal name, worker type, and employment status (Spec2-D1.1).
- **Organizational-placement authority** — where the worker sits: the department, division, cost-center, organization-code, location, and reporting-line attributes from which OrgPath is computed (Spec2-D1.1; Spec2-D3.5).

No other system — and specifically not the Active Directory OU estate, not a manually maintained group, and not a directory administrator's edit — is an authoritative source for either fact. Where a downstream attribute disagrees with HR, HR wins and the downstream value is corrected.

### D2. The change-request workflow is the governance gate over HR deltas, not an independent origin

OrgTree's change-request workflow (Book_03 Chapter 2) sits **downstream of HR and upstream of the registry**. Its role is to govern HR-supplied structural deltas — to review, approve, and version *changes to the shape of the tree* (nodes added, renamed, merged, moved, archived) before they are committed — not to be an independent data origin that competes with HR. Person-to-node assignment flows from HR through the integration middleware and is reconciled against the governed tree; structural change to the tree itself is the reviewed, human-gated act. The closed loop is therefore: **HR system of record → integration middleware (OrgPath computation, ADR-035 codebook) → OrgTree registry (change-request-governed) → OrgPath attribute → policy-bearing dynamic groups.** This makes HR the source and the change-request workflow the control, with no contradiction between them.

### D3. OrgPath overlay supersedes OU remediation for a drifted estate

When the inherited Active Directory OU estate has drifted from the true organizational structure, the transition to OrgPath **does not realign or restructure the OU tree to match reality.** It instead:

1. builds the true structure as the governed OrgTree, seeded from HR and explicitly independent of the current AD OU layout (Book_04 Chapter 1);
2. stamps the HR-derived OrgPath attribute on every identity and resource object;
3. re-bases all policy targeting onto OrgPath-keyed dynamic groups (node and branch groups per ADR-036 / ADR-039), so governance no longer reads OU position; and
4. inventories the residual dependencies that still bind to OU placement — Group Policy links, delegated administration, and legacy applications — in the dependency map (Book_03 Chapter 8; Book_04 Chapter 13), and **decommissions** them on the cloud-forward path.

OU remediation as a standalone project — moving objects between containers to make the OU tree "correct" — is explicitly **not** the UIAO transition strategy. It is expensive, high-risk, and obsoleted by the overlay: once policy reads OrgPath, the OU tree's correctness is no longer a governance signal. The estate is retired, not realigned. This is not "ignore OUs forever": while on-premises AD persists during coexistence, residual OU bindings are governed by the dependency map and retired deliberately, not left to rot.

### D4. The source is HR-agnostic; the specific system is a vertical choice

Per ADR-003, the architecture binds to no specific HR product. Per [ADR-085](adr-085-universal-enterprise-positioning.md), the specific system of record is a property of the deployed **vertical**, not of the core engine:

- **Federal vertical** — the source is the OPM HRIT instantiation: agency HR systems of record (NFC EmpowHR/FPPS, Treasury HR Connect, DCPDS, DOI Interior Business Center HR) feeding an OPM-operated Entra Government tenant, with OPM lifecycle services (USA Staffing, eOPF, EHRI), USAccess PIV as the credential trust anchor, SCIM 2.0 near-real-time provisioning under the ≤15-minute SLA of OMB M-25-21, and single-ATO reciprocity per [ADR-054](adr-054-single-ato-reciprocity.md). See Spec2-D6.1.
- **Any other vertical** — the same source slot is filled by a commercial HCM (Workday, Oracle HCM Cloud, SAP SuccessFactors, or any future selection) with no change to D1–D3. The middleware adapter changes; the doctrine does not.

Describing the *source* as inherently federal is a positioning bug under ADR-085. OPM HRIT is the federal instantiation of a vertical-agnostic source role.

## Consequences

### Positive

- Resolves the unstated source question in the OrgPath Narrative; Book_02 Chapter 3 and Book_03 Chapter 4 can now name HR as the origin without contradicting the registry-as-authority model.
- Gives the mover lifecycle (Spec2-D2.2) a doctrinal foundation: an OrgPath change event is reliable exactly to the degree the HR→OrgTree integration is reliable, which is now an explicit, governed dependency rather than an implicit assumption.
- Routes organizations away from a costly OU-remediation project and toward the overlay-and-retire path the substrate was designed for.
- Keeps the federal OPM HRIT work correctly scoped as a vertical adapter pack, consistent with ADR-085.

### Negative / costs

- Requires the integration middleware as a standing operational surface (already accepted in ADR-003) and an HR-to-OrgTree reconciliation discipline that must be validated end-to-end before the mover workflow is relied upon for compliance-critical realignment.
- Demands HR data quality (Spec2-D1.8); a drifted or low-quality HR feed produces a drifted OrgTree, moving — not eliminating — the data-quality burden. The authoritative source must be *correct*, not merely *designated*.
- Residual OU-bound dependencies (GPO, delegation, legacy apps) must be actively inventoried and decommissioned; ignoring them during coexistence reintroduces the drift this ADR routes around.

## Alternatives considered

- **AD/OU as the source of truth, remediated into alignment.** Rejected: the OU estate is a drifted downstream projection, not an authority; remediating it is expensive, high-risk, and obsoleted once policy reads OrgPath (D3).
- **The change-request workflow as the independent source.** Rejected: it cannot scale to per-person placement and would duplicate, and inevitably diverge from, the HR system that already owns hire/position/separation as a business authority. It is retained as the *gate over structural deltas* (D2).
- **Binding the doctrine to a named HR product.** Rejected under ADR-003 and ADR-085: the source must be HR-agnostic and vertical-scoped (D4).

## References

- [ADR-003 — API-Driven Inbound Provisioning as HR-Agnostic Canonical Path](adr-003-api-driven-inbound-provisioning.md)
- [ADR-035 — OrgPath Codebook Binding](adr-035-orgpath-codebook-binding.md)
- [ADR-036 — Dynamic Group Provisioning](adr-036-dynamic-group-provisioning.md)
- [ADR-037 — Administrative Unit Provisioning](adr-037-admin-unit-provisioning.md)
- [ADR-039 — Policy Targeting](adr-039-policy-targeting.md)
- [ADR-054 — Single-ATO Reciprocity](adr-054-single-ato-reciprocity.md)
- [ADR-085 — Universal-Enterprise Positioning of the UIAO Core Engine](adr-085-universal-enterprise-positioning.md)
- [UIAO_007 — OrgTree Modernization (AD to Entra ID)](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- Spec2-D1.1 — Canonical HR Attribute Schema
- Spec2-D3.1 — API-Driven Inbound Provisioning Architecture
- Spec2-D3.5 — OrgPath Population Pipeline
- Spec2-D2.2 — Mover Workflow Specification
- Spec2-D6.1 — Federal HRIT Integration Runbook
- OrgPath Narrative — Book_02 Chapter 3, Book_03 Chapter 4, Book_04 Chapters 1 and 9A
