---
document_id: IFO_010
title: "Platform Annex — Windows Endpoints via Autopilot Device Preparation"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-13"
updated_at: "2026-05-14"
boundary: GCC-Moderate
canon_anchor: ADR-067
platform: windows-endpoint
publish_to_site: true
publication_style: narrative
published_at: docs/modernization/intune-first.qmd
---

# Platform Annex — Windows Endpoints via Autopilot Device Preparation

> Per-platform implementation of the five-phase Intune-first process
> for Windows endpoints. The process is the same as in
> [`../process.md`](../process.md); this annex specifies the
> platform-specific mechanics for each phase.
>
> **Default enrollment vector:** Windows Autopilot Device Preparation
> (Autopilot v2). Autopilot v1 (legacy profiles) remains a footnoted
> compatibility path for organizations not yet on v2.
>
> **Canonical join target:** Microsoft Entra Join. Domain-join is
> forbidden by ADR-001; HAADJ is forbidden by ADR-001.

---

## Phase 1 — Procure (Windows-specific)

The Phase 1 mechanics in [`../process.md`](../process.md) apply
without modification. Windows-specific intake fields:

- `asset_class` = `windows-endpoint` (laptop / desktop / Surface / 2-in-1)
- `vendor_program` is one of:
  - `autopilot-direct` — organization registers hardware hashes itself
    via Microsoft Graph
  - `autopilot-reseller` — reseller registers hardware hashes on the
    organization's behalf (CDW Autopilot pre-provisioning, Insight,
    Connection, etc.)

For `autopilot-reseller`, the procurement record's
`vendor_program_records[].registered_by` field captures whether the
reseller or the procurement system performed the registration. Both
are equally acceptable provided the OrgPath tag is correctly applied
in Phase 2.

---

## Phase 2 — Pre-stage (Windows Autopilot mechanics)

### 2.1 — Hardware-hash registration

The hardware hash is a base64-encoded composite of the device's TPM
attestation, BIOS serial, and other identifiers. It uniquely
identifies the physical device. Registration paths:

| Source | Method |
|---|---|
| Reseller-supplied | Reseller uploads via their integration with Microsoft Cloud Solution Provider APIs; appears in the organization's Autopilot device list within minutes |
| Organization-collected (existing devices) | `Get-WindowsAutopilotInfo` PowerShell script run on the device; output uploaded via Microsoft Graph |
| Vendor pre-provisioned | OEM ships device already registered in the organization's tenant (HP, Dell, Lenovo) — no separate upload needed |

For Intune-first net-new procurement, the recommended path is
**vendor pre-provisioned via OEM**, with `autopilot-reseller` as
the secondary path. Organization-collected registration is an
exception path for hardware that arrived without pre-registration.

### 2.2 — Group Tag carries OrgPath

The Autopilot device record supports a `groupTag` field
(persisted on the `windowsAutopilotDeviceIdentity` Graph resource).
This bundle's convention:

```
groupTag = "OrgPath:" + asset_orgpath
```

For example, a device for `/Root/Finance/Accounting/AccountsReceivable`
carries:

```
groupTag = "OrgPath:/Root/Finance/Accounting/AccountsReceivable"
```

The procurement system writes this Group Tag at the same time it
writes the hardware hash. The Group Tag is the carrier signal that
the runtime OrgPath stamping script reads in Phase 4.

### 2.3 — Deployment profile assignment

The Autopilot device is assigned to a deployment profile via dynamic
group membership. The membership rule selects on Group Tag prefix:

```
(device.devicePhysicalIDs -any (_ -startsWith "[OrderID]:OrgPath:"))
```

This dynamic group is evaluated by Entra ID and includes every device
with an OrgPath-prefixed Group Tag. The deployment profile assigned
to this group:

- **Deployment mode:** User-driven (for personal assignments) or
  Self-deploying (for shared/kiosk/lab/service)
- **Join type:** Microsoft Entra Join (per ADR-001 — never
  Hybrid Microsoft Entra Join)
- **Out-of-box experience customizations:** Skip privacy settings,
  skip user license terms, language defaults, regional defaults
- **Enrollment status page:** Required, blocking, with the OrgPath
  stamping script in scope (see §4.3 below)

