---
document_id: IFO_002
title: "Intune-First Asset Onboarding — The Five-Phase Process"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-13"
updated_at: "2026-05-14"
boundary: GCC-Moderate
canon_anchor: ADR-071
publish_to_site: true
publication_style: narrative
published_at: docs/modernization/intune-first.qmd
---

# Intune-First Asset Onboarding — The Five-Phase Process

> The canonical process for taking a net-new asset from purchase order
> to production-governed state. Five phases. Each phase has a defined
> owner, defined inputs, defined outputs, defined gate criteria.
>
> This is a platform-neutral process. Per-platform enrollment mechanics
> live in [`platforms/`](platforms/). The same five phases apply to a
> Windows laptop, a macOS workstation, an iPad, an Android phone, and
> an Arc-managed server — what changes is the vendor program used in
> Phase 2 and the enrollment vector used in Phase 4.

---

## Phase overview

| Phase | Owner | Trigger | Output | Gate to next phase |
|---|---|---|---|---|
| 1. Procure | Procurement | Business request for an asset | Approved purchase order with OrgPath assignment | OrgPath is recorded on the PO and validated against the OrgTree registry |
| 2. Pre-stage | Procurement + Vendor | PO submitted to vendor | Vendor program record (Autopilot device profile, ABM device assignment, etc.) | Vendor program record references the assigned OrgPath in the relevant tag/group |
| 3. Position | Governance pipeline | Vendor confirms hardware-hash / serial registration | Pre-staged Entra ID device object placeholder OR procurement-side mapping table entry | Mapping is committed to the governance repository and reviewed |
| 4. Provision | End user (zero-touch) or IT (assisted zero-touch) | Asset arrives at recipient location | Enrolled, OrgPath-stamped, compliant device | Compliance policy returns Compliant; Conditional Access grants access |
| 5. Validate | Governance pipeline | Device first compliance evaluation completes | Validation record in the governance audit log | All Phase 5 checks pass; device removed from quarantine if applicable |

A device that completes all five phases is **production-governed** and
indistinguishable from any other steady-state managed device. A device
that fails any gate enters quarantine (Pillar 5 of the doctrine) and
its onboarding ticket is escalated.

---

## Phase 1 — Procure

### Owner

Procurement, with governance pipeline as a peer system.

### Inputs

- Business request for an asset (the requisition or PO request)
- Recipient identity (Entra ID UPN) for personally-assigned devices, or
  receiving location (OrgTree node ID) for shared / kiosk / lab devices
- Asset class (laptop / mobile / tablet / server / etc.)
- Vendor and SKU
- Quantity and serial-number range if known at request time

### Activities

1. Procurement validates that the recipient has a valid Entra ID UPN
   and an OrgPath value already stamped on their user object. If the
   recipient is a not-yet-onboarded user, the user-side onboarding (HR
   pipeline) must complete first; the asset request is held.

2. For personally-assigned devices, procurement reads the recipient's
   OrgPath from Entra ID via the same Graph permission used by the ETL
   pipeline. The asset's intended OrgPath is set equal to the
   recipient's OrgPath.

3. For shared / kiosk / lab / role-bound devices, procurement consults
   the OrgTree registry to identify the correct OrgPath for the
   receiving location or role. The asset's intended OrgPath is set to
   that value.

4. Procurement validates the proposed OrgPath against the OrgTree
   registry — the OrgPath must resolve to a Status: Active node. If it
   does not, the procurement request is held pending governance
   review.

5. The approved OrgPath is recorded on the purchase order in a
   structured field that downstream automation can read. The
   OrgTree node ID is also recorded as a stable cross-reference (node
   names can change; node IDs do not).

### Outputs

- Approved PO with `OrgPath` and `OrgNodeId` fields populated
- Procurement record committed to the governance repository under
  `governance/procurement/orders/{PO-number}.json`
- Audit log entry recording the OrgPath assignment, the recipient or
  receiving location, and the procurement officer's identity

### Gate to Phase 2

- [ ] OrgPath is present on the PO and is non-empty
- [ ] OrgPath resolves to a Status: Active node in the OrgTree registry
- [ ] OrgNodeId matches the leaf node of the OrgPath
- [ ] PO is committed to the governance repository

---

## Phase 2 — Pre-stage

### Owner

