# Phase I — Legacy: UIAO-Assisted View of Pure Active Directory Domain Join

## How to read this document

This document is the UIAO-assisted single-phase view of the legacy phase of
device governance. The corresponding without-UIAO description of this phase
lives in the master narrative at [`baseline-without-uiao.md`](baseline-without-uiao.md)
as Part I, and stands alone for any reader who does not need the UIAO
overlay. This document is intended for internal strategy, architecture,
governance, and compliance audiences who want to understand how the
organization's UIAO governance substrate is layered onto an otherwise
conventional on-premises Active Directory estate.

The reader is assumed to have read Part I of the master narrative, or to read
it alongside this document. This document does not repeat the operational
description of the legacy phase; it focuses exclusively on what UIAO adds.

---

## What UIAO is, briefly

UIAO is the organization's internal governance substrate for identity,
device management, and access control. It is not a Microsoft product or an
externally marketed framework; it is an internal architecture that sits
across Microsoft Entra ID, Microsoft Intune, on-premises Active Directory,
and human-resources information technology systems, providing canonical
organizational positioning for users and devices (OrgPath), continuous drift
detection against canonical state, and evidence emission for compliance and
audit. Where Microsoft's products describe how to configure each plane
individually, UIAO describes how the planes are wired together as a single
governed system.

UIAO does not replace Active Directory, Group Policy, Microsoft Intune, or
any other Microsoft service. It is a layer above them: a canonical
specification of what the organization expects its devices and users to look
like, paired with a drift engine that detects when reality diverges from
specification, and an evidence pipeline that records every governed action
for downstream audit and compliance attestation.

---

## How UIAO applies to the legacy phase

The legacy phase predates the architectural shift to cloud identity, but it
does not predate the need for governance. Where UIAO is in operation, the
legacy phase is governed by overlaying canonical position and drift detection
onto the existing on-premises infrastructure rather than by transforming the
infrastructure itself. UIAO accepts that Active Directory, Group Policy,
Microsoft Configuration Manager, imaging pipelines, and on-premises
certificate services are the operating substrate, and it provides governance
on top of them.

The first contribution is **inventory canonicalization**. UIAO surveys the
Active Directory-joined device estate continuously, reconciling computer
objects in the directory against inventory in Microsoft Configuration
Manager, records in the asset management database, and human-resources
records describing the user assigned to each device. The result is a single
canonical device record per physical asset, carrying its organizational
position (business unit, region, security tier, asset class), its ownership
lineage (assigned user, manager, cost center), and its expected configuration
baseline. The canonical record remains the source of truth even when the
underlying records in Active Directory, Configuration Manager, and the asset
database have drifted apart from one another, as they invariably do over
multi-year operating windows.

The second contribution is **Group Policy drift detection**. UIAO's drift
engine reads the resultant set of policy applied to each domain-joined
device on a recurring cadence, compares the actual applied state against the
canonical policy specification associated with the device's OrgPath, and
emits drift signals when devices diverge. Divergence sources include
intentional GPO scope changes that were not propagated to the canonical
specification, manual local administrator modification, registry tampering,
Group Policy replication failures between domain controllers, organizational
unit restructuring that moves a device into a policy scope different from
its canonical expectation, and devices that have been disconnected from
domain controllers long enough that their applied policy has gone stale.
Without UIAO, these drift conditions are typically discovered during
security incidents or annual audits, often months after the divergence began.

The third contribution is **stale-object identification and lifecycle
hygiene**. UIAO cross-references Active Directory computer objects against
the human-resources system's employment records, identifying machine
accounts whose primary user has departed the organization, dormant
department codes whose hardware should have been retired, and computer
objects that have not authenticated to a domain controller in sufficient
time to indicate the underlying hardware is no longer in service. Stale
objects are flagged for retirement before they accumulate into the hundreds
or thousands of dormant records that legacy estates typically exhibit, and
before they become attack surface for credential-stuffing or
service-account-abuse attacks.

