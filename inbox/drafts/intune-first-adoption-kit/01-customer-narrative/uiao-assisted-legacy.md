# Phase I — Legacy: UIAO-Assisted Detailed Reference

## How to read this document

This document is the UIAO-assisted detailed reference for the legacy phase of Windows endpoint governance. It parallels the structure of the without-UIAO companion ([`without-uiao-legacy.md`](without-uiao-legacy.md)) and describes, section by section, how the organization's internal UIAO governance framework augments the legacy on-premises estate. It is intended for internal strategy, architecture, governance, and compliance audiences who want to understand the governance overlay applied to a conventional Active Directory environment. Readers without UIAO context should consult the without-UIAO companion first; readers comparing the two should expect parallel section organization.

The legacy phase, as defined in the without-UIAO companion, is the operating model in which devices are joined to on-premises Active Directory, governed by Group Policy, supplied by Microsoft Configuration Manager, and patched and secured by on-premises infrastructure, with no cloud identity, no mobile device management plane, and perimeter-based trust. UIAO does not transform this architecture; it observes, specifies, reconciles, and emits evidence on top of it. The user-facing surface, the administrator-facing surface, and the underlying mechanics remain pure Microsoft. What changes is the governance posture.

## What UIAO is

UIAO is the organization's internal governance substrate for identity, device management, and access control. It is not a Microsoft product or an externally marketed framework; it is an internal architecture that sits across Microsoft Entra ID, Microsoft Intune, on-premises Active Directory, Microsoft Configuration Manager, and human-resources information technology systems, providing canonical organizational positioning for users and devices (OrgPath), continuous drift detection against canonical state, and evidence emission for compliance and audit attestation.

UIAO does not replace Active Directory, Group Policy, Configuration Manager, or any other Microsoft service. It is a layer above them: a canonical specification of what the organization expects its devices, users, and policies to look like, paired with a drift engine that detects when reality diverges from specification, and an evidence pipeline that records every governed action for downstream audit. The substrate operates continuously rather than at audit windows, surfaces divergences within hours rather than during incident response, and produces structured evidence that is queryable on demand rather than reconstructed retrospectively.

The substrate has several major components. The canonical specification holds the organization's intent — what devices should exist, what users should exist, how they are organizationally positioned, what policies should apply, what compliance state should result. The drift engine continuously reads the actual state from the underlying systems and compares it against the specification. The reconciliation engine resolves identity across systems that should agree but frequently do not. The evidence ledger captures every observation and every remediation for later audit. The remediation router moves resolvable findings to appropriate automated or human-driven workflows.

## The legacy phase reviewed

The legacy phase architecture is described in detail in the without-UIAO companion. The principal components are domain controllers (providing authentication, directory, DNS, and Group Policy delivery), Microsoft Configuration Manager (providing application and update delivery), Active Directory Certificate Services (providing PKI), file and print servers (providing storage), on-premises Exchange and SharePoint (providing collaboration), and the deployment infrastructure (providing imaging). Devices are joined to the domain at first provisioning, retrieve configuration through Group Policy, receive applications through Configuration Manager, and operate inside the corporate network perimeter or extended through VPN or DirectAccess. There is no cloud directory, no MDM plane, and no continuous compliance evaluation.

Understanding this architecture is the prerequisite for understanding the UIAO overlay. The sections that follow describe what UIAO adds to each architectural dimension.

## How UIAO is layered onto the legacy estate

UIAO is deployed onto a legacy estate without disrupting the underlying infrastructure. The deployment is observational and read-mostly: UIAO reads from Active Directory through LDAP queries and the Active Directory cmdlets, reads from Configuration Manager through the SMS provider and the administration service API, reads from the asset management database through ODBC or REST connectors, reads from Active Directory Certificate Services through the CES and CEP enrollment policy endpoints, and reads from the human-resources information technology system through whatever integration that system supports.

What UIAO writes back is constrained and explicit. The substrate does not modify Group Policy Object content, does not modify Configuration Manager applications or task sequences, and does not modify user or computer object attributes outside the scope of governance findings. When UIAO performs remediation (retiring a stale computer object, removing a departed user from groups, updating a misconfigured certificate template assignment), the action is recorded in the evidence ledger with the authorizing canonical specification version and the human approver if approval was required. The underlying systems remain authoritative for the surfaces they govern; UIAO is authoritative for the canonical specification of what those surfaces should hold.

