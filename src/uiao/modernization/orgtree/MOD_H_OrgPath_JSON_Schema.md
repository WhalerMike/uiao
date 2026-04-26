---
document_id: MOD_H
title: "Appendix H — OrgPath JSON Schema"
version: "2.0"
status: DRAFT
classification: CANONICAL
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-26
boundary: GCC-Moderate
namespace: MOD
parent_canon: UIAO_008
binding_adrs:
  - ADR-035
  - ADR-045
---

# Appendix H — OrgPath JSON Schema

Purpose

This appendix defines the canonical JSON Schema 2020-12 documents for all OrgTree data objects. These schemas are the machine-readable contract for data validation across the Governance OS.

Scope

Covers JSON Schema definitions for OrgPathEntry, OrgPathCodebook, DynamicGroupDefinition, and AttributeMapping objects. All schemas are tenant-agnostic and validate structure only (not tenant-specific values).

Canonical Structure

Each schema follows JSON Schema 2020-12 specification with $schema, $id, title, description, type, properties, required, and additionalProperties: false.

Technical Scaffolding

OrgPathEntry Schema

{   "$schema": "https://json-schema.org/draft/2020-12/schema",   "$id": "https://uiao.gov/schemas/orgpath-entry.schema.json",   "title": "OrgPathEntry",   "description": "Schema for a single OrgPath code entry in the canonical codebook.",   "type": "object",   "properties": {     "code": {       "type": "string",       "pattern": "^ORG(-[A-Z]{2,6}){0,8}$",       "description": "The OrgPath code string."     },     "level": {       "type": "integer",       "minimum": 0,       "maximum": 8,       "description": "Hierarchy level: 0=Root, 1=Division, 2=Department, 3=Unit, 4=Team, 5=Sub-Team, 6=Cell, 7=Crew, 8=Squad."     },     "description": {       "type": "string",       "minLength": 1,       "maxLength": 256,       "description": "Human-readable description of this OrgPath node."     },     "parentPath": {       "type": ["string", "null"],       "pattern": "^ORG(-[A-Z]{2,6}){0,7}$",       "description": "The OrgPath code of the parent node. Null for root."     },     "allowedChildrenPattern": {       "type": "string",       "description": "Regex pattern for valid child OrgPath codes."     },     "maxDepth": {       "type": "integer",       "minimum": 0,       "maximum": 8,       "description": "Maximum additional depth allowed below this node."     },     "status": {       "type": "string",       "enum": ["active", "deprecated", "pending"],       "description": "Current lifecycle status of this OrgPath code."     },     "createdDate": {       "type": "string",       "format": "date-time",       "description": "ISO 8601 datetime when this code was created."     },     "modifiedDate": {       "type": "string",       "format": "date-time",       "description": "ISO 8601 datetime when this code was last modified."     },     "owner": {       "type": "string",       "minLength": 1,       "description": "Role or group responsible for this OrgPath node."     }   },   "required": ["code", "level", "description", "parentPath", "allowedChildrenPattern",                "maxDepth", "status", "createdDate", "modifiedDate", "owner"],   "additionalProperties": false }

OrgPathCodebook Schema

{   "$schema": "https://json-schema.org/draft/2020-12/schema",   "$id": "https://uiao.gov/schemas/orgpath-codebook.schema.json",   "title": "OrgPathCodebook",   "description": "Schema for the complete OrgPath codebook containing all valid OrgPath entries.",   "type": "object",   "properties": {     "schemaVersion": {       "type": "string",       "const": "2020-12",       "description": "JSON Schema version used for this codebook."     },     "codebookVersion": {       "type": "string",       "pattern": "^\\d+\\.\\d+\\.\\d+$",       "description": "Semantic version of the codebook content."     },     "generatedDate": {       "type": "string",       "format": "date-time",       "description": "ISO 8601 datetime when this codebook was generated."     },     "entries": {       "type": "array",       "items": { "$ref": "orgpath-entry.schema.json" },       "minItems": 1,       "description": "Array of OrgPath entries. Codes must be unique."     }   },   "required": ["schemaVersion", "codebookVersion", "generatedDate", "entries"],   "additionalProperties": false }

DynamicGroupDefinition Schema

{   "$schema": "https://json-schema.org/draft/2020-12/schema",   "$id": "https://uiao.gov/schemas/dynamic-group.schema.json",   "title": "DynamicGroupDefinition",   "description": "Schema for a dynamic group definition in the OrgTree group library.",   "type": "object",   "properties": {     "groupName": {       "type": "string",       "pattern": "^OrgTree-[A-Za-z0-9-]+$",       "description": "Display name following OrgTree naming convention."     },     "groupType": {       "type": "string",       "enum": ["Security", "M365"],       "description": "Group type: Security or Microsoft 365."     },     "membershipRule": {       "type": "string",       "minLength": 1,       "description": "Entra ID dynamic membership rule syntax."     },     "orgPathScope": {       "type": "string",       "description": "The OrgPath prefix this group covers."     },     "purpose": {       "type": "string",       "minLength": 1,       "description": "Business purpose for this group."     }   },   "required": ["groupName", "groupType", "membershipRule", "orgPathScope", "purpose"],   "additionalProperties": false }

AttributeMapping Schema

{   "$schema": "https://json-schema.org/draft/2020-12/schema",   "$id": "https://uiao.gov/schemas/attribute-mapping.schema.json",   "title": "AttributeMapping",   "description": "Schema for a legacy-to-Entra attribute mapping entry.",   "type": "object",   "properties": {     "legacyAttribute": {       "type": "string",       "description": "Active Directory attribute name."     },     "entraAttribute": {       "type": "string",       "description": "Entra ID / Microsoft Graph attribute name."     },     "dataType": {       "type": "string",       "enum": ["String", "Integer", "Boolean", "Reference", "Array", "DateTime"],       "description": "Data type of the attribute value."     },     "maxLength": {       "type": ["integer", "null"],       "minimum": 1,       "description": "Maximum character length. Null for non-string types."     },     "required": {       "type": "boolean",       "description": "Whether this attribute is required for every user."     },     "validationRule": {       "type": "string",       "description": "Validation rule description or regex."     },     "orgTreeUsage": {       "type": "string",       "description": "How this attribute is used in the OrgTree model."     }   },   "required": ["legacyAttribute", "entraAttribute", "dataType", "required",                "validationRule", "orgTreeUsage"],   "additionalProperties": false }

Boundary Rules

All schema $id URIs are namespace identifiers only; they do not imply an external hosting dependency.

Schemas validate data structures used within M365 GCC-Moderate operations exclusively.

Drift Considerations

Schema Drift: If a data object in the repository does not validate against its schema, that constitutes schema drift. Severity: Critical.

Schema changes must follow Workflow 4 (Attribute Schema Change Request) in Appendix E.

Governance Alignment

These schemas are the machine-readable expression of Principle 2 (Schema Fixity). The additionalProperties: false constraint on every schema ensures that no ungovern attributes can be introduced without a schema change, which requires a governed workflow.
