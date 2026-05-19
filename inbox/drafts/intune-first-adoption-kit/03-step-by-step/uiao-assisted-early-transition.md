# Phase II — Early Transition: Step-by-Step Laptop Onboarding (UIAO-Assisted)

## Audience and purpose

This guide is for new IT staff learning the early transition laptop onboarding process in an environment where UIAO governance is in place. The device-side mechanics (PXE, imaging, domain join, Group Policy, Configuration Manager) are identical to the without-UIAO version of this phase, which is identical to the Phase I Legacy mechanics. What changes is the cloud identity preparation pipeline, which is significantly more automated and reliable under UIAO than under the manual ticket-driven workflows typical without UIAO.

Read [`without-uiao-early-transition.md`](without-uiao-early-transition.md) for the underlying procedure, then read this document for the UIAO-specific automation and verification touchpoints.

The phase architecture under UIAO is described in [`01-customer-narrative/uiao-assisted-early-transition.md`](../01-customer-narrative/uiao-assisted-early-transition.md).

## Quick reference

| Question | Answer |
|---|---|
| Is PXE boot used? | **Yes** — identical to without-UIAO. |
| Is imaging used? | **Yes** — same reference image, same task sequence. |
| Is a barcode scanner used? | **Yes** — and the scan updates both the asset database and the canonical device record. |
| Is the laptop joined to a domain? | **Yes** — on-premises Active Directory. |
| Does the device have a cloud identity? | **No** — only the user has a cloud identity. |
| How long does provisioning take? | Same as without-UIAO: 2-3 hours elapsed. |
| What does UIAO change in Phase II? | Cloud identity is fully pre-provisioned and verified by UIAO before device handoff; license assignment, mailbox provisioning, group memberships, and MFA enrollment are automated from the human-resources joiner event; the user's first sign-in to cloud apps is predictably smooth. |

## What UIAO adds versus the without-UIAO version

Phase II without UIAO has a characteristic operational pattern: device-side provisioning is straightforward (identical to Phase I), but the cloud-side preparation involves multiple parallel manual steps (license assignment, mailbox provisioning, group memberships, MFA enrollment) that are easy to miss for individual users. The result is that some users receive their device, sign in to Windows successfully, and then encounter a cloud-side gap on first sign-in to Outlook or Teams (no mailbox, no license, MFA not enrolled). The helpdesk absorbs the resulting volume.

UIAO eliminates the cloud-side gap by treating the human-resources joiner event as the trigger for a coordinated provisioning sequence across all surfaces. By the time the device arrives at the user's hands, the user's cloud identity is fully ready: OrgPath assigned, license assigned, mailbox provisioned, OneDrive provisioned, group memberships in place, MFA factor enrolled (or enrollment campaign in flight with documented completion deadline), Conditional Access scope established. The user's first sign-in to cloud applications is predictably smooth.

## Software inventory at provisioning completion

Identical to the without-UIAO version. UIAO does not add agent software on the device.

## Pre-arrival activities

The device-side pre-arrival activities are identical to the without-UIAO version (procurement, vendor preparation, asset tag preparation, reference image maintenance, task sequence maintenance).

**UIAO-driven cloud identity preparation** runs as an automated sequence triggered by the human-resources joiner event for the user who will receive the device:

1. **HRIT joiner event arrives**: The HR system signals that a new hire (or role-changed user) is approaching their start date. The event includes the user's identity, organizational position, manager, start date, and assigned hardware request.

2. **OrgPath assignment**: UIAO computes the canonical OrgPath for the user from the HR data — business unit, region, security tier, employment classification, position in the management chain.

3. **On-premises Active Directory user object**: UIAO creates the AD user object in the appropriate organizational unit, with initial attributes populated from HR. The initial password is set per canonical specification (typically a complex temporary password delivered to the manager through a secure channel).

4. **Microsoft Entra Connect synchronization**: The new AD user object synchronizes to Microsoft Entra ID on the next sync cycle (typically within 30 minutes). UIAO projects OrgPath onto the cloud identity at synchronization time using directory extension attributes.

5. **License assignment**: UIAO assigns the Microsoft 365 license (E3, E5, or business-tier) derived from OrgPath. Licenses are mapped to OrgPath classifications in the canonical specification, so the same OrgPath always yields the same license.

6. **Mailbox provisioning**: With the license assigned, Exchange Online provisions a mailbox for the user. UIAO observes mailbox creation and emits an evidence record.

7. **OneDrive provisioning**: OneDrive for Business provisions the user's storage. UIAO observes provisioning and emits an evidence record.

8. **Group memberships**: UIAO assigns the user to security groups derived from OrgPath. The group memberships drive Conditional Access scoping, federated SaaS application access, and any role-based access entitlements.

9. **MFA enrollment campaign**: UIAO emails the user an invitation to enroll an MFA factor before their start date. The invitation directs the user to the My Sign-Ins portal, walks through factor selection, and confirms enrollment when complete. The enrollment is tracked against the user's UIAO record.

10. **Federated SaaS application provisioning**: For SaaS applications integrated with Microsoft Entra ID where the user's role requires access, UIAO triggers just-in-time provisioning or pre-provisioning according to the application's federation configuration.

11. **KYC attestation**: UIAO verifies that the cloud identity matches the HR data, that all required attributes are populated, that the assigned license is correct, that group memberships match the OrgPath-expected set, and that MFA enrollment is complete or in flight.

All of this completes before the user's start date, typically a week or more in advance. The device-side imaging then happens close to the start date, with the cloud identity already ready.

## Step 1 through Step 6: Device receipt through post-imaging verification

Identical to the without-UIAO version (which is identical to Phase I). Receive, BIOS verify, network connect, PXE boot, task sequence run, verify.

