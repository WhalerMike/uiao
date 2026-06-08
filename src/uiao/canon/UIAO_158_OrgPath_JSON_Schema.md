---
document_id: UIAO_158
title: "Appendix H — OrgPath Codebook JSON Schema (Model C)"
version: "3.0"
status: Current
owner: Michael Stratton
created_at: "2026-04-18"
updated_at: "2026-05-24"
provenance_flatten:
  prior_id: "MOD_H"
  flattened_at: "2026-05-10"
  flattened_by: "ADR-060"
---

# Appendix H — OrgPath Codebook JSON Schema (Model C)

> **Model C — 15-facet multi-attribute (per [ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md)).** The canonical OrgPath JSON Schema validates the **per-facet Codebook document** declaring each of the 10 named facets with its slot binding, kind (enumerated / typed / reserved), and per-facet enumeration or typed pattern. The executable schema is [`schemas/orgpath/codebook.schema.json`](../schemas/orgpath/codebook.schema.json) (JSON Schema draft 2020-12; `schema_version: 2.0.0`). The Python loader at [`uiao.modernization.orgtree.codebook`](../modernization/orgtree/codebook.py) additionally enforces the **slot-uniqueness invariant** after JSON Schema validation passes — cross-property uniqueness is not expressible in JSON Schema, so the loader is the enforcement point. This appendix is the v3.0 Model C rewrite; the prior Model A composite-hyphen schemas (`OrgPathEntry`, `OrgPathCodebook`, `DynamicGroupDefinition`, `AttributeMapping`) were retired by ADR-078 Phase 1 and are no longer authoritative.

## Purpose

Define the canonical JSON Schema 2020-12 document for the **per-facet OrgPath Codebook**. This is the machine-readable contract for data validation across the Governance OS Model C surface.

## Scope

Covers the JSON Schema definition for the Codebook document (collection of Facet declarations). Per-value validation against a specific facet's enumeration or typed pattern is a runtime concern executed by the Python loader against the loaded codebook — not a schema concern (JSON Schema cannot validate values against an enumeration defined elsewhere in the same document).

Other Model C-relevant schemas:

