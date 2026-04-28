---
title: Drift Engine Overview — Executive Brief
doc-type: executive-brief
canon-source: docs/docs/16_DriftDetectionStandard.qmd
derived-from: uiao canon
---

# Drift Engine Overview — Executive Brief

For federal CIO/CISO leadership, UIAO’s drift engine is the control that continuously answers: *“Are we still operating exactly as canonized policy, identity, and evidence rules require?”* It classifies drift using one taxonomy, assigns operational urgency, and drives a bounded remediation path.

## Canonical drift classes

UIAO uses five classes (verbatim from the Drift Detection Standard):

- `DRIFT-SCHEMA` — structure no longer matches canonical schema.
- `DRIFT-SEMANTIC` — structure is valid, but meaning is stale or inconsistent.
- `DRIFT-PROVENANCE` — evidence chain is incomplete, invalid, or broken.
- `DRIFT-AUTHZ` — data moved outside its authorized consent envelope.
- `DRIFT-IDENTITY` — issuer cannot be resolved to a verified identity object.

## Severity model and operational obligation

| Severity | Meaning | Operational obligation |
|---|---|---|
| `P1` | Active-use claim with provenance/identity risk | Halt affected flow, alert immediately, escalate to governance leadership (Canon Steward / Architecture Lead / CISO path) |
| `P2` | Live schema/semantic drift | Auto-remediate when deterministic; otherwise escalate within 1 hour |
| `P3` | Dormant/historical drift | Queue remediation and close within 24 hours |
| `P4` | Style/metadata drift with no semantic impact | Log and auto-remediate within 72 hours |

## Where drift is detected

1. **CI substrate walker** (`uiao substrate walk`, `substrate-drift.yml`) detects shipped classes now: `DRIFT-SCHEMA` and `DRIFT-PROVENANCE`.
2. **Runtime conformance runner** detects runtime drift during adapter execution and emits remediation-contract records (`drift_class`, `severity`, timestamps, remediation action, evidence, escalation path).

## How leaders should consume drift output

- **Governance tickets:** every material event becomes a tracked governance action with explicit owner and SLA.
- **OSCAL evidence regeneration:** drift outcomes trigger regeneration of affected evidence artifacts so SSP/POA&M narratives stay canon-accurate.
- **Enforcement adapter feedback:** remediation outcomes (`halt | fix | flag | log`) feed enforcement behavior to reduce repeat drift.

## Maturity snapshot (current)

| Drift class | Maturity |
|---|---|
| `DRIFT-SCHEMA` | **SHIPPED** |
| `DRIFT-PROVENANCE` | **SHIPPED** |
| `DRIFT-SEMANTIC` | **TARGET** (partial runtime design) |
| `DRIFT-AUTHZ` | **DESIGN-ONLY** (pending runtime implementation) |
| `DRIFT-IDENTITY` | **DESIGN-ONLY** (pending runtime implementation) |

**Leadership takeaway:** UIAO already ships structural/provenance drift enforcement in CI, with the same taxonomy and severity contract extending to runtime semantic, authorization, and identity drift as those controls are completed.
