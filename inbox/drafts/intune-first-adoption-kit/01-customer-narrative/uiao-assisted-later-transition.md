# Phase III — Later Transition: UIAO-Assisted View of Hybrid Microsoft Entra Join and Intune Co-Management

## How to read this document

This document is the UIAO-assisted single-phase view of the later transition
phase — Hybrid Microsoft Entra Join with Microsoft Intune co-management, the
operationally most demanding phase of the journey. The corresponding
without-UIAO description of this phase lives in the master narrative at
[`baseline-without-uiao.md`](baseline-without-uiao.md) as Part III.

This document is intended for internal strategy, architecture, governance,
and compliance audiences who want to understand how the organization's UIAO
governance substrate reduces the operational cost and risk of hybrid
coexistence.

---

## What UIAO is, briefly

UIAO is the organization's internal governance substrate for identity,
device management, and access control. It is an internal architecture that
sits across Microsoft Entra ID, Microsoft Intune, on-premises Active
Directory, Microsoft Configuration Manager, and human-resources information
technology systems, providing canonical organizational positioning for
users and devices (OrgPath), continuous drift detection against canonical
state, and evidence emission for compliance and audit.

UIAO does not replace any of the underlying Microsoft technologies. In the
later transition phase specifically, UIAO does not perform hybrid join,
does not enroll devices into Intune, and does not adjust co-management
workload sliders. It observes, specifies, reconciles, and emits evidence.

---

## How UIAO applies to the later transition

The later transition phase is the operationally most expensive phase of the
journey because two management planes run in parallel and must remain
consistent with each other. UIAO's role in this phase is to make the
consistency tractable: to detect divergence between the planes early, to
reconcile device identity across the five systems where it can appear, and
to drive co-management workload assignment from a canonical policy
specification rather than from ad-hoc collection membership.

The first contribution is **device-plane OrgPath binding at the hybrid
join boundary**. As a device completes hybrid Microsoft Entra Join, UIAO
projects the canonical OrgPath onto both the Active Directory computer
object and the corresponding Microsoft Entra ID device object. OrgPath is
derived from the assigned user's user-plane OrgPath (established in
Phase II) modified by device-class attributes (form factor, asset class,
ownership classification, location). The result is that every hybrid-joined
device carries authoritative organizational positioning on both planes,
queryable for policy scoping, compliance evaluation, and audit. Without
UIAO, organizational positioning is implicit through organizational unit
placement and ad-hoc group membership, and the two planes' positions are
not guaranteed to agree.

The second contribution is **drift detection on the hybrid join itself**.
UIAO's drift engine watches the hybrid join handshake for each device and
surfaces failures that would otherwise be silent. The drift signals
include: devices that joined the on-premises domain but failed to register
in Entra ID (the most common silent failure), devices that registered in
Entra ID but were never enrolled in Intune, devices whose hybrid identity
is present but stale because the Entra Connect sync has not propagated a
required attribute, duplicate device objects in Entra ID arising from
re-imaging or re-joining without proper retirement, and devices whose
Service Connection Point points at a tenant other than the intended one.
Each of these failure modes can cause a device to pass Conditional Access
when it should not, or fail Conditional Access when it should not; the
drift engine surfaces them within hours of occurrence rather than during
the next incident.

The third contribution is **five-system reconciliation**. A device in the
later transition phase can appear in five places: the on-premises Active
Directory computer object, the Microsoft Entra ID device object, the
Microsoft Intune managed device record, the Microsoft Configuration Manager
client record, and the Windows Autopilot device record. UIAO reconciles
these five records continuously and emits findings when they disagree.
Disagreement is common: a device that was re-imaged retains its old Intune
record but acquires a new Active Directory record; a device that was
migrated between organizational units retains its old Configuration Manager
collection membership; a device whose Entra device object was manually
deleted continues to authenticate via its Active Directory machine
credential. Each disagreement is a compliance and Conditional Access
hazard. Without UIAO, these disagreements are discovered during incidents
or audits, not before.

