# GCC-Moderate Boundary Probe — Validation Queries

Seven KQL queries that the GCC Boundary Probe adapter executes against an
agency Sentinel / Log Analytics workspace to validate that the telemetry
pipeline assumed by the GCC-Moderate Boundary Assessment is actually in
place. Each query is a one-call diagnostic; together they form the
operational scorecard that backs the assessment's §10.2 dashboard
completeness scores.

## Queries

| File | Symptom | Source memo § |
|---|---|---|
| `01-entra-diagnostic-completeness.kql` | #1 — Invisible non-interactive / SPN / MI sign-ins | §13.3.1 |
| `02-mailitemsaccessed-operationalization.kql` | #2 — Exchange mailbox-access blind spot | §13.3.2 |
| `03-intune-ingestion.kql` | #4 — Intune compliance-state lag | §13.3.3 |
| `04-master-telemetry-health.kql` | #6 — Sentinel correlation false-negatives | §13.3.4 |
| `05-ca-evaluation-completeness.kql` | #5 — CA evaluation-log incompleteness | §13.3.5 |
| `06-power-platform-audit.kql` | #7 — Power Platform activity opacity | §13.3.6 |
| `07-exchange-security-baseline.kql` | (Exchange admin ops baseline) | §13.3.7 |

## Source provenance

All queries are derived from
`inbox/New_FedRAMP_Boundary/M365_GCC-Moderate_Telemetry_and_Boundary_Assessment_External_with_images.docx`,
Section 13.3.

## Consumers

- `gcc_boundary_probe/probe.py` — runs each query via the Log Analytics
  Query API and emits per-symptom drift findings (`DRIFT-BOUNDARY` class).
- `src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml` — gap-matrix rows
  cross-reference these queries via the symptom mapping above.
- Customer doc: `docs/customer-documents/compliance/boundary-authorization/B1-gcc-moderate-boundary-model.qmd`.
