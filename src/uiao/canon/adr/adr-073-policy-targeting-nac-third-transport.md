---
id: ADR-073
title: "OrgTree Policy Targeting — NAC as Third Transport (Amends ADR-039)"
status: proposed
date: 2026-05-15
deciders:
  - governance-steward
  - identity-engineer
  - network-engineering-steward
supersedes: []
amends:
  - ADR-039
related_adrs:
  - ADR-035
  - ADR-036
  - ADR-037
  - ADR-038
  - ADR-039
  - ADR-047
canon_refs:
  - UIAO_010_OrgPath_in_Azure_Policy
  - UIAO_011_OrgPath_in_Intune_and_Device_Governance
  - UIAO_012_OrgPath_in_NAC_and_8021X
  - UIAO_151_OrgPath_Codebook
  - UIAO_152_Dynamic_Group_Library
  - UIAO_153_Attribute_Mapping_Table
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-073-policy-targeting-nac-third-transport.html
---

# ADR-073: OrgTree Policy Targeting — NAC as Third Transport (Amends ADR-039)

## Status

Proposed

## Context

[ADR-039](adr-039-policy-targeting.md) (accepted 2026-04-20) defined
OrgTree policy targeting as a **dual transport** model:

1. **Intune** — configuration profiles and compliance policies bound
   to `OrgTree-*` dynamic groups via Graph (UIAO_011).
2. **Azure Policy** — assignments bound to OrgPath ARM tag selectors
   on Arc-enrolled machines (UIAO_010).

The dual-transport model covers the *configuration* and *compliance
evaluation* planes for Entra-joined clients and Arc-enrolled servers.
It does not cover the **network admission** plane — the point at which
a device first contacts the wired or wireless infrastructure and
requests a network address.

Three independent pieces of work converged on the same gap:

1. **DM_030** (RADIUS / NPS migration adapter) specifies the
   source-to-target transition for the AAA tier — replacing AD-bound
   NPS with Cisco ISE, Aruba ClearPass, or Entra RADIUS Proxy — but
   does not specify the steady-state targeting binding.
2. **ADR-047** (Proposed) registers the `network-aaa/` and
   `network-access/` adapter categories and closes `implemented_by`
   gaps in AC-18 / IA-3 / IA-5(2), but does not specify how those
   registered adapters consume OrgTree-* dynamic groups.
3. **Intune-First doctrine** (ADR-071) Pillar 1 requires devices to
   carry an OrgPath before reaching production, but Intune compliance
   evaluation runs *after* the device has obtained a network address.
   Without a network-edge targeting layer, a device with no
   compliance state can still land on the corporate VLAN.

Each piece of work landed referencing "the AAA server consults the
OrgTree-* group," but no canon document declared the contract.

The corpus review at `docs/planning/reviews/802-1x-nac-review.md`
catalogued this gap among ten others in the 802.1X / NAC surface.
Wave 1 (commit `c56015e`) fixed terminology. ADR-047 fixes adapter
registration and `implemented_by` closure. This ADR fixes the
targeting binding.

## Decision

### D1 — Promote ADR-039 from dual transport to triple transport

ADR-039's two-transport canon is extended in place. The
`canon/data/orgpath/policy-targets.yaml` schema gains a third
top-level section:

```yaml
nac_assignments:
  - assignment_name: nac-fin-corp-endpoint
    aaa_server: cisco-ise
    policy_ref:
      kind: policy-set
      match_by: name
      value: NAC-FIN-CorpEndpoint
    target_group: OrgTree-FIN-Devices
    enforcement:
      vlan_id: 142
      dacl_name: dACL-FIN-Standard
      sgt_tag: 16
      posture_profile: Posture-CorpEndpoint-Standard
      change_of_authorization: true
    intent: permit
    gcc_boundary: gcc-moderate
```

Schema constraints:

