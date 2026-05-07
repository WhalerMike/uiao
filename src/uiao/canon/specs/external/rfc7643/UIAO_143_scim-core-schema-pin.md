---
document_id: UIAO_143
title: "SCIM Core Schema (RFC 7643) — Substrate Pin"
version: "1.0"
status: Current
classification: CANONICAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-05-07"
updated_at: "2026-05-07"
---

# SCIM Core Schema (RFC 7643) — Substrate Pin

> **Purpose:** Pin RFC 7643 — *System for Cross-domain Identity Management:
> Core Schema* (September 2015) as the substrate-level canonical schema for
> identity payload exchange across UIAO. Establishes the vendor-neutral
> baseline that every SCIM-bearing data path in canon already implicitly
> relies on (D3.1 §5.2 canonical user shape, D3.2 middleware, D3.4 attribute
> mapping engine, D5.4 HR system onboarding playbook).

## 1. Why this pin exists

SCIM is referenced as a load-bearing wire format throughout Spec 2 (the
inbound provisioning architecture) and Spec 3 (service-account scan), but
canon never pinned the underlying IETF document. That gap meant:

- Any reference to "SCIM payload" in canon resolved to *whatever version of
  SCIM the reader had in mind*.
- Schema authors had no canonical source for the `User`, `Group`, and
  `EnterpriseUser` shapes the middleware must validate against.
- Drift detection had nothing to compare future SCIM extensions to.

This pin closes that gap. RFC 7643 is the substrate's normative reference
for core SCIM resources. Vendor-specific extensions (notably the Microsoft
extension at `urn:ietf:params:scim:schemas:extension:enterprise:2.0:User` /
`urn:scim:schemas:extension:Microsoft:2.0:User`) layer on top of this base
and live alongside their respective adapters.

## 2. Authority

| Field | Value |
|---|---|
| Document | RFC 7643 — System for Cross-domain Identity Management: Core Schema |
| Authority | IETF (Standards Track, ISSN 2070-1721) |
| Authors | P. Hunt (Ed.), K. Grizzle, E. Wahlstroem, C. Mortimore |
| Published | September 2015 |
| Companion RFCs | RFC 7642 (Definitions/Use Cases), RFC 7644 (Protocol) |
| Local copy | [`rfc7643.txt`](./rfc7643.txt) |
| SHA-256 | `df799c112a3fa5be3c0fe054c08b1f4eb5d07590c4c8343a014c4537bf638ae3` |
| Lines | 5827 |
| License | BCP 78 / Simplified BSD (per RFC text, §"Copyright Notice") |

The verbatim text is preserved as `.txt` rather than re-encoded as
Markdown so that future hash comparisons against the IETF distribution
remain trivial. The walker is configured to skip `README.md` files; the
companion `.txt` file is not traversed by the metadata validator (which
scans `.md` only).

## 3. Scope of this pin

**In scope** (substrate-level, vendor-neutral):

- Core resource types defined in RFC 7643 §4: `User`, `Group`,
  `EnterpriseUser` (the `urn:ietf:params:scim:schemas:extension:enterprise:2.0:User` extension).
- Common attributes and metadata defined in RFC 7643 §3.
- Attribute data types and characteristics defined in RFC 7643 §2.

**Out of scope** for this pin (handled elsewhere):

- SCIM **Protocol** (RFC 7644) — request/response semantics, filter syntax,
  bulk operations, error handling. Cited from D3.1 / D3.2; a future pin
  may add it as a sibling external reference if substrate code begins
  speaking the protocol directly.
- **Vendor extension schemas** — Microsoft's `Enterprise User` overlay
  (used by D3.4 §`extensionAttribute1`) and any other vendor-specific
  attributes belong adjacent to the consuming adapter, not here. A
  `src/uiao/schemas/scim/extensions/microsoft/` namespace is reserved
  for this in a follow-up.

## 4. Derived artifacts

The following JSON Schemas under `src/uiao/schemas/scim/` are derived
from the resource definitions in RFC 7643 §4 and inherit this pin's
authority:

| Schema | RFC reference | Purpose |
|---|---|---|
| [`user.schema.json`](../../../../schemas/scim/user.schema.json) | §4.1 | Core SCIM User resource |
| [`group.schema.json`](../../../../schemas/scim/group.schema.json) | §4.2 | Core SCIM Group resource |
| [`enterprise-user.schema.json`](../../../../schemas/scim/enterprise-user.schema.json) | §4.3 | Enterprise User extension |

Each schema's `$id` and `description` cite RFC 7643 by section. The
schemas are intentionally permissive (no `additionalProperties: false`
on the resource bodies) to accommodate the extensibility model RFC 7643
§3.3 mandates; restrictive validation is a deliberate decision for each
consumer (e.g. middleware in D3.2 may layer a closed schema on top).

## 5. Adapter taxonomy note

Per UIAO_003, adapters are runtime connectors with a `class` ×
`mission-class` declaration. RFC 7643 is **not** an adapter — it is a
specification consumed by adapters. Several future adapters may
register against this pin:

- An outbound SCIM provisioning adapter (mission-class: `identity`,
  class: `integration`) would emit payloads that validate against
  `user.schema.json` / `group.schema.json`.
- An inbound SCIM ingestion adapter (also identity / integration)
  would accept payloads validated by the same schemas.

Neither adapter exists today; this pin makes their construction a pure
implementation task rather than a spec-and-build task.

## 6. Provenance and drift

- **Source of truth** — `rfc7643.txt` in this directory; the SHA-256 in
  §2 is the immutability anchor. Any change to that file without an
  accompanying ADR is a `DRIFT-PROVENANCE` finding.
- **Update path** — RFC 7643 has no successor as of the publication
  date of this pin. If an updated SCIM core schema is published, retire
  this pin via supersession ADR rather than editing in place.
- **Cross-references** — D3.1 §5.2, D3.2 §3.5, D3.4 (attribute mapping
  engine), D5.4 (HR onboarding playbook), Spec 2 D2.5 §9 (SCIM
  Operation), `src/uiao/abstractions/providers.py` (lists `SCIM` as an
  abstract capability). A follow-up pass may rewrite these citations to
  point at this UIAO_143 pin explicitly.

## 7. References

- IETF RFC 7643 — local copy at [`./rfc7643.txt`](./rfc7643.txt)
- IETF RFC 7642 — SCIM Definitions, Overview, Concepts, and Requirements
- IETF RFC 7644 — SCIM Protocol
- UIAO_003 — Adapter Segmentation Overview (adapter taxonomy)
- Spec 2 D3.1 — API-Driven Inbound Provisioning Architecture (§5.2 SCIM
  payload contract)
- Spec 2 D3.4 — Attribute Mapping Engine Configuration (§ Microsoft
  extensionAttribute1 mapping)
