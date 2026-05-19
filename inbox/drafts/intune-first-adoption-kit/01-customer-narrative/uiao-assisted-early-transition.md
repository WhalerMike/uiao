# Phase II — Early Transition: UIAO-Assisted Detailed Reference

## How to read this document

This document is the UIAO-assisted detailed reference for the early transition phase of Windows endpoint governance — the phase in which user identity has been extended into Microsoft Entra ID for purposes of cloud-resident application access while device identity, device configuration, and device governance remain entirely anchored in on-premises Active Directory. It parallels the structure of the without-UIAO companion ([`without-uiao-early-transition.md`](without-uiao-early-transition.md)) and describes, section by section, how the organization's internal UIAO governance framework augments the architectural asymmetry that defines this phase.

The early transition phase is operationally significant because it introduces cloud identity infrastructure without yet committing to cloud device management. The asymmetry — cloud-aware users, on-premises-only devices — is the source of both the value (users gain access to cloud services) and the limitation (Conditional Access cannot evaluate device posture) of this phase. UIAO's role is to ensure the new cloud surface area is governed coherently from inception rather than arriving as a parallel ungoverned plane that has to be reconciled later.

## What UIAO is

UIAO is the organization's internal governance substrate for identity, device management, and access control. It sits across Microsoft Entra ID, Microsoft Entra Connect, Microsoft 365 services, federated software-as-a-service applications, on-premises Active Directory, Configuration Manager, and human-resources information technology systems, providing canonical organizational positioning for users (OrgPath), continuous drift detection across the systems, and evidence emission for compliance attestation.

In the early transition phase, UIAO is most architecturally visible at the identity boundary: the moment when on-premises user identities are projected into the cloud directory via Entra Connect. UIAO consumes the same synchronization stream and projects OrgPath onto cloud identities, making canonical organizational positioning available to Conditional Access, Microsoft 365 policy, and federated software-as-a-service applications immediately upon cloud-identity establishment.

## The early transition phase reviewed

The without-UIAO companion describes the early transition architecture in detail. The principal addition compared to the legacy phase is Microsoft Entra ID as a cloud directory, populated from on-premises Active Directory via Microsoft Entra Connect (formerly Azure Active Directory Connect). Synchronized identities authenticate against the cloud directory using one of three mechanisms (password hash synchronization, pass-through authentication, federated authentication via Active Directory Federation Services or a third-party federation provider). Microsoft 365 services (Exchange Online, SharePoint Online, OneDrive for Business, Microsoft Teams) consume the cloud identity for authentication and authorization. Software-as-a-service applications outside Microsoft 365 federate with the cloud directory through SAML or OpenID Connect. Conditional Access policies begin to enforce sign-in conditions for cloud applications (multi-factor authentication, location restrictions, legacy authentication blocks). Devices, critically, remain entirely AD-joined, GPO-governed, and Configuration Manager-managed; there is no device object in the cloud directory and no enrollment in Microsoft Intune.

## How UIAO is layered onto the early transition

UIAO is layered onto the early transition by adding cloud-side observation and specification to the legacy-side governance already in place from Phase I. The legacy-side substrate (canonical inventory, drift detection, OU policy verification, joiner/mover/leaver propagation from human-resources) continues to operate unchanged. New components address the cloud surface: a Microsoft Entra ID adapter reads cloud identity and group state, a Microsoft 365 adapter reads service configuration (Exchange Online, SharePoint Online, Teams, OneDrive), a Conditional Access adapter reads policy state, and a federated SaaS adapter reads each federated application's federation configuration. The canonical specification expands to include cloud-side intent (which users should exist in the cloud, with which group memberships, with which OrgPath; which Conditional Access policies should be in place with what conditions and grants; which federated applications should be integrated with what trust settings).

The drift engine evaluates both legacy-side and cloud-side state and emits unified findings. A drift finding may span both planes — for example, a user whose on-premises group membership has not yet propagated to the cloud directory through Entra Connect synchronization, or a user whose cloud OrgPath does not match the OrgPath that would be computed from current human-resources data. Cross-plane findings are characteristic of the early transition phase and are operationally critical because they precede the device-aware Conditional Access of later phases.

