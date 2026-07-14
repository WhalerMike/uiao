# Identity-Aware Networking vs Application-Aware Networking — and where UIAO sits

> **Positioning note (inbox draft — not canon).** Two networking concepts that
> travel together in modern architectures (SASE, Zero Trust, advanced SD-WAN)
> but answer different questions. This note keeps the generic industry framing
> as the on-ramp, then grounds it in the repo's own canon so the distinction
> maps onto UIAO's actual planes instead of staying vendor-abstract. Key
> anchors: **ADR-066** (Application-Aware Networking & Token-Bound Transport),
> **ADR-085** (universal-enterprise positioning), and the OrgPath/identity
> plane in canon.

## The two questions

- **Application-Aware Networking** asks **"*what* is flowing?"** — is this Zoom,
  Salesforce, or database replication? The network classifies the *application
  or traffic type* and treats it intelligently (path selection, QoS, AppQoE).
  Classic enablers: DPI, app signatures, SD-WAN application-aware routing, SDN
  controllers. Primary goal: **performance and user experience**.
- **Identity-Aware Networking** asks **"*who* is behind it?"** — an authorized
  employee on a compliant device, or an unknown service account? The network (or
  the security layer alongside it) validates *identity and context* and applies
  policy accordingly. Classic enablers: IdPs (Okta, Entra ID, Ping), Cisco ISE,
  service meshes, SASE platforms; techniques include micro-segmentation,
  continuous authentication, device posture, and **token / JWT claim inspection**.
  Primary goal: **security, least privilege, access control**.

They are orthogonal, not competing: one keys on *traffic*, the other on
*principal + context*. Real architectures want both — classify the app to route
it well, validate the identity to decide whether it's allowed at all.

## Quick comparison

| Aspect | **Application-Aware** | **Identity-Aware** |
|---|---|---|
| **Focus** | What application / traffic type is flowing | Who (user, device, service, workload) is making the request |
| **Key question** | "Is this Zoom, Salesforce, or DB replication?" | "Is this an authorized user on a compliant device?" |
| **Goal** | Optimize routing, QoS, and experience for app needs | Enforce policy, least privilege, and access control |
| **Techniques** | DPI, app signatures, app-aware routing, AppQoE | Zero Trust, micro-segmentation, continuous auth, token/JWT claims, device posture |
| **Enablers** | SD-WAN, SDN controllers, traffic classification | IdPs, Cisco ISE, service meshes, SASE |
| **Auth-model fit** | Loosely coupled to the auth model | Strongly favors **token-based** (JWT claims) over Kerberos tickets |
| **Best for** | Performance & UX in complex app estates | Security & access control in distributed environments |

**Worked example (they combine):** *This traffic is **Zoom** → give it
low-latency priority (application-aware). It's **Alice on a corporate laptop with
valid token claims** → allow it (identity-aware). Same Zoom traffic from an
unknown device or a service account lacking claims → block or restrict.* That
join — app policy × identity policy — is what "intent-based" / "context-aware"
networking actually means.

## The Kerberos → token shift is why identity-aware became practical

- **Client-Server + Kerberos era:** networks were simpler and identity was
  handled centrally by the domain, so neither awareness was needed at scale.
- **Token-based + distributed / microservices era:** you need both. JWT + claims
  make identity-aware networking far more powerful than Kerberos tickets ever
  could in a cloud-native world, because the claim set travels with the request
  and can be inspected per hop.

## Where UIAO sits (grounding the generic frame in canon)

UIAO doesn't reimplement either networking layer — it **governs and proves**
both, and its canon already names each side:

- **Identity-aware side → the identity/addressing plane.** UIAO's core is the
  *Unified Identity-Addressing-Overlay Architecture*; the governed identity
  primitive is **OrgPath** (HR-sourced org placement that drives ABAC /
  Zero-Trust targeting and survives reorgs). "Who is this principal and where do
  they sit?" is exactly the identity-aware question, expressed as a
  drift-detectable attribute rather than a static group membership. UIAO also
  carries the token side directly: **ADR-066** adopts **token-bound, per-call
  transport authorization**, which *is* identity-aware networking enforced at
  the transport layer.
- **Application-aware side → ADR-066 / the AAN corpus.** UIAO's canonical home
  for application-aware networking is **ADR-066 ("Application-Aware Networking
  and Token-Bound Transport Plane")** and the *Application-Aware Overlay Fabric
  Model* (UIAO_123). The federal **AAN** document series is *external companion
  content* for the federal vertical (per ADR-085's positioning); UIAO consumes
  its evidence through the **FedRAMP AAN Evidence Catalog** conformance adapter
  (`src/uiao/canon/adapter-registry.yaml`), binding it to NIST controls.
- **The two-plane join.** This mirrors the CM-8 asset-identity join already
  described in `UIAO_vs_OrgPath_vs_AAN_Positioning.md`: OrgPath keys
  *people/devices* (identity addressing), IPAM/DDI keys *hosts/subnets* (network
  addressing). Identity-aware and application-aware networking are the runtime
  expressions of those same two planes — and UIAO is the layer that ingests both
  as canon-anchored evidence and emits the continuous, drift-checked OSCAL/KSI
  authorization package.

**Mental model:** *Application-aware networking routes the traffic,
identity-aware networking authorizes the principal, and UIAO governs and proves
both against canon.*

## Caveat

The vendor framing (Cisco, Palo Alto, Zscaler, Cloudflare all "do both") is
accurate at the marketing altitude but says nothing about *evidence*. UIAO's
contribution is not a third networking box — it's turning "we do both" into a
continuously attested, drift-detectable authorization package. Keep that
distinction explicit whenever this note feeds customer-facing material: the two
awarenesses are the *controls*; UIAO is the *proof*.

---

*Provenance: distilled from a positioning conversation on identity-aware vs
application-aware networking (2026-07-14), reconciled against ADR-066, ADR-085,
the OrgPath canon chain, and `inbox/UIAO_vs_OrgPath_vs_AAN_Positioning.md`.
Inbox draft — not canon; promote to `docs/` or `src/uiao/canon/` with a
UIAO_NNN allocation only after governance review.*
