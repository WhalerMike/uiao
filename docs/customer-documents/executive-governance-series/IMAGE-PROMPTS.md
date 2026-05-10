# IMAGE-PROMPTS — Executive Governance Series

<!-- Maintained by docs/customer-documents authors. Pipeline:
     scripts/generate_images.py harvests [IMAGE-NN: ...] placeholders
     from each chapter's index.qmd directly. Chapters live in subdirs
     (chNN-*/index.qmd) so this sidecar opts out of file-level companion
     binding; per-chapter prompts are catalogued here as documentation. -->
<!-- companion: none -->

## ch01-why-governance-fails — IMAGE-01

Diagram showing four common governance failure modes as silos. Four
vertical columns labeled Fragmented Identity, Uncorrelated Telemetry,
Point-in-Time Evidence, Tool-Shaped Policy — each shows a tool-stack
icon with broken connections (red dashes). Below the silos, a
horizontal bar labeled "Missing Substrate" emphasizes the absent
connecting layer. Clean engineering blueprint style, dark navy
(#0D1B2E) and teal (#1E8C8C) on white background, with red (#C74040)
reserved for the broken connections. No photographs, purely
diagrammatic.

## ch02-compliance-paradox — IMAGE-01

Compliance paradox curve diagram. Horizontal axis labeled "Time",
vertical axis labeled "Substrate truth (vs reported state)". Two
curves diverge: a teal curve labeled "Reported compliance state" stays
flat (high), and a navy curve labeled "Actual substrate state" trends
downward over time. The widening gap between curves is shaded red and
labeled "Accumulated risk". A dashed vertical line at the right edge
labeled "Audit cycle" shows where the gap is rediscovered. Clean
engineering blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) on
white background, with red (#C74040) reserved for the risk-gap
shading. No photographs, purely diagrammatic.

## ch03-drift-as-primary-threat — IMAGE-01

Drift threat hierarchy diagram. A central dark navy bar labeled
"Substrate Drift — the primary governance threat" anchors the page.
Above it, four smaller threat categories (phishing, supply chain,
insider risk, configuration error) shown as boxes with arrows pointing
down at the central bar — indicating "drift is the substrate-level
threat the others manifest through". Below the central bar, the five
UIAO drift classes (SCHEMA, SEMANTIC, PROVENANCE, AUTHZ, IDENTITY)
shown as a horizontal taxonomy strip in teal. Clean engineering
blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) on white
background. No photographs, purely diagrammatic.

## ch04-deterministic-governance — IMAGE-01

Deterministic governance reproducibility diagram. Two parallel
pipeline rows. Top row labeled "Original assembly" shows: Canon vN +
Inputs(t1) → Substrate Pipeline → Evidence Bundle (hash: 0x4f2c…).
Bottom row labeled "Independent re-assembly (months later)" shows:
Canon vN + Inputs(t1) → Substrate Pipeline → Evidence Bundle (hash:
0x4f2c…). Both bundle-hash values shown identical, with a verification
check icon between them. A separate side panel highlights the four
ADR-006 properties: no silent drops, append-only writes, ordered
records, idempotent ingestion. Clean engineering blueprint style, dark
navy (#0D1B2E) and teal (#1E8C8C) on white background. No
photographs, purely diagrammatic.

## ch05-adapter-model — IMAGE-01

Dual-axis adapter taxonomy diagram. A 2-by-5 matrix. Rows are the two
adapter classes — Modernization (change-making) and Conformance
(read-only observation). Columns are the five mission classes —
Identity, Telemetry, Policy, Enforcement, Integration. Filled cells
show example adapters in each combination (e.g. Modernization ×
Identity: bluecat-address-manager; Conformance × Policy: scubagear).
Below the matrix, four canon invariants are labeled as a footer band:
gcc-boundary: gcc-moderate, ssot-mutation: never-without-modernization-
class, certificate-anchored: true, object-identity-only: true. Clean
engineering blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) on
white background. No photographs, purely diagrammatic.

## ch06-evidence-over-attestation — IMAGE-01

Attestation-versus-evidence-stack diagram. Two parallel vertical
stacks. Left stack labeled "Attestation primary" shows a thin "machine
evidence" base topped by a thick "human attestation" cap; an arrow
shows the human cap as the primary artifact. Right stack labeled
"Evidence primary (UIAO)" shows a thick "canonical machine evidence"
base with a thin "human review" cap; an arrow shows the evidence base
as the primary artifact. A footer line emphasizes "human review
remains, but is not load-bearing for verification". Clean engineering
blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) on white
background. No photographs, purely diagrammatic.

## ch07-operational-tempo — IMAGE-01

Operational tempo cadence diagram. A horizontal time axis with four
parallel lanes labeled by SLA tier: P1 (Immediate, red), P2 (1 hour,
amber), P3 (24 hours, yellow), P4 (72 hours, teal). Each lane shows
event markers — drift findings — at characteristic intervals, with
arrow markers indicating remediation completion within the SLA. A
vertical "now" line on the right edge shows the substrate's
continuous-detection posture; findings to the left of "now" should be
remediated; findings to the right are future detections waiting to
fire. Clean engineering blueprint style, dark navy (#0D1B2E) and teal
(#1E8C8C) primary, with the four severity colors used only on lane
headers. No photographs, purely diagrammatic.

## ch08-governance-at-scale — IMAGE-01

Substrate scaling diagram. Three concentric layers. Innermost (small)
layer labeled "Canon (small, stable, ADR-governed)" with a single
tight ring. Middle layer labeled "Policy mappings (large,
registry-managed)" with a broader ring filled with many small
registry-entry icons. Outermost layer labeled "Runtime adapters
(per-tool, per-program)" with the broadest ring filled with adapter
icons fanning outward. Arrows indicate "small canon → many mappings →
many adapters" as the scaling vector. Clean engineering blueprint
style, dark navy (#0D1B2E) and teal (#1E8C8C) on white background. No
photographs, purely diagrammatic.

## ch09-governance-operating-system — IMAGE-01

Synthesis diagram showing eight chapters as inputs feeding into a
single Governance OS box. Eight labeled arrows enter from the left
side: ch01 Why Governance Fails / ch02 Compliance Paradox / ch03
Drift / ch04 Deterministic Governance / ch05 Adapter Model / ch06
Evidence over Attestation / ch07 Operational Tempo / ch08 Governance
at Scale. The central box is labeled "UIAO Governance OS" and shows
three core layers (Canon SSOT, Substrate Services, Consumer Surfaces).
Three outputs flow out the right: ATO-package-ready evidence, drift
findings as continuous signal, modernization-anchored adapters. Clean
engineering blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) on
white background. No photographs, purely diagrammatic.