The deployment topology is typically a small set of servers (physical or virtual) running the UIAO services, with read access to the directories and management databases of the legacy estate. The footprint is small relative to the estate it governs — typically two to four servers regardless of estate size, with horizontal scaling possible for very large estates.

## Inventory canonicalization

The first substantial UIAO contribution to the legacy phase is inventory canonicalization. The legacy estate maintains device records in several places: Active Directory holds computer objects with machine credentials and OU placement, Configuration Manager holds device records with client identifiers and collection memberships, the asset management database holds asset tags and procurement metadata, and the human-resources system holds assigned-user records that point at specific hardware. Each of these records is authoritative for its own surface, but the records frequently disagree about specific devices: a device may have an Active Directory computer object but no Configuration Manager client record (suggesting failed client installation), a Configuration Manager client record but no asset record (suggesting incomplete procurement intake), an asset record but no Active Directory record (suggesting a device that was never joined), or four records that all exist but identify the same physical device by different names.

UIAO reconciles these records continuously and produces a single canonical device record per physical asset. The canonical record carries the device's organizational position (business unit, region, security tier, asset class), its ownership lineage (assigned user, manager, cost center), its hardware identifiers (serial number, hardware hash where available, MAC addresses), its expected configuration baseline, and its current observed state. The canonical record is the source of truth for compliance evidence and remains accurate even when the underlying records drift apart from one another. When UIAO surfaces a finding — "this device is in Active Directory but is missing from Configuration Manager" — it does so by reference to the canonical record rather than by tedious manual cross-referencing.

The reconciliation algorithm is configurable but typically uses serial number as the primary key (since it is the most stable identifier across record types), hostname as a secondary key, and MAC address as a tertiary tiebreaker. Conflicts in which the keys disagree are surfaced as findings requiring administrator review. The reconciliation runs on a recurring cadence (typically every fifteen to sixty minutes); changes to any source system propagate to the canonical record within that window.

## Group Policy drift detection

The second UIAO contribution is Group Policy drift detection. The legacy phase's principal configuration mechanism is Group Policy, with policies defined in the directory, linked to organizational units, and applied to devices on a recurring refresh interval. The applied state on each device should match the policy specification implied by the device's OU placement and group memberships, but in practice it frequently does not. Sources of divergence include manual local administrator modifications that override applied policy, registry tampering by users or by malware, Group Policy replication failures between domain controllers in different sites, organizational unit restructuring that moves a device into a different policy scope without the corresponding policy specification updating, devices that have been offline long enough for their applied policy to have gone stale, and intentional policy changes that have not yet replicated through the directory.

UIAO's drift engine reads the resultant set of policy from each domain-joined device on a recurring cadence (typically once daily for full evaluation, more frequently for security-critical settings), compares the actual applied state against the canonical policy specification associated with the device's OrgPath, and emits drift signals when devices diverge. The drift signal includes the device identifier, the affected setting, the expected value (per canonical specification), the observed value, the suspected cause where the engine can infer it, and the suggested remediation. Drift signals are routed to either automated remediation (for unambiguous cases such as registry rollback to canonical value) or human review (for cases involving security-critical settings or where the cause is unclear).

The drift engine is bidirectional in a specific sense: it can also detect canonical-specification drift (the specification has been amended in a way that does not match the actual operational requirements), which surfaces as a different finding class requiring specification update rather than device remediation. Without bidirectional checking, the engine would gradually push the estate into compliance with an obsolete specification.

## Stale object identification

The third UIAO contribution is identification of stale objects across the directory and supporting systems. Stale computer objects accumulate naturally in any long-operating Active Directory environment: devices are retired without being removed from the directory, devices are re-imaged without the prior record being cleaned up, devices that have not authenticated in months or years continue to occupy directory entries, and replicated objects from defunct sites or domains persist beyond their useful life.

UIAO cross-references Active Directory computer objects against the canonical inventory, against the human-resources system's employment records, and against the last-authentication-time recorded on each computer object. Computer objects whose primary assigned user has departed the organization more than thirty days ago, whose last authentication exceeds the canonical-specification staleness threshold (typically sixty to ninety days), or whose hardware no longer appears in the asset database are flagged as candidates for retirement. The retirement workflow can be fully automated (canonical specification grants UIAO authority to disable and eventually delete) or human-gated (each retirement is reviewed by an administrator).