## OrgPath on user objects at the identity-sync boundary

The first major UIAO contribution in the early transition is projection of OrgPath onto user objects in Microsoft Entra ID. As Entra Connect synchronizes user identities from on-premises Active Directory to the cloud directory, UIAO computes the canonical OrgPath for each user from human-resources data and projects it onto the cloud identity's attributes. The projection happens at synchronization time, so cloud identities arrive in Entra ID already carrying authoritative organizational positioning — business unit, region, employment classification, security tier, position in the management chain — available immediately to Conditional Access, Microsoft 365 access policies, dynamic group rules, and any cloud-resident service that needs to scope by organizational attribute.

OrgPath is encoded as a structured set of extension attributes on the user object. The specific encoding is configurable but typically uses Microsoft Entra ID's directory schema extensions or the on-premises Active Directory's extension attributes (which Entra Connect synchronizes). The canonical specification holds the OrgPath taxonomy and the derivation rules; UIAO maintains the projection continuously, updating cloud-side OrgPath as human-resources data changes.

Without UIAO, organizational positioning in Microsoft Entra ID is either absent (cloud-side groups exist but with no authoritative organizational meaning) or assembled through ad-hoc dynamic group rules over user attributes (which produces groupings without an explicit canonical specification of intent). With UIAO, OrgPath is the canonical primitive; cloud groups are derived from OrgPath where they need to exist for technical reasons (Microsoft Entra security groups for Conditional Access scoping, for example), but the source of truth is OrgPath itself.

## HRIT-driven joiner, mover, and leaver propagation

The second major UIAO contribution is automated joiner, mover, and leaver propagation tied to the human-resources information technology system. The legacy phase's UIAO deployment already includes HRIT integration for AD-side identity provisioning; the early transition phase extends the integration to span the cloud-side surfaces.

A new hire event from the HRIT system triggers, in a coordinated sequence: creation of the on-premises Active Directory user object in the appropriate OU, setting of initial password per canonical specification, addition to security groups derived from OrgPath, synchronization to Microsoft Entra ID via Entra Connect, projection of OrgPath onto the cloud identity, assignment of Microsoft 365 licenses derived from OrgPath, provisioning of Exchange Online mailbox, provisioning of OneDrive for Business storage, application of Conditional Access scope per OrgPath, and granting of access to federated software-as-a-service applications appropriate to the new hire's role. Each step is recorded in the evidence ledger.

Role change events update OrgPath, which propagates to group memberships in both planes, license entitlements, Conditional Access scope, and access to federated applications. Departure events execute the inverse sequence: removal from Conditional Access scope, license revocation, mailbox disposition (placed on litigation hold per retention policy, then archived, then deleted per canonical specification), removal from federated applications, removal from groups, disabling of cloud and on-premises identities, hiding from global address list, and eventual deletion after the retention window.

Without UIAO, this work is typically split across multiple manual ticket-driven workflows, with predictable failure modes: forgotten cloud license revocation (departed users continuing to consume licenses), lingering group memberships (allowing access continuation past the intended termination point), orphaned cloud resources (mailbox or OneDrive contents inaccessible to anyone), and inconsistent retention behavior across services.

## Know Your Customer attestation for cloud identity

The third major UIAO contribution is Know Your Customer attestation for cloud identity. The KYC module verifies continuously that each cloud identity continues to correspond to an actively employed, properly classified, and currently authorized human, and that the canonical attributes on the identity match the underlying human-resources state. The attestation runs continuously rather than at quarterly access review windows, surfacing deviations within hours of occurrence.