The deployment profile is created once per organization; per-device
customization happens via Group Tag values, not per-device profiles.

---

## Phase 3 — Position (Windows mechanics)

Phase 3 produces an entry in:

```
governance/autopilot/orgpath-mapping.csv
```

with columns: `SerialNumber`, `OrgPath`, `OrgNodeId`, `Source`,
`AssignmentType`, `RecipientUPN`. The Windows-specific dry-run
validation in Phase 3:

1. The pipeline retrieves the Autopilot device record by serial
2. Validates that `groupTag` starts with `OrgPath:`
3. Validates that the OrgPath in the Group Tag matches the
   procurement-record `asset_orgpath`
4. Validates that the deployment profile assignment matches the
   intended `asset_assignment_type` (User-driven for personal,
   Self-deploying for shared/kiosk/lab/service)
5. Validates that the enrollment status page configuration includes
   the OrgPath stamping script

A mismatch at any step is a Phase 3 blocking error.

---

## Phase 4 — Provision (Windows-specific enrollment)

The runtime enrollment flow:

### 4.1 — Out-of-Box Experience (OOBE)

The device powers on for the first time. OOBE detects the Autopilot
registration via the hardware hash hash sent to the Autopilot
service. The deployment profile downloads. The user is prompted only
to select keyboard layout, connect to network, and (for User-driven
deployments) sign in with their Entra ID credentials.

For Self-deploying mode (kiosk / shared / lab), no user sign-in is
required during OOBE — the device authenticates itself using the
TPM attestation from its hardware hash.

### 4.2 — Enrollment Status Page (ESP)

The ESP runs after OOBE completes. The ESP has three phases:

- **Device Setup** — runs as SYSTEM; applies device-targeted
  configuration profiles, certificates, and assignment of the
  governance App Registration's PKCS certificate (required for the
  OrgPath stamping script's certificate-based authentication)