Beyond computer objects, the same staleness logic applies to user objects (departed users still enabled), group memberships (users still in security groups after role changes), certificate enrollments (issued certificates for devices no longer in service), Configuration Manager client records (clients that have not reported in extended periods), and DNS records (forward and reverse records for IP addresses no longer assigned). The accumulated cleanup over a multi-year operating window is substantial; UIAO typically reduces stale object counts by 80 to 95 percent within the first six months of deployment.

## OU policy compliance verification

The fourth UIAO contribution is policy compliance verification against organizational unit placement. The legacy phase uses OU placement as the principal mechanism for targeting Group Policy: a Group Policy Object linked to an OU applies to every device or user object within that OU (and below, unless inheritance is blocked). The organization's intent is encoded in the linking, but the linking is maintained by human administrators and is subject to drift.

UIAO catalogs the GPOs linked to each OU and verifies that the linked set matches the canonical policy specification for the business unit, region, and security tier represented by that OU's OrgPath classification. Drift between the expected GPO assignments and the actual GPO assignments — a GPO that should be linked but is not, a GPO that should not be linked but is, a GPO whose link order has been modified in a way that affects policy precedence — is surfaced as a governance finding. The finding can be resolved by amending the canonical specification (the actual linking was correct, the specification was outdated) or by remediating the linking (the specification was correct, the linking had drifted).

This is the inverse of traditional GPO management. Rather than humans assembling the right set of GPO links by recollection of policy intent, UIAO holds the policy intent as a structured specification and continuously verifies the assembly. New OUs created as the organization restructures are detected and their canonical policy assignment is computed automatically; missing GPO links surface as findings rather than going undetected until the next audit.

## PKI and certificate lifecycle governance

The fifth UIAO contribution is governance of the public-key infrastructure. Active Directory Certificate Services issues certificates to users, computers, and services based on certificate templates published in the directory and autoenrollment policies delivered via Group Policy. The lifecycle of each issued certificate — issuance, renewal, revocation, expiry — is tracked by AD CS, but the governance posture (which template assignments are appropriate, which certificates are still required by their original use case, which certificates have escaped their intended scope) is not natively tracked.

UIAO catalogs each certificate template, each autoenrollment policy, and each issued certificate, and continuously verifies that the template-policy-certificate chain matches the canonical specification. Templates whose security permissions have drifted, autoenrollment policies that target unexpected OUs, certificates issued to devices that should not have received them, and certificates approaching expiry without a renewal path are all surfaced as findings. The PKI administrator's quarterly review of the certificate authority is replaced by continuous observation and exception handling.

## Configuration Manager cohort canonicalization

The sixth UIAO contribution is canonicalization of Configuration Manager device collections and deployment cohorts. Configuration Manager uses collections (groups of devices, with membership defined by query, direct assignment, or include/exclude rules) as the principal targeting mechanism for applications, updates, baselines, and task sequences. Collection membership drifts over time as devices are added, removed, re-imaged, or migrated, and the intended membership versus actual membership of any given collection requires manual reconciliation.

UIAO holds canonical specifications for each significant collection — what OrgPath classification, what device class, what migration cohort, what compliance tier — and projects those specifications into Configuration Manager collection query rules. The collections are no longer maintained by humans editing query syntax; they are generated from the canonical specification and updated automatically as the specification or the underlying device population changes. Drift between expected and actual collection membership surfaces as a finding.

This pattern extends to deployment assignments. A deployment targeting "OrgPath classification: standard knowledge worker, security tier: medium, geographic region: North America" is expressed in canonical terms and projected to the collection-by-collection deployment structure that Configuration Manager actually uses.

## Patching compliance and evidence

The seventh UIAO contribution is patching compliance and evidence emission. The legacy phase's patching infrastructure (WSUS, Configuration Manager Software Update Point, deployment rings, maintenance windows, automatic deployment rules) is operationally sound but produces evidence that is fragmented across multiple consoles and time-bounded by reporting retention.

UIAO consumes Configuration Manager patch compliance data and projects it onto the canonical inventory, producing per-device, per-patch compliance state with full historical retention. Patching evidence — which devices received which patches at which time, which patches failed and why, which devices fell behind and for how long — is queryable retrospectively in support of audit response, security incident investigation, and migration planning. The drift engine surfaces devices that have fallen behind canonical patching expectations, with attribution to the underlying cause where possible.

## Endpoint security drift detection

The eighth UIAO contribution is endpoint security drift detection. The legacy phase's endpoint security stack (BitLocker, Microsoft Defender Antivirus or its predecessors, Windows Firewall, AppLocker or Software Restriction Policies) is configured through Group Policy and applied to devices through the standard mechanisms. Compliance with the intended security baseline is verified through periodic scans, audit reviews, or response to security incidents.

