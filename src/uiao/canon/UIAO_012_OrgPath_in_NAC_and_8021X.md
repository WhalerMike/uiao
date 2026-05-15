---
document_id: UIAO_012
title: "OrgPath in NAC / 802.1X & Cert-Based Network Admission"
version: "0.1"
status: Draft
classification: CANONICAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-05-15"
updated_at: "2026-05-15"
# foundational-trace: <reserved — populate when Charter Restoration PR-E lands>
---

# OrgPath in NAC / 802.1X & Cert-Based Network Admission

> **Purpose.** Operator-facing narrative that wraps the executable canon
> for OrgPath-driven NAC policy targeting. The targeting decision is
> made in [ADR-073](adr/adr-073-policy-targeting-nac-third-transport.md)
> (amending [ADR-039](adr/adr-039-policy-targeting.md) from dual
> transport to triple transport) and declared in the
> `nac_assignments[]` section of
> [`canon/data/orgpath/policy-targets.yaml`](data/orgpath/policy-targets.yaml).
> The adapter-registration surface is decided in
> [ADR-047](adr/adr-047-network-aaa-adapter-registration.md).
> This document explains *what an operator does, in what order, and
> what catches them when they get it wrong*.
>
> **Companion documents.**
> [UIAO_010 OrgPath in Azure Policy](UIAO_010_OrgPath_in_Azure_Policy.md)
> covers the Arc-server transport.
> [UIAO_011 OrgPath in Intune & Device Governance](UIAO_011_OrgPath_in_Intune_and_Device_Governance.md)
> covers the Entra-joined-client transport.
> This document covers the **network-edge** transport — the one that
> applies at the L2/L3 port, before either of the other two has had a
> chance to evaluate compliance.
>
> **Migration anchor.**
> The AD-to-cloud migration of the AAA tier itself is owned by DM_030
> ([`directory-migration/adapters/radius/radius-adapter-interface.md`](../modernization/directory-migration/adapters/radius/radius-adapter-interface.md)).
> DM_030 is the *source-to-target* surface; this document is the
> *steady-state targeting* surface.

## Scope

In scope:

- NAC policy targeting for **Entra-joined clients** and **Arc-enrolled
  servers** that authenticate to the network via 802.1X (wired or
  wireless) or via cert-based VPN client posture.
- The `nac_assignments[]` section of
  `canon/data/orgpath/policy-targets.yaml` (introduced by ADR-073).
- The OrgPath-to-VLAN, OrgPath-to-ACL, and OrgPath-to-posture-policy
  binding contracts that make NAC targeting deterministic.
- The certificate-based identity carrier that ties device identity
  (per UIAO_153 / ADR-038) to network admission decisions.
- Three-plane device model interactions ([ADR-034](adr/adr-034-three-plane-device-model.md))
  that determine which devices are reachable from this targeting
  surface in the first place.

Out of scope:

- Intune profile / compliance-policy targeting — see **UIAO_011**.
- Azure Policy targeting on Arc — see **UIAO_010**.
- Authoring of RADIUS policy bodies, VLAN definitions, or ACL bodies.
  Policy bodies live in the NAC platform's authoring surface (Cisco
  ISE policy sets, Aruba ClearPass services, Entra RADIUS Proxy
  config) and are consumed by reference (`policy_ref.match_by: name`).
- The AAA-tier migration *from* AD-bound NPS *to* cloud RADIUS. That
  is DM_030's job; this document picks up at the post-migration
  steady state.
- Hybrid-Azure-AD-joined (HAADJ) clients. HAADJ is deprecated per
  [ADR-001](adr/adr-001-haadj-deprecated-entra-join-only.md);
  Entra-join is the only governed client posture.
- Pure MAC Authentication Bypass (MAB) for IoT / OT. MAB is governed
  by an Infoblox-managed MAC reservation table consulted by the AAA
  server (see DM_030 §IoT note and ADR-047 §1.2). OrgPath does not
  apply to MAB.

## Authoritative artifacts

