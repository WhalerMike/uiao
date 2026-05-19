# Windows Enrollment Diagnostic Cookbook — UIAO-Assisted View

**Audience:** Identity engineers, governance staff, and architecture leads
familiar with the organization's UIAO framework, plus helpdesk leads who
want to understand the diagnostic capabilities UIAO provides above and
beyond the manual cookbook.

**Purpose:** This document is the UIAO-assisted companion to
[`enrollment-diagnostic-cookbook.md`](enrollment-diagnostic-cookbook.md),
which describes the manual diagnostic process for the top ten Windows
enrollment failure modes. The without-UIAO companion stands alone and
remains the canonical operational reference for individual ticket
diagnosis. This document describes what UIAO adds to and surrounds the
manual diagnostic process.

The reader is assumed to have read the without-UIAO companion. This document
does not repeat the symptom descriptions, diagnostic commands, root cause
analyses, or remediation steps; it focuses exclusively on what UIAO
contributes.

---

## What UIAO is, briefly

UIAO is the organization's internal governance substrate providing
canonical organizational positioning, continuous drift detection, and
evidence emission across Microsoft Entra ID, Microsoft Intune, on-premises
Active Directory, and integrated systems.

---

## How UIAO augments enrollment diagnosis

The first contribution is **drift-engine pre-detection of failure modes
before users encounter them**. The top ten failure modes in the without-
UIAO companion are reactive by construction: a user reports a problem, an
engineer diagnoses, an engineer remediates. UIAO's drift engine detects
most of these failure modes proactively, before any user encounters them.
Silent hybrid join failures (failure mode 1) are surfaced within hours of
the failed registration attempt rather than weeks later when the user is
denied access by Conditional Access. Devices that joined Microsoft Entra
ID but failed to enroll in Microsoft Intune (failure mode 4) are surfaced
when the canonical reconciliation runs and notices the absence in Intune.
Duplicate device objects (failure mode 7) are surfaced when the
reconciliation detects two device records corresponding to a single
canonical asset. The engineering team works a curated queue of findings
rather than waiting for the user-report ticket cycle.

The second contribution is **OrgPath cross-reference for ambiguous
identity**. Failure mode 7 (duplicate device object) and failure mode 9
(device joined to personal Microsoft Account) are particularly difficult
to diagnose without an authoritative source about what the device "should"
be. UIAO provides that source. The canonical device record carries the
expected serial number, hardware hash, OrgPath assignment, and current
owner. A diagnostic engineer can query the canonical registry by serial
number and immediately see which of two duplicate Entra device objects is
the canonical one, or that neither is, and what the device should have
been enrolled as. The diagnosis collapses from minutes of investigation
to seconds of lookup, and the lookup answers a question the underlying
Microsoft surfaces cannot answer at all.

The third contribution is **evidence emission for every diagnostic
action**. Each step a diagnostic engineer takes — sync triggered, MDM
enrollment retried, device reset initiated, duplicate retired, hybrid
join re-attempted, PRT refreshed — emits a structured evidence record to
the canonical ledger. The evidence ledger becomes the chronological
record of how the device arrived at its current state and what was done
to recover it, queryable during incident review, audit attestation, and
root-cause analysis. Without UIAO, this chronology lives in ticket
comments and engineer recollection, and is reconstructed by humans during
post-incident review.

The fourth contribution is **automated remediation for canonical-state
deviations**. Several of the failure modes in the cookbook have
remediations that can be performed without human judgment once the
diagnosis is clear. UIAO performs these remediations automatically when
the drift signal is unambiguous: triggering MDM enrollment via
DeviceEnroller for devices in failure mode 4, retiring stale duplicates
for failure mode 7, refreshing PRT for failure mode 6 when the cause is a
recent password change, re-pushing the Autopilot profile assignment for
devices in failure mode 2 whose registration is healthy but whose profile
is missing. Human engineers are involved only for failure modes that
require judgment — compliance policy adjustment, Conditional Access
exception authorization, hardware retirement decisions, vendor escalation.

The fifth contribution is **failure-mode pattern detection across the
estate**. The without-UIAO cookbook diagnoses one device at a time. UIAO
detects patterns across the estate. A sudden uptick in failure mode 2
(Autopilot not picking up the device) correlated with a specific reseller
suggests a procurement contract issue; a sustained pattern of failure
mode 5 (Conditional Access blocking) correlated with a specific business
unit suggests a policy misconfiguration or training gap; a pattern of
failure mode 10 (policies not applying) correlated with a recent Intune
configuration change suggests a regression. Pattern detection turns
individual diagnostic findings into governance signals that drive systemic
remediation rather than per-device firefighting.

The sixth contribution is **a closed feedback loop from diagnosis to
specification**. When UIAO encounters a failure mode that the canonical
specification did not anticipate — a new error code, a previously-
unseen drift class, a remediation path that was not previously
documented — the encounter becomes input to specification update. The
specification grows over time to cover the actual operating envelope of
the estate, not just the envelope that was foreseen at the time of
authoring. The cookbook itself benefits: a new failure mode 11 emerges
when the canonical specification documents it after the second or third
encounter.

---

## What is measurably different

| Diagnostic concern | Without UIAO | With UIAO |
|---|---|---|
| Detection cadence | User reports a problem to helpdesk | Drift engine detects within hours of occurrence |
| Identity ambiguity resolution | Engineer investigates manually across multiple systems | Canonical registry lookup answers in seconds |
| Diagnostic chronology | Ticket comments and engineer notes | Structured evidence ledger |
| Routine remediation | Engineer performs each step manually | Unambiguous remediations performed automatically |
| Cross-device pattern detection | Incident review months later | Continuous correlation against drift findings |
| Audit evidence for diagnostic actions | Reconstructed from tickets | Continuously emitted to ledger |
| Specification update from incident | Manual documentation update if remembered | Closed feedback loop into canonical specification |

---

## What UIAO does not change

UIAO does not change the commands in the without-UIAO companion. The
output of `dsregcmd /status`, the contents of the Microsoft-Windows-AAD
event log, the structure of the Intune Management Extension log, and the
Microsoft Graph query syntax — all are exactly as documented in the
without-UIAO cookbook. The diagnostic vocabulary is identical because the
underlying Microsoft mechanics are identical. An engineer trained on the
without-UIAO companion is fully competent to operate in a UIAO-augmented
environment; the additional capabilities reduce manual work but do not
require relearning the underlying technology.

What UIAO changes is *when* diagnosis happens (proactively rather than
reactively), *who* performs routine remediation (automation rather than
humans for the unambiguous cases), and *how* the diagnostic chronology
becomes durable audit evidence. The engineer's role shifts from reactive
triage toward judgment-call diagnosis and toward feeding insight back
into the canonical specification.

---

## Canonical anchors

UIAO anchors for the diagnostic governance overlay live in the
organization's internal repository under `src/uiao/governance/`
(drift engine) and `src/uiao/canon/` (evidence ledger schemas and the
specification surface that diagnostic findings update).
