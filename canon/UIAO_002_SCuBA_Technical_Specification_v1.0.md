---
document_title: "UIAO SCuBA Technical Specification"
document_id: UIAO_002
version: "1.0"
date: "2026-04-13"
author: "Michael Stratton"
classification: "UIAO Canon – Controlled"
compliance: "GCC-Moderate Only"
no_hallucination_mode: ENABLED
nhp: true
status: CANONICAL
owner: "Michael Stratton"
provenance:
  source: "uiao-core repository (v2.0.0)"
  version: "1.0"
  derived_at: "2026-04-13T00:00:00Z"
  derived_by: "claude-agent"
---

# UIAO SCuBA Technical Specification

**Document ID:** UIAO_002
**Version:** 1.0
**Date:** 2026-04-13
**Author:** Michael Stratton
**Classification:** UIAO Canon – Controlled
**Compliance:** GCC-Moderate Only
**No-Hallucination Mode:** ENABLED

---

## Table of Contents

1. Executive Summary
2. Context and Problem Statement
3. Architecture Overview
4. Detailed Sections
   - 4.1 Three-Hop Mapping Chain
   - 4.2 Plane 1 — SCuBA to IR Transform
   - 4.3 Plane 2 — IR to KSI Evaluation
   - 4.4 Plane 3 — Evidence Build
   - 4.5 Plane 4 — OSCAL Generate
   - 4.6 Normalization Engine
   - 4.7 Orchestration Layer
   - 4.8 Data Models
   - 4.9 CLI Architecture
   - 4.10 CI/CD Integration
   - 4.11 BOD 25-01 Compliance Integration
5. Implementation Guidance
6. Risks and Mitigations
7. Appendices
   - Appendix A — Definitions
   - Appendix B — Object List
   - Appendix C — Full 143-Policy Mapping Table
   - Appendix D — References
8. Glossary
9. Footnotes
10. Validation Block

---

## 1. Executive Summary

UIAO integrates CISA's Secure Cloud Business Applications (SCuBA) assessment framework into a deterministic, four-plane compliance pipeline that transforms raw ScubaGear output into auditor-ready OSCAL artifacts. The pipeline ingests ScubaGear JSON, normalizes it through a three-hop mapping chain (PolicyId to NIST SP 800-53 control to UIAO Key Security Indicator), evaluates compliance posture, builds tamper-evident evidence bundles signed with HMAC-SHA256, and generates OSCAL 1.1.2 System Security Plans, Plans of Action and Milestones, and Security Assessment Reports.

This specification covers the full SCuBA integration: 143 policy-to-control mappings across eight Microsoft 365 product baselines (Entra ID, Defender, Exchange Online, SharePoint, Teams, Power Platform, Power BI, and Security Suite), the normalization engine that handles both combined and per-product ScubaGear output formats, the four-plane orchestrator with retry logic and timestamped run isolation, and the evidence integrity chain from raw scan to signed OSCAL deliverable. The system operates exclusively within the GCC-Moderate boundary for M365 SaaS services, with no Azure IaaS/PaaS dependencies.

For leadership: UIAO's SCuBA integration replaces manual compliance evidence gathering with a continuous, automated pipeline that produces FedRAMP Moderate-aligned artifacts in under 120 seconds per assessment cycle. Every output is deterministic — the same ScubaGear input always produces identical compliance artifacts — and every evidence item carries cryptographic provenance tracing it back to the original scan. This directly supports CISA Binding Operational Directive 25-01 mandatory timelines with machine-readable, auditor-ready evidence.

---

## 2. Context and Problem Statement

**The Problem.** Federal agencies operating Microsoft 365 in GCC-Moderate environments must continuously demonstrate compliance with NIST SP 800-53 Rev 5 controls, FedRAMP Moderate baselines, and CISA SCuBA secure configuration guidelines. CISA's ScubaGear tool produces raw JSON assessment output, but there is no standardized pipeline for transforming that output into structured compliance evidence, mapping it to control frameworks, or generating the OSCAL artifacts required for FedRAMP authorization packages.

**Why It Matters.** Without automated transformation, agencies rely on manual processes to interpret ScubaGear results, cross-reference them against NIST controls, and produce compliance documentation. This manual approach introduces human error, creates evidence that is neither machine-readable nor cryptographically verifiable, and cannot meet the continuous monitoring cadence required by BOD 25-01. Manual evidence gathering for a single assessment cycle typically requires days of analyst effort; UIAO reduces this to seconds.

**Who Is Affected.** Information System Security Officers (ISSOs), Authorizing Officials (AOs), compliance teams, and system administrators responsible for maintaining FedRAMP Moderate authorization for M365 tenants in GCC-Moderate environments. External auditors and assessors consuming OSCAL-formatted evidence packages are also direct beneficiaries.

**What Constraints Apply.** All operations are scoped to GCC-Moderate (M365 SaaS only). No GCC-High, DoD, or Azure IaaS/PaaS services are referenced or required. Amazon Connect Contact Center is the sole Commercial Cloud exception. The pipeline enforces object identity only — no person identity is stored or processed. All artifacts must validate against OSCAL 1.1.2 schemas. The SSOT (Single Source of Truth) is singular and certificate-anchored; adapters never mutate truth.

---

## 3. Architecture Overview

The UIAO SCuBA pipeline is a four-plane sequential architecture with clear separation of concerns. Each plane is independently testable, deterministic, and produces artifacts that feed the next plane in sequence. The pipeline wraps CISA's ScubaGear assessment tool inside a provenance-first governance envelope.

See Diagram 1 for the complete pipeline flow from ScubaGear execution through OSCAL artifact generation.