- **Dynamic Group rules** under Model C are Entra dynamic membership rule strings composed of facet predicates — the rule string is validated by Entra's parser at group creation, not by a UIAO schema. UIAO governance validates the *library entry* shape (group name + canonical rule + facet attribution); see UIAO_152 v3.0 for the rebuilt library.
- **Administrative Unit memberships** under Model C compose facet predicates exactly like dynamic groups; see UIAO_154 v3.0.
- **HR-to-Entra attribute mapping** under Model C is per-facet inbound provisioning: 10 source HR fields → 10 `extensionAttribute*` slots. The mapping is declared per facet in the codebook itself (each facet's `source` and `transform` keys, when present), not in a separate AttributeMapping document.

## Canonical Structure

The schema follows JSON Schema 2020-12 specification: `$schema`, `$id`, `title`, `description`, `type: object`, `properties`, `required`, and `additionalProperties: false`.

## Codebook Schema

The canonical schema validates a Codebook document with **per-facet declarations**. The complete schema lives at [`src/uiao/schemas/orgpath/codebook.schema.json`](../schemas/orgpath/codebook.schema.json); the structural summary:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://uiao.gov/schemas/orgpath-codebook.schema.json",
  "title": "OrgPath Codebook (Model C)",
  "description": "Per-facet codebook declaring the 10 named facets + 5 reserved slots that compose Model C OrgPath. Slot uniqueness is loader-enforced after schema validation.",
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "2.0.0",
      "description": "Codebook schema version — bound to Model C per ADR-078."
    },
    "codebook_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semantic version of the codebook content."
    },
    "generated_date": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 datetime when this codebook was generated."
    },
    "facets": {
      "type": "array",
      "items": { "$ref": "#/$defs/Facet" },
      "minItems": 10,
      "description": "Array of Facet declarations. Each of the 10 named slots (extensionAttribute1..10) must be claimed by exactly one facet; reserved slots (extensionAttribute11..15) may appear with kind: reserved."
    }
  },
  "required": ["schema_version", "codebook_version", "generated_date", "facets"],
  "additionalProperties": false,
  "$defs": {
    "Facet": {
      "type": "object",
      "oneOf": [
        { "$ref": "#/$defs/EnumeratedFacet" },
        { "$ref": "#/$defs/TypedFacet" },
        { "$ref": "#/$defs/ReservedFacet" }
      ]
    },
    "EnumeratedFacet": {
      "type": "object",
      "properties": {
        "name":        { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
        "attribute":   { "type": "string", "pattern": "^extensionAttribute(1[0-5]|[1-9])$" },
        "kind":        { "const": "enumerated" },
        "description": { "type": "string" },
        "enumeration": {
          "type": "array",
          "items": { "$ref": "#/$defs/EnumerationValue" },
          "minItems": 1
        },
        "status": { "enum": ["active", "deprecated", "pending"] },
        "owner":  { "type": "string", "minLength": 1 }
      },
      "required": ["name", "attribute", "kind", "enumeration", "status", "owner"],
      "additionalProperties": false
    },
    "TypedFacet": {
      "type": "object",
      "properties": {
        "name":          { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
        "attribute":     { "type": "string", "pattern": "^extensionAttribute(1[0-5]|[1-9])$" },
        "kind":          { "const": "typed" },
        "description":   { "type": "string" },
        "value_type":    { "enum": ["string", "integer", "date"] },
        "value_pattern": { "type": "string" },
        "allow_empty":   { "type": "boolean", "default": false },
        "status":        { "enum": ["active", "deprecated", "pending"] },
        "owner":         { "type": "string", "minLength": 1 }
      },
      "required": ["name", "attribute", "kind", "value_type", "status", "owner"],
      "additionalProperties": false
    },
    "ReservedFacet": {
      "type": "object",
      "properties": {
        "name":        { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
        "attribute":   { "type": "string", "pattern": "^extensionAttribute(1[0-5]|[1-9])$" },
        "kind":        { "const": "reserved" },
        "description": { "type": "string" }
      },
      "required": ["name", "attribute", "kind"],
      "additionalProperties": false
    },
    "EnumerationValue": {
      "type": "object",
      "properties": {
        "value":       { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "status":      { "enum": ["active", "deprecated"], "default": "active" },
        "replaced_by": { "type": "string" }
      },
      "required": ["value"],
      "additionalProperties": false
    }
  }
}
```

## Per-Facet Validation Semantics

JSON Schema validates the *Codebook document shape*. Runtime per-value validation against the loaded codebook is performed by the Python loader and the (Phase 5-scheduled) per-facet drift engine:

| Facet kind | Per-value validation |
|---|---|
| **enumerated** | Value must appear in the facet's `enumeration` list with `status: active`. Values with `status: deprecated` trigger Phantom Drift (P3); when `replaced_by` is set, the engine reassigns the principal to the successor. |
| **typed** | Value must satisfy `value_type` and (if present) match `value_pattern`. Empty string is rejected unless `allow_empty: true`. |
| **reserved** | Value must be null/empty. Any non-empty value on a reserved facet is rejected until the slot is promoted to enumerated or typed via governed PR. |

## Slot-Uniqueness Invariant (Loader-Enforced)

JSON Schema cannot express cross-property uniqueness (no construct equivalent to `UNIQUE (attribute)` across array items). The Python loader's `_validate_integrity` step runs after schema validation passes and rejects any codebook where two facets bind the same slot:

```
Facets 'region' and 'second_facet' both bind to 'extensionAttribute1'.
Each extensionAttribute slot must be claimed by at most one facet.
```

A violation surfaces as **Slot Drift** (P1) in the drift engine — see UIAO_163 v2.0.

## Boundary Rules

All schema `$id` URIs are namespace identifiers only; they do not imply an external hosting dependency. Schemas validate codebook documents used within M365 GCC-Moderate operations exclusively.

## Drift Considerations

**Schema Drift.** If the loaded codebook document does not validate against `codebook.schema.json`, that is schema drift. Severity: Critical (P1).

**Slot Drift.** If schema validation passes but the loader's slot-uniqueness check fails, that is Slot Drift. Severity: Critical (P1). Distinct from value-level drift categories (Value, Format, Orphan, Phantom).

**Schema-change governance.** Schema changes follow Workflow 4 (Attribute Schema Change Request) in Appendix E. Changing a facet's slot binding requires a superseding ADR (slot bindings are not per-tenant overrides).

## Governance Alignment

This schema is the machine-readable expression of Principle 2 (Schema Fixity) under Model C. The `additionalProperties: false` constraint on every schema object ensures no ungoverned attributes can be introduced into the codebook without a schema change, which requires a governed workflow. Per-facet decomposition expresses Principle 5 (Composability): each facet validates and governs independently.
