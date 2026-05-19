# Intune-First Adoption Kit

Operational implementation artifacts for the organization's current Intune-first
adoption work. This kit is the practical companion to the strategic narrative:
the narrative explains the journey from Active Directory Domain Join to pure
Microsoft Entra Join, and the kit gives engineering, procurement, helpdesk,
identity, and security staff the concrete material they need to actually
execute on it.

---

## Audience map — read this first

The kit serves two distinct audiences. Pick the entry point that matches your
role, and ignore the other folder unless you're curious.

**Executive, customer-facing, or socialization audience** — read
[`01-customer-narrative/`](01-customer-narrative/). The narrative explains the
four-phase journey from traditional Active Directory Domain Join through hybrid
coexistence to pure Microsoft Entra Join, in technical depth appropriate for a
CIO-level reader. It is intended to be exported to Word, branded, and
circulated. It does not assume any prior context on the organization's internal
strategy.

**Engineering, helpdesk, procurement, identity, or security audience** — read
[`02-coworker-artifacts/`](02-coworker-artifacts/). Each document in this
folder answers one operational question concretely: how to procure a device
that lands cloud-native, how to translate a Group Policy setting into an Intune
equivalent, how to diagnose an enrollment failure, how to roll out Conditional
Access without locking users out. The documents are intended to be scanned,
bookmarked, and pasted into tickets — not read end-to-end.

---

## With and without UIAO

Most documents in this kit exist as a matched pair: a primary (without-UIAO)
document that stands alone for any reader and remains the canonical
operational reference, plus a companion UIAO-assisted document that
describes what the organization's internal governance framework adds.
Readers without UIAO context can rely entirely on the primary documents;
readers with UIAO context can consult the UIAO-assisted companions to see
how the same operational concerns are augmented under governance.

The customer-narrative folder uses a slightly different convention: a single
master without-UIAO narrative covers all four phases of the journey, and
four per-phase UIAO-assisted companions describe what UIAO adds in each
phase. The two conventions reflect the different audiences — coworker
artifacts are scan-and-find references where matched pairs work cleanly,
while the customer narrative is read end-to-end as a phased journey.

## Status

| Document | Audience | Status |
|---|---|---|
| [`01-customer-narrative/baseline-without-uiao.md`](01-customer-narrative/baseline-without-uiao.md) | Executive, customer (4-phase overview, all phases in one document) | Draft, ready for review |
| [`01-customer-narrative/without-uiao-legacy.md`](01-customer-narrative/without-uiao-legacy.md) | Executive, customer (Phase I detailed) | Draft, ready for review |
| [`01-customer-narrative/uiao-assisted-legacy.md`](01-customer-narrative/uiao-assisted-legacy.md) | Executive, customer (Phase I UIAO-assisted) | Draft, ready for review |
| [`01-customer-narrative/without-uiao-early-transition.md`](01-customer-narrative/without-uiao-early-transition.md) | Executive, customer (Phase II detailed) | Draft, ready for review |
| [`01-customer-narrative/uiao-assisted-early-transition.md`](01-customer-narrative/uiao-assisted-early-transition.md) | Executive, customer (Phase II UIAO-assisted) | Draft, ready for review |
| [`01-customer-narrative/without-uiao-later-transition.md`](01-customer-narrative/without-uiao-later-transition.md) | Executive, customer (Phase III detailed) | Draft, ready for review |
| [`01-customer-narrative/uiao-assisted-later-transition.md`](01-customer-narrative/uiao-assisted-later-transition.md) | Executive, customer (Phase III UIAO-assisted) | Draft, ready for review |
| [`01-customer-narrative/without-uiao-full-transition.md`](01-customer-narrative/without-uiao-full-transition.md) | Executive, customer (Phase IV detailed) | Draft, ready for review |
| [`01-customer-narrative/uiao-assisted-full-transition.md`](01-customer-narrative/uiao-assisted-full-transition.md) | Executive, customer (Phase IV UIAO-assisted) | Draft, ready for review |
| [`02-coworker-artifacts/procurement-one-pager.md`](02-coworker-artifacts/procurement-one-pager.md) | Procurement, asset management | Draft, ready for review |
| [`02-coworker-artifacts/procurement-one-pager-uiao-assisted.md`](02-coworker-artifacts/procurement-one-pager-uiao-assisted.md) | Procurement, asset management | Draft, ready for review |
| [`02-coworker-artifacts/gpo-to-intune-matrix.md`](02-coworker-artifacts/gpo-to-intune-matrix.md) | Desktop engineering, security policy | Draft, ready for review |
| [`02-coworker-artifacts/gpo-to-intune-matrix-uiao-assisted.md`](02-coworker-artifacts/gpo-to-intune-matrix-uiao-assisted.md) | Desktop engineering, security policy | Draft, ready for review |
| [`02-coworker-artifacts/enrollment-diagnostic-cookbook.md`](02-coworker-artifacts/enrollment-diagnostic-cookbook.md) | Helpdesk, field techs | Draft, ready for review |
| [`02-coworker-artifacts/enrollment-diagnostic-cookbook-uiao-assisted.md`](02-coworker-artifacts/enrollment-diagnostic-cookbook-uiao-assisted.md) | Helpdesk, field techs | Draft, ready for review |
| [`02-coworker-artifacts/conditional-access-rollout-playbook.md`](02-coworker-artifacts/conditional-access-rollout-playbook.md) | Identity, security, change advisory | Draft, ready for review |
| [`02-coworker-artifacts/conditional-access-rollout-playbook-uiao-assisted.md`](02-coworker-artifacts/conditional-access-rollout-playbook-uiao-assisted.md) | Identity, security, change advisory | Draft, ready for review |