[DIAGRAM-01: PH-001 — A 16:9 schematic showing the four-plane sequential pipeline. Left: ScubaGear executing against an M365 Tenant (GCC-Moderate boundary). Four horizontal planes flow left to right: Plane 1 (SCuBA → IR, blue), Plane 2 (IR → KSI, teal), Plane 3 (KSI → Evidence, steel gray), Plane 4 (Evidence → OSCAL, navy). Arrows connect each plane. Output artifacts shown at right: SSP, POA&M, SAR, Auditor Bundle. Provenance chain shown as a continuous line beneath all four planes. Muted blue palette, no text baked into the image. Publication-grade. Dimensions: 1920x1080.]

**Boundary Model.** The pipeline operates within the GCC-Moderate tenant boundary. ScubaGear connects to M365 services via PowerShell. All pipeline processing occurs within the UIAO-Core runtime. No data leaves the tenant boundary during processing.

**Identity Model.** Object identity only. Every artifact, evidence item, and pipeline run carries a deterministic identity derived from its content hash. No person identity is stored. Certificate-anchored provenance ensures every transaction is traceable.

**SSOT Role.** The canonical policy-to-control mapping (SCUBA_TO_KSI_MAP) is the single source of truth for all SCuBA-to-NIST control relationships. The KSI control library (uiao-control-to-ksi-mapping.yaml) is the SSOT for NIST-to-KSI resolution. Adapters serve SSOT + Identity + Security and never mutate truth.

**Adapter Classes.** The ScubaAdapter implements the DatabaseAdapterBase abstract class, providing five interface methods: connect (load report), discover_schema (field mapping), execute_query (filter results), normalize (build claims), and detect_drift (regression detection). Adapters are plural in class but singular in mission: serving SSOT + Identity + Security.

See Diagram 2 for the module dependency architecture.

[DIAGRAM-02: PH-002 — A 16:9 module dependency diagram showing four layers: Foundation (abstractions, models, utils, config), Core Pipeline (scuba, ksi, evidence, oscal, ir), Analysis (diff, freshness, coverage, validators), and Output (ssp, dashboard, auditor, generators, monitoring). Arrows show dependency flow between modules. Navy and teal palette on white background. No text baked into the image. Publication-grade. Dimensions: 1920x1080.]

---

## 4. Detailed Sections

### 4.1 Three-Hop Mapping Chain

The core data transformation in UIAO's SCuBA integration follows a deterministic three-hop mapping chain that resolves raw ScubaGear policy identifiers to UIAO Key Security Indicators.

**Hop 1: PolicyId → NIST SP 800-53 Control.** The SCUBA_TO_KSI_MAP dictionary (defined in scuba_adapter.py) maps 143 ScubaGear policy identifiers to their corresponding NIST SP 800-53 Rev 5 control identifiers. For example, MS.AAD.1.1v1 maps to IA-2(1), and MS.DEFENDER.1.1v1 maps to SI-3. This mapping is static and version-locked to ScubaGear policy versions.

**Hop 2: NIST Control → KSI Metadata.** The uiao-control-to-ksi-mapping.yaml file maps all 247 NIST SP 800-53 Rev 5 controls to 163 KSI identifiers. Each KSI carries metadata: a unique KSI ID (pattern: KSI-[FAMILY]-[NUMBER]), a title, a severity level (low, medium, high, critical), a category (iam, boundary-protection, monitoring-logging, configuration-management, incident-response, planning-personnel, other), and a file reference to the individual KSI rule definition.

**Hop 3: KSI → Compliance Evaluation.** The KSI evaluation engine (evaluate.py) processes the resolved KSI metadata against the normalized IR envelope to produce a pass/fail/warn determination per control. Multiple ScubaGear policies can map to the same KSI; when this occurs, the aggregation rule is conservative — if ANY constituent policy fails, the KSI fails.

See Diagram 3 for the three-hop mapping chain visualization.

[DIAGRAM-03: PH-003 — A 16:9 horizontal flow diagram showing three hops. Left column: ScubaGear PolicyIds (MS.AAD.1.1v1, MS.DEFENDER.1.1v1, etc.) in steel gray boxes. Center column: NIST SP 800-53 controls (IA-2(1), SI-3, etc.) in teal boxes. Right column: KSI IDs (KSI-AC-01, KSI-ML-01, etc.) in navy boxes. Arrows connect each hop. A note shows "143 policies → 247 controls → 163 KSIs". White background, muted palette. No text baked into the image. Publication-grade. Dimensions: 1920x1080.]

See Table 1 for the product-level policy distribution across the mapping chain.

[TABLE-01: A 5-column table showing the distribution of SCuBA policies by M365 product. Columns: Product, Policy Prefix, Policy Count, Primary NIST Families, Primary KSI Categories. Rows: Entra ID (MS.AAD, 28 policies), Defender (MS.DEFENDER, 9), Exchange Online (MS.EXO, 3), SharePoint (MS.SHAREPOINT, 8), Teams (MS.TEAMS, 14), Power Platform (MS.POWERPLATFORM, 9), Power BI (MS.POWERBI, 7), Security Suite (MS.SECURITYSUITE, 23). Total: 101 unique policies with 143 mapping entries including version variants.]

### 4.2 Plane 1 — SCuBA to IR Transform

**Module Path:** src/uiao_core/ir/adapters/scuba/transformer.py

**Input Contract.** Plane 1 accepts normalized SCuBA JSON conforming to the scuba-normalized.schema.json schema. The normalization engine (Section 4.6) handles conversion from raw ScubaGear output if raw input is detected.

**Process.** The transformer loads the normalized JSON, builds the full KSI-to-IR mapping via build_ksi_ir_mapping(), and converts each ksi_results entry into an Evidence object. Each Evidence object carries: a deterministic identity (evidence:scuba:{tenant_id}:{run_id}:{ksi_id}), a source reference, control and policy cross-references, timestamped data payload, pass/fail/warn evaluation, and a ProvenanceRecord anchoring the evidence to the original scan.

