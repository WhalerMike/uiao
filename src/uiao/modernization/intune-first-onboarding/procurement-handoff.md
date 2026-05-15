---
document_id: IFO_003
title: "Procurement Handoff — Intake Checklist and Procurement-System Integration"
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

# Procurement Handoff — Intake Checklist and Procurement-System Integration

> The operational mechanics of Phase 1 of the five-phase process. This
> document tells the procurement team (and the systems they operate)
> exactly what must happen at PO time, in what order, and what the
> governance pipeline expects to see in the procurement record that
> gets committed to the governance repository.

---

## §1. Why procurement is the first governance step

Every device the organization owns occupies an organizational position
— Finance laptop, Operations tablet, lab workstation, reception
kiosk, file server. That position is determined the moment a person
or business owner decides "we need a new device for this purpose."
The decision precedes the purchase order; the purchase order is the
first system-of-record artifact that captures it.

If procurement does not capture the position in a structured field,
the position must be reconstructed downstream — by inferring it from
the eventual primary user, by manual ticket triage, by hardware-hash
mapping tables maintained out of band. Each reconstruction step is a
chance for the position to drift from intent. Procurement-time
capture eliminates the reconstruction.

The doctrine pillar this implements: **Pillar 2 — Procurement is the
first governance step** (see [`doctrine.md`](doctrine.md) §Pillar 2).

---

## §2. Procurement intake checklist

The following fields must be present on every asset purchase request
before approval. Procurement officers may not approve a request with
incomplete fields. Procurement systems should enforce these as
required fields in the intake form.

### Required fields

| Field | Type | Source | Validation |
|---|---|---|---|
| `recipient_upn` | string (UPN) | Requestor input | Must resolve to a Status: Enabled user in Entra ID |
| `recipient_orgpath` | string (OrgPath) | Derived from `recipient_upn` via Entra ID lookup | Must be non-empty; must match an Active node in the OrgTree registry |
| `recipient_orgnodeid` | string (NodeId) | Derived from `recipient_orgpath` | Must equal the leaf node ID of the OrgPath |
| `asset_class` | enum | Requestor input | One of: `windows-endpoint`, `macos-endpoint`, `ios-tablet`, `ios-phone`, `android-phone`, `android-tablet`, `windows-server`, `linux-server` |
| `asset_assignment_type` | enum | Requestor input | One of: `personal`, `shared`, `kiosk`, `lab`, `service` |
| `asset_orgpath` | string (OrgPath) | See §3 below | Must be non-empty; must match an Active node in the OrgTree registry |
| `asset_orgnodeid` | string (NodeId) | Derived from `asset_orgpath` | Must equal the leaf node ID of the OrgPath |
| `vendor` | string | Requestor input | Must match a registered vendor in the procurement vendor registry |
| `vendor_program` | enum | Derived from `vendor` + `asset_class` | One of: `autopilot-direct`, `autopilot-reseller`, `apple-abm`, `apple-asm`, `android-zerotouch`, `samsung-knox-me`, `arc-direct` |
| `quantity` | integer | Requestor input | Must be ≥ 1 |
| `serial_range_known_at_po` | boolean | Requestor input | True if the serial-number range will be known at PO submission |
| `expected_delivery` | date | Vendor SLA | Must be ≥ today + vendor processing time |
| `requested_by` | string (UPN) | Procurement system | Auto-populated |
| `approved_by` | string (UPN) | Procurement officer | Auto-populated at approval |
| `governance_review_required` | boolean | Auto-evaluated | True if any field below triggers governance review (see §4) |

### Optional fields (recommended)

| Field | Use |
|---|---|
| `cost_center` | Finance reconciliation; should match the OrgPath segment's cost center |
| `business_justification` | Free text; surfaced in audit log on review |
| `replacement_for_serial` | If this asset replaces an existing asset, the predecessor's serial — used for offboarding chain-of-custody |
| `lifecycle_milestones` | Expected lifecycle dates: warranty expiry, refresh cycle, decommissioning target |

---