| Role | Artifact |
|---|---|
| Canonical data | [`canon/data/orgpath/policy-targets.yaml`](data/orgpath/policy-targets.yaml) — `nac_assignments[]` (introduced by ADR-073) |
| JSON Schema | [`schemas/orgpath/policy-targets.schema.json`](../schemas/orgpath/policy-targets.schema.json) — extended by ADR-073 |
| Targeting decision | [ADR-073: OrgTree Policy Targeting — NAC as Third Transport](adr/adr-073-policy-targeting-nac-third-transport.md) (amends ADR-039) |
| Adapter registration | [ADR-047: Network AAA Adapter Registration](adr/adr-047-network-aaa-adapter-registration.md) |
| Migration source-to-target | [DM_030 RADIUS / NPS Adapter Interface](../modernization/directory-migration/adapters/radius/radius-adapter-interface.md) |
| OrgPath codebook (selector vocabulary) | [UIAO_151_OrgPath_Codebook](UIAO_151_OrgPath_Codebook.md) |
| Dynamic-group canon (target groups) | [UIAO_152_Dynamic_Group_Library](UIAO_152_Dynamic_Group_Library.md) |
| Device-plane OrgPath writes (cert subject / SAN origin) | [UIAO_153_Attribute_Mapping_Table](UIAO_153_Attribute_Mapping_Table.md) + [ADR-038](adr/adr-038-device-plane-orgpath.md) |
| Three-plane device model | [ADR-034](adr/adr-034-three-plane-device-model.md) |
| Substrate handoff | [UIAO_164_Execution_Substrate_Integration_Layer](UIAO_164_Execution_Substrate_Integration_Layer.md) |

If any pair in the table above goes out of sync (a NAC assignment
references a dynamic group UIAO_152 no longer declares, a cert subject
template references an OrgPath segment not in UIAO_151, the AAA server
issues a VLAN the canon does not declare), that is a
`DRIFT-PROVENANCE` finding by definition.

## The targeting model

OrgPath governs NAC by **certificate identity at L2/L3 admission**,
read by the AAA server, mapped to dynamic-group membership, and
enforced by the L2/L3 authenticator (switch / WLC / VPN concentrator)
as a VLAN assignment plus optional dACL or SGT.

```
+----------------------------+     +----------------------------+
| canon/data/orgpath/        |     | canon/data/orgpath/        |
| dynamic-groups.yaml        |     | policy-targets.yaml        |
| (UIAO_152 / ADR-036)       |     | (this document)            |
| OrgTree-IT-Users,          |     | nac_assignments[]          |
| OrgTree-FIN-Users, ...     |     |                            |
+--------------+-------------+     +--------------+-------------+
               | named group                      | references group
               v                                  v
        +---------------------------------------------+
        | NacPolicyTargetingAdapter (loader)          |
        |  - validates every target_group is in       |
        |    UIAO_152 dynamic-groups.yaml             |
        |  - validates every vlan_id / acl_name /     |
        |    posture_profile is in the AAA-server-    |
        |    side inventory canon                     |
        |  - emits 4-op NAC plan                      |
        +-----------------------+---------------------+
                                |
                                v
        +---------------------------------------------+
        | AAA server (ISE / ClearPass / Entra RADIUS  |
        | Proxy / NPS-Extension for Entra Auth)       |
        |  - consults dynamic-group membership via    |
        |    Graph (Entra-RADIUS) or via SCIM /       |
        |    Graph delta sync (ISE / ClearPass)       |
        |  - maps OrgTree-* group → policy set        |
        |  - returns RADIUS Access-Accept with        |
        |    Tunnel-Private-Group-ID (VLAN) +         |
        |    Cisco-AVPair / Filter-ID (dACL) +        |
        |    posture-policy reference                 |
        +-----------------------+---------------------+
                                |
                                v
        +---------------------------------------------+
        | Authenticator (Cisco Catalyst / Aruba CX /  |
        | Cisco WLC / Palo Alto GlobalProtect)        |
        |  - enforces VLAN assignment on the port     |
        |  - applies dACL or SGT for east-west        |
        |    segmentation                             |
        |  - reports session state to NAC platform    |
        |    for posture re-evaluation                |
        +---------------------------------------------+
```

Four consequences flow from this:

1. **The dynamic group must already exist in canon** before any NAC
   assignment authored here can target it. Same property as Intune
   (UIAO_011): the loader fails at PR CI if `target_group` is not in
   `dynamic-groups.yaml`.

2. **Device identity is the certificate.** The 802.1X supplicant
   presents a device certificate (EAP-TLS) whose subject or SAN
   carries enough identity to look the device up in Entra ID. The
   AAA server then consults Entra group membership for the device
   object — *not* for the user logged into the device. This makes
   pre-user-logon network admission deterministic (consistent with
   the doctrine in [Intune-First Asset Onboarding](../modernization/intune-first-onboarding/doctrine.md)
   §5.3).