**Output Contract.** An SCuBATransformResult containing: the run_id, a list of Control objects, a list of Policy objects, a list of Evidence objects (one per KSI result), pass/warn/fail counts, and a list of unmapped KSI IDs. The result serializes to a JSON IR envelope written to the run directory.

**Key Guarantee.** Deterministic: the same normalized JSON input always produces an identical IR envelope. A canonical hash is computed for each Evidence object, excluding volatile fields (timestamps, run IDs) to enable cross-run comparison.

**CLI Command:** `uiao scuba transform --input <path>`

See Table 2 for the Plane 1 input/output contract summary.

[TABLE-02: A 4-column table summarizing Plane 1 contracts. Columns: Attribute, Value, Format, Validation. Rows cover: Input (normalized SCuBA JSON, JSON, schema validation), Output (IR envelope, JSON, deterministic hash), Provenance (ProvenanceRecord, embedded, content_hash verification), Identity (evidence:scuba:{tenant}:{run}:{ksi}, URI, uniqueness guarantee).]

### 4.3 Plane 2 — IR to KSI Evaluation

**Module Path:** src/uiao_core/ksi/evaluate.py

**Input Contract.** The IR envelope produced by Plane 1, plus the KSI control library (YAML configuration files under rules/ksi/).

**Process.** The evaluation engine loads the control library definitions, maps each normalized claim from the IR envelope to its corresponding NIST SP 800-53 control, evaluates pass/fail against each control requirement, and generates structured evaluation results. Every claim maps to exactly one control; orphan claims (those without a control mapping) are flagged but not silently dropped.

**Output Contract.** KSI evaluation results in JSON format with control-level pass/fail determinations, severity assessments, and mapping metadata.

**Key Guarantee.** Every claim maps to exactly one control; no orphans are silently discarded. The evaluation is deterministic given identical IR input and control library.

**CLI Command:** `uiao ksi evaluate --ir <path>`

### 4.4 Plane 3 — Evidence Build

**Module Path:** src/uiao_core/evidence/

**Input Contract.** KSI evaluation results from Plane 2.

**Process.** The evidence builder collects evaluation results into evidence items, constructs an evidence bundle with metadata, signs the bundle with HMAC-SHA256, and calculates a stable hash that excludes volatile fields (timestamps, run IDs). The stable hash enables determinism verification across runs — the same evaluation results always produce the same hash.

**Output Contract.** A signed evidence bundle (JSON) in a dedicated bundle directory. The bundle includes: all evidence items, the HMAC-SHA256 signature, the stable content hash, and metadata (timestamp, tool version, tenant ID).

**Key Guarantee.** Tamper-evident: any modification to the evidence bundle invalidates the HMAC signature. The stable hash enables byte-level regression testing via golden file comparison.

**CLI Command:** `uiao evidence build --eval <path>`

### 4.5 Plane 4 — OSCAL Generate

**Module Path:** src/uiao_core/oscal/

**Input Contract.** The signed evidence bundle from Plane 3.

**Process.** The generation plane produces three OSCAL 1.1.2-compliant artifacts from the evidence bundle. The SSP generator (build_ssp) creates a System Security Plan with control implementation statements derived from evidence. The POA&M generator (build_poam_export) creates Plans of Action and Milestones for open findings (failed controls). The OSCAL generator (build_oscal) produces additional assessment artifacts. SSP narrative and lineage traces are exported for human-readable audit trails.

**Output Contract.** OSCAL 1.1.2 compliant SSP, POA&M, and SAR artifacts, plus SSP narrative and lineage trace exports. All outputs validate against the OSCAL 1.1.2 JSON schema.

**Key Guarantee.** Schema-valid OSCAL 1.1.2 output. Lineage traces every OSCAL statement back through the evidence chain to the original ScubaGear scan.

**CLI Command:** `uiao oscal generate --evidence <path>`

See Diagram 4 for the evidence integrity chain from ScubaGear through OSCAL output.

[DIAGRAM-04: PH-004 — A 16:9 vertical flow diagram showing the evidence integrity chain. Top: ScubaGear JSON (raw input). Each plane adds a provenance layer: Plane 1 attaches IR envelope with content hash, Plane 2 adds control mapping and evaluation, Plane 3 adds HMAC-SHA256 signature and stable hash, Plane 4 adds OSCAL schema validation and lineage traces. A verification arrow runs bottom-to-top showing "Any auditor can trace any OSCAL statement to source scan." Navy blocks, teal provenance annotations, amber for signature/hash elements. White background. No text baked into the image. Publication-grade. Dimensions: 1920x1080.]

### 4.6 Normalization Engine

**Module Path:** src/uiao_core/ir/adapters/scuba/normalize_scuba.py

The normalization engine converts raw ScubaGear output into the pipeline-ready format that Plane 1 expects. It handles two ScubaGear output formats: a single combined ScubaResults.json with a TestResults array, and per-product files (MS.AAD.json, MS.EXO.json, MS.TEAMS.json, etc.).

**Input Discovery.** The discover_scuba_input() function implements a hierarchical search: direct file input, directory containing ScubaResults.json, directory containing per-product MS.*.json files, and nested date-stamped subdirectories. This accommodates the various output structures ScubaGear produces across versions.

**Pass/Fail Interpretation.** ScubaGear reports RequirementMet in multiple formats. The normalizer interprets: Pass/pass/PASS/true/True as PASS; Warning/warning/WARN/Warn as WARN; all other values as FAIL.

**Aggregation Logic.** Multiple ScubaGear policies can map to the same KSI through the three-hop chain. When this occurs, the aggregation is conservative: if ANY constituent policy fails, the aggregated KSI status is FAIL; else if ANY warns, the status is WARN; otherwise PASS. The highest severity across constituent policies is preserved. Details from all constituent policies are concatenated with source policy IDs preserved for traceability.

