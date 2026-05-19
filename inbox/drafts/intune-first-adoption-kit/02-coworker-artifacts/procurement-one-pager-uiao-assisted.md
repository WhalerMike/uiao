# Procurement Guide — UIAO-Assisted View

**Audience:** Procurement officers and asset managers familiar with the
organization's UIAO governance framework, plus internal strategy and
architecture audiences reviewing how UIAO augments procurement.

**Purpose:** This document is the UIAO-assisted companion to
[`procurement-one-pager.md`](procurement-one-pager.md), which describes the
procurement actions that make Intune-first device acquisition work without
reference to any internal governance framework. The without-UIAO companion
stands alone and remains the canonical operational reference for procurement
officers. This document describes what UIAO adds to and surrounds that
operational reference.

The reader is assumed to have read the without-UIAO companion. This document
does not repeat the PO clause, vendor qualifying questions, verification
steps, or failure modes; it focuses exclusively on what UIAO contributes.

---

## What UIAO is, briefly

UIAO is the organization's internal governance substrate for identity,
device management, and access control. It is an internal architecture
sitting across Microsoft Entra ID, Microsoft Intune, on-premises Active
Directory, and upstream procurement, asset, and human-resources systems,
providing canonical organizational positioning (OrgPath), continuous drift
detection, and evidence emission.

---

## How UIAO augments procurement

The first contribution is **OrgPath assignment at procurement time**. Every
purchase order begins with the assignment of the future device's OrgPath:
business unit, region, asset class, ownership classification, security
tier, cost center, and assigned user (if known at procurement time). The
OrgPath is written to the canonical device record before the PO is sent to
the vendor. The Autopilot deployment profile, Apple Business Manager
assignment, or Android Zero-Touch configuration provided to the vendor is
generated from the OrgPath; the vendor does not choose a profile, the
procurement decision determines the profile. The without-UIAO companion
treats profile selection as a procurement-officer decision; with UIAO, the
profile is a derived attribute of OrgPath.

The second contribution is **canonical pre-registration verification**.
The procurement guide's section 3 (verification before shipment) is
performed by UIAO automatically. Each device the vendor reports as
registered is queried against the canonical registry; absence triggers an
immediate finding and routes back to the vendor for remediation under the
PO clause. The verification cadence is "every device, every shipment,"
which is operationally infeasible at scale without automation but is the
right cadence for organizations subject to federal compliance regimes.

The third contribution is **vendor performance scoring**. Each vendor's
track record on cloud-native procurement — registration success rate,
profile assignment accuracy, time-to-registration, accuracy of confirmation
reports — is recorded in the canonical evidence ledger. Vendor qualification
status (section 2 of the without-UIAO companion) is then driven by data
rather than by impression. Vendors whose track record degrades surface as
governance findings before they cause significant operational impact, and
vendors whose track record is consistently strong become candidates for
expanded relationships and reduced verification overhead.

The fourth contribution is **automated handling of the failure modes in
section 5**. When the canonical registry detects a device registered into
the wrong tenant, a device registered without a profile assignment, or a
device registered with the wrong profile, the remediation workflow is
initiated automatically and routed to the appropriate human — vendor
account manager, internal asset manager, or procurement officer — without
ticket-creation friction. The remediation cost is paid by the responsible
party automatically under the PO clause; the evidence record of the
failure becomes input to vendor performance scoring.

The fifth contribution is **procurement-to-validation evidence chain**.
Every step from purchase-order issuance through vendor confirmation,
device arrival, registration validation, out-of-box-experience provisioning,
and first compliance evaluation is recorded as a linked sequence in the
canonical evidence ledger. The chain is the audit substrate for federal
compliance attestation and for demonstrating to internal stakeholders
that the procurement-to-production pipeline is governed end-to-end. The
chain also supports root-cause analysis when something goes wrong: an
auditor asking "how did this non-compliant device end up in production"
can trace it back through every governance event in the procurement
pipeline.

---

## What is measurably different from the without-UIAO baseline

| Concern | Without UIAO | With UIAO |
|---|---|---|
| OrgPath determination | Assigned post-arrival, by humans | Assigned at PO issuance; baked into vendor pre-registration |
| Pre-shipment verification cadence | Manual per order, easy to skip on routine purchases | Automated per device; absence is a hard finding |
| Vendor qualification | Periodic review by impression | Continuous data-driven scoring |
| Failure-mode handling | Ticket-driven manual remediation | Automated routing to appropriate human under PO clause |
| Procurement-to-production evidence | Ad-hoc emails and screenshots, assembled retrospectively | Structured ledger entries, queryable in real time |
| Volume scaling | Each procurement is a separately-managed event | Volume is governance-bounded rather than headcount-bounded |

---

## What UIAO does not change

UIAO does not modify the vendor's pre-registration mechanism, the Microsoft
Cloud Solution Provider API, the Apple Business Manager portal, or the
Windows Autopilot service. The procurement officer continues to issue
purchase orders, the vendor continues to register devices into the tenant,
and the device continues to provision through the cloud-native out-of-box
experience. The PO clause from section 1 of the without-UIAO companion
remains exactly as written; UIAO does not change contractual expectations
between the organization and the vendor.

What UIAO changes is the *upstream specification* (OrgPath drives the
profile rather than profile selection being an independent decision) and
the *downstream verification and evidence* (automated rather than manual).
The mechanics of the vendor relationship are unchanged.

---

## Canonical anchors

UIAO anchors for procurement live in the organization's internal repository
under
[`src/uiao/modernization/intune-first-onboarding/`](../../../src/uiao/modernization/intune-first-onboarding/),
principally in
[`procurement-handoff.md`](../../../src/uiao/modernization/intune-first-onboarding/procurement-handoff.md)
and the surrounding doctrine and process specifications anchored by ADR-067
and ADR-071. The OrgPath taxonomy specification, the vendor adapter
specifications, and the procurement evidence ledger schema are also
available under `src/uiao/`.