3. **OrgPath travels in the cert.** The device certificate's subject
   DN, a SubjectAltName OtherName, or a custom v3 extension carries
   the OrgPath value. ADR-073 §"OrgPath cert carriage" specifies the
   canonical carrier; the certificate-issuing transport (Intune
   SCEP/PKCS, Microsoft Cloud PKI, or AD CS during the hybrid
   window) writes it at issuance time, per UIAO_153 / ADR-038.

4. **Policy authoring and policy assignment are separate
   workflows.** This document governs assignment only. Policy bodies
   (ISE policy sets, ClearPass services, NPS Connection Request
   Policies during the hybrid window) are authored in the AAA
   platform and bound here by name. A policy that exists in canon by
   name but not on the AAA server surfaces as `nac-policy-missing`.

## Policy reference grammar

Each entry in `nac_assignments[]` carries a `policy_ref`:

| Field | Type | Constraint |
|---|---|---|
| `aaa_server` | enum | `cisco-ise`, `aruba-clearpass`, `entra-radius`, `nps` (the last only valid during the hybrid window — see §"Hybrid-window NPS handling" below). Maps to the adapter registered under `src/uiao/adapters/network-aaa/` per ADR-047. |
| `policy_kind` | enum | `policy-set` (ISE), `service` (ClearPass), `connection-policy` (Entra-RADIUS / NPS), `posture-profile` (cross-vendor) |
| `match_by` | enum | `name` (recommended — stable across redeploys) or `id` (vendor-specific GUID — brittle). |
| `value` | string | The policy name or ID. **Required format**: `NAC-<scope>-<purpose>` (e.g., `NAC-Baseline-CorpEndpoint`, `NAC-FIN-RestrictedSegment`). Loader enforces at PR CI. |

Default to `match_by: name`. Reach for `id` only when two policies
share a name on the AAA server and you must disambiguate — itself a
governance smell worth fixing upstream.

## Enforcement grammar

Each entry carries the network-side enforcement payload the AAA server
returns on Access-Accept:

| Field | Type | Constraint |
|---|---|---|
| `vlan_id` | integer | 1–4094; must exist in the IPAM canon (DM_010 / BlueCat / InfoBlox) for the site the device is expected to authenticate from |
| `dacl_name` | string (optional) | Named downloadable ACL or Filter-ID; must exist on the AAA server's dACL inventory |
| `sgt_tag` | integer (optional) | Cisco TrustSec Security Group Tag, if SGT-based segmentation is in use; must exist in the SGT registry |
| `posture_profile` | string (optional) | Named posture-assessment profile (e.g., `Posture-CorpEndpoint-Standard`); must exist on the AAA server |
| `change_of_authorization` | boolean | If `true`, the AAA server issues CoA on Intune-compliance-state transitions to force re-evaluation; if `false`, posture is evaluated only at session start |

A canonical NAC assignment is the *triple* `(policy_ref, target_group,
enforcement)`. Three triples form a unique key — duplicate triples
fail the loader.

## Intent grammar

Each entry carries an `intent`:

| Intent | Effect | Use when |
|---|---|---|
| `permit` | Devices in `target_group` receive the enforcement payload (VLAN + dACL + posture) on Access-Accept | Default for any positive admission assertion. |
| `quarantine` | Devices in `target_group` receive a quarantine VLAN + restrictive dACL on Access-Accept, even if other checks pass | Used for `ORG-BRANCH-UNPOSITIONED` (the Intune-First quarantine branch) and for any branch declared "no-network" by governance |
| `deny` | Devices in `target_group` receive Access-Reject; the supplicant is bounced and cannot complete L2 association | Reserved for explicit exclusion zones (decommissioned OrgPath segments, hostile-takeover containment). Requires governance review on every PR; loader flags any new `deny` for two-person review. |

`quarantine` is the network-edge analog of the Intune-side
`/UNPOSITIONED` compliance posture — a device with no Active OrgPath
gets a quarantine VLAN at the port *before* Intune even has a chance
to evaluate compliance. This closes the pre-compliance-evaluation
window described in [Intune-First doctrine](../modernization/intune-first-onboarding/doctrine.md)
§Pillar 1.

## Operator workflows

### Add a new NAC assignment

1. **Confirm the policy exists** on the AAA server. The
   `policy_ref.value` resolves by name. If the AAA server does not
   yet hold a policy with that name, the next `plan` produces a
   `nac-policy-missing` op — not an error, but a governance-review
   op that will not auto-apply.