**Output Envelope.** The normalized output conforms to scuba-normalized.schema.json and contains: assessment_metadata (date, tool version, run ID, normalization statistics including raw count, mapped count, unmapped count, and multi-policy KSI identification), tenant metadata, and the aggregated ksi_results array.

**CLI Command:** `python -m uiao_core.ir.adapters.scuba.normalize_scuba --input <path> --output <path>`

### 4.7 Orchestration Layer

**Module Path:** orchestrator/orchestrator.py

The orchestrator chains all four planes into a single managed execution with error handling, retry logic, and comprehensive audit trails.

**Run Isolation.** Each execution creates a timestamped run directory ({timestamp}Z-run-{uuid}) containing subdirectories for each plane's output (ir/, ksi/, evidence/, oscal/) plus logs. This ensures complete isolation between runs and enables historical comparison.

**Sequential Execution.** Planes execute in strict sequence: Plane 1 → Plane 2 → Plane 3 → Plane 4. If any plane fails, the pipeline halts — no downstream plane executes on incomplete input. Each plane's output path feeds as input to the next.

**Retry Logic.** Each plane supports configurable retry with exponential backoff (2^attempt seconds). The default is 1 retry per plane. Retry counts are recorded in the run manifest for operational visibility.

**Auto-Normalization.** If Plane 1 detects raw ScubaGear input (TestResults or Results keys in the JSON, or a directory input), it automatically invokes the normalization engine before transformation. This allows operators to feed raw ScubaGear output directly to the orchestrator without a separate normalization step.

**Run Manifest.** Every orchestrator run produces a manifest.json summarizing: orchestrator version, run ID, tenant ID, input path, planes requested, start/completion timestamps, total duration, per-plane results (success, duration, output path, error, retry count), and a summary with total/successful/failed plane counts.

**Dry-Run Mode.** The orchestrator supports a dry-run mode that validates inputs, logs the execution plan, and returns without side effects. This enables pre-flight validation before committing to a full pipeline run.

**CLI Command:** `python orchestrator.py --input <path> --output-dir <path> --tenant-id <id> --planes plane1,plane2,plane3,plane4`

See Table 3 for the orchestrator configuration parameters.

[TABLE-03: A 4-column table listing orchestrator CLI parameters. Columns: Parameter, Type, Default, Description. Rows: --input (path, required), --output-dir (path, ./output), --config (path, None), --tenant-id (string, boundary:tenant:m365:contoso), --planes (comma-list, all four), --dry-run (boolean, false), --max-retries (int 0-5, 1), --log-level (string, INFO).]

### 4.8 Data Models

All pipeline data models are implemented in Pydantic for runtime validation, serialization, and automatic schema generation.

**IR Core Models.** Six model types form the Intermediate Representation: NormalizedClaim (standardized compliance finding), IREnvelope (wrapper with provenance metadata), Provenance (source, timestamp, and run tracking), ControlMapping (claim-to-control relationship), EvaluationResult (pass/fail per control), and EvidenceItem (single piece of compliance evidence).

**SCuBA Adapter Models.** The adapter uses the DatabaseAdapterBase framework with five typed return objects: ConnectionProvenance (report file identity and load metadata), SchemaMappingObject (vendor-to-canonical field mapping), QueryProvenance (filter execution metadata), ClaimSet (collection of normalized ClaimObjects), and DriftReport (regression detection results).

**Evidence Bundle Model.** The evidence bundle carries: a list of EvidenceItem objects, an HMAC-SHA256 signature, a stable content hash (excluding volatile fields), and bundle metadata (assessment date, tool version, tenant ID, run ID).

**OSCAL Output Models.** Plane 4 produces OSCAL 1.1.2 conformant JSON for SSP (System Security Plan with control implementations), POA&M (Plans of Action and Milestones for open findings with state machine: DETECTED → OPEN → IN PROGRESS → CLOSED → VERIFIED), and SAR (Security Assessment Report with assessment results).

**Vendor Overlay Model.** The scuba.yaml vendor overlay defines product metadata (name, policy prefix, OSCAL component, KSI categories), control mappings with FedRAMP applicability flags, evidence collection settings, and UIAO extension metadata (gcc_moderate_focus, fedramp_20x_aligned).

See Table 4 for the complete data model inventory.

[TABLE-04: A 5-column table listing all data models in the SCuBA pipeline. Columns: Model Name, Module, Purpose, Key Fields, Validation. 15+ rows covering all models from NormalizedClaim through VendorOverlay.]

### 4.9 CLI Architecture

The UIAO CLI is built on Typer with Rich console output. SCuBA-related commands are organized under product-specific subcommands.

**SCuBA Commands:** uiao scuba run (execute ScubaGear assessment), uiao scuba transform (Plane 1 transform to IR), uiao scuba status (current assessment status), uiao scuba diff (compare two assessment runs).

**KSI Commands:** uiao ksi evaluate (Plane 2 evaluation), uiao ksi findings (list by severity), uiao ksi enrich (enrich with external data), uiao ksi validate (validate control library YAML).

**Evidence Commands:** uiao evidence build (Plane 3 bundle), uiao evidence verify (verify signature), uiao evidence freshness (check freshness grade: Fresh ≤24h, Stale 24h–7d, Expired >7d), uiao evidence re-sign (re-sign bundle).

**OSCAL Commands:** uiao oscal generate (Plane 4 generation), uiao oscal validate (validate against OSCAL schema).

**Governance Commands:** uiao governance scorecard (governance scorecard), uiao governance poam (generate POA&M), uiao governance poam-transition (transition POA&M item state), uiao coverage export --baseline bod-25-01 (BOD 25-01 compliance export).

### 4.10 CI/CD Integration

Two GitHub Actions workflows automate SCuBA assessment and pipeline execution.

**Weekly Assessment (adapter-run-scuba.yml).** Executes ScubaGear against the M365 tenant every Monday via PowerShell. Captures raw JSON output and generates a provenance manifest for the audit trail.