Procurement (executes the writes), vendor (operates the program),
governance pipeline (verifies the writes).

### Inputs

- Approved PO from Phase 1
- Vendor program credentials (Autopilot service principal, ABM API
  token, Android Zero-Touch service account, Knox Mobile Enrollment
  customer credentials, Arc onboarding service principal)
- Hardware-hash file or serial-number list from the vendor's order
  fulfillment system

### Activities

The activities in this phase differ per platform. Common to all
platforms:

1. The hardware-hash or serial-number for each unit is uploaded to the
   vendor's enrollment program. Vendors that ship pre-registered
   hardware (CDW Autopilot pre-provisioning, Apple ABM-enrolled
   resellers, Android Zero-Touch resellers) handle this step in their
   order pipeline; for direct-to-organization purchases, the
   procurement team uploads the hash/serial set after receiving the
   shipment manifest.

2. Each device record in the vendor program is tagged with the OrgPath
   value from the PO. The exact tagging mechanism varies:
   - **Windows Autopilot:** device assigned to a deployment profile
     whose Group Tag carries the OrgPath value, or to a dynamic group
     whose membership rule selects on Group Tag
   - **Apple ABM/ASM:** device assigned to an MDM server selection
     whose name encodes the OrgPath, with the OrgPath also written to
     the ABM device note field for audit
   - **Android Zero-Touch / Knox Mobile Enrollment:** device assigned
     to a configuration whose tag carries the OrgPath value
   - **Azure Arc:** the onboarding token issued for the server is
     tagged with the OrgPath as a resource tag at issuance time

3. The procurement system writes the vendor program identifier (the
   Autopilot device ID, the ABM device ID, the Zero-Touch device ID,
   or the Arc onboarding token reference) back to the governance
   repository's procurement record from Phase 1.

### Outputs

- Vendor program records exist for every unit in the PO
- Each vendor program record carries the OrgPath assignment
- Cross-references between PO line items and vendor program records
  committed to the governance repository
- Audit log entry recording the vendor program assignment

### Gate to Phase 3

- [ ] Every unit in the PO has a vendor program record
- [ ] Every vendor program record carries the correct OrgPath tag
- [ ] Cross-references are committed to the governance repository
- [ ] No vendor program write operation returned an error that was not
      reconciled

---

## Phase 3 — Position

### Owner

Governance pipeline.

### Inputs

- PO + vendor program records from Phases 1 and 2
- OrgTree registry (for OrgPath validation)
- Hardware-hash → OrgPath mapping CSV from procurement

### Activities

1. The governance pipeline reads the procurement record committed in
   Phase 2 and produces an entry in the hardware-hash mapping file at
   `governance/autopilot/orgpath-mapping.csv` (or the vendor-program
   equivalent for non-Windows platforms). Each entry has columns for
   `SerialNumber`, `OrgPath`, `OrgNodeId`, and `Source` (set to
   `procurement` to distinguish from manually-added entries).

2. For Windows Autopilot devices, the pipeline verifies that the
   Autopilot deployment profile assignment writes the appropriate
   Group Tag value, so that the runtime user-derivation script in the
   OrgPath/Intune narrative §4.2 can fall back to the procurement-
   provided OrgPath if user lookup fails.

3. For Apple ABM, Android Zero-Touch, and Arc, the pipeline verifies
   that the management profile / configuration / onboarding token
   carries an attribute the runtime enrollment process can read.

4. The pipeline runs a dry-run validation: it simulates an enrollment
   for each device record by walking the runtime OrgPath stamping
   logic against the procurement-provided OrgPath, and confirms that
   the simulated outcome is the intended OrgPath. Any mismatch is a
   pipeline-blocking error.

5. The mapping file and validation results are committed to the
   governance repository. A second governance team member reviews the
   commit before the device is allowed to ship.

### Outputs

- Updated `governance/autopilot/orgpath-mapping.csv` (or per-platform
  equivalent) with one row per asset
- Pipeline-validated dry-run results showing the intended OrgPath for
  each asset matches the procurement record
- Governance repository commit reviewed by a second team member
- Audit log entry recording the position assignment and the reviewer

### Gate to Phase 4

- [ ] Every asset has a row in the position mapping file
- [ ] Dry-run validation produced no mismatches
- [ ] Governance repository commit has been reviewed and approved
- [ ] Quarantine OrgPath value `/UNPOSITIONED` does not appear for any
      asset whose procurement record specified a real OrgPath