The fourth contribution is **canonical-policy-driven co-management workload
assignment**. Microsoft Configuration Manager exposes workload sliders that
determine, per device collection, whether each workload domain (compliance
policies, device configuration, endpoint protection, Office Click-to-Run,
Windows Update for Business, client applications, resource access) is owned
by Configuration Manager or by Microsoft Intune. Without UIAO, workload
assignment is driven by collection membership rules that have to be
maintained by humans and that drift over time. With UIAO, workload
assignment is expressed against OrgPath ("devices in regulated business
units, migration cohort 3, with security tier high should have these
specific workloads on Intune as of this date"), and Configuration Manager
collection membership is generated from the canonical specification.

The fifth contribution is **migration risk scoring**. UIAO computes a
risk score per device that estimates the likelihood of a clean migration
into Phase IV. The score considers Trusted Platform Module health, BitLocker
recovery key presence, Windows version, hardware model compatibility,
peripheral and driver compatibility, network connectivity classification,
user training status, and any open drift findings on the device. The score
drives migration cohort assignment, identifying devices that can be
migrated immediately, devices that require remediation first, and devices
that should be retired through hardware refresh rather than migrated. The
score is recomputed continuously as remediations land and as new findings
arise.

The sixth contribution is **evidence emission per workload transition**.
Each time a co-management workload slider moves a workload domain from
Configuration Manager to Intune for a population of devices, UIAO records
the transition in the evidence ledger: which workload, which devices,
which canonical policy version was active at the transition, which
administrator authorized the transition, what compliance state the
affected devices had at the moment of transition. The evidence is the audit
record of how the estate moved from co-management toward Intune-only
management, and it is queryable retrospectively for compliance attestation
and for incident root-cause analysis.

---

## What is measurably different from the without-UIAO baseline

| Concern | Without UIAO | With UIAO |
|---|---|---|
| Silent hybrid join failures | Discovered when a user is denied access by Conditional Access | Surfaced by drift engine within hours; remediation workflow automated |
| Duplicate device objects | Accumulate across re-imaging and migration cycles; cleanup is project-based | Detected at creation; retirement of stale duplicates is automated |
| Five-system identity reconciliation | Manual during audits | Continuous; disagreement surfaces as governance findings |
| Co-management workload assignment | Collection membership rules maintained by humans, drift inevitable | Generated from canonical OrgPath-scoped policy specification |
| Migration cohort planning | Estate survey by humans; cohort assignment by judgment | Risk-scored automatically; cohort assignment is the output of the score |
| Workload transition evidence | Change management tickets and screenshots | Structured evidence ledger entry per workload-population transition |
| Identity-device binding | Inferred from sign-in logs | Tracked canonically; one user can be canonical owner of multiple devices, each device canonically owned by one user |

---

## What UIAO does not change in the later transition

UIAO does not perform the hybrid join handshake itself. It does not modify
the Microsoft Entra Connect sync engine, the Group Policy delivery
mechanism that triggers hybrid registration, or the certificate trust
relationship between the on-premises domain and Microsoft Entra ID. UIAO
does not enroll devices into Intune; it observes that enrollment has
happened and reconciles the result with its canonical specification.
UIAO does not adjust workload sliders in Microsoft Configuration Manager
directly; it generates the collection membership and policy specification
from which workload assignment is derived, and human administrators apply
the slider changes through normal change management.

What UIAO changes is the *cost and risk profile* of running two management
planes in parallel. The work that humans would otherwise do — reconciling
identity across five systems, discovering silent join failures, planning
migration cohorts, generating audit evidence — is performed continuously
by UIAO. The phase remains operationally expensive (two planes are
inherently more expensive than one), but the marginal cost of governance,
audit, and migration planning is substantially reduced.

---

## Authoritative sources and canonical anchors

Microsoft Learn references for the underlying Hybrid Microsoft Entra Join,
Microsoft Intune, and Microsoft Configuration Manager co-management
technologies are listed in the master narrative
([`baseline-without-uiao.md`](baseline-without-uiao.md)).

UIAO canonical anchors for the later-transition governance overlay live in
the organization's internal repository under `src/uiao/`. The principal
anchors are the device-plane OrgPath binding specification (ADR-038), the
five-system reconciliation specification, the migration risk scoring
algorithm, the co-management workload assignment specification, and the
phase-III evidence ledger schema.