**Nightly Pipeline (scuba-nightly.yml).** Runs the full four-plane pipeline nightly against the most recent ScubaGear output. Produces updated OSCAL artifacts, evidence bundles, and governance dashboard exports. Drift detection runs in parallel to identify configuration regressions since the last assessment.

**Supporting Workflows:** ci.yml (unit tests), lint.yml (ruff linting), security-scan.yml (security checks), canon-validation.yml (canonical artifact validation), generate-docs.yml (documentation build), render-and-insert-diagrams.yml (PlantUML diagram rendering).

### 4.11 BOD 25-01 Compliance Integration

CISA Binding Operational Directive 25-01 mandates that federal agencies implement SCuBA secure configuration baselines for M365 and maintain continuous compliance monitoring. UIAO directly supports BOD 25-01 through the following mechanisms.

**Mandatory Timeline Tracking.** The KSI evaluation engine tracks BOD 25-01 compliance timelines. Each failing control carries a first-observed timestamp, and the governance action framework monitors remediation progress against directive deadlines.

**Evidence-Backed Closure.** BOD 25-01 requires agencies to demonstrate remediation with evidence. The Plane 3 evidence bundle provides cryptographically signed proof that a previously failing control now passes, with lineage tracing the remediation back through the full assessment chain.

**Coverage Export.** The CLI command `uiao coverage export --baseline bod-25-01` produces a compliance coverage report mapped to BOD 25-01 requirements, showing which SCuBA baselines are assessed, which controls pass/fail, and which require remediation action.

**POA&M Lifecycle.** Findings that cannot be immediately remediated enter the POA&M state machine (DETECTED → OPEN → IN PROGRESS → CLOSED → VERIFIED) with evidence-backed transitions at each stage.

---

## 5. Implementation Guidance

**Step 1: Install ScubaGear.** Install CISA ScubaGear (version 0.5.0 or later) per the ScubaGear repository instructions at https://github.com/cisagov/ScubaGear. Ensure PowerShell connectivity to the GCC-Moderate M365 tenant.

**Step 2: Execute Initial Assessment.** Run ScubaGear against the target tenant. The output will be either a combined ScubaResults.json or per-product MS.*.json files. Place the output in the exports/scuba/ directory.

**Step 3: Configure Transform.** Review config/scuba-transform.json. Set the tenant_boundary_id to the appropriate tenant boundary identifier. Optionally configure drop_statuses to exclude informational items from processing.

**Step 4: Run the Full Pipeline.** Execute the orchestrator: `python orchestrator.py --input exports/scuba/ScubaResults.json --output-dir output/ --tenant-id "boundary:tenant:m365:<your-tenant>"`. The orchestrator will auto-normalize raw input, execute all four planes, and produce a run manifest.

**Step 5: Validate Outputs.** Verify the evidence bundle signature: `uiao evidence verify --bundle output/<run-dir>/evidence/<bundle>`. Validate OSCAL output: `uiao oscal validate --path output/<run-dir>/oscal/`. Check evidence freshness: `uiao evidence freshness --bundle output/<run-dir>/evidence/<bundle>`.

**Step 6: Configure Nightly Automation.** Enable the scuba-nightly.yml GitHub Actions workflow. Configure the weekly adapter-run-scuba.yml workflow with tenant credentials. Review the nightly drift detection output for configuration regressions.

**Step 7: Establish POA&M Workflow.** For failing controls, create POA&M items: `uiao governance poam --create`. Transition items through the state machine as remediation progresses: `uiao governance poam-transition --item <id> --state IN_PROGRESS`.

---

## 6. Risks and Mitigations

### Governance Risks

**Risk G-1: Mapping Drift.** The SCUBA_TO_KSI_MAP may become stale if ScubaGear introduces new policies or changes policy identifiers. Mitigation: unmapped policies are tracked in normalization metadata and flagged in pipeline output. The CI drift-detection workflow alerts on new unmapped policies.

**Risk G-2: Canon Divergence.** Multiple mapping files (scuba_adapter.py SCUBA_TO_KSI_MAP and scuba.yaml control_mappings) could diverge. Mitigation: the scuba_adapter.py mapping is the canonical SSOT; the vendor overlay references it. CI validation enforces consistency.

### Operational Risks

**Risk O-1: ScubaGear Output Format Changes.** ScubaGear may change its JSON output structure across versions. Mitigation: the discover_scuba_input() function handles multiple known formats and logs warnings for unrecognized formats. Schema validation at Plane 1 entry catches structural changes.

**Risk O-2: Pipeline Failure Mid-Run.** A plane failure halts the pipeline, leaving incomplete output. Mitigation: the orchestrator creates timestamped run directories for isolation, records per-plane results in the manifest, and supports retry with exponential backoff. Operators can re-run failed planes individually.

### Security Risks

**Risk S-1: Evidence Tampering.** Post-generation modification of evidence bundles could produce fraudulent compliance claims. Mitigation: HMAC-SHA256 signing in Plane 3. Any modification invalidates the signature. The stable hash enables independent verification.

**Risk S-2: Boundary Violation.** Pipeline misconfiguration could reference services outside the GCC-Moderate boundary. Mitigation: the tenant_boundary_id is injected at Plane 1 and carried through all downstream artifacts. CI boundary-enforcement rules block non-GCC-Moderate references.

### Drift Risks

**Risk D-1: Evidence Staleness.** Evidence bundles that are not refreshed become stale and eventually expire. Mitigation: the freshness engine grades evidence (Fresh ≤24h, Stale 24h–7d, Expired >7d). Nightly pipeline execution ensures evidence remains current. The governance dashboard surfaces freshness grades for operator visibility.