UIAO continuously verifies endpoint security state across the estate. BitLocker enabled or disabled on each device, BitLocker recovery key escrowed correctly or not, Microsoft Defender Antivirus active or inactive with current signatures, Windows Firewall enabled with policy applied, application control policies active and in expected mode — all are observed continuously and compared against canonical specification. Drift surfaces as a finding; security-critical drift (BitLocker disabled on a high-tier device, antivirus disabled, firewall disabled) triggers escalated alerting rather than queued findings.

## Imaging and provisioning audit

The ninth UIAO contribution is imaging and provisioning audit. The legacy phase's deployment pipeline (Microsoft Deployment Toolkit, Configuration Manager task sequences, reference images, driver injection) produces devices in known configurations, but the question "which devices have been deployed from which reference image at which time" is not natively answered by Configuration Manager.

UIAO tracks each device's deployment history: which task sequence ran, which reference image was applied, which driver package was injected, which post-deployment scripts ran, which applications were installed during the task sequence versus afterward. The history is the input to root-cause analysis for devices exhibiting unexpected configuration, and it is the audit substrate for demonstrating that the deployed configuration matches the canonical specification at the moment of deployment.

## Joiner, mover, and leaver propagation

The tenth UIAO contribution is automated joiner, mover, and leaver propagation. The legacy phase's identity lifecycle is typically driven by manual provisioning workflows: a new hire ticket arrives in helpdesk, a domain administrator creates the user object, group memberships are added based on role, a mailbox is provisioned, and so on. Each step is a manual operation susceptible to omission or error.