---

## Phase 4 — Provision

### Owner

End user (for zero-touch deployments) or IT (for assisted zero-touch
deployments). The user does not need to know they are participating
in the governance process — they sign in to the device, the device
provisions itself.

### Inputs

- Asset, physically delivered to the recipient
- Network connectivity at the provisioning location
- The recipient's Entra ID credentials (for personally-assigned
  devices) or the kiosk / lab's pre-provisioning service principal
  (for shared devices)

### Activities

The activities in this phase differ per platform. Common to all
platforms:

1. The user powers on the device. The device contacts the vendor
   program (Autopilot service, ABM, Zero-Touch, Arc) and retrieves
   its assigned configuration profile, including the OrgPath
   assignment from Phase 3.

2. The device is placed into the appropriate Entra ID dynamic group
   based on its OrgPath value. Group membership evaluation may be
   asynchronous and take minutes to complete; the device's enrollment
   status page (where applicable) can wait for membership to converge
   before completing.

3. The OrgPath value is stamped on the device object in Entra ID.
   For Windows, this is the runtime stamping script from the
   OrgPath/Intune narrative §4.2 with procurement-provided OrgPath as
   the priority source over user-derivation. For other platforms,
   stamping is via the equivalent enrollment-time hook.

4. Compliance policies assigned to the device's branch group are
   evaluated. If the device meets the compliance policy, it is
   marked Compliant. Conditional Access grants resource access. The
   user can begin productive use.

5. The Intune device category is updated to reflect the OrgTree node
   type per the OrgPath/Intune narrative §6.

### Outputs

- Enrolled device object in Entra ID
- OrgPath stamped on the device object
- Compliance policy evaluation completed and recorded
- Conditional Access grant logged
- Initial telemetry visible in Intune device list and in the OrgPath
  compliance dashboard

### Gate to Phase 5

- [ ] Device appears in the Intune managed devices list
- [ ] OrgPath value on the device object matches the procurement record
- [ ] Compliance state is one of: Compliant, ConfigManager (for
      legitimate Arc cases), or InGracePeriod (with a documented
      grace-period justification)
- [ ] Device is a member of at least one ORG-NODE-* and one
      ORG-BRANCH-* group corresponding to its OrgPath
- [ ] No enrollment-time error events appear in the Intune device
      diagnostic log

---

## Phase 5 — Validate

### Owner

Governance pipeline.

### Inputs

- Device object from Phase 4
- Procurement record from Phase 1
- Intune compliance state
- Conditional Access access logs (post-enrollment first sign-in)

### Activities

1. The governance pipeline runs the post-enrollment validation suite
   against the newly enrolled device. The full validation checklist
   is in [`validation-and-evidence.md`](validation-and-evidence.md);
   the load-bearing checks at this phase are:
   - Procurement-recorded OrgPath equals the OrgPath stamped on the
     device object
   - Device is in the expected dynamic groups
   - Compliance policy result is recorded and is Compliant
   - Scope tag matches the OrgTree node's scope-tag-bearing ancestor
   - Device category matches the OrgTree node type
   - First Conditional Access grant log entry exists for the
     recipient user signing in to this device (if a personally-assigned
     device)

2. If all checks pass, the pipeline marks the device's onboarding as
   complete in the governance audit log and removes the asset from
   the open-onboarding queue.

3. If any check fails, the pipeline:
   - Writes a failure record to the governance audit log specifying
     which check failed and what the observed-vs-expected values were
   - Quarantines the device by overwriting its OrgPath to
     `/UNPOSITIONED` and triggering an Intune sync (see OrgPath/Intune
     narrative §6.2)
   - Opens a governance ticket for human review
   - Leaves the asset in the open-onboarding queue with status
     `failed-validation` until the ticket is resolved

4. Evidence artifacts (compliance evaluation timestamp, OrgPath stamp
   timestamp, first sign-in timestamp, Conditional Access grant log
   entry) are committed to the governance evidence store per
   [`validation-and-evidence.md`](validation-and-evidence.md) §3.

### Outputs

- Onboarding-complete record in the governance audit log
- Evidence artifacts in the governance evidence store
- (On failure) governance ticket and quarantine state