2. **Confirm the target dynamic group exists in canon.** Group must
   be declared in `canon/data/orgpath/dynamic-groups.yaml`
   (UIAO_152). If not, declare the group via the ADR-036 workflow
   first.
3. **Confirm the VLAN exists in IPAM canon.** The `vlan_id` must
   resolve to an active VLAN in the BlueCat / InfoBlox canon for the
   site set the device is expected to authenticate from. A VLAN
   reference that resolves to no IPAM record fails the loader.
4. **Pick the tightest target group.** Membership keys off OrgPath;
   selecting a wider group and relying on `deny` to subtract is
   forbidden by the two-person-review rule — narrower targeting
   reduces blast radius and avoids the deny-list maintenance burden.
5. **Pick the intent.** Default `permit`. Use `quarantine` for
   explicit no-network branches (UNPOSITIONED, decommissioning).
   `deny` is exception-only.
6. **PR the change.** The loader runs in CI. Cross-canon integrity
   surfaces immediately:
   - `target_group` not in UIAO_152 → loader error
   - `vlan_id` not in IPAM canon → loader error
   - duplicate `(policy_ref, target_group, enforcement)` triple →
     loader error
   - new `deny` intent → governance-review block (loader marks PR
     `needs-governance-approval`)
7. **After merge, the adapter `plan` against the AAA server** emits
   one of:
   - `nac-assign-create` — AAA server has no assignment binding this
     policy to this group with this enforcement; auto-applies.
   - `nac-assign-update` — AAA server has the binding but parameters
     differ; auto-applies.
   - `nac-policy-missing` — AAA server lacks the policy; governance
     review.
   - `nac-assign-phantom` — AAA server has an OrgTree-named
     assignment canon does not declare; governance review.

### Change the VLAN / dACL of an existing assignment

Edit the enforcement payload in place, PR the change, let the loader
validate. The next reconcile produces `nac-assign-update`. Note that
VLAN changes are user-visible — they typically cause a re-DHCP and a
session re-authentication. Plan during a change window.

### Retire an assignment

Delete the entry. The next reconcile produces `nac-assign-phantom`
against the assignment that still exists on the AAA server. Phantom
ops never auto-apply.

## Canonical operation vocabulary (NAC subset)

ADR-073 defines four NAC ops, mirroring the Intune and Azure Policy
vocabularies:

| Op | Auto-applies | Meaning |
|---|---|---|
| `nac-assign-create` | yes | Canon declares an assignment the AAA server lacks. |
| `nac-assign-update` | yes | Canon and AAA server diverge on policy reference, target group, or enforcement payload. |
| `nac-policy-missing` | **no** — governance review | The referenced policy does not exist on the AAA server. |
| `nac-assign-phantom` | **no** — governance review | AAA server has an OrgTree-named assignment canon does not declare; possible unauthorized policy-consumer drift. |

The auto-apply / governance-review property is enforced by the
adapter, same as Intune and Azure Policy. NAC has additional bite:
a wrong VLAN assignment can land thousands of devices on the wrong
segment in a single reconcile cycle. Governance review on phantom
and missing ops is the safety belt.

## OrgPath cert carriage

802.1X EAP-TLS requires the supplicant to present a certificate. For
OrgPath-driven NAC to work, the OrgPath value must be derivable from
the certificate the AAA server sees. The canonical carrier is the
`subjectAltName.OtherName` extension with OID
`1.3.6.1.4.1.{UIAO-PEN}.1.1` (UIAO PEN to be obtained — interim use
of `1.3.6.1.4.1.99999.1.1` until issuance) and a UTF8String value
matching the OrgPath grammar in UIAO_151.

| Cert source | OrgPath carriage mechanism | When it applies |
|---|---|---|
| **Intune SCEP / PKCS profile** | Subject template includes `{{OrgPath}}` token (resolved per UIAO_153); SAN OtherName populated from the device's Entra OrgPath extension attribute | Steady state for Entra-joined clients post-Intune-First |
| **Microsoft Cloud PKI** | Same template surface as SCEP / PKCS; Cloud PKI is the issuing CA | Steady state for organizations not running on-prem AD CS |
| **AD CS** | OU placement of the certificate template determines the OrgPath value at issuance via the GPO-driven enrollment policy | Hybrid window during DM_030 migration; superseded by Intune SCEP at cutover |
| **Manual cert install** | Out of band; governance audit entry required | Exception path; should not appear in steady state |

The AAA server reads the OrgPath from the SAN OtherName (preferred)
or, if absent, falls back to the subject DN's `OU=` component
(legacy-AD-CS interop only). The fallback is a `DRIFT-IDENTITY`
finding — it works, but it means a device is still presenting an
AD-shaped cert in the post-migration steady state.

