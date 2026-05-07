---
title: "Drift Detection Standard — DRIFT-BOUNDARY Amendment"
id: UIAO_016_AMEND_001
status: proposed
date: 2026-04-19
amends: "docs/docs/16_DriftDetectionStandard.qmd"
canon_ref: ADR-030
---

# Amendment to UIAO Drift Detection Standard
## Adding DRIFT-BOUNDARY as Sixth Drift Class

### Context

The existing five-class drift taxonomy does not cover a class of
failure discovered in GCC-Moderate deployments: features nominally
within the FedRAMP-authorized boundary that are silently unavailable
due to undocumented Microsoft restrictions or telemetry dependencies
conflicting with FedRAMP compliance controls.

### Amendment

Add the following to Section 3 (Drift Classification) of
`docs/docs/16_DriftDetectionStandard.qmd`:

---

## DRIFT-BOUNDARY (Class 6)

**Definition:** A feature, capability, or data flow that is nominally
within the authorized system boundary and appears available in
administrative interfaces, but is functionally unavailable or produces
no operational data due to one or more of the following:

1. **Telemetry dependency conflict:** The feature requires a telemetry
   pipeline (e.g., Windows DiagTrack, Azure Monitor Agent) that
   FedRAMP compliance controls correctly block or restrict.

2. **Undocumented CSP restriction:** The cloud service provider has
   restricted the feature for government tenant types without clear
   documentation in the service description.

3. **Planning-phase unavailability:** The feature is on the CSP's
   government roadmap but has not yet been delivered, creating a
   gap between what the SSP may claim and what actually functions.

4. **Cross-boundary telemetry flow:** The feature requires data to
   flow to a system or service outside the authorized FedRAMP
   boundary, making it incompatible with the authorization.

**Key distinction from other classes:**

| Class | Drift location | Correctable by tenant? |
|---|---|---|
| DRIFT-SCHEMA | Repository/tenant schema | Yes |
| DRIFT-SEMANTIC | Data value inconsistency | Yes |
| DRIFT-PROVENANCE | Missing attribution | Yes |
| DRIFT-AUTHZ | Authorization deviation | Yes |
| DRIFT-IDENTITY | Identity object state | Yes |
| **DRIFT-BOUNDARY** | **CSP infrastructure** | **No — requires CSP action or compensating control** |

DRIFT-BOUNDARY findings cannot be auto-remediated. They require either:
- A compensating control that provides equivalent governance capability
  within the authorized boundary, OR
- Formal AO risk acceptance documented in the SSP, OR
- Resolution by Microsoft delivering government support for the feature.

**Severity classification:**

| Impact | Severity | Example |
|---|---|---|
| Active security control | P1 | Device Health Attestation unavailable |
| Operational visibility | P2 | Endpoint Analytics empty |
| Compliance documentation | P2 | SSP claims unavailable feature |
| Feature capability | P3 | Location fence unavailable |
| Analytics only | P3 | Workbooks absent |

**Detection mechanism:**

DRIFT-BOUNDARY findings are produced by the `gcc-boundary-probe-v1`
adapter, which performs functional testing of Microsoft features within
the tenant on a weekly schedule. The probe distinguishes between:

- `SILENTLY_BLOCKED` — API accessible, data pipeline blocked
- `EXPLICITLY_UNAVAIL` — documented as unavailable for government
- `PLANNING_PHASE` — on Microsoft roadmap, not yet delivered
- `FUNCTIONAL` — works as documented

**Registry artifact:**

All DRIFT-BOUNDARY findings are recorded in the canonical
`gcc-boundary-gap-registry.yaml` with:
- NIST 800-53 control mapping
- Compensating control reference
- ATO documentation guidance
- KSI signal set integration

This registry is a formal ATO artifact that feeds the SSP
inherited controls section and continuous monitoring evidence base.

**Remediation states:**

| State | Meaning |
|---|---|
| COMPENSATED | UIAO provides equivalent in-boundary capability |
| GAP_UNMITIGATED | No compensating control — AO risk acceptance required |
| FUNCTIONAL | Feature operational — no drift |
| MONITORING | Previously blocked, now functional — under observation |

---

### Walker Integration

The substrate walker (`uiao substrate walk`) includes DRIFT-BOUNDARY
in its output when the gcc-boundary-probe adapter has been run.
DRIFT-BOUNDARY findings with severity P1 set `report.blocking = True`
and cause `uiao substrate drift` to return exit code 1 when
`GAP_UNMITIGATED` P1 gaps exist without documented AO acceptance.
