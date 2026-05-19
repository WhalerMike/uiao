# Phase I — Legacy: Step-by-Step Laptop Onboarding (UIAO-Assisted)

## Audience and purpose

This guide is for new IT staff learning the legacy laptop onboarding process in an environment where UIAO governance is in place. The mechanics of provisioning are identical to the without-UIAO version (PXE boot, imaging, domain join, Group Policy, Configuration Manager); UIAO adds upstream specification, automated reconciliation, drift detection, and evidence emission at specific checkpoints along the workflow. A new technician should read [`without-uiao-legacy.md`](without-uiao-legacy.md) first to learn the underlying process, then read this document to understand the UIAO-specific touchpoints.

The phase architecture under UIAO is described in [`01-customer-narrative/uiao-assisted-legacy.md`](../01-customer-narrative/uiao-assisted-legacy.md).

## Quick reference

| Question | Answer |
|---|---|
| Is PXE boot used? | **Yes** — identical to without-UIAO. UIAO does not change the imaging mechanic. |
| Is imaging used? | **Yes** — same reference image, same task sequence, same WIM-based deployment. |
| Is a barcode scanner used? | **Yes** — and at receiving the scan additionally creates or updates the canonical device record in UIAO, not just the asset database row. |
| Is the laptop joined to a domain? | **Yes** — to the on-premises Active Directory domain. |
| Does the user touch the device before handoff? | **No** — same as without-UIAO. |
| How long does provisioning take? | Same as without-UIAO: 2-3 hours elapsed, 30-45 minutes hands-on. UIAO does not add to provisioning time. |
| What does UIAO change for the technician? | UIAO validates the canonical state of the device after provisioning; the technician confirms UIAO has accepted the device into canonical state before handoff. |

## What UIAO adds versus the without-UIAO version

UIAO in the legacy phase is observational and overlay-mode: it does not perform the imaging, does not adjust Group Policy, does not change Active Directory or Configuration Manager. It reads from those systems, projects canonical state onto the device record, watches for drift, and emits evidence. The technician's hands-on workflow is unchanged in mechanics; what changes is the surrounding governance posture and a small number of verification touchpoints.

The UIAO-specific touchpoints in the legacy provisioning workflow are:

1. **Pre-arrival**: The canonical device record is pre-populated from procurement data before the device arrives at receiving.
2. **Receiving**: The asset tag scan additionally updates the canonical device record with the as-received state.
3. **Post-imaging verification**: An additional check confirms UIAO has reconciled the new device's identity across Active Directory, Configuration Manager, and the asset database.
4. **Pre-handoff**: An additional check confirms UIAO has emitted the expected evidence records for this provisioning event.
5. **Continuous monitoring**: After handoff, UIAO continues to monitor the device for Group Policy drift, stale-object accumulation, and security baseline state, surfacing findings to the operational queue.

## Software inventory at provisioning completion

Identical to the without-UIAO version. UIAO does not add agent software to the device itself in the legacy phase — UIAO reads from Active Directory, Configuration Manager, and other systems centrally. There is no UIAO client agent on the device.

## Pre-arrival activities

Same as without-UIAO, with one addition: the procurement system feeds purchase-order data into UIAO at PO issuance. UIAO creates a placeholder canonical device record indicating "device on order, expected arrival, OrgPath assigned." The OrgPath is determined from the purchase order's metadata (the requesting business unit, the cost center, the assigned user from the requisition).

When the device arrives, the receiving technician's scan updates the placeholder record with the actual hardware identifiers (serial number from the laptop, asset tag from the corporate tag).

## Step 1: Device receipt and inspection

Identical to the without-UIAO procedure (verify against PO, inspect for damage, scan serial number, affix and scan asset tag, stage in imaging area).

**UIAO touchpoint**: When the receiving technician scans the asset tag, the receiving system both creates the asset database row (as in without-UIAO) and posts the hardware identifiers to UIAO. UIAO matches the identifiers to the pre-existing placeholder canonical record (from pre-arrival), updates the record's state to "Received, ready for provisioning," and emits a structured evidence record to the canonical ledger marking the receipt event. The technician does not see additional UI; the integration is server-to-server.

## Step 2: BIOS / UEFI verification

Identical to the without-UIAO procedure. UIAO does not interact with firmware configuration directly; the technician verifies UEFI boot mode, Secure Boot enabled, TPM active, and boot order as documented in the without-UIAO version.

## Step 3: Network connectivity

Identical to the without-UIAO procedure. Wired Ethernet to the imaging subnet.

## Step 4: PXE boot to Windows Preinstallation Environment

Identical to the without-UIAO procedure. PXE boot, ConfigMgr boot image delivery, WinPE loads, task sequence wizard appears.

**UIAO touchpoint** (transparent to the technician): The task sequence wizard, when configured for the UIAO-integrated environment, queries the canonical device record by serial number and uses the OrgPath classification to pre-populate the device-class selection. The technician confirms the selection rather than independently choosing the task sequence; the canonical record drives the choice. If the canonical record disagrees with the task sequence the technician would otherwise pick, a finding is raised before the task sequence proceeds.

## Step 5: Task sequence execution

Identical to the without-UIAO procedure in mechanics. The reference image applies, drivers inject, the device reboots and joins the domain, the ConfigMgr client installs, applications install, Group Policy applies, BitLocker enables, the device reboots into its final state.

**UIAO touchpoint** (continuous, server-side): As the task sequence progresses, the ConfigMgr site database is updated with the new client record, and the Active Directory directory is updated with the new computer object. UIAO's reconciliation engine, running continuously, observes the new records appearing and adds them to the canonical device record. The reconciliation typically completes within fifteen minutes of the task sequence completion.