## Three-plane device model interactions

[ADR-034](adr/adr-034-three-plane-device-model.md) declares three
device planes; NAC reaches all three differently:

| Plane | OrgPath source for NAC | Reachable from this canon? |
|---|---|---|
| **Entra-joined client** | OrgPath extension attribute on Entra device object → Intune-issued cert's SAN OtherName | **Yes** — primary surface. ISE / ClearPass / Entra-RADIUS read Entra group membership via Graph; the device's OrgPath determines its policy set. |
| **Arc-enrolled server** | OrgPath ARM tag → Arc-issued cert (where applicable; servers more commonly use IPsec / private VPN admission, not 802.1X) | **Partial** — applies for servers that 802.1X-authenticate against a wired infrastructure switch; otherwise governed via UIAO_010 at the Azure Policy plane. |
| **Hybrid (HAADJ)** | Forbidden — superseded by ADR-001 | No — devices in this plane are a `DRIFT-IDENTITY` finding, not a NAC-targeting gap. |

The dual-reachability of Arc servers (some via NAC, some via Azure
Policy only) is intentional. NAC scope for servers covers the
*physical-port* admission decision; Azure Policy covers the
*workload-configuration* decision. They are not redundant; they
operate at different layers.

## Boundary rules

- Every Entra-joined client and Arc-enrolled server reachable from
  this canon MUST be in the GCC-Moderate boundary. The loader's
  per-entry `gcc-boundary: gcc-moderate` invariant applies, same as
  UIAO_010 and UIAO_011.
- Cross-tenant device targeting is out of scope. A device whose
  primary tenant is not the governed tenant is invisible to the AAA
  server's group lookup and is excluded from `nac_assignments[]`
  evaluation.
- The AAA server itself must be inside the GCC-Moderate boundary.
  Cisco ISE / Aruba ClearPass on-prem deployments operate inside the
  boundary by definition; Entra RADIUS Proxy is a Microsoft GCC-
  Moderate service per ADR-047.
- For wireless 802.1X (AC-18), the wireless infrastructure (WLCs,
  APs) is in scope; SSID-to-OrgPath binding is enforced via the
  RADIUS Access-Accept VLAN assignment, same as wired.

## Drift considerations

Four drift classes apply directly to NAC, paralleling the Intune and
Azure Policy patterns:

| Class | Trigger |
|---|---|
| `DRIFT-PROVENANCE` | An entry references a `target_group` that no longer exists in `dynamic-groups.yaml`, or a `vlan_id` that no longer exists in the IPAM canon. Loader catches at PR CI. |
| `DRIFT-AUTHZ` | A `nac-assign-phantom` op surfaces an OrgTree-named assignment on the AAA server canon does not declare — possible unauthorized policy authoring on the NAC console. |
| `DRIFT-SEMANTIC` | A canonical assignment's enforcement payload (VLAN / dACL / posture) diverges from the AAA server after console-side edit. Surfaces as `nac-assign-update` until canon reabsorbs or the console edit is reverted. |
| `DRIFT-IDENTITY` | An Entra-joined client whose certificate lacks the SAN OtherName OrgPath carrier — the AAA server can authenticate the device but cannot place it in the correct policy set. Falls back to subject-DN OU= parsing (legacy interop only); flagged as identity-plane drift against UIAO_153. |

`DRIFT-IDENTITY` is the load-bearing concern at this transport. A
device whose OrgPath extension attribute is missing or stale will
either (a) fail the AAA group lookup entirely and hit the
quarantine VLAN, or (b) authenticate with an AD-shaped cert whose
OU= no longer corresponds to a canonical OrgPath. Both are
governance findings; neither is silent.

## Hybrid-window NPS handling

During the DM_030 migration window — after cloud RADIUS has been
deployed but before NPS has been decommissioned — both AAA servers
may be in service simultaneously. The canon accommodates this by
allowing `aaa_server: nps` with `intent: permit` on a per-assignment
basis, with two constraints:

1. Every `nps` assignment must have a paired `cisco-ise` (or
   `entra-radius`) assignment with the *same* target group and
   enforcement payload. The loader enforces the pairing — an `nps`
   entry without its cloud-side twin is rejected.
2. The DM_030 retirement readiness checklist (see DM_050 / Entra
   Connect retirement) gates the removal of all `nps` entries. When
   the checklist passes, a single PR drops every `nps` entry; the
   loader confirms no orphaned twins remain.