The attestation checks include: the user's employment state in human-resources (active, on leave, terminated, contractor with unexpired engagement); the user's organizational position matching the OrgPath projected on the cloud identity; the user's required attributes for their classification (clearance status, role assignment, geographic restriction, security training completion); the user's authentication factor enrollment (multi-factor authentication configured, primary factor and backup factor present, recovery options set); the user's group memberships matching the OrgPath-derived expected set; the user's privileged role assignments matching the canonical entitlement specification; and the user's recent access patterns matching the expected pattern for their classification.

KYC findings range from low-severity informational items (a user's group membership has drifted slightly from OrgPath expectation) to high-severity security signals (a departed employee's cloud identity is still active and authenticating) and are routed accordingly. The KYC layer is particularly important for organizations subject to federal compliance regimes where personnel reliability and current authorization status are themselves audit subjects.

## Conditional Access scoping by OrgPath

The fourth major UIAO contribution is Conditional Access policy scoping by OrgPath rather than by ad-hoc security group membership. Microsoft's Conditional Access engine evaluates policies whose target population is defined by Microsoft Entra ID security group membership or by user-attribute-based dynamic rules. Either mechanism can be used to scope a policy, but neither natively expresses the policy's organizational intent — the relationship between a policy and the population it protects is implicit, distributed across group definitions, and difficult to audit.

UIAO replaces the implicit scoping with explicit OrgPath-driven scoping. A policy targets, for example, "active employees in business units classified as handling controlled unclassified information, with security tier high or above," and OrgPath provides the authoritative answer about who that is. The policy specification expresses the intent in OrgPath terms; UIAO projects the intent into the security groups that Conditional Access actually targets, generating and maintaining the group memberships automatically. Policy scope changes are made by amending the canonical specification and the projection updates accordingly.

The result is auditable Conditional Access policy. A policy's target population is queryable directly ("who is in scope for the require-MFA-from-untrusted-locations policy today, and why") rather than reconstructed from group membership lookups. Drift in scope (a security group that should be in scope but has lost members, or a security group that should not be in scope but has gained members) surfaces as a finding rather than going undetected.

## Microsoft 365 service configuration governance

The fifth major UIAO contribution is governance of Microsoft 365 service configuration. Exchange Online, SharePoint Online, Microsoft Teams, and OneDrive for Business each have substantial configuration surfaces administered through their respective admin centers. The configurations are independent of the cloud identity directory and are operationally maintained by service-specific administrators (Exchange Online administrators, SharePoint Online administrators, and so on). The configurations can drift from organizational intent over time.

UIAO catalogs each service's configuration against canonical specification: mailbox storage policies, retention policies, sharing policies, external collaboration policies, Teams meeting policies, Teams app permission policies, OneDrive sharing and external access policies, SharePoint site provisioning templates, and so on. Drift between expected and actual configuration surfaces as a finding. The service administrators continue to use their respective admin centers for routine operations; UIAO catches the drift that arises from ad-hoc configuration changes, deprecated default values that have not been re-baselined, and post-incident changes that have not been propagated to canonical specification.

## Federated software-as-a-service application governance

The sixth major UIAO contribution is governance of federated software-as-a-service applications. Cloud-resident SaaS applications integrated with Microsoft Entra ID through SAML 2.0 or OpenID Connect each have their own configuration: trust settings on the Entra ID side, configuration on the application side, user provisioning rules, group-claim mapping, attribute mapping, and just-in-time provisioning behavior. The federation relationships accumulate over time as new applications are added, and the governance posture across the portfolio is difficult to maintain without explicit cataloging.

UIAO catalogs each federated application: which OrgPath classifications are entitled to access it, what attributes are mapped, what groups are claimed, what provisioning rules are in place, when the federation certificate expires, when the application's metadata last changed, and whether the application's configuration matches the canonical federation specification. Federation certificate expiry (a common failure mode that breaks SAML-based federation without warning) is surfaced well in advance of the expiry date. Drift between expected and actual federation configuration surfaces as a finding.

## Microsoft Entra Connect health monitoring