- **Account Setup** — runs as the signed-in user (or as the
  Self-deploying mode's pseudo-user); applies user-targeted
  configurations and runs the OrgPath stamping script
- **Application Setup** — installs required applications

The Account Setup phase is where OrgPath stamping happens.

### 4.3 — OrgPath stamping script (modified for procurement-priority)

The OrgPath/Intune narrative §4.2 documents the canonical OrgPath
stamping script for user-derivation. This bundle modifies the
script's source-of-OrgPath ordering to put procurement-record values
first:

**Source priority for `$deviceOrgPath`:**

1. **Procurement record** — pulled from the Autopilot Group Tag (read
   via Graph against the device's own Autopilot record). This is the
   primary source.
2. **Hardware-hash mapping CSV** — the
   `governance/autopilot/orgpath-mapping.csv` file, pre-staged to the
   device via a configuration profile. This is the secondary source,
   used if the Group Tag is malformed or empty.
3. **User derivation** — read the provisioning user's OrgPath from
   their Entra ID user object. This is the tertiary fallback for
   personally-assigned devices when neither Group Tag nor mapping CSV
   carries a value.
4. **Quarantine** — `/UNPOSITIONED`. The terminal fallback when no
   OrgPath source produces a valid value.

The script writes `$deviceOrgPath` to the device object's OrgPath
extension attribute via Graph (`Update-MgDevice`), per the
narrative's existing implementation.

The reordering preserves the runtime user-derivation path as a
fallback (which is critical for organizations that have not yet
implemented procurement-side integration) while making procurement-
record values authoritative when available. Existing deployments that
rely on user-derivation continue to function; deployments that
implement procurement-side integration get deterministic OrgPath
without further changes.

### 4.4 — Dynamic group convergence

After OrgPath is stamped, Entra ID's dynamic group membership engine
re-evaluates the device against all rules referencing the OrgPath
extension attribute. Convergence latency varies; for production
deployments, expect 5–30 minutes for the device to appear in its
ORG-NODE-* and ORG-BRANCH-* groups.

The ESP's Account Setup phase can wait for membership convergence by
polling Get-MgGroupTransitiveMember against an expected group. The
OrgPath/Intune narrative §6.2 documents the post-stamp Intune sync
request that accelerates the device's first compliance evaluation.

### 4.5 — First compliance evaluation

After the device appears in its branch group, the compliance policies
assigned to that branch group are evaluated. For most policies,
evaluation completes within minutes of group membership. The device's
compliance state transitions to `Compliant` (or `NonCompliant` if
the device fails the policy — typically due to Secure Boot,
BitLocker, or TPM gating).

A compliant device satisfies Conditional Access's compliance grant
control. The user can now access organizational resources. The
device is out of OOBE/ESP and into productive use.

---

## Phase 5 — Validate (Windows-specific checks)

The full validation checklist is in
[`../validation-and-evidence.md`](../validation-and-evidence.md).
Windows-specific items:

- [ ] Device join type is **Microsoft Entra Join** (not Hybrid, not
      Workplace Join, not AAD Registered)
- [ ] Device's Autopilot deployment profile is the procurement-
      assigned profile (not a default profile that happened to apply)
- [ ] The Group Tag on the Autopilot device record matches
      `OrgPath:{asset_orgpath}` from the procurement record
- [ ] The OrgPath extension attribute on the Entra device object
      matches the procurement-record `asset_orgpath`
- [ ] The Intune device category matches the OrgTree node type per
      the narrative §6.2 mapping
- [ ] The compliance policy is the correct branch policy (not just a
      baseline policy, unless the asset is at the root branch)
- [ ] No HAADJ artifacts present on the device (no `dsregcmd /status`
      indication of Domain-Joined: YES; no AzureAdJoined: YES paired
      with DomainJoined: YES)

---

## Anti-patterns explicitly forbidden

The following Windows-specific patterns are forbidden by this
doctrine for net-new assets:

- **AD domain join.** No new endpoint is domain-joined. ADR-001.
- **Hybrid Azure AD Join (HAADJ).** Forbidden for new devices.
  ADR-001.
- **Manual AAD registration via Settings → Accounts → Access
  work or school.** This is user-driven manual enrollment; it is
  exception path A only.
- **SCCM-led provisioning followed by Intune co-management
  enablement.** SCCM is the migration surface; net-new assets do not
  enter SCCM. Pillar 4.
- **Provisioning Packages (.PPKG) for offline provisioning** outside
  of disconnected-network exception cases that have a documented
  exception grant. The provisioning package mechanism produces the
  same governance gap as offline provisioning generally — it
  bypasses zero-touch enrollment.
- **Device deployment via image (WIM) with offline join.** Same
  rationale as Provisioning Packages — bypasses enrollment-time
  governance.

If any of these patterns is operationally required for a specific
asset class, an exception grant is required per
[`../doctrine.md`](../doctrine.md) §4.

---

## Vendor-specific notes

### CDW (Autopilot pre-provisioning reseller)

CDW's Autopilot pre-provisioning service registers hardware hashes
into the customer tenant before shipping. CDW's portal supports
arbitrary Group Tag assignment as part of the order configuration —
the procurement system supplies the OrgPath-tagged value at order
time, CDW writes it during their fulfillment pipeline.

### HP Dell Lenovo (OEM direct registration)

OEM direct registration via the manufacturer's portal supports Group
Tag assignment. The procurement system supplies the value via the
OEM's order API.

### Direct purchase without reseller integration

For purchases where neither the OEM nor a reseller supports
pre-registration with Group Tag, the procurement team must collect
hardware hashes after delivery and register them via Microsoft Graph.
This is a slower path; if used routinely, vendor selection should be
revisited per the latency notes in [`../process.md`](../process.md).

---

## References

- [ADR-001 — HAADJ Deprecated](../../../canon/adr/adr-001-haadj-deprecated-entra-join-only.md) (controlling precedent for Windows endpoint join target)
- OrgPath/Intune narrative §4 (Autopilot enrollment mechanics) — `inbox/drafts/complete-narrative/source-docx/OrgPath and Microsoft Intune — Structural Device Governance at Enterprise Scale.md`
- OrgPath/Intune narrative §6 (post-stamp Intune sync) — same document
- [Microsoft Learn — Autopilot Device Preparation overview](https://learn.microsoft.com/en-us/autopilot/device-preparation/overview)
- [Microsoft Learn — Cloud-native endpoints planning guide](https://learn.microsoft.com/en-us/mem/solutions/cloud-native-endpoints/cloud-native-endpoints-planning-guide)