This is the only place in the OrgPath canon where two transports for
the same governance fact are permitted to coexist. The pairing rule
keeps the dual-state finite and auditable.

## Forcing-function rationale

OrgPath-driven NAC targeting exists because:

1. **NIST 800-53 IA-3 and AC-18 require device authentication at
   network admission**, not just at application access. 802.1X
   EAP-TLS is the canonical mechanism; AAA-driven VLAN assignment is
   how the authentication decision becomes an enforcement action.
2. **The Intune-First doctrine (Pillar 1) requires devices to carry
   an OrgPath value before they reach production**, but Intune-side
   compliance evaluation happens *after* the device has obtained a
   network address. Without an OrgPath-driven network admission
   layer, a device with no Intune compliance state can still get on
   the corporate VLAN. NAC at the port closes this window.
3. **The directory migration (DM_030) replaced AD-bound NPS with
   cloud RADIUS** but did not specify the steady-state targeting
   binding. Without UIAO_012, the migrated AAA tier has no
   governance contract for how it consults Entra group membership.
4. **Cisco ISE, Aruba ClearPass, and Entra RADIUS Proxy each support
   group-membership-driven policy** — but each has its own console,
   its own authoring vocabulary, and its own drift surface. A canon
   binding declared in `nac_assignments[]` and applied by the
   adapter is the single source of truth across all three.

## Invariants the chain enforces

For any device that authenticates to the corporate network via
802.1X in the post-migration steady state:

- The device presents a certificate whose SAN OtherName (preferred)
  or subject DN OU= (legacy fallback) carries an OrgPath value
  matching an Active node in the OrgTree registry, or equals the
  quarantine value `/UNPOSITIONED`.
- The AAA server resolves the device's Entra device object,
  consults its dynamic-group memberships, and returns the
  enforcement payload declared in `nac_assignments[]` for the
  matching `(policy_ref, target_group, enforcement)` triple.
- The authenticator applies the enforcement payload to the L2/L3
  port. The device's network reachability is now scoped to its
  OrgPath — Finance laptops land on the Finance VLAN, Lab
  workstations land on the lab VLAN, UNPOSITIONED devices land on
  the quarantine VLAN.
- Any deviation from the above produces one of the four drift
  classes above; none is silent.

These invariants are the network-edge analog of the user-plane
invariants in UIAO_153 and the policy-plane invariants in UIAO_010
and UIAO_011.

## Related work

- [UIAO_010 OrgPath in Azure Policy](UIAO_010_OrgPath_in_Azure_Policy.md) — Arc / workload-configuration transport (same ADR family, different plane).
- [UIAO_011 OrgPath in Intune & Device Governance](UIAO_011_OrgPath_in_Intune_and_Device_Governance.md) — Entra-joined client / compliance-policy transport (same ADR family, different plane).
- [UIAO_007_OrgTree_Modernization_AD_to_EntraID](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) — programmatic context for the OrgTree work.
- [UIAO_151_OrgPath_Codebook](UIAO_151_OrgPath_Codebook.md) — selector vocabulary that drives dynamic-group membership.
- [UIAO_152_Dynamic_Group_Library](UIAO_152_Dynamic_Group_Library.md) — the OrgTree-* group catalog this document targets.
- [UIAO_153_Attribute_Mapping_Table](UIAO_153_Attribute_Mapping_Table.md) — OrgPath device-plane writeback origin; carries OrgPath into Intune-issued certs.
- [DM_030 RADIUS / NPS Adapter Interface](../modernization/directory-migration/adapters/radius/radius-adapter-interface.md) — migration source-to-target (this doc is the steady-state sibling).
- [Intune-First Asset Onboarding doctrine](../modernization/intune-first-onboarding/doctrine.md) §5 — the OrgPath assignment authority chain whose output is what the AAA server reads.
- ADRs that anchor this binding chain: [ADR-001](adr/adr-001-haadj-deprecated-entra-join-only.md), [ADR-034](adr/adr-034-three-plane-device-model.md), [ADR-035](adr/adr-035-orgpath-codebook-binding.md), [ADR-036](adr/adr-036-dynamic-group-provisioning.md), [ADR-038](adr/adr-038-device-plane-orgpath.md), [ADR-039](adr/adr-039-policy-targeting.md), [ADR-047](adr/adr-047-network-aaa-adapter-registration.md), [ADR-073](adr/adr-073-policy-targeting-nac-third-transport.md).