The seventh major UIAO contribution is Microsoft Entra Connect health monitoring. The Entra Connect synchronization server is operationally critical — its failure or misconfiguration breaks the cloud identity surface — and Microsoft provides health monitoring through the Microsoft Entra Connect Health service. UIAO consumes the health data, projects it against canonical specification (the Entra Connect server should be running, the synchronization should be completing within an expected interval, the synchronization scope should match canonical specification, the connector accounts should have appropriate permissions, the staging-mode secondary server should be in expected state), and surfaces findings when reality diverges.

Synchronization errors that affect specific identities (duplicate proxy addresses, invalid UPN formats, attribute size limits, conflicting source-of-authority) are surfaced with attribution to the affected identity and the underlying cause. The errors are routed to the appropriate administrator for resolution rather than discovered when a specific user reports inability to access cloud services.

## Multi-factor authentication enrollment governance

The eighth major UIAO contribution is multi-factor authentication enrollment governance. Multi-factor authentication is typically introduced during the early transition phase, and its operational success depends on user enrollment coverage. Microsoft Entra ID can require multi-factor for sign-ins (via Conditional Access), but it cannot directly cause users to enroll the required factors; enrollment depends on user action.

UIAO catalogs enrollment state for each cloud identity: which factors are registered, which are configured as primary versus backup, which are missing per canonical specification, and which factors have aged past their expected refresh interval. Users with incomplete enrollment are surfaced as findings, routed through an enrollment campaign workflow that contacts them through email or other channels, escalating after a configurable delay, and ultimately enforcing through Conditional Access once a per-OrgPath enforcement threshold (typically 95 to 99 percent enrollment coverage) is reached. The enforcement is staged by OrgPath cohort to avoid the productivity disruption of lockout for users who have not yet enrolled.

## Microsoft Coverage Doctrine for cloud applications

The ninth major UIAO contribution is the Microsoft Coverage Doctrine for cloud applications. The doctrine catalogs each cloud application (Microsoft 365 services and federated SaaS) and notes the gap between Microsoft's native capabilities and the organization's policy expectations. For example, the doctrine catalogs where Conditional Access can enforce a policy versus where the policy must be enforced inside the application itself, where Microsoft Information Protection sensitivity labels can carry policy versus where labels are advisory, where multi-factor authentication can be made phishing-resistant versus where weaker factors remain in use, where data loss prevention can be enforced versus where it is only audit-mode, and so on. The doctrine becomes the input to compensating-control planning that closes specific gaps with overlays such as application-internal controls, data-loss-prevention policies, or specific Conditional Access patterns.

## Evidence emission for compliance attestation

The tenth major UIAO contribution is evidence emission extended into the cloud surface. The evidence ledger established in the legacy phase continues to operate; new event classes capture cloud-side activity. Conditional Access policy evaluations, Microsoft 365 service configuration changes, federated SaaS integration changes, Entra Connect synchronization events, multi-factor authentication enrollment events, and KYC findings are all recorded in the ledger with timestamp, actor, canonical specification version in effect, and contextual metadata. The ledger is queryable for cloud-surface compliance attestation in addition to the legacy-surface attestation it already supported.

For organizations subject to federal compliance regimes, the cloud-surface evidence is increasingly important because the cloud surface is where many of the access decisions are now made. The ability to demonstrate that Conditional Access policies were configured correctly and operating during a specific window, that multi-factor authentication was enforced for the relevant population, and that federated applications were governed against canonical specification is the audit substrate that the compliance regime requires.

## What UIAO does not change

UIAO does not modify the behavior of Microsoft Entra Connect, the authentication mechanics of password hash synchronization or pass-through authentication, the token issuance pipeline of Microsoft Entra ID, the fundamental operation of Microsoft 365 services, or the Conditional Access policy evaluation engine. Users sign in to cloud applications the same way they would without UIAO. The cloud identity surface continues to be authoritative for the applications it serves. The Entra Connect synchronization server continues to operate on its own cadence.

