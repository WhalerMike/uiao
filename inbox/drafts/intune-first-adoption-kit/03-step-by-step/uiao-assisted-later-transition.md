# Phase III — Later Transition: Step-by-Step Laptop Onboarding (UIAO-Assisted)

## Audience and purpose

This guide is for new IT staff learning the hybrid laptop onboarding process in an environment where UIAO governance is in place. The mechanics of device provisioning are identical to the without-UIAO version (PXE boot, imaging, domain join, hybrid registration, Intune enrollment); UIAO adds reliable detection of the silent failure modes that are characteristic of Phase III, automated reconciliation across the five systems where device identity can appear, canonical-specification-driven policy assignment, and continuous evidence emission.

Read [`without-uiao-later-transition.md`](without-uiao-later-transition.md) for the underlying procedure, then read this document for the UIAO-specific touchpoints. Read [`uiao-assisted-legacy.md`](uiao-assisted-legacy.md) and [`uiao-assisted-early-transition.md`](uiao-assisted-early-transition.md) for the foundational UIAO touchpoints that carry forward into Phase III.

The phase architecture under UIAO is described in [`01-customer-narrative/uiao-assisted-later-transition.md`](../01-customer-narrative/uiao-assisted-later-transition.md).

## Quick reference

| Question | Answer |
|---|---|
| Is PXE boot used? | **Yes** — identical to without-UIAO. UIAO does not change the imaging mechanic. |
| Is imaging used? | **Yes** — same reference image, same task sequence baseline plus the Phase III hybrid join and MDM enrollment additions. |
| Is Autopilot used? | **Sometimes** — for greenfield cohorts. UIAO's device-plane OrgPath binding works equivalently whether the device arrives via PXE imaging or via Autopilot pre-registration. |
| Is a barcode scanner used? | **Yes** — at receiving, updating both the asset database and the canonical device record. |
| Is the device hybrid-joined? | **Yes** — and UIAO observes the hybrid join attempt, surfaces silent failures within hours, and reconciles the resulting cloud identity against the canonical device record. |
| Does the device enroll in Microsoft Intune? | **Yes** — and UIAO verifies the enrollment, observes the configuration profiles delivered, and reconciles the Intune managed device record against the canonical record. |
| How long does provisioning take? | Same as without-UIAO: 3-4 hours elapsed. UIAO does not add to provisioning time but adds confidence that the device is genuinely ready. |

## What UIAO adds versus the without-UIAO version

Phase III without UIAO is the operationally most complex phase. The without-UIAO failure modes are characteristic: silent hybrid join failures that surface weeks later when Conditional Access denies the user; duplicate device objects accumulating across re-imaging cycles; identity records disagreeing across the five systems (Active Directory, Microsoft Entra ID, Microsoft Intune, Configuration Manager, Microsoft Autopilot for hybrid pilots); compliance policies that produce different results than the configuration profiles they evaluate; co-management workload assignments that drift from the canonical migration plan.

UIAO addresses each of these failure modes at the structural level. The drift engine watches for silent failures continuously. The reconciliation engine identifies disagreement across the five systems. The canonical specification drives compliance policy and workload assignment automatically, eliminating the drift between intent and implementation. The result is that the Phase III provisioning workflow becomes operationally tractable rather than operationally fragile.

## Software inventory at provisioning completion

Identical to the without-UIAO version. UIAO does not add a device-side agent in Phase III; the substrate reads from the central directories and management surfaces.

## Pre-arrival activities

The without-UIAO pre-arrival activities apply (procurement, vendor preparation, asset tags, reference image, task sequences, hybrid join configuration verification, Intune tenant readiness, co-management workload assignment, cloud identity preparation).

**UIAO-driven additions**:

1. **Canonical device record creation at PO issuance**: As in Phase II, UIAO creates a placeholder canonical record with OrgPath assigned when the purchase order is issued.

2. **Device-plane OrgPath specification**: UIAO computes the device-plane OrgPath that will be projected onto the device's records (both Active Directory computer object and Microsoft Entra ID device object) when the device is provisioned. The device-plane OrgPath is derived from the assigned user's user-plane OrgPath (established in Phase II) modified by device-class attributes (form factor, asset class, ownership classification, security tier).

3. **Migration cohort assignment**: UIAO assigns the device to a migration cohort based on its OrgPath and the canonical migration plan. Cohort 1 devices may go through Autopilot rather than PXE imaging; cohort 2 devices follow the traditional PXE-imaged hybrid path; cohort 3 devices receive a specific workload-slider configuration. The cohort assignment determines which task sequence variant the device will use.

