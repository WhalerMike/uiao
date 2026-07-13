# UIAO vs OrgPath vs AAN — Roles, Overlaps, Complementarity, and Value

> **Positioning note (inbox draft — not canon).** A grounded comparison of three
> things that are easy to conflate because they share a doctrinal vocabulary
> (HR-as-SSOT, Zero Trust, an authoritative "naming/addressing plane", NIST
> 800-53 / CM-8, explicit drift). Sourced from the repo's own canon —
> ADR-085 (UIAO positioning), the OrgPath/LocPath ADR chain, ADR-066 (AAN
> concept), and the AAN corpus under `inbox/` — with the key citations inline.

## The one-line answer: three different altitudes, not three peers

- **UIAO** is the **engine** — a vertical-agnostic *governance substrate* that
  proves and generates compliance.
- **OrgPath** (with **LocPath**) is a **plane inside that engine** — the governed
  identity-addressing primitive.
- **AAN** is a **content vertical that runs on top** — the federal
  networking-modernization program whose evidence the engine consumes.

Comparing their "roles" as if they were competing products is the wrong frame;
the useful comparison is how the three layers relate.

## Side-by-side

| | **UIAO** | **OrgPath** (+ LocPath) | **AAN** (Federal App-Aware Networking) |
|---|---|---|---|
| **What it is** | Unified Identity-Addressing-Overlay Architecture — a governance OS / substrate | A governed org-placement naming attribute derived from an HR-sourced OrgTree registry | A ten-volume federal networking-modernization document series + IaC/ServiceNow kits |
| **Altitude** | The engine | A plane *within* the engine (the addressing plane) | A domain corpus *on top of* the engine |
| **Role** | Turn compliance into a deterministic pipeline: SSOT canon → drift detection → schema-enforced adapters → canon-anchored OSCAL/KSI evidence | Restore the shared organizational substrate AD's OU tree lost; be the stable key that drives ABAC / Zero-Trust targeting and survives reorgs | Say *which* network mechanisms (IPAM/DDI, SD-WAN, TIC 3.0, 802.1X…) close *which* NIST controls, and produce the evidence |
| **Addresses…** | (the engine itself) | **principals** — where a user/device sits in the org (`Region=NCR\|Department=IT\|…`) | **hosts/traffic** — the network naming/addressing/transport plane (IP, DNS, circuits) |
| **Scope** | Vertical-agnostic core; federal is the most-mature *adapter pack* (ADR-085) | UIAO canon; general-enterprise, federal (OPM HRIT) as one instantiation | External **companion content** for the federal vertical — explicitly *"not part of UIAO"* |
| **Home in repo** | `src/uiao/` (canon, schemas, adapters, ksi, oscal…) | `src/uiao/canon/` (UIAO_007/011/013/151/193/194; ADR-035/048/088/098/102) | `inbox/Application Aware Networking/` + `infoblox-ddi-book/` |
| **Produces** | OSCAL SSP/POA&M, KSI signals, drift findings, evidence bundles / graph | A drift-detectable attribute + dynamic groups feeding Conditional Access / SASE / Intune | Books, a compliance spine, and Terraform/ServiceNow kits — evidence for UIAO's adapter |

## Where they overlap

- **Shared doctrinal spine.** All three invoke the same four ideas — **HR as the
  single source of truth**, **Zero Trust / SASE**, an authoritative
  **naming/addressing plane**, and **NIST 800-53 / CM-8 + explicit drift**. That
  shared vocabulary is why they feel like peers.
- **UIAO ∩ OrgPath** is *containment*, not overlap: OrgPath literally **is**
  UIAO's addressing plane. They share the canon, the drift taxonomy
  (`DRIFT-IDENTITY`), and the evidence pipeline.
- **UIAO ∩ AAN** is *consume-and-emit*: a UIAO conformance adapter — the
  **"FedRAMP AAN Evidence Catalog"** (`src/uiao/canon/adapter-registry.yaml`) —
  binds AAN's document evidence to NIST controls, and the AAN *concept* has a
  canonical home in **ADR-066** ("Application-Aware Networking & Token-Bound
  Transport"). The AAN *corpus itself* is external.
- **OrgPath ∩ AAN** is the subtle one: they are **architecturally parallel** (a
  grep for `OrgPath` inside the AAN files returns nothing). They connect only
  through shared doctrine (HR-SSOT, ADR-066's SASE/ZTNA fabric) — not direct
  cross-references.

## Where they're complementary (the real value)

They are the **two halves of the CM-8 join**, plus the engine that proves it:

- **OrgPath = identity addressing** — "who is this principal, and where do they
  sit in the org?" → drives *policy targeting*.
- **AAN's IPAM/DDI = network addressing** — "what/where is this host on the
  wire?" → the *network naming/transport* plane.
- Both reconcile to the **same CM-8 asset-identity join key**; neither is the
  other. OrgPath keys *people/devices*; IPAM/DDI keys *hosts/subnets*.
- **UIAO** is the layer that ingests both as canon-anchored evidence and emits
  the continuous, drift-checked OSCAL/KSI authorization package.

**Mental model:** *AAN builds the network substrate, OrgPath builds the identity
substrate, and UIAO governs and proves both.*

## Value of each, standalone

- **UIAO** — converts authorization/compliance from a perpetual document project
  into a **deterministic pipeline output** with cryptographic provenance and
  drift containment. Value: *reuse and rigor* — the same engine serves any
  vertical, and drift is never silently tolerated.
- **OrgPath** — the **one attribute that survives reorgs, transfers, and rejoins**
  without manual remediation, making Zero-Trust / ABAC targeting deterministic
  and *drift-detectable* instead of a spreadsheet of static group memberships.
  Value: a *stable, governed identity primitive*, now vendor-neutral across
  clouds (ADR-098).
- **AAN** — the **federal networking-modernization playbook**: the domain
  expertise mapping specific mechanisms to specific control closures (with the
  "no alternate closure path" necessity arguments), plus deployable IaC /
  ServiceNow kits and a machine-checked compliance spine. Value: *domain content
  + an evidence source* — the thing that gives UIAO's federal adapter pack
  something concrete to attest.

## Caveat / opportunity

The **OrgPath ↔ AAN** link is doctrinal, not yet wired at the document level. The
most natural place to tighten the story is to explicitly reconcile **OrgPath
(organizational addressing)** and **IPAM/DDI (network addressing)** as the two
CM-8 addressing planes — one keying principals, one keying hosts, both feeding
the same join key that UIAO attests.