## §3. Determining `asset_orgpath`

The `asset_orgpath` field is the single most important field in the
intake checklist. It determines every downstream governance outcome.
The determination rule depends on `asset_assignment_type`:

| `asset_assignment_type` | Rule for `asset_orgpath` |
|---|---|
| `personal` | `asset_orgpath` = `recipient_orgpath`. Personally-assigned devices inherit the recipient's organizational position. |
| `shared` | `asset_orgpath` = OrgPath of the receiving location's OrgTree node. Procurement must consult the OrgTree registry for the location. The recipient field is the ordering officer; the location is determined separately. |
| `kiosk` | `asset_orgpath` = OrgPath of the kiosk's functional purpose (e.g., `/Root/Operations/Reception`). Kiosk OrgPaths are pre-populated in the OrgTree registry by governance. |
| `lab` | `asset_orgpath` = OrgPath of the lab. Lab OrgPaths are typically a dedicated `/Lab` subtree under the owning division. |
| `service` | `asset_orgpath` = OrgPath of the service-account-owning team. Service-purpose devices (build servers, monitoring nodes, DDI appliances) belong to the operating team's OrgPath, not the consuming users'. |

For `shared`, `kiosk`, `lab`, and `service` assignments, the
procurement officer is responsible for selecting the correct OrgPath
from the OrgTree registry. The procurement intake form should provide
an OrgPath picker that surfaces only Active nodes. Free-text entry
of OrgPath values is forbidden — typos produce mappings that fail
Phase 3 dry-run validation.

If the correct OrgPath cannot be determined at intake time (rare,
typically for lab equipment whose lab assignment is pending), the
intake is held pending governance disposition. The procurement
request is **not approved** until OrgPath is resolved.

---

## §4. Governance-review triggers

A procurement request requires governance review (in addition to
standard procurement approval) if any of the following are true:

- `asset_assignment_type` is `service` AND `asset_class` is a server
- `asset_orgpath` is in a scope-tag-bearing OrgTree node (governance
  needs to confirm scope tag delegation aligns with the receiving
  team)
- `vendor_program` is `arc-direct` (server onboarding intersects with
  ADR-002 constraints; governance reviews to confirm OS version)
- `asset_class` is `linux-server` (Linux endpoint exception path B may
  apply; governance reviews to confirm the asset is genuinely a
  server, not an endpoint)
- `quantity` ≥ 25 (bulk orders trigger governance review for
  organizational-scaling assessment)
- `replacement_for_serial` is populated AND the predecessor's
  offboarding has not been completed (chain-of-custody risk)

Governance review is asynchronous and SLA-bound. Standard target: 1
business day for reviews flagged at intake; 3 business days for
exception requests.

---

## §5. The procurement record

When a procurement request is approved, the procurement system
produces a **procurement record** committed to the governance
repository at:

```
governance/procurement/orders/{PO-number}.json
```

The record is a JSON document with the following schema:

```json
{
  "po_number": "PO-2026-001234",
  "po_issued_at": "2026-05-13T14:30:00Z",
  "po_issued_by": "procurement-officer@agency.gov",
  "approved_by": "procurement-manager@agency.gov",
  "approved_at": "2026-05-13T14:35:00Z",
  "vendor": "CDW-G",
  "vendor_program": "autopilot-reseller",
  "asset_class": "windows-endpoint",
  "asset_sku": "Lenovo ThinkPad X1 Carbon Gen 12",
  "asset_assignment_type": "personal",
  "recipient_upn": "j.smith@agency.gov",
  "recipient_orgpath": "/Root/Finance/Accounting/AccountsReceivable",
  "recipient_orgnodeid": "AR-NODE-042",
  "asset_orgpath": "/Root/Finance/Accounting/AccountsReceivable",
  "asset_orgnodeid": "AR-NODE-042",
  "quantity": 1,
  "expected_delivery": "2026-05-27",
  "governance_review_required": false,
  "governance_reviewed_by": null,
  "governance_reviewed_at": null,
  "vendor_program_records": [],
  "phase": "1-procure-complete",
  "phase_history": [
    {"phase": "1-procure-complete", "completed_at": "2026-05-13T14:35:00Z"}
  ]
}
```

