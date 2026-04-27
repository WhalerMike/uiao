# Resolved Positions on Disputed Questions

Several questions in scope for the source assessment were initially the
subject of conflicting analytical conclusions. This file records the
position adopted for each, on a most-documented, most-conservative
basis.

| Question | Resolved position |
|---|---|
| How many M365 dashboards are unavailable in GCC-Moderate? | Two confirmed unavailable (Adoption Score and INR), one inferred unavailable (Endpoint Analytics Advanced tier). CQD and Usage Analytics are available with operational caveats. |
| Is Teams CQD available in GCC-Moderate? | Available, with 28-day EUII retention as the operational constraint. |
| Is M365 Usage Analytics available? | Available via the GCC-specific connector; the Marketplace template app is the only missing variant. |
| Is the boundary-inference framework (NIST SI-4 / AU-2 / AU-3 / SC-7) valid? | Accepted as methodological, with explicit `documented: inferred` labeling rather than asserted unavailability. |
| Is INR explicitly unavailable? | Yes — confirmed unavailable (verbatim Microsoft text). |
| Are agencies in BOD 25-01 / M-22-09 violation? | Core requirements achievable with agency-side analytics; not free out of the box. Optimal maturity not achievable without compensating engineering. |
| Should TTPs and hour-level detection gaps be quantified? | Provided in [`mitre-chains.md`](mitre-chains.md) and the gap matrix with explicit acknowledgment that detection-gap orders of magnitude are analytical synthesis, not vendor-published numbers. |

## Conceptual framings used throughout this assessment

| Term | Meaning |
|---|---|
| **False negative** | Absence of "not available" language is not evidence of availability. |
| **Telemetry paradox** | Controls meant to protect government data create a shadow zone where advanced attack patterns thrive. |
| **Forensic cliff** | The 28-day CQD EUII purge and 180-day Audit Standard retention create incident-discovery dead zones. |
| **Digital disengagement** | The missing communication-volume baseline is a flight-risk insider indicator. |
| **Grey-ware** | Attacks that evade EDR but show as performance outliers, invisible without Endpoint Analytics. |
| **Sovereign blind spot compound chain** | Multiple gaps combining to enable undetectable nation-state-grade exfiltration. |
| **Ghost compromise** | The proxy + BYOD + low-and-slow exfiltration scenario described in [`mitre-chains.md`](mitre-chains.md). |
