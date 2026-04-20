---
document_id: MOD_N
title: "Appendix N — Execution Substrate Integration Layer"
version: "1.0"
status: DRAFT
classification: CANONICAL
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
namespace: MOD
parent_canon: UIAO_008
---

# Appendix N — Execution Substrate Integration Layer

> **Substrate Update (April 2026):** This appendix originally referenced Execution Substrate as the execution substrate. The execution substrate is now implementation-configurable — any compliant automation agent (e.g., Copilot Tasks, PowerShell Runbooks, GitHub Actions) may serve as the execution brain, provided it conforms to the instruction set schema and execution contract defined below. All references have been updated to the generic term "Execution Substrate."

Purpose

This appendix defines the integration layer between Copilot (governance brain) and Execution Substrate (execution brain), including the instruction set schema, execution contract, handoff protocol, and error handling.

Scope

Covers all communication between Copilot and Execution Substrate for governance operations. All executed instructions target M365 GCC-Moderate services exclusively.

Canonical Structure

The integration follows a request-response pattern: Copilot produces an instruction set, Execution Substrate executes it, and Copilot validates the result.

Technical Scaffolding

Integration Architecture

+------------------+                              +--------------------+ |     COPILOT      |                              |   EXECUTION SUBSTRATE    | | (Governance)     |                              | (Execution)        | |                  |   1. Generate Instruction     |                    | |  +------------+  |   2. Validate boundaries      |                    | |  | Governance |  |   3. Dispatch                 |                    | |  | Rules      |--+----Instruction Set (JSON)---->|  +-------------+  | |  +------------+  |                              |  | Execute     |  | |                  |                              |  | Literally   |  | |  +------------+  |   6. Validate result          |  +------+------+  | |  | Provenance |  |   7. Record provenance        |         |         | |  | Log        |<-+----Execution Result (JSON)---+  4. Run |         | |  +------------+  |                              |  5. Return result  | +------------------+                              +--------------------+

Instruction Set Schema

{   "$schema": "https://json-schema.org/draft/2020-12/schema",   "$id": "https://uiao.gov/schemas/instruction-set.schema.json",   "title": "InstructionSet",   "description": "Instruction payload from Copilot to Execution Substrate.",   "type": "object",   "properties": {     "instructionId": {       "type": "string",       "format": "uuid",       "description": "Unique identifier for this instruction."     },     "instructionType": {       "type": "string",       "enum": ["execute-powershell", "execute-graph-query", "validate-schema", "generate-report"],       "description": "Type of execution requested."     },     "payload": {       "type": "object",       "description": "Execution-specific payload. Structure varies by instructionType."     },     "constraints": {       "type": "array",       "items": { "type": "string" },       "description": "Boundary rules that must be satisfied during execution."     },     "expectedOutput": {       "type": "object",       "description": "Schema describing the expected result structure."     },     "issuedAt": {       "type": "string",       "format": "date-time"     },     "issuedBy": {       "type": "string",       "const": "copilot",       "description": "Always 'copilot'; instructions only flow from governance brain."     }   },   "required": ["instructionId", "instructionType", "payload", "constraints",                "expectedOutput", "issuedAt", "issuedBy"],   "additionalProperties": false }

Execution Contract

Execution Substrate MUST NOT interpret instructions beyond literal execution.

Execution Substrate MUST return structured results conforming to expectedOutput.

Execution Substrate MUST halt execution immediately upon detecting a boundary violation.

Execution Substrate MUST NOT modify governance artifacts, schemas, or codebooks.

Execution Substrate MUST log all execution steps with timestamps.

Handoff Protocol

Copilot generates an instruction set conforming to the schema above.

Copilot validates the instruction against all boundary rules (Appendix K, Decision Tree 5).

Copilot dispatches the validated instruction to Execution Substrate.

Execution Substrate parses the instruction and executes the specified operation.

Execution Substrate returns a structured result with status, output data, and any errors.

Copilot validates the result against expectedOutput schema.

Copilot records full provenance: instructionId, timestamp, executor, result hash.

Error Codes

Boundary Rules

All instructions must target M365 GCC-Moderate services only.

The constraints array in every instruction must include "boundary:m365-gcc-moderate".

Execution Substrate must validate each API endpoint against the M365 GCC-Moderate service list before execution.

Drift Considerations

If Execution Substrate executes an instruction that Copilot did not generate, that constitutes execution substrate drift. Severity: Critical.

Integration layer changes require Workflow 8.

Governance Alignment

This appendix is the canonical specification of Principle 6 (Two-Brain Execution). The separation between governance and execution is enforced architecturally, not just procedurally.