The `vendor_program_records` array is empty at PO approval time. It
is populated by the Phase 2 pre-stage step with one entry per unit:

```json
{
  "vendor_program_records": [
    {
      "unit_index": 0,
      "serial_number": "PF3X9KTM",
      "hardware_hash": "T0FCQUFDRkF...truncated...QkIyRkE=",
      "vendor_program_id": "autopilot-device-id-78a3...",
      "registered_at": "2026-05-19T09:12:00Z",
      "registered_by": "procurement-pipeline@agency.gov",
      "orgpath_tagged": true,
      "orgpath_tag_value": "/Root/Finance/Accounting/AccountsReceivable",
      "orgpath_tag_mechanism": "autopilot-group-tag"
    }
  ]
}
```

The procurement record is the system-of-record for the asset
throughout the onboarding process. Each phase appends to
`phase_history` and updates `phase` to the current phase. The
final state for a successfully onboarded asset is:

```json
{
  "phase": "5-validate-complete",
  "phase_history": [
    {"phase": "1-procure-complete", "completed_at": "..."},
    {"phase": "2-prestage-complete", "completed_at": "..."},
    {"phase": "3-position-complete", "completed_at": "..."},
    {"phase": "4-provision-complete", "completed_at": "..."},
    {"phase": "5-validate-complete", "completed_at": "..."}
  ]
}
```

---

## §6. Procurement system integration

The procurement system must implement the following integrations to
satisfy this doctrine:

### 6.1 — Read integration with Entra ID

The procurement system reads the recipient's user object to retrieve
`recipient_orgpath`. Required Graph permissions for the
procurement system's service principal:

- `User.Read.All` — to look up recipient by UPN and retrieve the
  OrgPath extension attribute

Permission scope is application; the procurement service principal
must be registered in Entra ID and consented per organizational
policy. The OrgPath extension attribute name follows the convention
established in the OrgPath/Intune narrative §4.2:

```
extension_{appIdNoHyphens}_OrgPath
```

where `appIdNoHyphens` is the App ID of the OrgPath governance App
Registration (the same App ID used by the user-side ETL pipeline).

### 6.2 — Read integration with the OrgTree registry

The procurement system reads the OrgTree registry to:

- Validate `asset_orgpath` resolves to a Status: Active node
- Populate the OrgPath picker for `shared`/`kiosk`/`lab`/`service`
  assignments
- Surface scope-tag-bearing nodes for governance-review triggering

The OrgTree registry is committed to the governance repository at the
path established by UIAO_007. The procurement system pulls the
registry on a refresh interval (recommended: every 15 minutes during
business hours, hourly otherwise) or via webhook on registry change.

### 6.3 — Write integration with vendor programs

The procurement system writes to vendor programs at Phase 2. The
write integration depends on the `vendor_program` value:

| `vendor_program` | Write API | Service principal |
|---|---|---|
| `autopilot-direct` | Microsoft Graph `/deviceManagement/windowsAutopilotDeviceIdentities` | Procurement system's Entra ID SP with `DeviceManagementServiceConfig.ReadWrite.All` |
| `autopilot-reseller` | Reseller's API for hardware-hash submission, then Microsoft Graph for Group Tag assignment | Reseller-specific token + procurement Entra SP |
| `apple-abm` | Apple Business Manager API (via MDM server connection) | ABM organization token via Microsoft Graph `/deviceAppManagement/iosVppTokens` |
| `apple-asm` | Apple School Manager (parallel to ABM for education organizations) | Same pattern as ABM |
| `android-zerotouch` | Android Device Provisioning Partner API | Google service account JSON key |
| `samsung-knox-me` | Knox Mobile Enrollment API | Knox customer credentials |
| `arc-direct` | Azure Resource Manager — Arc onboarding service | Procurement system's Azure SP with Arc onboarding role |