**UIAO touchpoints** at these steps mirror the Phase I UIAO-assisted touchpoints: the receiving scan updates the canonical device record; the task sequence wizard pre-populates the device class from the canonical record's OrgPath; the reconciliation engine observes the new domain join and ConfigMgr client registration.

## Step 7: Asset record update and user assignment

The asset database update happens as without-UIAO. UIAO observes the update and mirrors it into the canonical device record.

**UIAO additional behavior**: UIAO performs a KYC check on the device-user binding. The check verifies that the assigned user's employment state is "Active," that the user's OrgPath has not changed since the device was procured, that the assigned device class matches the user's role expectations, and that there are no open governance findings on the user (account flagged for security review, OrgPath drift, missing required training, etc.). Any anomaly is surfaced as a finding before handoff.

## Step 8: Pre-handoff cloud identity verification

The without-UIAO version of this step requires the technician to manually verify the cloud identity across multiple admin centers. The UIAO-assisted version replaces the manual checks with a single canonical-record query.

The technician queries UIAO by the user's identifier or the device's serial number. The expected response shows:

- User cloud identity present in Microsoft Entra ID, OrgPath projected
- Microsoft 365 license assigned, license type matches OrgPath
- Exchange Online mailbox provisioned, mailbox storage reachable
- OneDrive for Business provisioned, storage initialized
- Security group memberships match OrgPath-expected set
- MFA enrollment complete (at least one factor registered)
- Conditional Access scope established
- KYC attestation passing
- No open governance findings

If everything is green, the device is ready for handoff. If anything is red or yellow, the gap is surfaced with the suggested remediation — typically a sync delay (UIAO has not yet observed a recent provisioning step) or an HR data gap (an OrgPath-dependent attribute is missing from HR and needs to be filled in before the dependent provisioning step completes).

The diagnostic effort that the without-UIAO version requires (querying multiple admin centers, joining results by user identifier, interpreting the state per surface) collapses to a single canonical query.

## Step 9: User handoff

Repack the device, attach the welcome packet, ship or hand off in person. Same as without-UIAO.

The welcome packet under UIAO additionally references the user's MFA enrollment (already complete), the assigned cloud applications and their first-sign-in paths, and a contact path for the helpdesk that includes the canonical device record identifier (used by the helpdesk to look up the device's state instantly on a support call).

## Step 10: User first sign-in

The user signs in to Windows with their domain credentials, then opens Outlook or another Microsoft 365 client. The cloud sign-in proceeds smoothly because the cloud identity is fully ready — MFA enrolled in advance, license assigned, mailbox provisioned, Conditional Access scope established.

**UIAO observes the first sign-in**: The Microsoft Entra sign-in log records the first successful interactive sign-in from the new device's IP (or, on a managed network, from a managed-network-classified IP). UIAO's adapter captures the event and emits an evidence record: "Device entered active operation: first user sign-in by [user], device [identifier]." The device transitions from "provisioned, handed off, awaiting first sign-in" to "active operation" in the canonical record.

## Continuous monitoring after handoff

After handoff, UIAO continues monitoring at the standard cadence for both the device side (Group Policy drift, ConfigMgr client health, security baseline state) and the cloud identity side (KYC attestation continuity, license entitlement correctness, group membership consistency, MFA factor health, Conditional Access policy state).

Findings that emerge in active operation route to the operational queue. Common cloud-side findings include:

- A user whose OrgPath has changed (because of a role move or transfer) but whose group memberships have not updated correspondingly
- A user whose MFA factor has aged past the configured refresh interval (typically 90 to 180 days) and requires re-attestation
- A user whose license has been removed accidentally (perhaps through manual admin action that should have gone through a governed workflow)
- A user whose KYC attestation has lapsed (HR data has not been refreshed within the window required for high-tier OrgPath classifications)

Each finding routes with context, suggested remediation, and the canonical specification version that drove the finding.

## Tools and equipment required

Same as the without-UIAO version. UIAO does not require additional tools at the imaging or handoff workstation. Access to the UIAO console via web browser is sufficient for all UIAO touchpoints.

## Common failures during provisioning and first sign-in

The without-UIAO failure modes (PXE failure, driver mismatch, domain join failure, Conditional Access denial on first sign-in, MFA enrollment incomplete, license missing, modern auth issues, Entra Connect lag) all apply identically in mechanics. UIAO eliminates most of these as production failure modes by detecting them before handoff:

- License missing → detected at Step 8 pre-handoff verification, resolved before handoff
- Mailbox not provisioned → detected at Step 8, resolved before handoff
- MFA not enrolled → enrollment campaign in flight or completed, surfaced as a finding if not complete
- Entra Connect lag → detected as a reconciliation delay, surfaced with the suggested remediation (force a sync, or wait)

The class of failure that survives into production under UIAO is much narrower: drift that emerges after handoff (a license accidentally removed, a group membership manually altered, a Conditional Access policy modified) is detected within hours by the drift engine and routed to remediation.

## Total time and resource cost per device

Imaging time per device: same as without-UIAO and same as Phase I (2 to 3 hours elapsed, 30 to 45 minutes hands-on).

Cloud identity preparation per user: dramatically reduced under UIAO because the work is automated from the HRIT event rather than manually performed per user. The identity team's per-user time is essentially zero for routine provisioning; the team's effort concentrates on exception handling, canonical specification maintenance, and the underlying integrations.

For an organization onboarding 50 to 100 users per month, the cloud identity preparation savings under UIAO typically free up 0.5 to 1 full-time-equivalent of identity team effort, which redirects to higher-value work (Conditional Access policy refinement, federated SaaS application onboarding, KYC attestation review).
