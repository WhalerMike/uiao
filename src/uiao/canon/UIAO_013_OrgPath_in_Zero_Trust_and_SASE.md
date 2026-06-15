---
document_id: UIAO_013
title: "OrgPath in Zero Trust & SASE / SSE"
version: "0.1"
status: Draft
owner: Michael Stratton
created_at: "2026-06-10"
updated_at: "2026-06-10"
publish_to_site: false
# Operator/architect narrative; companion to UIAO_010/011/012 and UIAO_120. Not yet published as a standalone canon page.
# foundational-trace: <reserved — populate when Charter Restoration PR-E lands>
---

# OrgPath in Zero Trust & SASE / SSE

> **Purpose.** Operator- and architect-facing narrative for how the
> OrgPath attribute feeds **Zero Trust** access decisions and
> **SASE / SSE** edge controls — especially for **generic / public
> cloud apps** (SaaS, internet-facing services) that lack deep native
> integration and can only be governed at the identity and edge layers.
> This document introduces **no new mechanism**: the Zero-Trust / SASE
> enforcement boundary is owned by
> [UIAO_120 Zero-Trust Integration Layer](specs/zero-trust.md) and the
> SASE / ZTNA overlay-fabric contract is decided in
> [ADR-066](adr/adr-066-application-aware-networking-and-token-bound-transport.md);
> the application-plane signal source (Defender for Cloud Apps /
> Conditional Access App Control) is registered in
> [ADR-049](adr/adr-049-microsoft-adapter-coverage-expansion.md). This
> document explains *how OrgPath sharpens those decisions, what an
> operator does, and what catches them when org context drifts*.
>
> **Companion documents — the OrgPath transport series.**
> [UIAO_010 OrgPath in Azure Policy](UIAO_010_OrgPath_in_Azure_Policy.md)
> covers the Arc-server workload-configuration transport.
> [UIAO_011 OrgPath in Intune & Device Governance](UIAO_011_OrgPath_in_Intune_and_Device_Governance.md)
> covers the Entra-joined-client compliance transport.
> [UIAO_012 OrgPath in NAC / 802.1X](UIAO_012_OrgPath_in_NAC_and_8021X.md)
> covers the network-edge admission transport.
> This document covers the **access-decision** transport — the one that
> applies when a user (on a device) reaches a cloud app, *upstream of
> the app itself*.

## What OrgPath is, in one paragraph

OrgPath is UIAO's deterministic organizational-addressing model. It
collapses legacy AD X.500 OU hierarchies
(`OU=IT,OU=Baltimore,OU=East,DC=contoso`) into a clean, cloud-native
string attribute — `CORP/US/EAST/BALTIMORE/IT` — stamped on **users**
and **devices** via Entra extension attributes or custom security
attributes. It is governed by a machine-readable **codebook** (SSOT in
YAML + JSON Schema, [UIAO_151](UIAO_151_OrgPath_Codebook.md)) and drives
downstream automation: dynamic groups, administrative units, movers
(event-driven recalculation), drift detection, and policy targeting.
Zero Trust treats **identity as the perimeter**; OrgPath turns the org
chart into a first-class, governed signal that the perimeter can act on.

## Scope

In scope:

- How OrgPath-derived **dynamic groups** ([UIAO_152](UIAO_152_Dynamic_Group_Library.md))
  and **administrative units** ([UIAO_154](UIAO_154_Delegation_Matrix_AUs_Roles.md))
  feed **Conditional Access** — the primary Zero-Trust enforcement
  engine in the Microsoft ecosystem.
- How the same OrgPath signal sharpens **SASE / SSE** controls (secure
  web gateway, CASB / Defender for Cloud Apps session control, ZTNA-style
  private access) for generic / public cloud apps.
- The cross-plane consistency that lets an access decision combine
  *who a user is in the org* (user-plane OrgPath) with *what device
  they are on* (device-plane OrgPath, UIAO_011/UIAO_153).
- Why governance and drift detection on the OrgPath signal are
  load-bearing for Zero-Trust trustworthiness and audit.

Out of scope:

- Azure Policy targeting on Arc — see **UIAO_010**.
- Intune profile / compliance-policy targeting — see **UIAO_011**.
- NAC / 802.1X network-admission targeting — see **UIAO_012**.
- The Zero-Trust pillar/evidence model and the SASE overlay-fabric
  schema themselves — owned by **UIAO_120** and **ADR-066**. This
  document is the *OrgPath consumer* of those surfaces, not their
  definition.
- Authoring of Conditional Access policy bodies, DLP policy bodies, or
  SASE forwarding profiles. Those are authored in their platform's own
  surface and consumed here by reference (the dynamic group or attribute
  they target).

## Authoritative artifacts

