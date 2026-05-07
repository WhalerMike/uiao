# SCIM 2.0 Core Schemas

JSON Schemas derived from **RFC 7643 — System for Cross-domain Identity
Management: Core Schema** (IETF, September 2015). Pinned by canon document
[`UIAO_143`](../../canon/specs/external/rfc7643/UIAO_143_scim-core-schema-pin.md).

| File | RFC reference | Schema URN |
|---|---|---|
| `common.schema.json` | §3.1 (Common Attributes), §2.3 (Data Types), §2.4 (Multi-Valued) | — (shared `$defs`) |
| `user.schema.json` | §4.1 | `urn:ietf:params:scim:schemas:core:2.0:User` |
| `group.schema.json` | §4.2 | `urn:ietf:params:scim:schemas:core:2.0:Group` |
| `enterprise-user.schema.json` | §4.3 | `urn:ietf:params:scim:schemas:extension:enterprise:2.0:User` |

## Conventions

- **Permissive by default.** Resource-level objects do not set
  `additionalProperties: false`. RFC 7643 §3.3 mandates an extensibility
  model; closing the schema at the substrate level would break it.
  Consumers that need closed validation (e.g. middleware in Spec 2 D3.2)
  layer a closed schema on top.
- **Cross-references via `$ref`.** Per-resource schemas reference
  `common.schema.json#/$defs/...` for shared shapes (`schemas`, `meta`,
  `multiValuedAttribute`, etc.). Loaders MUST resolve `$ref` relative to
  the schema's `$id`.
- **Citations in `description`.** Every property documents the RFC 7643
  section it derives from, so a reader can move from the schema to the
  pinned text in `canon/specs/external/rfc7643/rfc7643.txt` without
  guesswork.
- **Vendor extensions live elsewhere.** Microsoft's overlay
  (`urn:scim:schemas:extension:Microsoft:2.0:User`, used by Spec 2 D3.4
  for `extensionAttribute1`) is intentionally *not* in this directory.
  When it lands it will go under `schemas/scim/extensions/microsoft/`,
  layered on top of these base schemas.

## Drift

Any change to these files without a corresponding update to UIAO_143 (or a
supersession ADR if RFC 7643 is replaced) is a `DRIFT-PROVENANCE` finding.
