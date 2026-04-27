# GCC-Moderate Boundary & Telemetry Assessment

Canonical analytical reference documenting how the FedRAMP Moderate
authorization boundary constrains M365 GCC-Moderate telemetry, including
the boundary-inference framework, capability dispositions, and the
compound-chain attack scenarios that drive the headline findings.

## Provenance

| Field | Value |
|---|---|
| Source document | `inbox/New_FedRAMP_Boundary/M365_GCC-Moderate_Telemetry_and_Boundary_Assessment_External_with_images.docx` |
| Source version | External v1.0, 2026-04-25 |
| Author | Michael Stratton |
| Promoted to canon | 2026-04-27 |
| Companion data | [`src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml`](../../../data/gcc-moderate-telemetry-gaps.yaml) |
| Companion docs | `inbox/New_FedRAMP_Boundary/GCC-Moderate_Boundary_and_ThousandEyes_Assessment_External_with_images.docx`, `inbox/New_FedRAMP_Boundary/FedRAMP_20x_Assessment_and_Implications.docx` |

## What this folder contains

| File | Purpose |
|---|---|
| `README.md` | This index. |
| `methodology.md` | The boundary-inference framework (SI-4 / AU-2 / AU-3 / SC-7) and the reverse-inference rule. |
| `capabilities.md` | Per-capability disposition: confirmed unavailable, documentation-limited, available, and architecturally constrained. |
| `mitre-chains.md` | Compound-chain attack scenarios that arise when multiple gap rows compound (Chain A, Chain B, "ghost compromise"). |
| `resolved-positions.md` | Methodological positions taken on previously-disputed questions (the source's §14). |

The machine-readable §6 gap matrix lives separately as
[`canon/data/gcc-moderate-telemetry-gaps.yaml`](../../../data/gcc-moderate-telemetry-gaps.yaml)
so validators, scorecards, and adapters can consume it directly.

## Authorization scope

**FedRAMP Moderate only** (M365 GCC-Moderate, .com commercial cloud).
GCC-High, DoD, and FedRAMP High environments are out of scope as
authorization targets and appear only as comparators where Microsoft
documentation enumerates them in the same line that names GCC-Moderate.
The .us-domain documentation purity rule applies: .us conclusions must
not be imported into .com without separate justification because the
.com boundary enforces telemetry constraints more strictly, not less.
AWS GovCloud is excluded (FedRAMP High + DoD SRG IL2/4/5 + ITAR).

## Cross-references

- ADR-033 (GCC Boundary Drift Class) — operational drift detection for the boundary documented here.
- ADR-043 (FedRAMP RFC-0026 CA-7 Integration) — continuous-monitoring pathway that consumes this assessment's evidence.
- `src/uiao/rules/ksi/boundary-protection/ksi-sc-07.yaml` — KSI realization of the SC-7 constraint cited throughout.
- `src/uiao/rules/ksi/monitoring-logging/` — KSI realizations of the SI-4 / AU-2 / AU-3 constraints.
- `src/uiao/adapters/modernization/gcc_boundary_probe/` — runtime collection harness; the §13.3 KQL queries land under `queries/` here.
- `docs/findings/fedramp-gcc-moderate-*.md` — per-row findings extracted from the gap matrix.
- `docs/customer-documents/compliance/boundary-authorization/B1-gcc-moderate-boundary-model.qmd` — customer-facing rendering of this content.

## Stewardship

Treat this folder as a canonical analytical reference. Updates require
either (a) revision of the source assessment in `inbox/`, with the
revised version re-promoted, or (b) targeted change with a provenance
note and a CHANGELOG entry. Do not edit ad-hoc.