| Role | Artifact |
|---|---|
| Zero-Trust pillar / enforcement model | [UIAO_120 Zero-Trust Integration Layer](specs/zero-trust.md) |
| SASE / ZTNA overlay-fabric contract | [ADR-066: Application-Aware Networking & Token-Bound Transport](adr/adr-066-application-aware-networking-and-token-bound-transport.md) |
| Application-plane signal (CASB / session control) | [ADR-049: Microsoft Adapter Coverage Expansion](adr/adr-049-microsoft-adapter-coverage-expansion.md) (Defender for Cloud Apps / Conditional Access App Control) |
| OrgPath codebook (selector vocabulary) | [UIAO_151 OrgPath Codebook](UIAO_151_OrgPath_Codebook.md) |
| Dynamic-group canon (target groups) | [UIAO_152 Dynamic Group Library](UIAO_152_Dynamic_Group_Library.md) + [ADR-036](adr/adr-036-dynamic-group-provisioning.md) |
| Administrative-unit / delegation canon | [UIAO_154 Delegation Matrix — AUs & Roles](UIAO_154_Delegation_Matrix_AUs_Roles.md) |
| User/device OrgPath writeback origin | [UIAO_153 Attribute Mapping Table](UIAO_153_Attribute_Mapping_Table.md) + [ADR-038](adr/adr-038-device-plane-orgpath.md) |
| Drift engine | [UIAO_163 Drift Detection Engine Specification](UIAO_163_Drift_Detection_Engine_Specification.md) |

If any pair above goes out of sync (a Conditional Access policy targets
an `OrgTree-*` group UIAO_152 no longer declares, an AU references an
OrgPath segment not in UIAO_151, a SASE policy references a group that
canon does not own), that is a `DRIFT-PROVENANCE` finding by definition.

## The targeting model

OrgPath governs Zero-Trust / SASE access by **attribute → dynamic group
→ policy**, not by enumerating users. The OrgPath attribute travels with
the identity; dynamic groups translate it into a membership the policy
engines already understand; Conditional Access (in-boundary) and the
SASE / CASB plane consume that membership at access time.

```
+----------------------------+     +----------------------------+
| canon/data/orgpath/        |     | canon/data/orgpath/        |
| codebook.yaml              |     | dynamic-groups.yaml        |
| (UIAO_151 / ADR-035)       |     | (UIAO_152 / ADR-036)       |
| CORP, CORP/FINANCE, ...    |     | OrgTree-FIN-Users, ...     |
+--------------+-------------+     +--------------+-------------+
               | active prefix                    | rule keys off OrgPath
               v                                  v
        +---------------------------------------------+
        | Entra ID                                    |
        |  - OrgPath stamped on user + device object  |
        |    (extension / custom security attribute)  |
        |  - dynamic group membership recomputed on   |
        |    mover events                             |
        +-----------------------+---------------------+
                                |
              +-----------------+------------------+
              v                                    v
   +-------------------------+        +--------------------------------+
   | Conditional Access      |        | SASE / SSE plane               |
   | (in-boundary ZT engine) |        | (SWG, CASB / Defender for      |
   |  - require compliant    |        |  Cloud Apps session control,   |
   |    device + phish-      |        |  ZTNA-style private access)    |
   |    resistant MFA        |        |  - consumes the same           |
   |  - session controls     |        |    OrgTree-* group / attribute |
   |  - block / step-up      |        |  - applies DLP, session        |
   |    per OrgTree-* group  |        |    recording, egress controls  |
   +-------------------------+        +--------------------------------+
                                |
                                v
                       generic / public cloud app
                  (governed UPSTREAM — before traffic lands)
```

Two consequences flow from this:

1. **The user and/or device must already carry an OrgPath value** before
   any policy authored against an `OrgTree-*` group can take effect.
   That value is written by the user/device-plane work
   (UIAO_153 / ADR-038), not by this document. A Conditional Access
   policy targeting `OrgTree-FIN-Users` simply does not apply to a
   principal whose OrgPath is absent or stale — there is no error
   condition; the policy is silently inapplicable. This is exactly why
   the governance / drift sections below are load-bearing.
2. **The dynamic group must already exist in canon** before a policy can
   target it. Same property as Intune (UIAO_011) and NAC (UIAO_012): a
   group is declared in `dynamic-groups.yaml` (UIAO_152) via the ADR-036
   workflow; targeting a group canon does not own surfaces as a phantom
   on the consuming plane.

## How OrgPath strengthens Zero Trust

Zero Trust centers on identity-as-perimeter, continuous verification,
least privilege, and context-aware decisions (user + device + app
sensitivity + risk). OrgPath helps in four concrete ways.

### 1. Granular, attribute-based policy targeting (ABAC-style)

