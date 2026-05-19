# Phase II — Early Transition: UIAO-Assisted View of Cloud Identity Adoption with On-Premises Device Governance

## How to read this document

This document is the UIAO-assisted single-phase view of the early transition
phase of device governance — the phase in which user identity has been
extended into Microsoft Entra ID for purposes of cloud-resident application
access, while device identity and device governance remain entirely anchored
in Active Directory. The corresponding without-UIAO description of this
phase lives in the master narrative at
[`baseline-without-uiao.md`](baseline-without-uiao.md) as Part II.

This document is intended for internal strategy, architecture, governance,
and compliance audiences who want to understand how the organization's UIAO
governance substrate is layered onto a hybrid identity / on-premises device
estate during the early transition.

---

## What UIAO is, briefly

UIAO is the organization's internal governance substrate for identity,
device management, and access control. It is not a Microsoft product or an
externally marketed framework; it is an internal architecture that sits
across Microsoft Entra ID, Microsoft Intune, on-premises Active Directory,
and human-resources information technology systems, providing canonical
organizational positioning for users and devices (OrgPath), continuous drift
detection against canonical state, and evidence emission for compliance and
audit.

UIAO does not replace Microsoft Entra Connect, Microsoft 365, Conditional
Access, or any other Microsoft service. It is a layer above them: a
canonical specification of what the organization expects, paired with a
drift engine and an evidence pipeline.

---

## How UIAO applies to the early transition

The early transition phase is the phase in which the organization first
acquires cloud identity surface area for its users while preserving the
on-premises device estate. UIAO's role in this phase is to ensure that the
cloud identity surface is governed coherently from inception, rather than
arriving as a parallel, ungoverned plane that has to be reconciled
retrospectively.

The first contribution is **OrgPath on user objects, established at the
identity-sync boundary**. As Microsoft Entra Connect synchronizes user
identities from the on-premises directory into the cloud directory, UIAO
projects the canonical OrgPath onto each user's Entra ID object. OrgPath
encodes business unit, region, employment classification, security tier,
and management chain, and it is derived from the human-resources information
technology system rather than from organizational unit placement in Active
Directory. This means cloud identities arrive in Entra ID already carrying
authoritative organizational positioning, available immediately to
Conditional Access, Microsoft 365 access policy, and any cloud-resident
service that needs to scope by organizational attribute. Without UIAO,
organizational positioning in Entra ID is either absent or assembled by
ad-hoc Entra group membership, neither of which is authoritative.

The second contribution is **HRIT-driven joiner/mover/leaver propagation**.
UIAO consumes events from the human-resources information technology system
(new hire, role change, transfer, leave of absence, termination) and
propagates the consequences across Active Directory, Entra ID, Microsoft
Exchange Online, Microsoft Teams, Microsoft SharePoint, and any other
integrated service. New employees arrive with their on-premises and cloud
identities pre-provisioned, their group memberships derived from OrgPath,
their mailbox and OneDrive provisioned, and their Conditional Access scope
established. Departing employees are de-provisioned across all surfaces in a
single coordinated action rather than through serial manual steps. Without
UIAO, joiner/mover/leaver is typically handled through ticket-driven manual
provisioning, with the predictable failure modes of forgotten cloud
licenses, lingering group memberships, and orphaned cloud resources.

The third contribution is **Know Your Customer attestation for cloud
identity**. UIAO's KYC module verifies that each cloud identity continues to
correspond to an actively employed, properly classified, and currently
authorized human. The attestation runs continuously rather than at
quarterly review windows, and it surfaces deviations such as accounts whose
human-resources state has changed without corresponding identity
adjustment, accounts whose OrgPath is inconsistent with the underlying
employment record, and accounts that lack required attributes for their
classification (clearance status, role assignment, geographic restriction).
The KYC layer is particularly important for organizations subject to
federal compliance regimes where personnel reliability and current
authorization status are themselves audit subjects.

