# Group Policy to Microsoft Intune Translation — UIAO-Assisted View

**Audience:** Desktop engineering, security policy owners, governance
and compliance staff familiar with the organization's UIAO framework.

**Purpose:** This document is the UIAO-assisted companion to
[`gpo-to-intune-matrix.md`](gpo-to-intune-matrix.md). The without-UIAO
companion provides the working setting-by-setting translation reference
and remains the canonical operational document for engineers performing
the migration. This document describes how UIAO changes the way the
migration is specified, executed, verified, and audited.

The reader is assumed to have read the without-UIAO companion. This
document does not repeat the per-setting translations.

---

## What UIAO is, briefly

UIAO is the organization's internal governance substrate providing
canonical organizational positioning (OrgPath), continuous drift
detection, and evidence emission across Microsoft Entra ID, Microsoft
Intune, on-premises Active Directory, and integrated systems. For the
Group Policy to Microsoft Intune migration, UIAO provides a canonical
policy specification surface that is independent of the delivery
mechanism.

---

## How UIAO augments the migration

The first contribution is **policy expressed once, projected to both
planes**. The organization's canonical policy specification lives in
UIAO's policy substrate, expressed in terms of OrgPath-scoped intent
rather than in terms of Group Policy Object linking or Microsoft Intune
configuration profile assignment. From the canonical specification,
UIAO generates the Group Policy Objects required for the legacy estate
and the Intune configuration profiles required for the cloud-native
estate. The two delivery mechanisms project the same canonical intent;
the canonical specification is the source of truth. Without UIAO,
organizations typically maintain two parallel policy artifacts (a Group
Policy Object and an Intune profile) by hand for any setting present in
both planes, with the predictable consequence that they drift apart over
time.

The second contribution is **automatic gap analysis against the
Microsoft Coverage Doctrine**. The Coverage Doctrine catalogs every
setting in the canonical policy specification and notes whether each is
addressable via Group Policy, via the Configuration Service Provider
surface, via both, via ADMX ingestion, via custom OMA-URI, or via none
of the above. The gap analysis is automatic: when a new setting is
added to the canonical specification, the Coverage Doctrine surfaces
whether a clean delivery path exists and what compensating control is
required if not. Without UIAO, gap discovery is reactive and per-
setting — typically discovered the first time an engineer attempts to
translate a specific GPO and cannot find an equivalent.

The third contribution is **drift detection on both planes**. The
without-UIAO migration produces, during the transitional period, a
population of devices receiving policy from Microsoft Intune and another
population still receiving policy from Group Policy. UIAO's drift engine
watches both planes and verifies that each device, regardless of which
plane delivers it, actually has the policy state its canonical
specification requires. Devices that should have a BitLocker policy
applied but do not — whether the failure is a GPO that did not deliver
or an Intune profile that conflicted with another profile — surface as
drift findings within hours of the failure. The two planes converge
toward the canonical specification under continuous monitoring rather
than drifting under intermittent audit.

The fourth contribution is **OrgPath-scoped policy assignment**. The
without-UIAO migration assigns policy through Group Policy organizational
unit linking and through Intune device group assignment. UIAO assigns
policy through OrgPath scoping: a security baseline applies to devices
in business units classified as handling controlled unclassified
information, the OrgPath taxonomy determines which devices match, and
the GPO linking plus the Intune group membership are generated from the
OrgPath classification. Policy scope changes are made by amending the
canonical specification, and the GPO and Intune projections update
automatically.

The fifth contribution is **evidence emission per setting per device**.
Each setting in the canonical specification, for each device, has an
evidence record indicating whether the setting is currently in the
expected state. The evidence record is queryable for compliance
attestation: a question like "demonstrate that every device in business
units handling controlled unclassified information has BitLocker enabled
with the canonical configuration" returns a structured answer with per-
device detail, including any exceptions and the authorization basis for
each exception. Without UIAO, this question is answered by an engineer
assembling reports from multiple consoles over multiple hours; with
UIAO, it is a query against the evidence ledger.

The sixth contribution is **migration sequencing driven by canonical
specification**. The without-UIAO companion's "Recommended migration
sequence" is a sensible default expressed in general terms (migrate
high-value security settings first, defer Group Policy Preferences items
that require scripting). UIAO replaces general guidance with specific
canonical migration cohorts: a particular GPO is scheduled for migration
on a particular date for a particular OrgPath classification, the
migration is verified by drift detection across both planes after the
move, and the result is recorded in the canonical migration ledger.
Migration becomes a structured program rather than an engineering
backlog.

---

## What is measurably different

| Concern | Without UIAO | With UIAO |
|---|---|---|
| Policy source of truth | Distributed: GPO definitions plus Intune profile definitions, frequently inconsistent | Single canonical specification, projected to both planes |
| Gap analysis | Discovered per-setting during migration | Automatic via the Microsoft Coverage Doctrine |
| Drift detection on Group Policy delivery | Reactive, during incidents or annual audits | Continuous via drift engine |
| Drift detection on Intune delivery | Limited Intune-side reporting | Same continuous drift engine, both planes |
| Policy scope expression | Manual OU linking plus Intune group membership | OrgPath classification drives both |
| Per-device per-setting evidence | Reconstructed from logs and reports | Continuously emitted to evidence ledger |
| Migration sequencing | Engineering backlog with judgment-based prioritization | Structured cohorts driven by canonical specification |

---

## What UIAO does not change

UIAO does not modify the underlying Group Policy or Microsoft Intune
Configuration Service Provider mechanics. The per-setting translations
in [`gpo-to-intune-matrix.md`](gpo-to-intune-matrix.md) remain exactly
correct, because the underlying CSP nodes and Group Policy registry
mappings are pure Windows and Microsoft technology. An engineer
migrating a specific GPO consults the same translation reference whether
UIAO is present or not. The engineer also uses the same Intune Settings
Catalog, the same ADMX ingestion mechanism, and the same security
baseline import workflow.

What UIAO changes is the *coherence and verification* of the migration:
that the same policy intent is delivered consistently to both planes,
that gaps are documented proactively rather than discovered reactively,
that drift is detected continuously, and that per-setting evidence is
available on demand for audit.

---

## Canonical anchors

UIAO anchors for the policy specification substrate live in the
organization's internal repository under `src/uiao/canon/` (canonical
policy specifications) and `src/uiao/governance/` (drift engine and
Coverage Doctrine).