Dynamic Entra groups are built with simple rules —
`OrgPath startsWith "CORP/FINANCE/"` or
`OrgPath eq "CORP/US/EAST/BALTIMORE/IT"` — and those groups feed
Conditional Access, the primary in-boundary enforcement engine. This
makes policies like the following expressible without enumerating users:

- *"Finance org-path users reaching a high-sensitivity SaaS app must use
  a compliant device + phishing-resistant MFA + session control."*
- *"Only specific org paths may reach a given public cloud app at all."*

No fleet of hand-maintained static groups: membership recomputes
automatically when people move in the org (the **mover** event).

### 2. Cross-plane consistency (user → device → access)

OrgPath propagates to **devices** as well as users (UIAO_011 / UIAO_153),
so an access decision can combine *who the user is in the org* with
*what device they are on*. When a user reaches a generic SaaS app —
directly or via SASE — the decision considers both planes from one
governed signal, rather than two unrelated attribute sources.

### 3. Administrative units + delegated governance

OrgPath-bound administrative units ([UIAO_154](UIAO_154_Delegation_Matrix_AUs_Roles.md))
scope admin permissions to org segments and tie into access reviews and
entitlement management. This keeps administration of the cloud-app
integrations and policies themselves least-privilege — the people who
manage Finance's SaaS access posture are scoped to the Finance OrgPath.

### 4. Governance & drift detection (the trust in Zero Trust)

In a Zero-Trust world, **stale or incorrect org context = broken
policy** — and broken silently (see consequence 1 above). UIAO's drift
engine ([UIAO_163](UIAO_163_Drift_Detection_Engine_Specification.md))
continuously validates that OrgPath assignments, dynamic-group
definitions, and the policy targets that consume them have not drifted.
This makes the identity signals feeding Conditional Access and the SASE
plane **auditable and reliable** — the difference between a Zero-Trust
control you can attest to and one you merely hope is correct (and the
basis for the OSCAL / KSI evidence the substrate emits).

## How OrgPath helps SASE / SSE for generic public cloud apps

SASE / SSE — Microsoft's Global Secure Access surface (Internet Access +
Private Access) plus CASB capabilities (Defender for Cloud Apps,
registered in ADR-049) — protects access to public-internet and SaaS
apps via cloud-delivered secure web gateway, CASB, and ZTNA-style
controls. Generic apps often support only basic SSO (SAML / OIDC) or
nothing at all. The leverage OrgPath provides:

- **Rich identity context at the edge.** SASE solutions authenticate via
  Entra ID, so OrgPath (as an attribute or via dynamic-group membership)
  travels with the user. CASB / SWG policy can then, e.g., apply stricter
  DLP or session recording for Finance / Legal / Executive org paths
  reaching risky SaaS, block or redirect by org segment + app risk, and
  enforce per-org-path exfiltration controls.
- **Dynamic policy targeting for SASE controls.** Platforms that consume
  Entra groups or attributes (Defender for Cloud Apps among them) can
  target the OrgPath-derived `OrgTree-*` groups directly — maintainable
  targeting without constant manual updates.
- **Upstream protection even for "dumb" apps.** For apps with weak native
  controls, protection happens *before* traffic reaches the app:
  Conditional Access (gated by OrgPath groups) blocks or steps up auth,
  and the SASE proxy enforces network/session controls. OrgPath makes
  those upstream decisions organizationally precise.
- **Hybrid / migration continuity.** During AD-to-Entra modernization (a
  core UIAO use case, [UIAO_007](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)),
  OrgPath replaces legacy OU-based thinking with attribute-based controls
  that work the same on day one of the cloud SASE rollout as in steady
  state.

## Practical benefits summary

| Area | Without OrgPath / UIAO | With OrgPath / UIAO |
|---|---|---|
| Policy granularity | Broad groups or per-app manual lists | Precise org-path dynamic groups + Conditional Access policies |
| Maintenance | Static groups go stale | Automatic via movers + drift detection |
| Device + user context | Limited | Unified OrgPath on both planes |
| Generic SaaS apps | Coarse controls or none | Org-aware CASB / SWG / CA upstream of the app |
| Compliance / audit | Hard to prove org-context accuracy | Governed codebook + drift classification + OSCAL artifacts |
| Zero-Trust maturity | Identity signals are flat | Rich, hierarchical, continuously validated context |

## Boundary rules

- Every user and device reachable from this transport MUST be in the
  GCC-Moderate boundary, consistent with UIAO_010/011/012. Conditional
  Access is a first-party in-boundary control and is the dependable
  enforcement engine here.
- **SASE / SSE availability is a service-availability question, not an
  architecture question.** Where a cloud-native SASE / SSE control
  (e.g., Global Secure Access Internet/Private Access) is **not yet
  available in the deployed boundary**, verify against current Microsoft
  service availability before relying on it — and fall back to the
  in-boundary engine: the same OrgPath-derived dynamic groups still
  drive Conditional Access, which does not depend on the SASE plane
  being present. The OrgPath signal is the constant; which planes consume
  it varies with what is GA in-boundary.