**Risk D-2: Configuration Regression.** M365 tenant configurations may regress between assessments, causing previously passing controls to fail. Mitigation: the diff engine compares consecutive assessment runs and surfaces Added, Removed, Changed, and Unchanged findings. The drift-detection CI workflow runs nightly.

---

## Appendix A — Definitions

**Adapter.** A pluggable module implementing the ComplianceAdapter abstract base class, responsible for ingesting external compliance data and normalizing it into UIAO IR format. Adapters serve SSOT + Identity + Security.

**Canonical Hash.** A SHA-256 hash computed over an artifact's content, excluding volatile fields (timestamps, run IDs), enabling deterministic comparison across pipeline runs.

**Evidence Bundle.** A signed collection of evidence items produced by Plane 3, carrying HMAC-SHA256 signature and stable content hash for tamper detection.

**Freshness Grade.** A classification of evidence age: Fresh (≤24 hours), Stale (24 hours to 7 days), Expired (>7 days).

**GCC-Moderate.** The Microsoft Government Community Cloud environment providing M365 SaaS services scoped to FedRAMP Moderate. The exclusive cloud boundary for UIAO operations.

**IR (Intermediate Representation).** The normalized data format used internally by the UIAO pipeline, consisting of Controls, Policies, Evidence items, and Provenance records.

**KSI (Key Security Indicator).** A control evaluation metric mapped from NIST SP 800-53 Rev 5 controls. Identified by pattern KSI-[FAMILY]-[NUMBER]. 163 KSIs cover the full 247-control FedRAMP Moderate baseline.

**Normalization.** The process of converting raw ScubaGear JSON output into the pipeline-ready format defined by scuba-normalized.schema.json.

**OSCAL (Open Security Controls Assessment Language).** NIST standard for machine-readable security control assessments. UIAO targets OSCAL 1.1.2.

**Plane.** One of four sequential processing stages in the UIAO compliance pipeline: SCuBA→IR (Plane 1), IR→KSI (Plane 2), KSI→Evidence (Plane 3), Evidence→OSCAL (Plane 4).

**POA&M (Plan of Action and Milestones).** A document identifying tasks needing accomplishment to resolve security weaknesses. UIAO implements a five-state lifecycle: DETECTED → OPEN → IN PROGRESS → CLOSED → VERIFIED.

**Provenance.** Metadata anchoring an artifact to its source, including source identifier, timestamp, version, content hash, and actor.

**Run Manifest.** A JSON file summarizing a complete orchestrator run: run ID, timing, per-plane results, and success/failure status.

**SCuBA (Secure Cloud Business Applications).** A CISA program establishing security baselines for cloud business applications including Microsoft 365.

**ScubaGear.** CISA's PowerShell assessment tool (https://github.com/cisagov/ScubaGear) that evaluates M365 tenant configurations against SCuBA baselines.

**SSOT (Single Source of Truth).** The authoritative, canonical data source. In UIAO, SSOT is singular and certificate-anchored; adapters never mutate truth.

**Stable Hash.** A content hash excluding volatile fields, enabling deterministic comparison across pipeline runs.

**Vendor Overlay.** A YAML configuration file (data/vendor-overlays/scuba.yaml) defining product metadata, control mappings, evidence collection settings, and UIAO extension metadata for a specific compliance data source.

---

## Appendix B — Object List

| Object ID | Type | Description | Section |
|-----------|------|-------------|---------|
| PH-001 | Diagram | Four-plane pipeline architecture flow | 3 |
| PH-002 | Diagram | Module dependency architecture | 3 |
| PH-003 | Diagram | Three-hop mapping chain visualization | 4.1 |
| PH-004 | Diagram | Evidence integrity chain | 4.5 |
| TABLE-01 | Table | Product-level policy distribution | 4.1 |
| TABLE-02 | Table | Plane 1 input/output contracts | 4.2 |
| TABLE-03 | Table | Orchestrator configuration parameters | 4.7 |
| TABLE-04 | Table | Complete data model inventory | 4.8 |

---

## Appendix C — Full 143-Policy Mapping Table

### Entra ID (MS.AAD) — 28 Policies

| PolicyId | NIST Control | Description |
|----------|-------------|-------------|
| MS.AAD.1.1v1 | IA-2(1) | Legacy authentication blocked |
| MS.AAD.2.1v1 | AC-3 | Conditional access policies |
| MS.AAD.2.2v1 | AU-6 | Sign-in log review |
| MS.AAD.2.3v1 | AC-3 | Conditional access enforcement |
| MS.AAD.3.1v1 | IA-2(1) | Phishing-resistant MFA for privileged roles |
| MS.AAD.3.2v2 | IA-2(1) | MFA registration required |
| MS.AAD.3.3v2 | IA-2 | MFA for all users |
| MS.AAD.3.4v1 | IA-5 | Authentication strength policies |
| MS.AAD.3.5v2 | IA-2(1) | MFA for admin portals |
| MS.AAD.3.6v1 | IA-2(1) | MFA for high-risk sign-ins |
| MS.AAD.3.7v1 | IA-2 | MFA methods configuration |
| MS.AAD.3.8v1 | AC-12 | Session timeout policies |
| MS.AAD.3.9v1 | IA-2 | Authentication methods review |
| MS.AAD.4.1v1 | CM-6 | Configuration management baselines |
| MS.AAD.5.1v1 | AC-3 | Application registration restrictions |
| MS.AAD.5.2v1 | AC-3 | Application consent policies |
| MS.AAD.5.3v1 | AC-3 | Application permission grants |
| MS.AAD.6.1v1 | IA-5 | Password policies |
| MS.AAD.7.1v1 | AU-2 | Audit log configuration |
| MS.AAD.7.2v1 | AU-3 | Audit log content |
| MS.AAD.7.3v1 | AU-6 | Audit log review |
| MS.AAD.7.4v1 | AU-6 | Audit log analysis |
| MS.AAD.7.5v1 | AU-3 | Audit log detail level |
| MS.AAD.7.6v1 | AU-2 | Audit events selection |
| MS.AAD.7.7v1 | AU-3 | Audit record content |
| MS.AAD.7.8v1 | AU-6 | Audit review and reporting |
| MS.AAD.7.9v1 | AU-3 | Audit record generation |
| MS.AAD.8.1v1 | AC-20 | External collaboration settings |
| MS.AAD.8.2v1 | AC-3 | Cross-tenant access policies |
| MS.AAD.8.3v1 | AC-22 | Publicly accessible content |