The fourth contribution is **Conditional Access policy scoping by OrgPath
rather than by ad-hoc Entra group membership**. Most organizations
implementing Conditional Access for the first time scope their policies to
Entra security groups, populated either manually or through dynamic
membership rules that read user attributes. This works but is fragile: the
relationship between a Conditional Access policy and the population it
protects is implicit, distributed across group definitions, and difficult to
audit. UIAO surfaces OrgPath as the canonical scoping primitive: a policy
targets, for example, "employees in the regulated business units assigned to
positions classified as having access to controlled unclassified
information," and OrgPath provides the authoritative answer about who that
is. The policy author writes intent; UIAO resolves it. Without UIAO, policy
scope drifts over time as group memberships are modified ad-hoc.

The fifth contribution is **anticipating device-plane OrgPath before
devices arrive in the cloud**. The early transition phase establishes
user-plane OrgPath. When devices subsequently migrate to hybrid join in
Phase III, or arrive cloud-native in Phase IV, their OrgPath assignment is
derived from the OrgPath of their assigned user (modified by device-class
attributes such as form factor, asset class, and ownership). The user-plane
OrgPath established in Phase II is the foundation on which device-plane
OrgPath is built. Organizations that adopt UIAO during the early transition
arrive at Phase III with the user-plane work already done; organizations
that defer UIAO until Phase III or IV must establish both planes
concurrently.

The sixth contribution is **Microsoft Coverage Doctrine for cloud
applications**. UIAO's Coverage Doctrine catalogs the cloud applications in
use, the access surfaces each provides, and the gaps between Microsoft's
native capabilities and the organization's policy expectations. For
example, the doctrine catalogs where Conditional Access can enforce a
policy versus where the policy must be enforced inside the application
itself, where Microsoft Information Protection labels can carry policy
versus where labels are advisory, and where multi-factor authentication can
be made phishing-resistant versus where weaker factors remain in use. The
doctrine becomes the input to remediation planning that closes specific
gaps with compensating controls.

---

## What is measurably different from the without-UIAO baseline

| Concern | Without UIAO | With UIAO |
|---|---|---|
| Organizational positioning in Entra ID | Absent or assembled through ad-hoc Entra groups | Canonical OrgPath projected at sync time, derived from HRIT |
| Joiner/mover/leaver propagation | Ticket-driven, manual across multiple systems | HRIT-event-driven, coordinated across AD, Entra, M365, integrated SaaS |
| Identity attestation cadence | Quarterly access reviews | Continuous KYC attestation against HRIT state |
| Conditional Access policy scope | Entra groups (populated manually or by dynamic rules); audit is laborious | OrgPath; policy intent is explicit and auditable |
| Foundation for device-plane OrgPath | Not established; must be assembled later concurrent with device migration | Established on user objects; device-plane OrgPath builds on it directly |
| Gap awareness for cloud applications | Discovered during specific incidents or audits | Cataloged proactively in the Coverage Doctrine |
| Compliance evidence for cloud identity | Manually assembled from sign-in logs and access reviews | Continuously emitted to evidence ledger |

---

## What UIAO does not change in the early transition

UIAO does not modify the behavior of Microsoft Entra Connect, the
authentication mechanics of password hash sync or pass-through
authentication, the token issuance pipeline of Microsoft Entra ID, or the
fundamental operation of Microsoft 365 services. Users sign in to cloud
applications the same way they would without UIAO. The cloud identity
surface continues to be authoritative for the applications it serves.

What UIAO changes is the *coherence and governance posture* of the cloud
identity surface: how organizational positioning is expressed, how
identity-lifecycle events propagate, how Conditional Access policies scope,
and how the foundation is laid for the device-plane work that arrives in
subsequent phases.

---

## Authoritative sources and canonical anchors

Microsoft Learn references for the underlying Entra Connect Sync,
Microsoft Entra ID, Conditional Access, and Microsoft 365 technologies are
listed in the master narrative
([`baseline-without-uiao.md`](baseline-without-uiao.md)).

UIAO canonical anchors for the early-transition governance overlay live in
the organization's internal repository under `src/uiao/`. The principal
anchors are the OrgPath taxonomy specification, the HRIT integration
adapter specification, the KYC attestation runbook, the Coverage Doctrine
catalog, and the user-plane evidence ledger schema.
