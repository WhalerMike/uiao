# IMAGE-PROMPTS — Validation Suites / Domains

<!-- Maintained by docs/customer-documents authors. Pipeline:
     scripts/generate_images.py harvests [IMAGE-NN: ...] placeholders
     from each domain's <domain>.qmd directly. Domain suites live in
     subdirs (<domain>/<domain>.qmd) so this sidecar opts out of
     file-level companion binding; per-domain prompts are catalogued
     here as documentation. -->
<!-- companion: none -->

## identity — IMAGE-01

Identity validation suite diagram. Center shows a "Conformance Gate"
rectangle. Inputs flow in from the left as four test categories:
Schema Conformance, Provenance Chain Integrity, Drift Detection
Coverage, Boundary Enforcement. Each test category lists 3-5 specific
checks underneath. Outputs flow out the right as a Pass/Fail signal
plus the canonical claim emission "domain-conformance-evidence".
Below the gate, a footer band shows the four canon invariants that
must hold. Clean engineering blueprint style, dark navy (#0D1B2E) and
teal (#1E8C8C) on white background. No photographs, purely
diagrammatic.

## cloud — IMAGE-01

Cloud validation suite diagram. Center shows a "Boundary Conformance
Gate" rectangle with the GCC-Moderate boundary line running vertically
through it. Test categories enter from the left: Endpoint Resolution,
Boundary Disposition, Schema Conformance, Drift Coverage. On the
right, a "Pass / Fail / Exception ADR Required" outcome panel. Below
the gate, a footer band lists the named exceptions per ADR-059
(Amazon Connect, SailPoint NERM). Clean engineering blueprint style,
dark navy (#0D1B2E) and teal (#1E8C8C) on white background. No
photographs, purely diagrammatic.

## zero-trust — IMAGE-01

Zero Trust validation suite diagram. Five vertical pillar columns
labeled Identity, Devices, Networks, Applications & Workloads, Data.
Each column shows a small conformance checkmark or gap badge for the
substrate-baseline tests. Across the bottom, a horizontal "Identity-
as-root-namespace conformance gate" runs through all five columns.
To the right, a panel showing "Decision-record emission shape:
provenance + zt_decision claim". Clean engineering blueprint style,
dark navy (#0D1B2E) and teal (#1E8C8C) on white background. No
photographs, purely diagrammatic.

## telemetry — IMAGE-01

Telemetry validation suite diagram. A horizontal pipeline runs from
Capture → Normalize → Assemble → Seal → Submit. Below the pipeline,
four "Determinism check" gates are placed at each stage, each labeled
with one ADR-006 property: no silent drops, append-only, ordered,
idempotent. To the right of the pipeline, a "Re-execution test"
panel shows the same pipeline rerun with input(t1) producing the same
bundle hash. Clean engineering blueprint style, dark navy (#0D1B2E)
and teal (#1E8C8C) on white background. No photographs, purely
diagrammatic.

## sase — IMAGE-01

SASE validation suite diagram. Center shows a SASE PDP/PEP node.
Inputs from the left: Identity Claim (from identity plane), Resource
Scope, Certificate Thumbprint, Policy Refs. Output to the right:
SASE decision record (permit / deny / escalate) with full provenance
envelope. Above the PDP, a small "Conformance gates" badge bar lists
the four test categories. Below, a footer band reads "SASE = identity-
driven, certificate-anchored, decision-recorded". Clean engineering
blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) on white
background. No photographs, purely diagrammatic.

## sdwan — IMAGE-01

SD-WAN validation suite diagram. Center shows three transport lanes
(MPLS, Internet, LTE/5G) feeding a central SD-WAN orchestrator. Above
the orchestrator, a "Conformance Gate" rectangle with four test
categories listed: Decision-record schema, Boundary disposition,
Telemetry-as-control, Drift coverage. Below, a footer band reads
"Each routing decision = canonical claim + provenance envelope".
Clean engineering blueprint style, dark navy (#0D1B2E) and teal
(#1E8C8C) on white background. No photographs, purely diagrammatic.