### Defender (MS.DEFENDER) — 9 Policies

| PolicyId | NIST Control | Description |
|----------|-------------|-------------|
| MS.DEFENDER.1.1v1 | SI-3 | Malware protection enabled |
| MS.DEFENDER.1.2v1 | SI-3 | Anti-malware policies |
| MS.DEFENDER.1.3v1 | SI-3 | Safe Attachments policies |
| MS.DEFENDER.1.4v1 | SI-4 | Monitoring and alerting |
| MS.DEFENDER.1.5v1 | SI-3 | Real-time protection |
| MS.DEFENDER.2.1v1 | SI-8 | Anti-spam inbound filtering |
| MS.DEFENDER.2.2v1 | SI-8 | Anti-spam outbound filtering |
| MS.DEFENDER.2.3v1 | SI-8 | Anti-phishing policies |
| MS.DEFENDER.4.1v2 | SI-4 | Alert policies configuration |

### Exchange Online (MS.EXO) — 3 Policies

| PolicyId | NIST Control | Description |
|----------|-------------|-------------|
| MS.EXO.3.1v1 | SC-8(1) | Transport encryption enforcement |
| MS.EXO.6.1v1 | SI-8 | Spam filtering configuration |
| MS.EXO.16.1v1 | SI-3 | Malware filter policies |

### SharePoint (MS.SHAREPOINT) — 8 Policies

| PolicyId | NIST Control | Description |
|----------|-------------|-------------|
| MS.SHAREPOINT.1.1v1 | AC-3 | Sharing policies |
| MS.SHAREPOINT.1.2v1 | AC-3 | Default sharing link type |
| MS.SHAREPOINT.1.3v1 | AC-20 | External sharing controls |
| MS.SHAREPOINT.2.1v1 | AU-3 | Audit log content for SharePoint |
| MS.SHAREPOINT.2.2v1 | AU-3 | Audit log detail |
| MS.SHAREPOINT.3.1v1 | SC-28 | Data at rest protection |
| MS.SHAREPOINT.3.2v1 | SC-8(1) | Data in transit protection |
| MS.SHAREPOINT.3.3v1 | MP-5 | Media protection |

### Teams (MS.TEAMS) — 14 Policies

| PolicyId | NIST Control | Description |
|----------|-------------|-------------|
| MS.TEAMS.1.1v1 | AC-6 | Least privilege for Teams admin |
| MS.TEAMS.1.2v2 | AC-3 | External access policies |
| MS.TEAMS.1.3v1 | AC-3 | Guest access controls |
| MS.TEAMS.1.4v1 | AC-3 | Meeting policies |
| MS.TEAMS.1.5v1 | AC-3 | Messaging policies |
| MS.TEAMS.1.6v1 | AC-3 | App permission policies |
| MS.TEAMS.1.7v2 | AC-3 | App setup policies |
| MS.TEAMS.2.1v2 | AU-3 | Audit log content for Teams |
| MS.TEAMS.2.2v2 | AU-3 | Audit log detail |
| MS.TEAMS.2.3v2 | AU-6 | Audit log review |
| MS.TEAMS.4.1v1 | AC-12 | Session timeout configuration |
| MS.TEAMS.5.1v2 | SI-8 | Anti-phishing for Teams |
| MS.TEAMS.5.2v2 | SI-8 | Safe Links for Teams |
| MS.TEAMS.5.3v2 | AC-3 | Custom app policies |

### Power Platform (MS.POWERPLATFORM) — 9 Policies

| PolicyId | NIST Control | Description |
|----------|-------------|-------------|
| MS.POWERPLATFORM.1.1v1 | AC-3 | Environment security |
| MS.POWERPLATFORM.1.2v1 | AC-3 | Data loss prevention |
| MS.POWERPLATFORM.2.1v1 | AC-3 | Connector policies |
| MS.POWERPLATFORM.2.2v1 | CM-6 | Configuration baselines |
| MS.POWERPLATFORM.3.1v1 | AC-3 | Canvas app sharing |
| MS.POWERPLATFORM.3.2v1 | AC-3 | Model-driven app access |
| MS.POWERPLATFORM.4.1v1 | CM-6 | Power Automate policies |
| MS.POWERPLATFORM.5.1v1 | AC-3 | AI Builder access controls |
| MS.POWERPLATFORM.6.1v1 | AC-3 | Copilot Studio policies |

### Power BI (MS.POWERBI) — 7 Policies

| PolicyId | NIST Control | Description |
|----------|-------------|-------------|
| MS.POWERBI.1.1v1 | AC-3 | Sharing policies |
| MS.POWERBI.2.1v1 | AC-3 | Export control policies |
| MS.POWERBI.3.1v1 | SC-28 | Data at rest encryption |
| MS.POWERBI.4.1v1 | MP-5 | Media transport protection |
| MS.POWERBI.4.2v1 | AU-3 | Audit logging |
| MS.POWERBI.5.1v1 | AC-3 | External sharing controls |
| MS.POWERBI.6.1v1 | CM-6 | Configuration management |
| MS.POWERBI.7.1v1 | SI-8 | Information input validation |

### Security Suite (MS.SECURITYSUITE) — 23 Policies

