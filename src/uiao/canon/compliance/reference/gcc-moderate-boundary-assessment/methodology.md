# Boundary-Inference Methodology

## Position

The single load-bearing methodological position of this assessment is:

> **Absence of an explicit "not available in GCC-Moderate" statement is
> not evidence of availability.** Many telemetry-dependent capabilities
> are constrained by the FedRAMP Moderate authorization boundary itself,
> regardless of what any product page says.

## Constraining controls

The boundary acts as a filter on outbound telemetry through four NIST
800-53 controls:

| Control | Constraint applied to outbound telemetry |
|---|---|
| **SI-4** (Information System Monitoring) | Monitoring data must remain within the authorized boundary unless explicitly scoped and authorized for export. |
| **AU-2** (Audit Events) | Audit content shipped off-boundary to commercial multi-tenant analytics may exceed authorized export scope. |
| **AU-3** (Content of Audit Records) | Same as AU-2 with respect to record content. |
| **SC-7** (Boundary Protection) | Continuous, rich telemetry to multi-tenant analytics services is exactly the cross-boundary flow SC-7 forces agencies to constrain. |

## Reverse-inference rule

If a feature requires telemetry to flow to Microsoft's commercial
multi-tenant processing pipeline, **and** the FedRAMP Moderate boundary
restricts that outbound flow under SI-4, AU-2, AU-3, or SC-7, **then the
signal is blocked or degraded by architecture** — even when no Microsoft
product page explicitly says so.

Findings produced under this rule are labeled `documented: inferred`
in the gap matrix rather than asserted as documented unavailability.

## Disposition vocabulary

The `documented` field on each gap matrix row uses one of four values:

| Value | Meaning |
|---|---|
| `confirmed` | Microsoft documentation explicitly states unavailability in GCC-Moderate (e.g., Adoption Score, INR). |
| `inferred` | No explicit documentation; blocked by SI-4 / AU-2 / AU-3 / SC-7 architecture per the reverse-inference rule. |
| `restricted` | Available but with default settings that suppress the signal (e.g., Office Optional diagnostic data defaults to Required). |
| `retention-limited` | Available but data lifetime caps create a forensic cliff (e.g., CQD EUII purged after 28 days; Audit Standard 180 days). |

## Documentation purity rule

A boundary-purity rule applies to which Microsoft documentation can be
cited in support of a GCC-Moderate (.com) finding:

- `.com`-domain documentation that enumerates GCC, GCC High, and DoD
  in a single line is the strongest source — "GCC" in such lists is
  GCC-Moderate per Microsoft's own naming.
- `.us`-domain documentation (Azure Government, Intune Government
  Service) and any GCC-High- or DoD-specific page **must not** be
  applied to GCC-Moderate (.com) without separate justification.
- The `.com` boundary enforces telemetry constraints more strictly than
  the `.us` boundary, not less. Importing `.us` conclusions into `.com`
  is an unsafe inference.

## What this methodology does not claim

- It does not claim that every architecturally-constrained capability
  is unavailable — only that fidelity is degraded by the boundary
  controls in ways that are predictable from the four NIST controls.
- It does not assert detection-gap orders of magnitude as
  vendor-published numbers; those are analytical synthesis, explicitly
  labeled as such where they appear in the assessment.
- It does not propose lifting the FedRAMP Moderate boundary. It scopes
  the structural ceiling and identifies the agency-side analytics
  investment that recovers Advanced ZTMM maturity within the boundary.
