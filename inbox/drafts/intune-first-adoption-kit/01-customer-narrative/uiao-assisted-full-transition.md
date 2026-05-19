# Phase IV — Full Transition: UIAO-Assisted View of Pure Microsoft Entra Join and Intune-First Onboarding

## How to read this document

This document is the UIAO-assisted single-phase view of the full transition
phase — net-new devices that are procured, provisioned, and operated entirely
within the cloud-native Microsoft Entra ID and Microsoft Intune surfaces,
without ever joining Active Directory. The corresponding without-UIAO
description of this phase lives in the master narrative at
[`baseline-without-uiao.md`](baseline-without-uiao.md) as Part IV.

This document is intended for internal strategy, architecture, governance,
and compliance audiences who want to understand how the organization's UIAO
governance substrate operationalizes the Intune-first model into a
repeatable, evidence-bearing, drift-resistant process.

---

## What UIAO is, briefly

UIAO is the organization's internal governance substrate for identity,
device management, and access control. It is an internal architecture that
sits across Microsoft Entra ID, Microsoft Intune, and the upstream
procurement, asset management, and human-resources systems, providing
canonical organizational positioning for users and devices (OrgPath),
continuous drift detection against canonical state, and evidence emission
for compliance and audit.

In the full transition phase, UIAO is most visible because the cloud-native
model exposes the smallest surface area of native Microsoft governance.
Microsoft Entra ID, Microsoft Intune, and Conditional Access provide the
operational mechanism; UIAO provides the canonical specification, the
process discipline, and the audit posture that bind those mechanisms into a
governed system.

---

## How UIAO applies to the full transition

The full transition phase is where UIAO is most architecturally significant,
because the cloud-native operating model has fewer built-in constraints on
device identity, organizational positioning, and lifecycle than the
on-premises model it replaces. UIAO supplies the constraints that the cloud
model does not enforce natively.

The first contribution is **the canonical five-phase Intune-first
onboarding process**. UIAO formalizes onboarding as a five-phase sequence:
Procure, Pre-stage, Position, Provision, and Validate. Each phase has
specified inputs, outputs, evidence emissions, and exit criteria. Procure
captures the procurement decision and the organizational context for the
device. Pre-stage registers the device into the appropriate vendor
pre-registration surface (Windows Autopilot, Apple Business Manager,
Android Zero-Touch, Azure Arc onboarding) before the device leaves the
vendor's possession. Position assigns OrgPath, dynamic group membership,
Conditional Access scope, compliance policy, application set, and update
ring, all derived from canonical specification rather than ad-hoc
assignment. Provision is the device-side Autopilot experience, which is now
fully determined by the canonical pre-stage and position decisions.
Validate verifies that the provisioned device matches its canonical
specification end-to-end, emits evidence of conformance, and admits the
device into production operation. The five-phase process is documented as
the organization's canonical specification, and ADR-067 and ADR-071 anchor
the doctrine.

The second contribution is **OrgPath assigned at procurement time**. The
single most consequential UIAO contribution in the full transition phase is
that OrgPath is determined at procurement time, written to the canonical
device record before the device ships, and inherited automatically by every
downstream system. The Autopilot deployment profile, the Apple Business
Manager device assignment, the Zero-Touch configuration assignment, and the
Azure Arc resource group placement are all derived from OrgPath. The
dynamic security group memberships that drive Conditional Access scoping
and compliance policy targeting are derived from OrgPath. The user
assignment, the asset class, the cost center, and the business unit are
encoded in OrgPath and are present on the device record before the device
is powered on. The device emerges from out-of-box experience already in the
right groups, already inside the right Conditional Access scope, already
evaluated against the right compliance policy, and already governed by the
right configuration profile.

The third contribution is **scoping Cloud Kerberos Trust by OrgPath**. The
cloud-native model accommodates on-premises resource access through
Microsoft Entra Kerberos (Cloud Kerberos Trust). UIAO ensures that the
reach-back is scoped: a device with one OrgPath can reach a particular set
of on-premises resources, while a device with a different OrgPath cannot.
Without UIAO, Cloud Kerberos Trust is either enabled globally (every
Entra-joined device can request tickets for any on-premises resource its
user is authorized for) or not at all. With UIAO, the reach-back is
expressed in terms of OrgPath-scoped Conditional Access policy, and the
on-premises resources themselves are tagged with the OrgPath classes
authorized to reach them. The scoping is enforced at the Conditional Access
boundary and observed by the Kerberos service ticket issuance pipeline.

The fourth contribution is **continuous validation against canonical
specification**. Every device in the full transition phase is evaluated
continuously by UIAO's drift engine. The evaluation reads the device's
current state from Microsoft Entra ID, Microsoft Intune, the assigned
Conditional Access policies, the current compliance state, the assigned
application set, and the current update ring posture, and compares each
dimension against the canonical specification the device was provisioned
to. Divergence is flagged and routed through a remediation workflow. The
divergence sources include compliance drift (a setting changed locally),
group membership drift (a security group was modified ad-hoc), policy drift
(a Conditional Access policy was modified in a way that affects this
device's scope), and ownership drift (the user assignment changed without
the device record updating).