The fourth contribution is **policy compliance verification against
OrgPath**. UIAO catalogs the GPOs linked to each organizational unit and
verifies that the linked set matches the canonical policy specification for
the business unit, region, and security tier represented by that OU's
OrgPath. Drift between the expected GPO assignments (per canonical
specification) and the actual GPO assignments (per Active Directory) is
surfaced as a governance finding requiring administrator review and either
remediation or specification update. This is the inverse of traditional GPO
management: rather than humans assembling the right set of GPOs by
recollection of policy intent, UIAO holds the policy intent as a structured
specification and verifies the assembly.

The fifth contribution is **pre-migration triage and readiness assessment**.
UIAO produces the device-by-device readiness assessment that determines
which legacy devices can be migrated to hybrid join in Phase III, which
require remediation before migration (Trusted Platform Module enablement,
BIOS firmware update, BitLocker pre-boot enablement, Windows version
upgrade, replacement of incompatible peripherals or drivers), and which
should be retired through hardware refresh rather than migrated at all. The
triage output is the structured input to migration planning for subsequent
phases, and it replaces what would otherwise be an estate-wide
reconnaissance project performed by humans inspecting devices one at a time.

The sixth contribution is **evidence emission for audit and compliance
attestation**. Every governed action UIAO performs — inventory reconciliation,
drift detection, stale-object retirement, policy verification, readiness
assessment — emits a structured evidence record to a downstream ledger.
The ledger is queryable for audit and compliance attestation, and it is
continuously up to date rather than assembled retrospectively. This matters
particularly for organizations subject to federal compliance regimes
(FedRAMP, FISMA, NIST 800-53) where audit evidence is otherwise gathered
through laborious manual collection across multiple systems.

---

## What is measurably different from the without-UIAO baseline

| Concern | Without UIAO | With UIAO |
|---|---|---|
| Device inventory accuracy | Records split across Active Directory, Configuration Manager, and the asset database, frequently inconsistent and reconciled manually during audits | Single canonical device record keyed by OrgPath, continuously reconciled against all source systems |
| Group Policy drift | Discovered during security incidents or annual audits, often months after divergence | Detected continuously by the drift engine, surfaced within hours of divergence |
| Stale computer objects | Accumulate until a periodic cleanup project that may run only every two or three years | Flagged within days of becoming stale, retirement workflow automated |
| Audit evidence | Manually assembled from event logs, screenshots, and ad-hoc queries during audit windows | Continuously emitted to a structured evidence ledger, queryable at any time |
| Migration planning input | Estate-wide reconnaissance project requiring weeks or months of engineering effort | Read directly from canonical inventory and OrgPath assignments |
| Policy compliance against ownership | Implicit through OU placement; verification is manual and intermittent | Explicit through OrgPath; verification is automated and continuous |
| Identity-device binding | Inferred from the user who most recently signed in to a device | Tracked canonically against the human-resources system's authoritative assignment |

---

## What UIAO does not change in the legacy phase

It is important to be precise about what UIAO does not change. UIAO does not
modify the underlying behavior of Active Directory authentication, Group
Policy delivery, Configuration Manager application distribution, or
Kerberos ticket issuance. Devices in the legacy phase continue to operate
under the same authentication, configuration, and patching mechanisms they
would in a non-UIAO environment. The user experience is unchanged. The
domain controller infrastructure is unchanged. The imaging pipeline is
unchanged.

What UIAO changes is the *governance posture*: what is known about the
estate, how quickly drift is detected, how readily evidence can be produced
for an auditor, and how cleanly the estate can be triaged for migration into
subsequent phases. These changes are not visible to the end user and are
visible to administrators only through the canonical records and drift
findings UIAO produces. The estate continues to operate; it merely operates
under a layer of observation and specification that was not present before.

---

## Authoritative sources and canonical anchors

Microsoft Learn references for the underlying Active Directory and Group
Policy technologies are listed in the master narrative
([`baseline-without-uiao.md`](baseline-without-uiao.md)).

UIAO canonical anchors for the legacy-phase governance overlay live in the
organization's internal repository under `src/uiao/`. Readers with internal
access can locate the relevant artifacts there; this document does not
duplicate them. The principal anchors are the canonical inventory schema,
the drift engine specification, the OrgPath taxonomy, and the evidence
ledger schema. The Microsoft Coverage Doctrine catalogs what Microsoft
provides at each layer of the legacy estate and what UIAO adds.