For each vendor program, the procurement system writes the OrgPath
value to the program's tag/group/configuration field per the per-
platform docs in [`platforms/`](platforms/).

### 6.4 — Write integration with the governance repository

The procurement system commits the procurement record JSON to the
governance repository at `governance/procurement/orders/{PO-number}.json`
on every state change:

- At PO approval (Phase 1 complete)
- After each vendor program write (Phase 2 incremental)
- After all vendor program writes complete (Phase 2 complete)

The commit message format:

```
procurement: {PO-number} {phase-transition}

OrgPath: {asset_orgpath}
Recipient: {recipient_upn}
Vendor: {vendor} ({vendor_program})
Quantity: {quantity}
```

The governance pipeline polls the procurement directory for new
commits and triggers Phase 3 (Position) on detection.

---

## §7. Failure modes and recovery

### 7.1 — Recipient OrgPath not present

If the recipient's user object has no OrgPath extension attribute,
the procurement intake is held. Resolution:

1. Verify the recipient user is intended to receive the asset (typo
   check, terminated-employee check)
2. If the user is correct, escalate to HR pipeline owner — the user
   has not been positioned in the OrgTree, which is itself a
   governance gap
3. Hold the procurement request until the user's OrgPath is stamped

### 7.2 — Asset OrgPath does not resolve to an Active node

The OrgTree registry returned no node matching the proposed
`asset_orgpath`, OR the matching node has Status other than Active
(Decommissioning, Decommissioned, Pending). Resolution:

1. The procurement officer reviews the proposed OrgPath against the
   OrgTree registry directly
2. If the proposed OrgPath is correct but the node is non-Active,
   escalate to governance — the node should be Active before
   accepting assets
3. If the proposed OrgPath is incorrect, correct it in the intake
   form and re-validate

### 7.3 — Vendor program write fails

The vendor program API returned an error during Phase 2 (token
expired, hardware hash already registered, vendor service outage).
Resolution:

1. The procurement system records the error in the procurement
   record's `vendor_program_records` entry with `registered_at: null`
   and an `error` field
2. The pipeline holds Phase 3 — the asset cannot be Positioned
   without a Pre-stage record
3. The procurement system retries the vendor program write on a
   backoff schedule (10 min, 1 hour, 4 hours, 1 business day)
4. If retries exhaust, the asset enters the procurement-error queue
   for human review

### 7.4 — Procurement record fails to commit to governance repository

The governance repository write returned an error (Git push refused,
auth failure, reviewer not available). Resolution:

1. The procurement record is held in the procurement system's
   outbound queue
2. The procurement system retries on a backoff schedule
3. If retries exhaust, the procurement record is escalated to the
   governance pipeline owner — no asset may proceed past Phase 1
   without the procurement record committed

### 7.5 — Discrepancy between intake `asset_orgpath` and runtime stamp

If, during Phase 5 validation, the runtime-stamped OrgPath on the
device object does not equal the procurement-record `asset_orgpath`,
the device is quarantined per Pillar 5. Resolution:

1. Phase 5 produces a quarantine entry and a governance ticket
2. The discrepancy may be: (a) the procurement record was wrong, (b)
   the runtime stamp was wrong, (c) the recipient changed
   organizational position between PO and provisioning
3. Governance disposition: confirm the correct OrgPath, update the
   asset's OrgPath via the ETL pipeline, re-run Phase 5 validation

The procurement record is **never retroactively edited** to match the
runtime stamp. A new audit log entry records the resolution; the
original procurement intent remains as the historical record.

---

## §8. Procurement officer training requirements

Procurement officers approving asset purchases under this doctrine
must be trained on:

- The five doctrine pillars (one-page summary in
  [`doctrine.md`](doctrine.md))
- The OrgTree registry structure (one-page summary referencing
  UIAO_007)
- The intake checklist (this document, §2)
- The governance-review triggers (this document, §4)
- The escalation paths for the failure modes (this document, §7)

Training cadence: at hire, and annually thereafter. Training records
are maintained per organizational training policy.
