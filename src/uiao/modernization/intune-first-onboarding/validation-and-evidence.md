---
document_id: IFO_004
title: "Validation Checklist, Drift Classes, and Evidence Emission"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-13"
updated_at: "2026-05-14"
boundary: GCC-Moderate
canon_anchor: ADR-067
publish_to_site: true
publication_style: narrative
published_at: docs/modernization/intune-first.qmd
---

# Validation Checklist, Drift Classes, and Evidence Emission

> The Phase 5 validation checklist, the drift classes that the
> Intune-first onboarding doctrine introduces or extends, and the
> evidence artifacts each successfully-onboarded asset emits.
>
> This document is platform-neutral. Platform-specific validation
> items are listed in the per-platform docs under
> [`platforms/`](platforms/) and inherit everything here.

---

## §1. Validation checklist (platform-neutral)

The checks below must pass for every asset, regardless of platform,
before the asset's onboarding is marked complete in the governance
audit log.

### Procurement record vs. observed state

- [ ] Procurement record exists at
      `governance/procurement/orders/{PO-number}.json`
- [ ] Procurement record's `phase` is `5-validate-pending` or
      `4-provision-complete`
- [ ] Procurement record's `asset_orgpath` is non-empty
- [ ] Procurement record's `asset_orgpath` resolves to an Active node
      in the OrgTree registry as of validation time
- [ ] Procurement record's `vendor_program_records` array contains
      one entry per unit, each with a non-null `registered_at`
- [ ] OrgPath value carried in the vendor program record (Group Tag,
      ABM device note, Zero-Touch / KME custom JSON, Arc resource
      tag) matches `asset_orgpath`

### Device existence and identity

- [ ] Device object exists in Entra ID (or, for Arc-only servers,
      Arc-enabled machine resource exists in the procurement-
      designated resource group)
- [ ] Device object's `physicalIds` (Windows) / `deviceIdentifier`
      (macOS/iOS) / `deviceId` (Android) / Arc machine resource
      `properties.vmId` corresponds to the procurement record's
      serial number for the unit
- [ ] Device join type matches the platform's expected canonical
      value (Microsoft Entra Join for Windows; Supervised + ADE for
      Apple; Device Owner mode for Android Enterprise; WORKGROUP +
      Arc for servers; Entra-joined via AADLoginForWindows for
      Server 2025+)

### OrgPath and group membership

- [ ] OrgPath extension attribute on the Entra device object equals
      `asset_orgpath` from the procurement record
- [ ] (Arc servers) Resource tag `OrgPath` on the Arc-enabled
      machine resource equals `asset_orgpath`
- [ ] Device is a member of the ORG-NODE-{NodeId} group corresponding
      to its leaf OrgPath
- [ ] Device is a member of the ORG-BRANCH-{NodeId} groups for every
      ancestor node up to the OrgTree root
- [ ] Device is NOT a member of ORG-BRANCH-UNPOSITIONED (the
      quarantine branch)