- `aaa_server` is an enum: `cisco-ise`, `aruba-clearpass`,
  `entra-radius`, `nps` (last permitted only with paired cloud
  twin — see D4 below).
- `policy_kind` enum: `policy-set`, `service`, `connection-policy`,
  `posture-profile`.
- `policy_ref.value` regex: `^NAC-[A-Z0-9-]+$` (canonical prefix
  enforced by the loader).
- `intent` enum: `permit`, `quarantine`, `deny`.
- `target_group` must resolve to a live UIAO_152 dynamic group
  (cross-canon integrity, same as Intune).
- `enforcement.vlan_id` must resolve to a live VLAN in the IPAM
  canon (DM_010 — BlueCat / InfoBlox).
- `(policy_ref, target_group, enforcement)` triple is unique.
- `assignment_name` values are unique across the entire file
  (Intune + Arc + NAC assignments share one namespace).

### D2 — Adapter dispatch

The reference adapter
`uiao.adapters.entra_policy_targeting.EntraPolicyTargetingAdapter`
becomes
`uiao.adapters.orgtree_policy_targeting.OrgTreePolicyTargetingAdapter`
(rename signals the broadened transport scope). It dispatches by
transport:

| Transport | Sub-adapter | Credentials |
|---|---|---|
| Intune | `IntunePolicyTargetingSubAdapter` | Graph application token (`DeviceManagementConfiguration.ReadWrite.All`) |
| Azure Policy | `ArcPolicyTargetingSubAdapter` | ARM SP with `Microsoft.Authorization/policyAssignments/*` |
| NAC | `NacPolicyTargetingSubAdapter` | Vendor-specific — Cisco ISE ERS API token, Aruba ClearPass API session, Entra RADIUS Proxy management API token, or NPS RPC (legacy) |

The NAC sub-adapter further dispatches by `aaa_server`. Each
AAA-server-specific implementation lives under
`src/uiao/adapters/network-aaa/{aaa_server}/` per ADR-047 D1, and
exposes the same plan / apply / reconcile verbs.

The rename is non-breaking: the existing
`EntraPolicyTargetingAdapter` symbol is re-exported as a thin alias
for one release cycle, then removed (deprecation note will land in
the v0.7 release notes).

### D3 — Op vocabulary extension

ADR-039's eight-op plan vocabulary grows by four NAC ops, for twelve
total:

| Op | Auto-applies | Meaning |
|---|---|---|
| `nac-assign-create` | yes | Canon declares an assignment the AAA server lacks. |
| `nac-assign-update` | yes | Canon and AAA server diverge on policy reference, target group, or enforcement payload. |
| `nac-policy-missing` | **no** — governance review | The referenced policy does not exist on the AAA server. |
| `nac-assign-phantom` | **no** — governance review | AAA server has an OrgTree-named assignment canon does not declare. |

The Intune and Arc op definitions from ADR-039 are unchanged. The
governance-review property of `missing` and `phantom` ops carries
over — NAC has the same broad blast radius (a single wrong VLAN
assignment can affect thousands of devices).

### D4 — Hybrid-window NPS handling

During the DM_030 migration window, both NPS and cloud RADIUS may be
in service simultaneously. The schema permits `aaa_server: nps`
entries with two constraints:

1. **Paired-twin rule.** Every `nps` entry must have a paired
   non-NPS entry with the same `target_group` and the same
   `enforcement` payload. The loader enforces the pairing at PR
   CI — an unpaired `nps` entry is rejected.
2. **Retirement gate.** Removing all `nps` entries from
   `nac_assignments[]` is gated by the DM_050 (Entra Connect /
   AAA-tier) Retirement Readiness Checklist. When the checklist
   passes, a single PR drops every `nps` entry; the loader confirms
   no orphaned twins remain.

This is the only place in the OrgPath canon where two transports
for the same governance fact are permitted to coexist. The pairing
rule keeps the dual-state finite, auditable, and bounded.

### D5 — OrgPath cert carriage