4. **Workload-slider verification**: UIAO checks that the canonical workload assignment for the device's cohort matches the actual workload slider settings in Configuration Manager. Drift between canonical and actual surfaces as a finding before any device in the cohort is provisioned.

5. **Compliance policy verification**: UIAO checks that the compliance policy that will apply to the device matches the canonical compliance specification for its OrgPath. Drift surfaces as a finding.

## Step 1 through Step 5: Device receipt through PXE task sequence start

Identical to without-UIAO. The receiving scan updates the canonical device record (as in Phase I and Phase II UIAO-assisted). The task sequence wizard pre-populates the device class from the canonical record, including the cohort-specific variant.

## Step 6: Task sequence execution

Identical to without-UIAO in mechanics. The Phase I core steps run, then the Phase III additions (hybrid join scheduled task, Microsoft Entra ID device registration, automatic MDM enrollment, Intune configuration profile delivery, compliance evaluation, Defender for Endpoint enrollment, Intune Win32 app delivery).

**UIAO touchpoints during task sequence**:

- As the device joins the domain, UIAO observes the new Active Directory computer object via the AD adapter and adds it to the canonical reconciliation queue.
- As the hybrid join attempts to complete, UIAO observes the registration in Microsoft Entra ID (or the absence of registration, in failure cases) via the Entra adapter.
- As Microsoft Intune enrollment completes, UIAO observes the new managed device record via the Intune adapter.
- As Configuration Manager registers the new client, UIAO observes the new client record via the ConfigMgr adapter.

UIAO's reconciliation engine joins these observations to the canonical device record and to one another. By the time the task sequence completes, the canonical record shows the device's state across all five surfaces (Active Directory, Microsoft Entra ID, Microsoft Intune, Configuration Manager, and Autopilot where applicable). If any expected surface is missing, the gap surfaces as a finding.

## Step 7: Post-imaging verification

The without-UIAO verification (Phase I core verifications plus Phase III hybrid join, MDM enrollment, Intune profile state, compliance state, Defender onboarding) applies.

**UIAO-assisted verification replaces the multi-console manual checks with a single canonical query**: The technician queries UIAO for the device's canonical state. The expected response shows:

- Active Directory computer object: present, in expected OU, OrgPath stamped
- Microsoft Entra ID device object: present, join type "Microsoft Entra hybrid joined," OrgPath projected, linked to the on-premises computer object
- Microsoft Intune managed device record: present, expected primary user, expected compliance state, configuration profiles delivered
- Configuration Manager client: present, reporting policy
- Five-system reconciliation: all five records (or all four for non-Autopilot devices) agree on serial number, device name, hardware identifiers
- OrgPath classification: matches canonical specification
- Compliance evaluation: Compliant
- Configuration profiles: all in "Succeeded" state
- Microsoft Defender for Endpoint: onboarded (if in scope)
- No open drift findings on the device
- Evidence ledger entries: device receipt, task sequence start and completion, domain join, hybrid join, Intune enrollment, profile applications, compliance evaluation

A device with all green indicators is ready for handoff. Any red or yellow indicator surfaces with the specific cause and the suggested remediation. The diagnostic time for a problem device collapses from manual cross-console investigation to a single UIAO query.

## Step 8: Asset record update and user assignment

Same as Phase II UIAO-assisted. UIAO observes the asset database update and mirrors it into the canonical record. The KYC layer verifies the device-user binding against current HR state.

## Step 9: Pre-handoff cloud identity verification

Same as Phase II UIAO-assisted. The technician queries UIAO for the unified canonical view of user cloud identity and device readiness. The without-UIAO multi-console verification collapses to a single query.

## Step 10: User handoff

Repack, ship or hand off, welcome packet includes the canonical device record identifier for helpdesk support lookups.

## Step 11: User first sign-in

The user signs in to Windows with domain credentials, opens cloud applications, encounters the device-aware Conditional Access policies. Because the device is verified hybrid-joined and Intune-compliant before handoff, the Conditional Access evaluation succeeds and the user reaches their cloud applications without unexpected denial.

UIAO observes the first sign-in via the Microsoft Entra sign-in log adapter and emits an evidence record marking the device's transition to active operation.

## Continuous monitoring after handoff

After handoff, UIAO continues monitoring at the standard cadence. Phase III monitoring is broader than Phase I/II because there is more surface area to observe:

