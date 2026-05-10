# IMAGE-PROMPTS — Modernization Specs

<!-- Maintained by docs/customer-documents authors. Pipeline:
     scripts/generate_images.py harvests [IMAGE-NN: ...] placeholders
     from each domain's <domain>.qmd, refreshes this sidecar, and emits
     PNGs into per-domain images/ directories. -->

## identity — IMAGE-01

Identity modernization domain diagram. Center shows the canonical
Identity Plane as a labeled rectangle with sub-zones for Attributes,
Computed Groups, Delegation, and Authentication context. Around the
perimeter, four modernization adapter slots labeled (entra-id,
active-directory, piv-usaccess, attribute-services) connect with
bidirectional arrows to the central plane. Below the plane, a thin
horizontal bar labeled "AODIM canonical attribute set: assignment
scope, organizational role, classification clearance" anchors the
model. Clean engineering blueprint style, dark navy (#0D1B2E) and teal
(#1E8C8C) on white background. No photographs, purely diagrammatic.

## cloud — IMAGE-01

Cloud modernization domain diagram. Center shows the GCC-Moderate
authorization boundary as a labeled rectangle. Inside the boundary:
M365 GCC-Moderate, Azure Government, in-boundary adapter slots
(intune, m365, entra-id, scubagear). Outside the boundary on the
right: two named Commercial exceptions per ADR-059 — Amazon Connect
(FedRAMP Moderate / AWS GovCloud), SailPoint NERM (FedRAMP Moderate /
AWS GovCloud). Each exception is connected to the boundary by a
labeled arrow showing its authorizing ADR. Below the diagram, a
footer band reads "gcc-boundary schema: discrete enum values per
ADR". Clean engineering blueprint style, dark navy (#0D1B2E) and teal
(#1E8C8C) on white background. No photographs, purely diagrammatic.

## zero-trust — IMAGE-01

Zero Trust modernization domain diagram. Five vertical pillar columns
labeled Identity, Devices, Networks, Applications & Workloads, Data —
each with one or two adapter slot icons (e.g. entra-id, intune,
scubagear, evidence pipeline). At the top of each column, a small
ZTMM maturity bar shows current substrate posture (teal for
Initial-to-Advanced, dashed extension for Optimal target). At the
base, a horizontal "Identity-as-root-namespace" bar runs across all
five columns, showing identity-plane primacy. Clean engineering
blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) on white
background. No photographs, purely diagrammatic.

## telemetry — IMAGE-01

Telemetry domain pipeline diagram. Horizontal flow from left to
right: Adapter Boundary (telemetry capture) → Provenance Envelope
Wrapper (canonical claim normalization) → Bundle Assembler (per
ADR-016 lifecycle) → OSCAL Emission (SSP / POA&M / KSI / Component
Definition). Below the pipeline, a "Determinism Guards" footer band
lists the four ADR-006 properties (no silent drops, append-only,
ordered, idempotent). To the right of the pipeline, a small panel
showing per-adapter retention contract per modernization-registry
entry. Clean engineering blueprint style, dark navy (#0D1B2E) and
teal (#1E8C8C) on white background. No photographs, purely
diagrammatic.

## sase — IMAGE-01

SASE modernization domain diagram. Center shows the six-plane
architecture as a vertical stack (Identity at top down to Management
at bottom). On the right side, three SASE service icons (CASB, SWG,
ZTNA) connect into the Network and Security & Compliance planes. On
the left side, an "Identity-derived addressing" arrow flows from the
Identity plane down through the Addressing plane into the Network
plane. Below the diagram, a footer band reads "SASE = identity-driven
overlay; perimeter VPN replaced by certificate-anchored access". Clean
engineering blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C)
on white background. No photographs, purely diagrammatic.

## sdwan — IMAGE-01

SD-WAN modernization domain diagram. Center shows three transport
lanes (MPLS, Internet, LTE/5G) feeding a central SD-WAN orchestrator.
Above the orchestrator, an arrow incoming from the Identity plane
labeled "identity-aware policy". Below the orchestrator, an arrow
outgoing to the Telemetry plane labeled "path/policy telemetry as
canonical claims". On the right, a "Drift findings" lane showing
canonical claim emissions for routing decisions, SLA breaches, and
policy mismatches. Clean engineering blueprint style, dark navy
(#0D1B2E) and teal (#1E8C8C) on white background. No photographs,
purely diagrammatic.
