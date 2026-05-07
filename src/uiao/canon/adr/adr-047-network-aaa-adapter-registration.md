---
adr: ADR-047
title: "Network AAA Adapter Registration and Control-Library `implemented_by` Closure"
status: Proposed
date: 2026-05-07
author: WhalerMike
supersedes: []
superseded_by: null
related:
  - ADR-007  # Multi-Cloud Adapter Model
  - ADR-013  # Adapter Failure Isolation
  - ADR-015  # Adapter Extensibility
  - ADR-044  # Substrate Governance Realignment
---

# ADR-047: Network AAA Adapter Registration and Control-Library `implemented_by` Closure

## Context

The 802.1X / NAC corpus review
(`docs/planning/reviews/802-1x-nac-review.md`, commit `e3d49cf`)
surfaced three coupled structural problems in the control library and
adapter registry. Wave 1
(commit `c56015e`) addressed the terminology and customer-doc gaps.
The remaining items cannot be fixed in isolation because each requires
a coordinated change across the control YAMLs, the adapter registry,
and the DRIFT-IDENTITY trust-anchor walker:

### Problem 1 — Network-AAA tier missing from `implemented_by`

`AC-18` (Wireless Access) and `IA-3` (Device Identification and
Authentication) describe 802.1X authentication but list only the
**authenticator** tier (`cisco-catalyst`) and the cert-issuance tier
(`entra-id`, `intune-mdm`) in `implemented_by`. They omit the
**authentication-server** tier (Cisco ISE, Windows NPS, or Entra
RADIUS Proxy) entirely.

802.1X is a three-party protocol (RFC 3580 §1.1):
supplicant → authenticator → authentication server. A control claim
that names only two of the three tiers cannot satisfy a meaningful
review. The modernization view (`adapters.qmd:134`) and the customer
docs (`01-platform-foundation.qmd:175`) both name the AAA tier
correctly; only the canonical control YAMLs do not.

### Problem 2 — `cisco-ise` and `cisco-catalyst` are referenced but not registered

Six control YAMLs name `cisco-ise` and/or `cisco-catalyst` as
implementers:

```
ac/AC-18.yml          → cisco-catalyst
ia/IA-3.yml           → cisco-catalyst
sa/SA-4(10).yml       → cisco-ise
sc/SC-7(5).yml        → cisco-ise
pe/PE-3(1).yml        → cisco-ise
```

Neither id is registered as a first-class adapter:

- `src/uiao/adapters/` has no `network/cisco-ise/` or
  `network/cisco-catalyst/` directory.
- No `adapter-manifest.json` exists for either id.
- `migration-adapter-registry.yaml` lists `cisco-ise` only as a nested
  `radius` *implementation*, not as a top-level adapter.

This violates the DRIFT-IDENTITY walker invariant established in
[ADR-044](adr-044-substrate-governance-realignment.md) and reinforced
by UIAO_110 (commit `01863ea`): every active adapter declares a
`trust-anchor:` and is reachable through a registered manifest. As-is,
the walker will either flag these tokens as drift or silently skip
them — both are wrong.

### Problem 3 — Status mismatch between AC-18 / IA-3 and IA-5(2)

| Control     | Status            | Depends on                               |
|-------------|-------------------|------------------------------------------|
| AC-18       | `implemented`     | IA-5(2) (cert lifecycle) — NOT impl.     |
| IA-3        | `implemented`     | IA-5(2) (cert lifecycle) — NOT impl.     |
| IA-5(2)     | `not-implemented` | —                                        |

A control cannot be `implemented` if a control it materially depends
on is `not-implemented`. The 802.1X (EAP-TLS) authentication described
in AC-18 and IA-3 *is* the certificate-based public-key authentication
of IA-5(2); the dependency is identity, not analogy.

The control library has no schema-enforced constraint that prevents
this kind of contradiction.

## Decision

### D1 — Introduce a registered `network-aaa` adapter category

Add a new top-level adapter category `src/uiao/adapters/network-aaa/`
with manifests for the four registered RADIUS implementations from
DM_030:

```
src/uiao/adapters/network-aaa/
├── cisco-ise/adapter-manifest.json
├── nps/adapter-manifest.json
├── aruba-clearpass/adapter-manifest.json
└── entra-radius/adapter-manifest.json
```

Each manifest declares `trust-anchor:` per UIAO_110, names the
upstream protocol surface (RADIUS / RadSec), and points back to its
DM_030 entry as `canon-source`.

Add a second category `src/uiao/adapters/network-access/` for the L2
authenticator tier (the switches and APs that originate the EAP
exchange):