802.1X EAP-TLS requires the supplicant to present a certificate the
AAA server can map to an Entra device object. The canonical OrgPath
carrier in the device certificate is:

- **Preferred:** `subjectAltName.OtherName` with OID
  `1.3.6.1.4.1.{UIAO-PEN}.1.1` (UIAO PEN to be obtained;
  interim use of a placeholder PEN until issuance) and UTF8String
  value matching the OrgPath grammar in UIAO_151.
- **Legacy fallback:** subject DN `OU=` component (AD CS-issued
  certs only; deprecated post-DM_030 cutover).

Certificate issuance authorities that participate in OrgPath-driven
NAC must implement the preferred carrier:

| Issuance authority | Carrier mechanism |
|---|---|
| Intune SCEP / PKCS profile | Subject + SAN template includes `{{OrgPath}}` token resolved from the device's Entra OrgPath extension attribute |
| Microsoft Cloud PKI | Same template surface as SCEP / PKCS |
| AD CS (hybrid window) | OU placement of cert template → SAN OtherName populated via template extension; deprecated at DM_030 cutover |

The legacy subject-DN OU= fallback path produces a `DRIFT-IDENTITY`
finding — it works, but it means a device in the post-migration
steady state is still presenting an AD-shaped cert.

### D6 — Migration plan

Three-phase landing, mirroring ADR-047 D4:

1. **Phase A (this ADR + UIAO_012 narrative):** Land the canon
   contract and the schema constraint **disabled** (warn-only). No
   `policy-targets.yaml` data changes yet. The adapter rename in D2
   ships as a no-op alias.
2. **Phase B (data population):** Land an initial set of
   `nac_assignments[]` entries covering the baseline branches
   (FIN, IT, ENG, OPS) and `ORG-BRANCH-UNPOSITIONED` quarantine.
   The schema constraint is still warn-only; CI green.
3. **Phase C (enforcement):** Flip the schema constraint from
   warn-only to blocking. The NAC sub-adapter's apply path becomes
   live for the registered AAA servers.

Phase A is this PR. Phases B and C follow as separate PRs.

### D7 — `implemented_by` closure (carries forward from ADR-047)

The control YAMLs touched by ADR-047 (AC-18, IA-3, IA-5(2),
SA-4(10), SC-7(5)) acquire a new evidence id:
`orgpath-nac-assignment-record`. The evidence artifact is the
post-apply commit of `policy-targets.yaml` plus the AAA-server
reconcile receipt. ADR-047's Phase B sweep PR is the place to land
this addition.

## Consequences

### Positive

- Closes the network-admission gap in the OrgPath canon. The three
  transports (configuration via Intune, workload via Azure Policy,
  admission via NAC) now have parallel governance contracts.
- DM_030's steady-state targeting is no longer implicit. The
  migration's exit criterion gains a concrete artifact:
  `nac_assignments[]` covers every governed network with no
  `nps`-only entries remaining.
- ADR-071 Intune-First Pillar 1 gains a network-edge enforcement
  layer. A device with no Active OrgPath now lands on the
  quarantine VLAN *before* it can even attempt a Conditional Access
  sign-in.
- Drift detection engine UIAO_163 gains a fifth plane
  (network-admission), parallel to the existing four. Posture
  delta between Intune-evaluated compliance and AAA-applied
  enforcement becomes a first-class finding.

### Negative / costs

- Three sub-adapters under one parent adapter increases the
  surface to test and maintain. The trade-off is that "OrgTree
  governs policy targeting" stays one decision rather than
  fragmenting into three.
- The hybrid-window NPS pairing rule (D4) adds loader complexity.
  This is intentional — it makes the dual-state finite and
  auditable rather than informal.
- The UIAO PEN for the OrgPath OtherName OID is a real procurement
  item. The interim placeholder PEN works for development but
  cannot ship to production NAC infrastructure without legal
  attribution clarity.