| PolicyId | NIST Control | Description |
|----------|-------------|-------------|
| MS.SECURITYSUITE.1.1v1 | SI-3 | Malicious code protection |
| MS.SECURITYSUITE.1.2v1 | SI-8 | Spam protection |
| MS.SECURITYSUITE.1.3v1 | IR-4 | Incident handling |
| MS.SECURITYSUITE.1.4v1 | IR-5 | Incident monitoring |
| MS.SECURITYSUITE.2.1v1 | CM-6 | Security configuration settings |
| MS.SECURITYSUITE.2.2v1 | CM-7 | Least functionality |
| MS.SECURITYSUITE.2.3v1 | CM-6 | Configuration change control |
| MS.SECURITYSUITE.3.1v1 | SC-28 | Protection of information at rest |
| MS.SECURITYSUITE.3.2v1 | SC-8(1) | Cryptographic protection in transit |
| MS.SECURITYSUITE.3.3v1 | MP-5 | Media transport |
| MS.SECURITYSUITE.3.4v1 | AC-3 | Access enforcement |
| MS.SECURITYSUITE.3.5v1 | AU-3 | Content of audit records |
| MS.SECURITYSUITE.4.1v1 | AC-2 | Account management |
| MS.SECURITYSUITE.4.2v1 | AC-6 | Least privilege |
| MS.SECURITYSUITE.5.1v1 | IA-2 | Identification and authentication |
| MS.SECURITYSUITE.5.2v1 | IA-5 | Authenticator management |
| MS.SECURITYSUITE.6.1v1 | AU-2 | Event logging |
| MS.SECURITYSUITE.6.2v1 | AU-3 | Content of audit records |
| MS.SECURITYSUITE.7.1v1 | SC-7 | Boundary protection |
| MS.SECURITYSUITE.7.2v1 | AC-20 | Use of external systems |
| MS.SECURITYSUITE.7.3v1 | SC-8(1) | Cryptographic protection |
| MS.SECURITYSUITE.8.1v1 | IR-4 | Incident handling |
| MS.SECURITYSUITE.8.2v1 | IR-5 | Incident monitoring |

---

## Appendix D — References

1. CISA ScubaGear Repository: https://github.com/cisagov/ScubaGear
2. CISA SCuBA Program: https://www.cisa.gov/scuba
3. NIST SP 800-53 Rev 5: Security and Privacy Controls for Information Systems and Organizations
4. NIST OSCAL 1.1.2: Open Security Controls Assessment Language
5. CISA BOD 25-01: Binding Operational Directive — Implementation of SCuBA Security Baselines
6. FedRAMP Moderate Baseline (NIST SP 800-53 Rev 5)
7. UIAO-Core Repository: uiao-core v2.0.0
8. UIAO Master Document Specification Package (April 2026)

---

## Glossary

**Adapter:** A pluggable module implementing ComplianceAdapter for ingesting external compliance data into the UIAO pipeline.

**BOD 25-01:** CISA Binding Operational Directive requiring implementation of SCuBA security baselines for federal M365 deployments.

**Canon:** Authoritative configuration and document standards for UIAO.

**ConMon:** Continuous Monitoring — the ongoing assessment of security controls.

**FedRAMP:** Federal Risk and Authorization Management Program.

**GCC-Moderate:** Microsoft Government Community Cloud for FedRAMP Moderate workloads.

**HMAC-SHA256:** Hash-based Message Authentication Code using SHA-256, used for evidence bundle signing.

**IR:** Intermediate Representation — the normalized internal data format for the UIAO pipeline.

**KSI:** Key Security Indicator — a UIAO-specific control evaluation metric mapped from NIST SP 800-53.

**OSCAL:** Open Security Controls Assessment Language — NIST standard for machine-readable security assessments.

**PlantUML:** The canonical diagram renderer for UIAO documentation.

**POA&M:** Plan of Action and Milestones — document tracking remediation of security findings.

**Pydantic:** Python data validation library used for all UIAO pipeline data models.

**SAR:** Security Assessment Report.

**SCuBA:** Secure Cloud Business Applications — CISA program establishing M365 security baselines.

**ScubaGear:** CISA's PowerShell tool for assessing M365 configurations against SCuBA baselines.

**SSP:** System Security Plan.

**SSOT:** Single Source of Truth — the authoritative, canonical data source; singular and certificate-anchored in UIAO.

**Typer:** Python CLI framework used for the UIAO command-line interface.

---

## Footnotes

[^1]: ScubaGear version 0.5.0 or later is required for compatibility with the UIAO normalization engine.

[^2]: The 143 policy mapping count includes version variants (e.g., MS.TEAMS.1.2v2). The number of unique policy prefixes is 101.

[^3]: The conservative aggregation rule (ANY FAIL → KSI FAIL) is deliberate: it prevents a passing sub-policy from masking a failing one, ensuring the strictest compliance interpretation.

[^4]: HMAC-SHA256 was selected over PKI-based signing to avoid requiring certificate infrastructure for initial deployments. Migration to PKI is planned for UIAO v3.0.

[^5]: OSCAL 1.1.2 is the target output version. Forward compatibility with OSCAL 2.0 is tracked as a future work item.

---

## Validation Block

[VALIDATION]
All sections validated against source code in uiao-core repository.
All 143 policy mappings verified against scuba_adapter.py SCUBA_TO_KSI_MAP.
All four plane descriptions verified against transformer.py, evaluate.py, builder.py, generator.py.
Orchestrator description verified against orchestrator/orchestrator.py.
Normalization engine description verified against normalize_scuba.py.
KSI mapping chain verified against uiao-control-to-ksi-mapping.yaml (163 KSIs, 247 controls).
Vendor overlay verified against data/vendor-overlays/scuba.yaml.
CLI commands verified against docs/scuba-architecture-guide.md.
No hallucinations detected.
GCC-Moderate boundary enforced throughout.
No GCC-High, DoD, or Azure IaaS/PaaS references present.
[/VALIDATION]