- Cross-tenant principals are out of scope: a user or device whose
  primary tenant is not the governed tenant is invisible to the group
  lookup and excluded from this transport's evaluation.

## Drift considerations

| Class | Trigger |
|---|---|
| `DRIFT-PROVENANCE` | A Conditional Access or SASE policy targets an `OrgTree-*` group no longer declared in `dynamic-groups.yaml`, or a dynamic-group rule references an OrgPath prefix no longer in the codebook. Caught at PR CI for the canon-owned side. |
| `DRIFT-AUTHZ` | A portal-authored, `OrgTree-*`-named CA policy or AU exists that canon does not declare — possible unauthorized targeting drift. |
| `DRIFT-IDENTITY` | A principal whose OrgPath attribute is missing or stale: the dynamic-group lookup fails, the access policy is **silently inapplicable**, and the Zero-Trust decision degrades to whatever the catch-all policy does. This is the load-bearing drift class at this transport — it is the mechanism by which "stale org context = broken policy." Carried against UIAO_153. |

`DRIFT-IDENTITY` is why this transport cannot be trusted without the
governance loop: unlike a malformed policy (which fails loudly), a
missing OrgPath value fails *quietly* — the policy still exists, it just
matches no one. Continuous drift detection is what converts that silent
failure into a surfaced finding.

## Forcing-function rationale

OrgPath-driven Zero-Trust / SASE targeting exists because:

1. **Generic / public cloud apps cannot be deeply governed from inside
   the app.** When you cannot push controls *into* a SaaS app, you must
   enforce them at the identity and edge layers — and those layers
   decide on attributes and group membership. OrgPath is the attribute
   that makes those decisions organizationally precise.
2. **Zero Trust requires context-aware, continuously verified
   decisions** (NIST SP 800-207). Flat identity signals cannot express
   "Finance, on a compliant device, reaching a high-risk app." A
   governed hierarchical org attribute can.
3. **Static group sprawl does not scale and goes stale.** Movers +
   dynamic groups keep targeting correct without manual maintenance;
   drift detection keeps it *attestable*.
4. **The substrate already owns the ZT/SASE enforcement boundary**
   (UIAO_120, ADR-066) and the application-plane signal source
   (ADR-049). What was missing was the OrgPath-series narrative for how
   the org attribute feeds them — this document closes that gap, the
   same way UIAO_010/011/012 close it for Azure Policy, Intune, and NAC.

## Related canon

- [UIAO_010 OrgPath in Azure Policy](UIAO_010_OrgPath_in_Azure_Policy.md) — Arc workload-configuration transport (sibling).
- [UIAO_011 OrgPath in Intune & Device Governance](UIAO_011_OrgPath_in_Intune_and_Device_Governance.md) — Entra-joined client compliance transport (sibling).
- [UIAO_012 OrgPath in NAC / 802.1X](UIAO_012_OrgPath_in_NAC_and_8021X.md) — network-edge admission transport (sibling).
- [UIAO_120 Zero-Trust Integration Layer](specs/zero-trust.md) — the ZT pillar/enforcement model this document consumes.
- [UIAO_193 OrgPath Multi-Cloud Binding Profiles](UIAO_193_OrgPath_MultiCloud_Binding.md) — vendor-neutral storage + facet carriage (SCIM / token claims) that delivers org context to non-Microsoft IdPs and SASE consumers.
- [UIAO_007 OrgTree Modernization AD → Entra ID](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) — programmatic context for the OrgTree work.
- [UIAO_151 OrgPath Codebook](UIAO_151_OrgPath_Codebook.md) — selector vocabulary.
- [UIAO_152 Dynamic Group Library](UIAO_152_Dynamic_Group_Library.md) — the `OrgTree-*` groups CA and SASE target.
- [UIAO_154 Delegation Matrix — AUs & Roles](UIAO_154_Delegation_Matrix_AUs_Roles.md) — OrgPath-bound administrative units.
- [UIAO_153 Attribute Mapping Table](UIAO_153_Attribute_Mapping_Table.md) — user/device OrgPath writeback origin.
- [UIAO_163 Drift Detection Engine Specification](UIAO_163_Drift_Detection_Engine_Specification.md) — the drift engine that keeps the signal attestable.
- ADRs anchoring this chain: [ADR-035](adr/adr-035-orgpath-codebook-binding.md), [ADR-036](adr/adr-036-dynamic-group-provisioning.md), [ADR-038](adr/adr-038-device-plane-orgpath.md), [ADR-049](adr/adr-049-microsoft-adapter-coverage-expansion.md), [ADR-066](adr/adr-066-application-aware-networking-and-token-bound-transport.md).