- Three-vendor NAC sub-adapter implementation (Cisco ISE, Aruba
  ClearPass, Entra RADIUS Proxy) is non-trivial. Each vendor's API
  surface is distinct. Phase C will likely land vendor-by-vendor,
  not all-at-once.

### Neutral / open

- Whether SGT (Cisco TrustSec) targeting belongs in
  `enforcement.sgt_tag` or in a fourth transport (`sgt_assignments[]`)
  is open. Current decision: SGT rides along with the existing NAC
  assignment because SGT is delivered via the same RADIUS
  Access-Accept response. If SGT-only targeting (no VLAN /
  dACL change) becomes common, a fourth transport may be warranted.
- Whether VPN cert-based admission (Palo Alto GlobalProtect, Cisco
  AnyConnect, Pulse Secure) should be a separate transport or
  folded into `nac_assignments[]` is open. Current decision: fold
  in via `aaa_server: cisco-ise` (or equivalent) since the AAA
  server is the same; the authenticator differs but the binding is
  identical.
- Wireless 802.1X (AC-18) and wired 802.1X (IA-3) use the same
  schema. SSID-to-OrgPath binding rides through the same VLAN-
  assignment enforcement payload. No separate canon needed.

## Alternatives considered

- **A separate ADR per AAA server (one for ISE, one for ClearPass,
  one for Entra RADIUS).** Rejected; the targeting decision is one,
  the vendor implementation is three. Same reasoning as ADR-039's
  single-adapter / dual-sub-adapter shape.
- **Fold NAC into ADR-047 instead of a new ADR.** Rejected;
  ADR-047 is about adapter registration and `implemented_by`
  closure. The targeting binding is a separate decision and
  deserves a separate ADR. ADR-073 references ADR-047 but does not
  consume it.
- **Skip the cert OrgPath carriage rule (D5) and rely on
  AAA-server-side Entra group lookup only.** Rejected; group
  lookup by `clientIdentifier` works for ISE / ClearPass but
  requires a Graph API round-trip per RADIUS request — at scale
  the latency degrades 802.1X timeout budgets. Cert-borne OrgPath
  is the in-band signal that avoids the round-trip.
- **Wait until UIAO PEN issuance is complete before publishing
  ADR-073.** Rejected; the PEN issuance is a long-lead procurement
  item that does not block the design. The interim placeholder PEN
  is acceptable for development; the canon will be updated when
  the real PEN issues.

## References

- [ADR-039](adr-039-policy-targeting.md) — the dual-transport
  predecessor this ADR amends.
- [ADR-047](adr-047-network-aaa-adapter-registration.md) — sibling
  ADR registering the AAA-tier adapter category.
- [ADR-071](adr-071-intune-first-asset-onboarding.md) — Intune-First
  doctrine whose Pillar 1 this ADR's network-edge enforcement
  closes.
- [UIAO_010 OrgPath in Azure Policy](../UIAO_010_OrgPath_in_Azure_Policy.md) — Arc transport sibling.
- [UIAO_011 OrgPath in Intune & Device Governance](../UIAO_011_OrgPath_in_Intune_and_Device_Governance.md) — Intune transport sibling.
- [UIAO_012 OrgPath in NAC / 802.1X](../UIAO_012_OrgPath_in_NAC_and_8021X.md) — operator-facing narrative for this ADR.
- DM_030 RADIUS / NPS Adapter Interface: [`directory-migration/adapters/radius/radius-adapter-interface.md`](../../modernization/directory-migration/adapters/radius/radius-adapter-interface.md).
- 802.1X / NAC corpus review: [`docs/planning/reviews/802-1x-nac-review.md`](../../../../docs/planning/reviews/802-1x-nac-review.md).
- IEEE 802.1X-2020 §5.1 — three-party authentication model.
- RFC 3580 — IEEE 802.1X RADIUS Usage Guidelines.
- RFC 5216 — EAP-TLS authentication protocol.