What UIAO changes is the coherence and governance posture of the cloud identity surface: how organizational positioning is expressed (OrgPath rather than ad-hoc grouping), how identity-lifecycle events propagate (HRIT-driven automation rather than ticket-driven manual workflows), how Conditional Access policies scope (OrgPath-derived rather than directly group-targeted), how the cloud service configurations are governed (continuously verified against canonical specification rather than periodically reviewed), and how the foundation is laid for the device-plane work that arrives in subsequent phases.

## What is measurably different from the without-UIAO baseline

| Concern | Without UIAO | With UIAO |
|---|---|---|
| Cloud identity organizational positioning | Absent or assembled through ad-hoc Microsoft Entra groups | Canonical OrgPath projected at synchronization time, derived from HRIT |
| Joiner/mover/leaver propagation | Ticket-driven, manual across on-premises and cloud surfaces | HRIT-event-driven, coordinated across all surfaces |
| Identity attestation cadence | Quarterly access reviews | Continuous KYC attestation against HRIT state |
| Conditional Access policy scope expression | Microsoft Entra groups, manually or dynamically maintained | OrgPath classification, generated and maintained automatically |
| Microsoft 365 service configuration | Service-specific admin centers, periodic reviews | Continuously verified against canonical specification |
| Federated SaaS application portfolio | Catalog maintained ad-hoc | Cataloged with federation health monitoring |
| Microsoft Entra Connect health | Microsoft's health service, reviewed when problems are noticed | Continuously projected against canonical specification |
| MFA enrollment coverage | Manual campaigns, periodic reporting | Continuous tracking with staged-rollout enforcement |
| Gap awareness for cloud applications | Discovered during incidents or audits | Cataloged proactively in Microsoft Coverage Doctrine |
| Compliance evidence for cloud surface | Manually assembled from sign-in logs and admin-center reports | Continuously emitted to structured evidence ledger |

## UIAO operational and cost overlay

The UIAO operational footprint in the early transition phase grows compared to the legacy phase, reflecting the addition of cloud-side adapters and the more elaborate canonical specification. The substrate continues to run on a small server cluster, with cloud-side adapters connecting to Microsoft Entra ID, Microsoft 365 services, and federated SaaS applications through their respective API surfaces (Microsoft Graph predominantly). The marginal staffing impact remains modest; identity engineers in the existing organization consume UIAO findings as one input to their workflows.

Cost in this phase reflects the cost overlay of running the cloud-side adapters and the slightly expanded canonical specification, partially offset by the savings from automated joiner/mover/leaver propagation, continuous KYC attestation reducing the manual access review burden, automated MFA enrollment campaign mechanics, and proactive federated SaaS application governance reducing the impact of certificate expiry and other federation failures.

## Carry-forward to subsequent phases

The user-plane OrgPath established in the early transition phase is the foundation for the device-plane OrgPath that arrives in the later transition phase (Phase III). When devices begin to be hybrid-joined and their Microsoft Entra ID device objects are created, the device-plane OrgPath is computed from the OrgPath of the assigned user (modified by device-class attributes such as form factor and asset class). Organizations that adopt UIAO during the early transition phase enter the later transition with the user-plane work already complete; organizations that defer UIAO until the later transition must establish both planes concurrently, which is operationally more demanding.

The HRIT integration established in the early transition continues to drive joiner/mover/leaver propagation in subsequent phases, with the propagation scope expanding to cover device assignments, device retirement, device-user binding verification, and other surfaces that arise as device-plane governance comes online.

## Canonical anchors

UIAO anchors for the early transition phase live in the organization's internal repository under `src/uiao/`. The principal artifacts include the OrgPath taxonomy specification, the HRIT integration adapter, the Microsoft Entra ID adapter, the Microsoft 365 service adapters, the federated SaaS adapter, the KYC attestation specification, the Microsoft Coverage Doctrine catalog, and the user-plane evidence ledger schema. Microsoft Learn references for the underlying Entra Connect Sync, Microsoft Entra ID, Conditional Access, and Microsoft 365 technologies are listed in the without-UIAO companion ([`without-uiao-early-transition.md`](without-uiao-early-transition.md)).