### Gate to "production-governed" status

- [ ] All Phase 5 validation checks pass
- [ ] Evidence artifacts committed
- [ ] Governance audit log marks onboarding complete
- [ ] Asset removed from open-onboarding queue

---

## Cross-phase concerns

### Latency targets

A reference latency target for the full onboarding process is **PO
issuance to production-governed within 14 calendar days for standard
hardware, within 5 calendar days for expedited orders**. The
breakdown by phase:

| Phase | Target latency | Notes |
|---|---|---|
| 1. Procure | Same business day | Procurement system writes OrgPath in the same transaction as PO approval |
| 2. Pre-stage | Vendor SLA + 2 business days | Bounded by vendor's hardware-hash registration cycle |
| 3. Position | Same business day | Pipeline runs nightly; expedited orders trigger an on-demand pipeline run |
| 4. Provision | First user logon at the recipient location | Bounded by shipping time and recipient availability |
| 5. Validate | Within 24 hours of Phase 4 completion | Pipeline runs nightly post-Phase-4 |

Latency exceeding the target enters the late-onboarding queue for
governance review. Repeated late entries against the same vendor or
recipient location are a signal for process review.

### Failure escalation

Failures at Phases 1–3 are pipeline-blocking and surface immediately.
Failures at Phase 4 surface within minutes via Intune enrollment
events; an enrollment that fails to enroll a device at all (Autopilot
provisioning error, ABM enrollment refusal) is logged in the vendor
program's diagnostic surface and escalates to procurement. Failures
at Phase 5 produce a governance ticket per the activities above.

### Rollback / reversal

A device whose Phase 5 validation fails and cannot be recovered is
**reset to factory and re-enrolled**, not patched in place. Repeated
patching of post-enrollment state to align with the procurement record
produces audit-trail divergence between "what procurement intended"
and "what production reflects" — divergence the governance evidence
graph is specifically designed to surface.

If the procurement record itself is wrong (the recipient's OrgPath
was incorrect at PO time), the correction path is:
1. Update the recipient's user object in HR / Entra
2. Re-run the user-side ETL pipeline to refresh OrgPath on the user
3. Re-run the device-side ETL pipeline against the device
4. Validate Phase 5 again

The procurement record is **not** retroactively edited. A new audit
log entry records the correction; the original procurement record
remains as the historical record of the original (incorrect)
intent.

---

## Process diagram

```
                      [Business request]
                              │
                              ▼
   ┌───────────────────────────────────────────────────┐
   │ Phase 1: Procure                                  │
   │   - Validate recipient OrgPath                    │
   │   - Set asset OrgPath = recipient OrgPath         │
   │   - Commit PO with OrgPath/OrgNodeId fields       │
   └───────────────────────────────────────────────────┘
                              │  Gate: OrgPath valid
                              ▼
   ┌───────────────────────────────────────────────────┐
   │ Phase 2: Pre-stage                                │
   │   - Upload hardware hash / serial to vendor       │
   │   - Tag vendor program record with OrgPath        │
   │   - Cross-ref written to governance repo          │
   └───────────────────────────────────────────────────┘
                              │  Gate: vendor record carries OrgPath
                              ▼
   ┌───────────────────────────────────────────────────┐
   │ Phase 3: Position                                 │
   │   - Update governance/.../orgpath-mapping.csv     │
   │   - Dry-run validation of OrgPath assignment      │
   │   - Two-person review of governance commit        │
   └───────────────────────────────────────────────────┘
                              │  Gate: dry-run clean, reviewed
                              ▼
                  [Asset ships to recipient]
                              │
                              ▼
   ┌───────────────────────────────────────────────────┐
   │ Phase 4: Provision (zero-touch)                   │
   │   - Device contacts vendor program                │
   │   - OrgPath stamped during enrollment             │
   │   - Compliance evaluated; CA grants access        │
   └───────────────────────────────────────────────────┘
                              │  Gate: Compliant + correct groups
                              ▼
   ┌───────────────────────────────────────────────────┐
   │ Phase 5: Validate                                 │
   │   - Procurement OrgPath == stamped OrgPath        │
   │   - Evidence artifacts committed                  │
   │   - Onboarding marked complete OR quarantined     │
   └───────────────────────────────────────────────────┘
                              │
                              ▼
                   [Production-governed]
```