- Device-plane drift on the Active Directory computer object (OU placement, group memberships, machine credential health)
- Device-plane drift on the Microsoft Entra ID device object (join state, group memberships, compliance state)
- Microsoft Intune policy state drift (configuration profiles that fail to apply, applications that fail to install, compliance policies that flip between compliant and non-compliant)
- Configuration Manager client health (client agents that stop reporting, policy that fails to apply, software updates that fail to install)
- Five-system reconciliation drift (records that begin to disagree after their initial reconciliation)
- Microsoft Defender for Endpoint signals (risk scores that elevate, vulnerabilities detected)

Findings route to the operational queue. Common Phase III findings that route to deployment or helpdesk teams include:

- Devices that have lost their hybrid join state (typically because of a TPM event or a credential issue)
- Devices that have stopped checking in to Intune (typically because of MDM channel corruption)
- Devices with conflicting GPO and Intune configuration (typically because a workload slider transition has not completed cleanly)
- Devices that have become duplicates in Microsoft Entra ID (typically because of a re-image without proper cleanup of the prior object)

## Migration cohort transitions

In addition to provisioning new devices, Phase III involves transitioning existing devices through migration cohorts. UIAO drives these transitions from the canonical migration plan:

1. **Workload-slider transition**: The canonical specification dictates that workload X moves from Configuration Manager to Microsoft Intune for cohort Y on date Z. UIAO generates the corresponding Configuration Manager collection and slider update, executes the change at the scheduled time, and observes the resulting state on each affected device.

2. **Device cohort promotion**: A device that has satisfied all readiness criteria for promotion to a different cohort (typically promotion from cohort 2 to cohort 1, indicating readiness for full transition to Phase IV) is identified by the migration risk scoring engine and routed to the appropriate transition workflow.

3. **Device retirement**: A device that has reached end-of-life per canonical specification (hardware refresh date, end of warranty, end of support for the OS version) is queued for retirement, with the user notified of the upcoming replacement and the asset record updated.

Each transition emits evidence records to the canonical ledger, producing the audit substrate for retrospective compliance attestation.

## Tools and equipment required

Same as the without-UIAO version. Access to the UIAO console via web browser is sufficient for all UIAO touchpoints. The multi-console workflows that the without-UIAO version requires (Microsoft Entra admin center, Microsoft Intune admin center, Configuration Manager admin console, Microsoft Defender XDR portal) are replaced by the unified UIAO query interface for routine checks; the underlying consoles remain available for deep investigation.

## Common failures during provisioning

The without-UIAO Phase I, II, and III failure modes (PXE failure, driver mismatch, domain join failure, application failure, BitLocker failure, cloud sign-in issues, MFA issues, license issues, silent hybrid join failure, failed MDM enrollment, compliance evaluation stuck, conflicting GPO and Intune policy, duplicate device objects) all apply in their mechanics.

UIAO's contribution to these failure modes:

- Silent hybrid join failure → detected by the drift engine within hours, surfaced as a finding with suggested remediation
- Duplicate device objects → detected at creation by the reconciliation engine; stale duplicates routed to automated retirement workflow
- Compliance evaluation stuck → observed by the Intune adapter, surfaced as a finding with the specific stuck setting identified
- GPO/Intune conflict → detected by the cross-plane policy reconciliation, surfaced with which canonical-specification value should apply
- MDM enrollment failure → observed by the Entra and Intune adapters, surfaced with the specific failure category (scope, license, network, TPM, etc.)

The failure modes themselves are not eliminated by UIAO; the mechanism is still Microsoft technology and still fails in characteristic ways. What UIAO eliminates is the time between failure and detection, and the manual investigation work between detection and remediation.

## Total time and resource cost per device

Imaging time per device: same as without-UIAO (3 to 4 hours elapsed, 45 to 60 minutes hands-on).

UIAO query overhead in the workflow: roughly 3 to 5 minutes per device (the unified verification query at Step 7 replaces several minutes of multi-console verification, with net savings).

The substantial UIAO cost savings in Phase III are not at the imaging-station level — they are at the operational-overhead level. The without-UIAO Phase III workflow consumes significant engineering effort in: silent hybrid join failure investigation (typically days per incident before UIAO detection), five-system reconciliation work during incidents (hours per incident), co-management workload assignment maintenance (hours per workload transition), audit evidence assembly (days per audit window). UIAO converts most of this from human labor to substrate operation, with corresponding reduction in incident severity and audit cost.