- [ ] Device is NOT a member of any ORG-NODE / ORG-BRANCH group it
      should not be in (e.g., a different branch's group)

### Compliance and Conditional Access

- [ ] Device's compliance state is `Compliant`
- [ ] Compliance state is the result of the branch-specific
      compliance policy assigned to the device's OrgPath segment
      (not solely a baseline policy that happens to apply)
- [ ] Conditional Access access logs show at least one successful
      sign-in to an organizational resource from the device since
      onboarding completed (for personally-assigned devices; service
      assignments validate via service-account sign-in)
- [ ] Conditional Access denied access from the device for any
      attempted sign-in that occurred BEFORE compliance evaluation
      completed (proves the doctrine pillar that ungoverned devices
      cannot access resources)

### Scope tags and administrative delegation

- [ ] Intune scope tag assignments on the device match the scope-tag-
      bearing OrgTree node ancestor (per OrgPath/Intune narrative §7)
- [ ] (Arc servers) Azure resource scope tags match the OrgPath
      delegation model

### Device category and metadata

- [ ] Intune device category matches the OrgTree node type (per
      OrgPath/Intune narrative §6.2 mapping)
- [ ] Device metadata fields populated: assigned user (for personal),
      enrollment date, OS version, manufacturer, model

### Audit trail

- [ ] Phase 1 commit exists in governance repository
- [ ] Phase 2 vendor program write events logged in procurement
      record's `phase_history`
- [ ] Phase 3 mapping file commit exists in governance repository
      with two-person review
- [ ] Phase 4 enrollment events captured in Intune device
      diagnostic logs
- [ ] Phase 5 validation execution timestamp recorded

If all checks pass, the procurement record's `phase` updates to
`5-validate-complete` and the asset is removed from the open-
onboarding queue. If any check fails, the asset enters quarantine
per Pillar 5.

---

## §2. Drift classes introduced or extended

The Intune-first doctrine introduces five drift classes. Each is
detected by the governance pipeline on its standard cadence and
classified per the existing UIAO drift detection standard
([`docs/docs/16_DriftDetectionStandard.qmd`](../../../../docs/docs/16_DriftDetectionStandard.qmd)).

### 2.1 — DRIFT-PROCUREMENT-MISMATCH

**Definition.** The OrgPath stamped on a device object does not
equal the OrgPath in the procurement record for that device's
serial number.

**How detected.** The governance pipeline correlates procurement
records with device objects by serial. For each correlation, the
pipeline compares the procurement-record `asset_orgpath` against
the device's stamped OrgPath. Any divergence is a finding.

**How classified.** Severity: HIGH. The divergence indicates either
that procurement intent was not honored (Phase 4 stamping went to
the wrong source) or that runtime conditions changed the device's
OrgPath after enrollment (post-enrollment ETL ran with a different
input than procurement intended).

**How remediated.** Human review. The governance team determines
whether to update the procurement record (if the device legitimately
changed organizational position) or to re-stamp the device (if
procurement was correct and runtime stamping was wrong). The
remediation is logged with the disposition.

### 2.2 — DRIFT-VENDOR-PROGRAM-CARRIER

**Definition.** The OrgPath value carried in the vendor program
record (Group Tag, ABM device note, Zero-Touch / KME custom JSON,
Arc resource tag) does not equal the procurement record's
`asset_orgpath`.

**How detected.** The governance pipeline polls the vendor program
APIs for each registered device and compares the carrier value to
the procurement record. Any divergence is a finding.

**How classified.** Severity: HIGH. The divergence indicates that
either the procurement-side write was incorrect, or the vendor
program record was modified after Phase 2 (which can happen via
the vendor's portal or via a competing automation).

**How remediated.** Pipeline-driven correction. The pipeline
re-writes the carrier to match the procurement record. If the write
fails, escalates to the procurement system owner.

### 2.3 — DRIFT-ENROLLMENT-VECTOR

**Definition.** A device enrolled in Intune via a path other than
the platform's canonical zero-touch enrollment vector, without an
exception path grant.

**How detected.** The governance pipeline queries the Intune
enrollment metadata for each device. Devices with `enrollmentType`
matching one of the manual / user-driven values are checked
against the exception path grant log. Devices without a matching
grant are findings.

**How classified.** Severity: MEDIUM (for endpoints that ended up
governed despite the wrong vector) or HIGH (for devices that
remain in a less-governed state, e.g., user-enrolled iOS that
cannot reach Supervised). Severity escalates to HIGH if the device
has accessed organizational resources before being detected.

**How remediated.** The governance team disposition: re-enroll via
zero-touch (factory reset and re-onboard through the canonical
vector) or grant a retroactive exception (with documentation).
Retroactive exceptions are time-limited; the device is queued for
re-enrollment at the exception expiration.

### 2.4 — DRIFT-CO-MANAGEMENT-NEW

**Definition.** A net-new Windows endpoint that landed in SCCM
co-management instead of Intune-first, identified by SCCM
registration timestamp post-dating the doctrine's effective date.

**How detected.** The governance pipeline correlates SCCM device
registration timestamps with Intune enrollment timestamps and the
procurement record. New devices that have an SCCM registration
event without a corresponding `intune-native` procurement record
are findings.

**How classified.** Severity: HIGH. Pillar 4 prohibition.

**How remediated.** Decision: either move the device into the
migration path (treat as if it were a pre-existing AD-joined
device) or re-enroll into Intune-first. The choice depends on
whether the device's enrollment can be reversed without disrupting
the user, and on whether the SCCM registration was a procedural
error or a documented exception.

### 2.5 — DRIFT-PROCUREMENT-RECORD-ABSENT

**Definition.** A device enrolled in Intune that has no
corresponding procurement record in the governance repository.

**How detected.** The governance pipeline correlates Intune-enrolled
devices with procurement records by serial. Devices without a
matching record are findings.

**How classified.** Severity: MEDIUM. The device is governed (it is
in Intune) but the chain-of-custody from procurement is broken.

**How remediated.** Investigate the gap. Possibilities: (a)
procurement system did not write the record (procurement integration
bug); (b) the device was acquired outside the procurement process
(grey-market or user-funded; needs procurement review); (c) the
device pre-dates the doctrine and is being onboarded as a migration
asset, not an Intune-first asset (re-classify; this is then not an
Intune-first concern). Each possibility produces a different
governance action.

---

## §3. Evidence emission

Each successfully onboarded asset emits the following evidence
artifacts to the governance evidence store. Evidence is HMAC-signed
per the FedRAMP Moderate evidence chain (see
`src/uiao/canon/UIAO_113`).

### 3.1 — Onboarding completion record

Path: `governance/evidence/intune-first/{PO-number}/{serial}.json`

Schema:

```json
{
  "evidence_type": "intune-first-onboarding-complete",
  "evidence_version": "1.0",
  "po_number": "PO-2026-001234",
  "serial_number": "PF3X9KTM",
  "asset_class": "windows-endpoint",
  "platform": "windows",
  "vendor_program": "autopilot-reseller",
  "vendor": "CDW-G",
  "asset_orgpath": "/Root/Finance/Accounting/AccountsReceivable",
  "asset_orgnodeid": "AR-NODE-042",
  "recipient_upn": "j.smith@agency.gov",
  "phase_completion_timestamps": {
    "phase_1_procure": "2026-05-13T14:35:00Z",
    "phase_2_prestage": "2026-05-15T09:12:00Z",
    "phase_3_position": "2026-05-15T22:00:00Z",
    "phase_4_provision": "2026-05-19T11:24:00Z",
    "phase_5_validate": "2026-05-20T03:00:00Z"
  },
  "validation_checks_passed": [...],
  "validation_checks_failed": [],
  "compliance_state_at_validation": "Compliant",
  "compliance_policy_id": "{guid}",
  "first_conditional_access_grant_at": "2026-05-19T11:30:00Z",
  "audit_chain_hash": "{sha256-of-evidence-chain}",
  "hmac": "{hmac-signature}"
}
```

### 3.2 — Quarantine record (on validation failure)

Path: `governance/evidence/intune-first/{PO-number}/{serial}-quarantined.json`

Same schema as 3.1, plus:

- `validation_checks_failed`: array of failed-check identifiers
- `quarantine_orgpath`: `/UNPOSITIONED`
- `quarantine_disposition`: `pending-review` initially; updated to
  the disposition outcome on resolution
- `quarantine_resolved_at`: null initially; populated on resolution
- `quarantine_resolution_artifact`: pointer to the disposition
  document

### 3.3 — Drift event records

Each detected drift class instance from §2 produces a drift event:

Path: `governance/evidence/drift-events/{date}/{drift-class}-{event-id}.json`

The event includes the device identification, the drift class, the
observed-vs-expected values, the severity classification, and the
remediation status. Drift events flow through the same evidence
chain as onboarding completion records.

### 3.4 — Procurement record (canonical)

The procurement record itself (committed to
`governance/procurement/orders/{PO-number}.json`) is the canonical
chain-of-custody artifact. It is the procurement-side audit trail;
the onboarding completion record is the governance-side audit
trail. Both are independently HMAC-signed and cross-reference each
other by PO number and serial.

### 3.5 — Mapping to FedRAMP / KSI controls

The evidence artifacts above support the following control families
in the FedRAMP Moderate baseline:

| Control | Evidence supporting |
|---|---|
| AC-2 (Account Management) | Onboarding records prove device-to-user assignment chain-of-custody |
| AC-19 (Access Control for Mobile Devices) | Mobile platform validation checks; Conditional Access grant logs |
| CM-2 (Baseline Configuration) | Compliance policy ID reference proves a baseline was applied at first compliance evaluation |
| CM-7 (Least Functionality) | Vendor program enrollment proves zero-touch path; manual enrollment evidence flagged via DRIFT-ENROLLMENT-VECTOR |
| CM-8 (Information System Component Inventory) | Procurement record + onboarding completion record together establish the inventory entry chain-of-custody |
| IA-3 (Device Identification and Authentication) | Entra Join / Supervised / Device Owner / Arc onboarding evidence proves device authentication is in place |
| MA-2 (Controlled Maintenance) | Lifecycle-milestone fields on the procurement record support maintenance scheduling |
| SC-15 (Collaborative Computing Devices) | Mobile platform validation includes restrictions on collaborative-computing features per branch policy |

Mapping to UIAO's KSI controls follows the same pattern via
`src/uiao/rules/ksi/`.

---

## §4. Validation pipeline scheduling

The validation pipeline runs on the following cadence:

| Trigger | What runs |
|---|---|
| Procurement record commits Phase 4 complete | Phase 5 validation for that asset within 2 hours |
| Nightly governance pipeline run | Phase 5 re-validation for all open-onboarding queue assets; drift detection for all classes |
| Weekly governance pipeline run | Drift event reconciliation; quarantine queue audit |
| Monthly governance pipeline run | Procurement chain-of-custody audit (DRIFT-PROCUREMENT-RECORD-ABSENT scan) |

The triggers are additive — a Phase 4 completion produces an
immediate validation; the nightly run ensures no asset is missed
even if its Phase 4 trigger was lost.

---

## §5. Validation pipeline implementation pointers

This document specifies the validation contract; the implementation
lands in:

- `src/uiao/adapters/modernization/intune_native/` (proposed location
  for the pipeline implementation when the doctrine is promoted)
- `src/uiao/schemas/intune-first-onboarding/` (proposed location for
  the JSON schemas defining the procurement record, evidence
  artifacts, and drift event formats)
- Integration with the existing OrgTree readiness bundle schema at
  `src/uiao/schemas/orgtree-readiness/orgtree-readiness.schema.json`

The implementation is a follow-up engineering item; this bundle
specifies what the implementation must do, not how it does it.