```
src/uiao/adapters/network-access/
├── cisco-catalyst/adapter-manifest.json
└── (future: aruba-cx, juniper-mist, ...)
```

Two categories rather than one because the AAA tier and the
authenticator tier have different trust anchors (RADIUS shared secret
or RadSec cert vs. switch management-plane cert) and different drift
surfaces.

### D2 — Close `implemented_by` on the affected control YAMLs

Add the AAA-tier id to every control whose narrative invokes 802.1X:

| Control      | Add to `implemented_by`           |
|--------------|-----------------------------------|
| AC-18        | `cisco-ise`                       |
| IA-3         | `cisco-ise`, `nps` (hybrid window) |
| IA-5(2)      | `cisco-ise`                       |
| SA-4(10)     | (already has `cisco-ise`)         |
| SC-7(5)      | (already has `cisco-ise`)         |

Add corresponding evidence ids
(`cisco-ise-radius-authentication-logs`,
`cisco-ise-eap-method-inventory`, `cisco-ise-mab-fallback-logs`).

### D3 — Add a control-library schema constraint preventing status contradictions

Extend the control-library schema with a rule:

> A control declared `status: implemented` MUST NOT list a
> `related_controls` entry whose own `status` is `not-implemented` or
> `partial`, **unless** the dependency is annotated
> `dependency_kind: informational` (cross-reference only, not
> realization).

Implement as a `canon-check` rule. The check fails on the existing
AC-18 / IA-3 ↔ IA-5(2) contradiction, forcing one of:

1. **Resolve up:** lift IA-5(2) to `implemented` once the cert
   lifecycle work lands.
2. **Resolve down:** demote AC-18 / IA-3 to `partial` until IA-5(2)
   is real.

Either resolution is acceptable; the ADR mandates that the
contradiction be removed, not which direction to remove it in.

### D4 — Migration plan

Three-phase landing:

1. **Phase A (this ADR + manifests):** Land the empty manifests and
   the schema constraint **disabled** (warn-only). No control YAMLs
   change yet. Reviewers can see the target shape.
2. **Phase B (control YAML closure):** Update `implemented_by` on the
   five affected controls. Walker is still warn-only; CI green.
3. **Phase C (constraint enforcement):** Flip the schema constraint
   from warn-only to blocking. Resolve the AC-18/IA-3 ↔ IA-5(2)
   status mismatch in the same PR.

Phases B and C can be combined if the IA-5(2) lift is ready;
otherwise B lands as a clean prep change and C blocks on the
substantive PKI work.

## Consequences

### Positive

- Closes the 802.1X tier-of-control gap surfaced by the corpus review.
- Makes the network-AAA tier first-class in the adapter registry,
  consistent with how IPAM, PKI, and LDAP are already modeled
  (DM_010, DM_020, DM_040).
- Adds a structural guard against status contradictions, which the
  review found by hand and which would otherwise recur.
- DRIFT-IDENTITY walker becomes correct on the network-AAA surface
  (today it is silent or wrong).

### Negative / costs

- Two new adapter categories means more drift surface to maintain.
- Phase C is not free: if the org chooses "resolve down," the SSP
  posture of AC-18 and IA-3 reduces from `implemented` to `partial`,
  which **must** be communicated to the AO before merge. This is the
  right answer (the prior posture was overclaiming) but it is
  externally visible.
- The schema constraint may surface other latent contradictions in
  the control library beyond the one the review found. This is a
  feature, not a bug, but it will likely require a sweep PR.

### Neutral / open

- Whether `nps` should remain in `implemented_by` after migration cut-
  over (Phase B vs. post-Phase B) is a separate operational question
  tracked under DM_030, not this ADR.
- The ADR index (`src/uiao/canon/adr/index.md`) is already stale
  (missing ADR-032 through ADR-046). Re-syncing the index is
  out of scope for this ADR but should be tracked as a follow-up.

## References

- 802.1X / NAC corpus review:
  `docs/planning/reviews/802-1x-nac-review.md` (commit `e3d49cf`)
- Wave 1 fixes commit `c56015e`
- DM_030 RADIUS / NPS Adapter Interface:
  `src/uiao/modernization/directory-migration/adapters/radius/radius-adapter-interface.md`
- UIAO_110 trust-anchor walker:
  `src/uiao/canon/UIAO_110-drift-identity.md` (commit `01863ea`)
- ADR-044 substrate governance realignment
- IEEE 802.1X-2020 §5.1 (three-party authentication model)
- RFC 3580 §1.1 (IEEE 802.1X RADIUS Usage Guidelines)