UIAO consumes joiner, mover, and leaver events from the human-resources information technology system and propagates the consequences across Active Directory, Exchange, Configuration Manager, the asset management database, and any other integrated system. New hires arrive with their identity, group memberships, mailbox, and assigned device pre-provisioned. Role changes propagate to group memberships, application entitlements, and access rights without manual intervention. Departures de-provision across all systems in a coordinated action, with retention windows enforced according to canonical specification (a departed user's account may be disabled immediately, hidden from the global address list immediately, removed from groups immediately, but the underlying object retained for ninety days for audit purposes before final deletion).

The automation does not eliminate the human roles involved — managers still approve role changes, security still authorizes elevated access — but it eliminates the manual ticket-driven mechanics of executing the approved changes.

## Evidence emission for compliance attestation

The eleventh UIAO contribution is evidence emission for compliance attestation. The legacy phase's audit evidence is assembled retrospectively from event logs, configuration reports, and ad-hoc queries, typically under deadline pressure during an audit window. The work is laborious and the result is point-in-time.

UIAO emits structured evidence continuously to a canonical evidence ledger. Every inventory observation, every drift finding, every remediation, every policy update, every certificate issuance, every joiner/mover/leaver event, every patching outcome is recorded with timestamp, actor, canonical specification version in effect at the time, and any contextual metadata. The ledger is queryable retrospectively for audit response, security incident investigation, and management reporting. Compliance attestation against frameworks such as the National Institute of Standards and Technology 800-53, the Federal Risk and Authorization Management Program, or industry frameworks such as the Payment Card Industry Data Security Standard becomes a query operation rather than an evidence-assembly project.

## Pre-migration triage to subsequent phases

The twelfth UIAO contribution is pre-migration triage. The transition from the legacy phase to subsequent phases requires per-device assessment of readiness: which devices are eligible for hybrid join (Phase III) or pure cloud join (Phase IV), which require remediation first (Trusted Platform Module enablement, BIOS update, BitLocker pre-boot, Windows version upgrade), and which should be retired through hardware refresh rather than migrated.

UIAO produces this triage as a continuous output rather than a one-time reconnaissance project. The canonical inventory already holds hardware capability data for each device; the canonical specification holds the readiness criteria for each downstream phase; the drift engine surfaces devices crossing into or out of readiness as their remediations land or as their hardware ages out of support. Migration planning consumes the triage output as input rather than performing the reconnaissance work directly.

## What UIAO does not change

It is important to be precise about what UIAO does not change in the legacy phase. UIAO does not modify the behavior of Active Directory authentication, Group Policy delivery, Configuration Manager application distribution, Kerberos ticket issuance, or any other mechanic of the underlying Microsoft technology. Devices in the legacy phase continue to operate under the same authentication, configuration, and patching mechanisms whether UIAO is present or not. The user experience is unchanged. The domain controller infrastructure is unchanged. The imaging pipeline is unchanged. Administrators continue to use Active Directory Users and Computers, Group Policy Management Console, Configuration Manager admin console, and the rest of the existing tooling.

What UIAO changes is the governance posture: what is known about the estate, how quickly drift is detected, how readily evidence can be produced, and how cleanly the estate can be triaged for migration. These changes are not visible to the end user and are visible to administrators only through the canonical records, drift findings, and evidence ledger queries that UIAO produces. The estate continues to operate; it merely operates under a layer of observation and specification that was not previously present.

## What is measurably different from the without-UIAO baseline

| Concern | Without UIAO | With UIAO |
|---|---|---|
| Device inventory accuracy | Records split across Active Directory, Configuration Manager, asset database, frequently inconsistent | Single canonical device record keyed by OrgPath, continuously reconciled |
| Group Policy drift | Discovered during incidents or annual audits | Detected continuously by drift engine, surfaced within hours |
| Stale computer objects | Accumulate until periodic cleanup project | Flagged within days, retirement workflow automated |
| OU policy compliance | Manual quarterly review | Continuous against canonical specification |
| Configuration Manager collection drift | Manually maintained query rules drift over time | Generated from canonical specification |
| Patching evidence retention | Limited by Configuration Manager retention | Full historical retention in evidence ledger |
| Endpoint security state | Periodic scans, audit-window reviews | Continuous observation, security-critical alerting |
| Imaging audit trail | Reconstructed from logs and tickets | Full per-device deployment history in evidence ledger |
| Joiner/mover/leaver propagation | Manual ticket-driven workflows | Automated propagation from human-resources events |
| Audit evidence assembly | Manually assembled during audit windows | Continuously emitted to structured ledger, queryable on demand |
| Migration readiness | Estate-wide reconnaissance project | Continuous output from drift engine and canonical specification |

## UIAO operational and cost overlay

The UIAO operational footprint in the legacy phase is modest. The substrate runs on a small server cluster (typically two to four servers, physical or virtual, depending on estate size and high-availability requirements), connects to the existing directories and management systems as a read-mostly observer, and produces governance findings and evidence records that are reviewed and acted on by the existing operational teams. UIAO does not require new specialist roles in the legacy phase; the existing directory administrators, Configuration Manager administrators, identity engineers, and security operations staff consume UIAO findings as one additional input to their existing workflows. The marginal staffing increment for operating UIAO itself is typically less than one full-time equivalent at organizations under ten thousand devices, growing modestly with estate size.

The cost overlay is similarly modest. UIAO licensing (if internal) or subscription costs are bounded relative to the existing on-premises Microsoft licensing. The operational cost savings — automation of joiner/mover/leaver propagation, reduction of stale-object cleanup projects, elimination of audit-assembly project work, faster drift detection reducing incident severity — typically offset the operational cost within twelve to eighteen months of deployment for organizations at moderate scale.

## Carry-forward to subsequent phases

The investment in UIAO during the legacy phase pays forward into subsequent phases. The canonical inventory established in the legacy phase becomes the foundation for hybrid join cohort planning in Phase III and for OrgPath-driven Autopilot pre-registration in Phase IV. The human-resources integration established in the legacy phase remains in service through every subsequent phase. The evidence ledger continues to accumulate across phases, producing a continuous audit substrate that spans the entire modernization journey. The drift engine adapts to new surfaces in each phase but continues to operate on the same architectural pattern.

Organizations that deploy UIAO during the legacy phase enter subsequent phases with the governance substrate already in place; organizations that defer UIAO until later phases must establish the substrate concurrent with the more demanding modernization work. The deferral is usually a false economy.

## Canonical anchors

UIAO anchors for the legacy phase live in the organization's internal repository under `src/uiao/`. The principal artifacts include the canonical inventory schema (defining the structure of canonical device records), the drift engine specification (defining the observation and finding model), the OrgPath taxonomy (defining the organizational positioning vocabulary), the evidence ledger schema (defining the structured evidence record format), the human-resources integration adapter specification, and the legacy-phase coverage doctrine (cataloging which legacy estate dimensions are governed and which remain ungoverned). Readers with internal access can locate the specific artifacts; this document does not duplicate them.

Microsoft Learn references for the underlying Active Directory, Group Policy, Configuration Manager, and Certificate Services technologies are listed in the without-UIAO companion ([`without-uiao-legacy.md`](without-uiao-legacy.md)).