---

## Why this kit exists separately from Microsoft's documentation

Microsoft Learn describes the products. This kit describes how to use them in
this organization's environment, and what to do when the Microsoft happy path
does not match operational reality. The value-add is in the synthesis across
products (Windows Autopilot, Apple Business Manager, Android Zero-Touch, Samsung
Knox Mobile Enrollment, and Azure Arc treated as one procurement decision
rather than five separate Microsoft pages), the contract-ready language
(Purchase Order clauses and qualifying questions for resellers), the
verification steps Microsoft does not write (how to confirm a device landed in
the tenant *before* it ships), and the failure modes Microsoft's documentation
does not address (what to do when the vendor missed the registration, when the
device landed in the wrong tenant, when the deployment profile was not
assigned).

The kit also acknowledges that most enterprises are operating in all four
phases of the adoption journey *simultaneously* rather than transitioning
through them sequentially. The coworker artifacts are written to be useful
whether the device in front of you is legacy AD-joined, hybrid, or cloud-native.

---

## Lifecycle and scope

This kit is operational, not canonical. Individual documents may eventually be
promoted to permanent reference status if a pattern proves durable, but the kit
as a whole is expected to evolve continuously while Microsoft's product
surfaces change, and to sunset once the organization's full transition to Entra
Join is complete and the residual hybrid population has been retired through
hardware refresh.

Documents in this kit should be updated whenever Microsoft announces a material
change to the relevant product surface, whenever the organization's tenant
configuration changes in a way that affects the guidance, or whenever a
failure mode is encountered in production that was not previously documented.

---

## Related canonical material

Readers who want the formal organizational doctrine — including the five-phase
process specification, the per-platform enrollment annexes, validation and
evidence emission requirements, and the architectural decision records that
anchor the strategy — can find it in the canonical repository under
[`src/uiao/modernization/intune-first-onboarding/`](../../../src/uiao/modernization/intune-first-onboarding/),
anchored by ADR-067 and ADR-071. The canon describes the *what* and the *why*;
this kit describes the *how* and the *what-to-do-when-it-goes-wrong*. Most
coworkers will only ever need this kit; the canon is available for readers who
want the underlying specification.
