# Conditional Access Staged Rollout — UIAO-Assisted View

**Audience:** Identity engineers, security policy owners, governance and
architecture staff familiar with the organization's UIAO framework.

**Purpose:** This document is the UIAO-assisted companion to
[`conditional-access-rollout-playbook.md`](conditional-access-rollout-playbook.md).
The without-UIAO companion describes the staged-rollout discipline that
makes Conditional Access deployment safe and remains the canonical
operational reference for identity engineers performing rollouts. This
document describes what UIAO adds: canonical policy scoping by OrgPath,
evidence emission per policy decision, automated drift detection on the
policy set, and integration with Know Your Customer attestation.

The reader is assumed to have read the without-UIAO companion. This
document does not repeat the staged rollout sequence, the audit-mode
discipline, or the rollback procedure.

---

## What UIAO is, briefly

UIAO is the organization's internal governance substrate providing
canonical organizational positioning (OrgPath), continuous drift
detection, and evidence emission across Microsoft Entra ID, Microsoft
Intune, and integrated identity systems.

---

## How UIAO augments Conditional Access rollout

The first contribution is **policy scoping by OrgPath rather than by
ad-hoc security group**. The without-UIAO companion scopes most policies
to "All users" with exclusions for break-glass accounts, which is the
correct default. The next level of refinement — distinguishing between
user populations that require different controls — typically uses Entra
security groups whose membership is maintained manually or through
dynamic rules over user attributes. UIAO replaces both with OrgPath
scoping. A policy targets the OrgPath classification "employees in
business units handling controlled unclassified information, security
tier high, currently active employment status," and UIAO resolves the
classification to a security group whose membership is generated and
maintained automatically. The policy author writes intent; UIAO provides
the population.

The second contribution is **canonical specification of the policy set
itself**. The Conditional Access policy set in production is generated
from a canonical specification rather than maintained as a collection of
independently-authored policies in the Entra admin center. The
specification describes each policy by its intent, its target population
(by OrgPath), its conditions (legacy auth, geographic location, sign-in
risk, device compliance, device join type), and its grant decision. From
the canonical specification, UIAO projects the actual Conditional Access
policy objects in Entra ID, and verifies continuously that the
projection matches the specification. Drift between the canonical
specification and the actual policy state surfaces as a governance
finding.

The third contribution is **Know Your Customer integration for the
break-glass account configuration**. The break-glass account exclusion
is among the most security-sensitive configurations in the entire
identity surface. UIAO's KYC integration verifies continuously that the
configured break-glass accounts continue to satisfy the canonical break-
glass specification: cloud-only, Global Administrator role assigned,
credentials within the rotation window (or explicitly non-rotating per
specification), last verified test sign-in within the policy window,
monitoring and alerting active. An account that has accidentally
acquired break-glass exclusion without satisfying the canonical
specification is a finding; an account configured as break-glass whose
specification has drifted is also a finding.

The fourth contribution is **evidence emission per policy decision**.
Microsoft Entra sign-in logs include per-sign-in detail about which
Conditional Access policies evaluated and what their decisions were.
The detail is operationally useful but ephemeral, retained for thirty
days by default and longer with Microsoft Entra ID P2 licensing. UIAO
captures the governance-relevant evidence into a long-term ledger: every
policy denial, every exception use, every break-glass sign-in, every
report-only policy match during a rollout. The ledger is the audit
substrate for demonstrating to regulators that access controls were
operating as specified during a particular window — a capability that
matters particularly for organizations subject to federal compliance
regimes where retention requirements exceed Entra's default retention.

The fifth contribution is **staged-rollout sequencing driven by
canonical migration cohort**. The without-UIAO companion sequences
policy introduction by policy type: block legacy authentication first,
then require multi-factor authentication, then require device
compliance. With UIAO, the sequencing additionally accounts for
migration cohort. Devices in cohort 1 (cloud-native, full transition)
are eligible for the device-compliance-required policy immediately;
devices in cohort 3 (hybrid join in progress) become eligible only
after their migration risk score crosses a documented threshold. The
canonical migration cohort assignment from the Phase III UIAO-assisted
view drives policy assignment automatically, so that no user is
suddenly denied access by a policy that their device cannot satisfy.

The sixth contribution is **continuous drift detection on the policy
set itself**. After enforce mode is enabled for a given policy, UIAO
watches the actual Conditional Access policy state in Entra ID. A
policy that has been disabled (whether intentionally during a rollback
or accidentally during investigation), a policy whose exclusion list
has been modified, a new policy created outside the canonical
specification, or a policy whose conditions have been adjusted without
specification update — all surface as drift findings. The without-UIAO
companion relies on quarterly review to catch these conditions; UIAO
catches them within hours.

---

## What is measurably different

| Concern | Without UIAO | With UIAO |
|---|---|---|
| Policy scope | Entra security groups, manually maintained | OrgPath classification, generated automatically |
| Policy specification source of truth | Policy objects in Entra admin center | Canonical specification, projected to Entra |
| Break-glass account verification | Manual quarterly review | Continuous KYC verification |
| Policy evaluation evidence retention | Sign-in logs (default thirty days) | Long-term structured evidence ledger |
| Staged rollout cohort assignment | Engineer judgment | Generated from canonical migration cohort |
| Policy state drift detection | Quarterly review | Continuous; surfaced within hours |
| Cross-policy consistency verification | Manual | Automatic against canonical specification |

---

## What UIAO does not change

UIAO does not modify the Conditional Access policy evaluation engine
itself. The conditions, grants, and decision logic in
[`conditional-access-rollout-playbook.md`](conditional-access-rollout-playbook.md)
remain exactly correct. The report-only-mode-first discipline remains
mandatory. The break-glass account discipline remains the foundation of
safe Conditional Access deployment. The rollback procedure remains the
procedure of last resort during incidents.

What UIAO changes is the *specification, projection, and evidence
posture* surrounding Conditional Access. The day-to-day engineering
practice is largely unchanged: policies are authored, deployed in
report-only mode, verified through sign-in log review, transitioned to
enforce mode, and rolled back if necessary. UIAO automates the boundary
work — scope generation, consistency verification, evidence capture,
drift detection — that humans would otherwise have to perform manually
and at lower fidelity.

---

## Canonical anchors

UIAO anchors for Conditional Access governance live in the
organization's internal repository under `src/uiao/canon/specs/`
(Conditional Access specifications), `src/uiao/governance/` (drift
detection), and `src/uiao/identity/` (OrgPath taxonomy and KYC
specifications).