The fifth contribution is **evidence emission for federal compliance
attestation**. Each phase of the onboarding process and each subsequent
governance event emits a structured evidence record to the canonical
ledger. The ledger is the audit substrate for FedRAMP, FISMA, NIST 800-53,
and any other compliance regime the organization is subject to. The
evidence records include the procurement decision, the pre-registration
confirmation, the OrgPath assignment, the Conditional Access scope
assignment, the compliance policy assignment, the provisioning completion,
the validation outcome, and every subsequent drift detection or
remediation. Auditors query the ledger directly rather than requesting
ad-hoc evidence packages from administrators.

The sixth contribution is **Know Your Customer integration at the
device-user binding boundary**. Each device-user assignment is verified
against the human-resources information technology system at provisioning
time and continuously thereafter. A device whose assigned user has changed
employment status, whose OrgPath no longer matches the user's current
position, or whose user has departed the organization is flagged for
re-assignment or retirement. The KYC layer ensures that the device-user
binding remains current rather than reflecting a snapshot from the
provisioning moment.

The seventh contribution is **the Microsoft Coverage Doctrine for the
cloud-native estate**. UIAO's Coverage Doctrine catalogs what Microsoft
provides in the cloud-native model — Autopilot, Intune, Conditional
Access, Entra ID Protection, Microsoft Defender for Endpoint, and the
surrounding ecosystem — and what gaps remain. The gaps include policy
expressiveness limitations on the Configuration Service Provider surface
where some legacy Group Policy settings have no equivalent, organizational
positioning gaps where Entra ID does not provide hierarchical organizational
units, and continuity gaps where certain on-premises capabilities require
explicit cloud reach-back. The doctrine is the input to compensating-control
planning that closes each documented gap with an UIAO-provided overlay.

---

## What is measurably different from the without-UIAO baseline

| Concern | Without UIAO | With UIAO |
|---|---|---|
| Onboarding process discipline | Ad-hoc procurement and provisioning per device | Five-phase canonical process with specified inputs, outputs, and exit criteria |
| Organizational positioning at provisioning time | Assigned post-hoc, after device reaches user | Assigned at procurement, inherited by every downstream system |
| Conditional Access scoping | Entra groups maintained manually | OrgPath-driven, generated from canonical specification |
| On-premises reach-back scoping | All-or-nothing per device | OrgPath-scoped per resource class |
| Drift detection cadence | Discovered during incidents or audits | Continuous; surfaced within hours |
| Audit evidence for federal compliance | Manually assembled per audit window | Continuously emitted to structured ledger, queryable on demand |
| Device-user binding currency | Snapshot at provisioning, manually maintained thereafter | Continuously verified against HRIT state via KYC |
| Gap awareness for cloud-native limitations | Discovered during specific feature requests | Cataloged in Microsoft Coverage Doctrine, remediation planned proactively |

---

## What UIAO does not change in the full transition

UIAO does not modify the behavior of Windows Autopilot, Microsoft Intune
policy delivery, Microsoft Entra ID authentication, or Conditional Access
policy evaluation. The device-side out-of-box experience is identical
whether or not UIAO is present; the user signs in, the device joins Entra
ID, Intune enrolls the device, configuration profiles deliver, and the
desktop appears. The hardware-side, network-side, and identity-side
mechanics are pure Microsoft.

What UIAO changes is the *upstream specification and downstream
attestation*. The Autopilot profile assigned to a device is generated by
UIAO from the canonical OrgPath specification rather than authored by hand
in the Intune console. The compliance policy applied to the device is
generated by UIAO from the canonical compliance specification rather than
maintained as an independent Intune-resident artifact. The dynamic group
memberships that drive Conditional Access scoping are generated by UIAO
from the canonical OrgPath specification rather than maintained as
independent Entra group definitions. The evidence emitted after each
governance event is structured against the canonical schema rather than
assembled from logs after the fact.

The cloud-native mechanism remains pure Microsoft. The governance posture
is what UIAO provides.

---

## Authoritative sources and canonical anchors

Microsoft Learn references for Windows Autopilot, Microsoft Entra Join,
Microsoft Intune, Conditional Access, and Cloud Kerberos Trust are listed
in the master narrative
([`baseline-without-uiao.md`](baseline-without-uiao.md)).

UIAO canonical anchors for the full-transition governance overlay live in
the organization's internal repository under
`src/uiao/modernization/intune-first-onboarding/` and are anchored by
ADR-067 and ADR-071. The principal artifacts are the five-phase process
specification, the procurement handoff specification, the platform-specific
enrollment annexes (Windows Autopilot, Microsoft Surface, macOS via Apple
Business Manager, iOS/iPadOS via Apple Business Manager, Android via
Zero-Touch and Knox Mobile Enrollment, Azure Arc-managed servers), the
validation and evidence emission specification, and the Microsoft Coverage
Doctrine catalog.