## Step 6: Post-imaging verification

The without-UIAO verification (domain join check, ConfigMgr client check, BitLocker check, Group Policy check, event log review) is performed identically.

**Additional UIAO verification step**: The technician queries UIAO for the canonical state of the new device by serial number. The expected response shows:

- Canonical device record reconciled across Active Directory (computer object present), Configuration Manager (client record present and reporting), and the asset database (assignment in place)
- OrgPath classification matches the task sequence's class
- Compliance state: provisional (the device will move to "compliant" after the first drift-engine evaluation, typically within an hour of task sequence completion)
- No outstanding drift findings on the device
- Evidence ledger entries present for: device receipt, task sequence start, task sequence completion, domain join, ConfigMgr enrollment, BitLocker enablement

If any of these is absent or incorrect, the device is not yet ready for handoff. The technician investigates the gap — typically a sync delay (UIAO has not yet reconciled across all the source systems) or a configuration issue (the task sequence completed with one or more steps in an unexpected state).

## Step 7: Asset record update and user assignment

The asset database update happens as in the without-UIAO procedure.

**UIAO behavior**: The asset database update is mirrored into the canonical device record automatically through the asset database adapter. The technician updates the asset database (the system of record for asset assignment); UIAO observes the change and updates the canonical record. The user assignment from the asset database is checked against the user's current human-resources state through the KYC layer; if the assigned user is on leave, in a different business unit than expected, or otherwise in an unexpected state, a finding is raised.

## Step 8: User handoff

Repack, ship or hand off, user signs in on first use. Same as without-UIAO.

**UIAO behavior**: The user's first sign-in produces a sign-in event captured in the Active Directory event log; UIAO's adapter observes the event and emits an evidence record marking "Device entered active operation: first user sign-in by [user], device [identifier], OrgPath [classification]." The device is now under continuous UIAO monitoring.

## Continuous monitoring after handoff

Once the device is in active use, UIAO continues monitoring at the standard cadence — typically daily Group Policy drift evaluation, continuous reconciliation of the device's identity across the source systems, security baseline state observation, and inclusion in the standard inventory and compliance reports.

The technician does not interact with UIAO further unless a finding emerges that requires hands-on remediation. Common findings that route to a deployment technician include:

- Devices that show domain-join drift (the secure channel has broken, requiring rejoin)
- Devices that have fallen off the ConfigMgr client roster (the client has stopped reporting, suggesting agent corruption)
- Devices that have drifted on security baseline state (BitLocker has been disabled locally, antivirus has stopped, Windows Firewall has been disabled)
- Devices flagged for retirement (the assigned user has departed and the canonical specification triggers retirement)

Each finding routes through the operational queue with the relevant context, the suggested remediation, and the canonical specification version that drove the finding.

## Tools and equipment required

Same as without-UIAO. UIAO does not require additional tools at the imaging station. Access to the UIAO console for post-imaging verification can be through a web browser on the imaging workstation; no specialized client is required.

## Common failures during provisioning

The without-UIAO failure modes (PXE boot failure, driver mismatch, domain join failure, application failure, BitLocker failure) all apply identically.

**Additional UIAO-specific failure modes**:

- **Canonical record absent at receiving**: The procurement system did not feed the PO data to UIAO, or the feed failed. The placeholder record is missing. The receiving scan creates an unmatched record. Resolution: investigate the procurement-to-UIAO feed; the device can be provisioned and the canonical record reconciled retrospectively.

- **OrgPath mismatch at task sequence selection**: The canonical record's OrgPath suggests a different task sequence than the technician would manually select. Resolution: confirm the canonical OrgPath is correct (consult procurement and the assigned user's role); if the OrgPath is wrong, update it in UIAO before proceeding.

- **Reconciliation delay at post-imaging verification**: UIAO has not yet reconciled the new device's records across all source systems. Resolution: wait fifteen to thirty minutes and re-query; if reconciliation does not complete, investigate the adapter logs.

- **Drift finding on a freshly-provisioned device**: UIAO detects that the freshly-imaged device does not match its canonical compliance baseline. Resolution: investigate the specific finding — typically the device has not yet completed all post-imaging policy applications, and the finding will clear on its own; persistent findings indicate an actual baseline issue.

## Total time and resource cost per device

Same as without-UIAO. The UIAO touchpoints add roughly two minutes of additional verification time per device (the canonical state query in Step 6), partially offset by reduced asset reconciliation work later (because the records are kept in agreement continuously rather than reconciled manually during audits).

The substantial cost savings UIAO provides in the legacy phase are not at the per-device imaging level — they are at the operational-overhead level (continuous drift detection avoiding incident-response work, automated stale-object cleanup, continuous evidence emission avoiding audit-assembly project work). The imaging technician's per-device time is essentially unchanged.

## When the user calls the helpdesk

In the without-UIAO environment, a user calling about a provisioning-related issue (the device not joining the domain, Group Policy not applying, an application missing) requires the helpdesk to query Active Directory, Configuration Manager, and the asset database separately, joining the data by hand.

In the UIAO-assisted environment, the helpdesk queries UIAO by serial number, asset tag, or assigned user, and the canonical device record returns a unified view: identity reconciliation state, current drift findings, recent evidence ledger entries, last successful Group Policy refresh, last successful ConfigMgr policy sync, BitLocker state, applied application list. The diagnostic question collapses from minutes of investigation to seconds of lookup.

This is one of the principal day-to-day operational benefits of UIAO in the legacy phase: not changes to the provisioning mechanism, but radical compression of the time required to answer the question "what is the current canonical state of this device" when something goes wrong later.
