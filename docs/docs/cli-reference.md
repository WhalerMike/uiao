# UIAO-Core CLI Reference

**Version:** Current (April 2026)
**Environment:** Commercial Cloud (FedRAMP-governed); GCC-Moderate applies to Microsoft 365 SaaS services only.
**Toolkit:** OSCAL compliance toolkit for US Government systems.

---

## 1. Overview

UIAO-Core is the canonical command-line toolkit for the Unified Integration Architecture & Operations (UIAO) framework. It automates the full lifecycle of compliance artifact generation, continuous monitoring, governance reporting, and auditor evidence packaging — from canon YAML source-of-truth through OSCAL-compliant outputs.

The CLI is organized around a deterministic pipeline architecture: Canon YAML → OSCAL generation → visual rendering → artifact packaging → continuous monitoring → IR (Intermediate Representation) governance pipeline. Every command is designed to be idempotent, auditable, and traceable to its canon source.

> **Governance Note**
> UIAO operates in Commercial Cloud as governed by FedRAMP unless specifically noted. GCC-Moderate applies to Microsoft 365 SaaS services only and does not include Azure services. We are not FedRAMP High.

---

## 2. Global Options

The following options are available on every UIAO-Core command invocation.

| Option | Short | Description |
|--------|-------|-------------|
| --version | -V | Show the UIAO-Core version and exit. |
| --help | | Show the top-level help message and exit. |

---

## 3. Command Reference by Pipeline Stage

### 3.1 Core OSCAL Generation & Validation

These commands form the foundation of the UIAO compliance pipeline. They produce and validate OSCAL (Open Security Controls Assessment Language) artifacts from the canonical YAML source-of-truth. Every downstream artifact — SSPs, POA&Ms, dashboards, briefings — traces its provenance back to the outputs of this stage.

| Command | Description | Pipeline Role |
|---------|-------------|---------------|
| generate-ssp | Generate an OSCAL SSP from canon YAML and data files. | Primary SSP generation; authoritative compliance narrative. |
| validate | Validate an OSCAL document against its schema. | Schema-level structural validation gate. |
| canon-check | Check canon YAML files for consistency. | First-line defense against configuration drift. |
| validate-ssp | Validate OSCAL artifacts with compliance-trestle Pydantic models. | Semantic validation beyond schema compliance. |

#### Details

**generate-ssp** — This is the primary SSP generation command. It reads the canonical YAML configuration and data files to produce a fully-formed OSCAL System Security Plan. The SSP is the authoritative compliance narrative for the system boundary, control implementations, and responsible parties.

**validate** — Performs schema-level validation of any OSCAL document (SSP, SAR, SAP, POA&M, component-definition) against the NIST OSCAL schema. Use this to catch structural errors before submission or downstream processing.

**canon-check** — Ensures that all canon YAML files are internally consistent — cross-references resolve, required fields are present, enumerations are valid, and no drift has occurred between canon sources. This is the first-line defense against configuration drift.

**validate-ssp** — Goes beyond schema validation by loading OSCAL artifacts through NIST compliance-trestle's Pydantic V1 models. This catches semantic errors that pass schema validation — invalid control references, orphaned parameters, broken cross-links. Note: Currently emits a compatibility warning on Python 3.14+ due to Pydantic V1 deprecation.

---

### 3.2 Visual & Artifact Generation

UIAO produces leadership-grade deliverables — DOCX briefings, PPTX decks, embedded diagrams, and AI-generated visuals. These commands render canon data into presentation-ready formats. All visuals use PlantUML for deterministic, version-controlled diagram generation. Gemini API integration provides AI-generated imagery for executive-facing materials.

| Command | Description | Pipeline Role |
|---------|-------------|---------------|
| generate-visuals | Render PlantUML diagrams to PNG for DOCX/PPTX embedding. | Diagram rendering stage; produces publication-quality PNGs. |
| generate-gemini | Generate images via Gemini API (requires GEMINI_API_KEY). | AI-generated visuals for executive-facing materials. |
| generate-pptx | Generate a leadership briefing PPTX deck. | Executive communication; governance and risk posture. |
| generate-docx | Generate a rich DOCX leadership briefing with embedded visuals. | Word-format leadership briefing with embedded diagrams. |
| generate-diagrams | Generate PlantUML .puml files and render them to PNG from canon YAML. | Deterministic, version-controlled diagram generation. |
| generate-docs | Render Jinja2 templates into Markdown docs using canon YAML and data files. | Parameterized documentation from templates. |
| generate-artifacts | Generate DOCX + PPTX with embedded PlantUML and Gemini visuals. | Full visual artifact pipeline in a single invocation. |
| generate-briefing | Generate personal briefing document from live repo state. | Daily operational awareness; live pipeline and governance status. |

#### Details

**generate-visuals** — Reads .puml source files and renders them to PNG at publication-quality resolution. Output PNGs are sized and titled for direct embedding into Word and PowerPoint artifacts. All images include titles and dimensions per UIAO standards.

**generate-gemini** — Produces AI-generated visuals using Google's Gemini API. Used for executive-facing imagery, conceptual illustrations, and briefing cover art. Requires the GEMINI_API_KEY environment variable.

**generate-pptx** — Produces a PowerPoint leadership briefing from canon YAML and rendered visuals. The deck follows canonical UIAO formatting and is designed for executive communication — governance status, risk posture, compliance narrative.

**generate-docx** — Produces a Word document leadership briefing with embedded PlantUML diagrams and Gemini visuals. Follows canonical formatting: muted-blue headers, black body text, titled and dimensioned images.

**generate-diagrams** — A two-stage command: first generates .puml source files from canon YAML data (system boundaries, data flows, network diagrams), then renders them to PNG. This is the canonical path for deterministic, version-controlled diagram generation.

**generate-docs** — Uses Jinja2 templating to produce Markdown documentation from canon YAML. Supports parameterized templates for recurring document types — control narratives, boundary descriptions, operational procedures.

**generate-artifacts** — A convenience command that runs the full visual artifact pipeline: PlantUML rendering → Gemini image generation → DOCX + PPTX assembly. Produces both deliverables in a single invocation with consistent embedded visuals.

**generate-briefing** — Produces a personalized briefing document by reading the live state of the UIAO repository — open issues, PR status, governance actions, drift alerts, and pipeline health. Designed for daily operational awareness.

---

### 3.3 Supply Chain Security

Software supply chain transparency is a FedRAMP and NIST requirement. UIAO generates machine-readable Software Bills of Materials (SBOMs) to document every dependency in the compliance toolkit itself and in assessed systems.

| Command | Description | Pipeline Role |
|---------|-------------|---------------|
| generate-sbom | Generate a CycloneDX 1.4 Software Bill of Materials (SBOM). | Supply chain transparency; EO 14028 compliance. |

#### Details

**generate-sbom** — Produces a CycloneDX 1.4-compliant SBOM enumerating all software components, dependencies, and versions. Supports supply chain risk assessment, vulnerability tracking, and Executive Order 14028 compliance.

---

### 3.4 Continuous Monitoring (ConMon)

Continuous monitoring is the operational heartbeat of FedRAMP compliance. These commands process live security telemetry (Sentinel alerts), manage Plans of Action & Milestones (POA&Ms), export ongoing authorization evidence, and produce KSI (Key Security Indicator) dashboards. The ConMon pipeline transforms raw security events into governance-grade artifacts.

| Command | Description | Pipeline Role |
|---------|-------------|---------------|
| conmon-process | Process a Sentinel alert and auto-upsert a POA&M entry. | Primary ConMon event processing automation. |
| conmon-export-oa | Export an OSCAL ongoing-authorization evidence artifact. | ATO maintenance; evidence for authorizing officials. |
| conmon-dashboard | Export the KSI continuous monitoring dashboard. | Governance-grade security posture summary. |

#### Details

**conmon-process** — Ingests a Microsoft Sentinel security alert, classifies it against the UIAO control framework, and automatically creates or updates the corresponding POA&M entry. This is the primary automation for continuous monitoring event processing.

**conmon-export-oa** — Produces an OSCAL-compliant ongoing authorization evidence package. This artifact demonstrates continuous compliance posture for ATO maintenance and ConMon reporting to authorizing officials.

**conmon-dashboard** — Generates the Key Security Indicator (KSI) dashboard — a governance-grade summary of security posture, control effectiveness, and operational health. Includes SLA status, drift indicators, and trend data.

---

### 3.5 Full Pipeline

For end-to-end generation from canon YAML through all output artifacts in a single deterministic pass.

| Command | Description | Pipeline Role |
|---------|-------------|---------------|
| generate-all | Run the full UIAO generation pipeline: YAML canon → all output artifacts. | Canonical "build everything" command; idempotent. |

#### Details

**generate-all** — Executes every generation stage in dependency order: canon validation → SSP generation → diagram rendering → Gemini visuals → DOCX/PPTX assembly → SBOM. This is the canonical "build everything" command. Idempotent — safe to re-run at any time.

---

### 3.6 Adapter Layer

Adapters are the integration boundary between external vendor tools and the UIAO canonical data model. They ingest third-party assessment outputs and normalize them into UIAO's DNS-style claim format — lightweight, human-readable, and traceable — without requiring heavy OSCAL conversion at the adapter boundary. The adapter layer is where external truth enters the UIAO provenance chain.

| Command | Description | Pipeline Role |
|---------|-------------|---------------|
| adapter-run | Run a vendor adapter and align claims (DNS-style, no heavy OSCAL conversion). | Generic adapter runner; normalizes vendor output. |
| adapter-run-scuba | Run SCuBA adapter: ingest ScubaGear report and map to UIAO KSI evidence. | Primary M365 security posture assessment integration. |

#### Details

**adapter-run** — The generic adapter runner. Ingests output from a vendor assessment tool, normalizes findings into DNS-style claims (e.g., M365.EXO.DKIM.PASS), and aligns them against UIAO's canonical control mapping. Adapter output feeds downstream IR and governance pipelines.

**adapter-run-scuba** — The specialized adapter for CISA's ScubaGear (Secure Cloud Business Applications) assessment tool. Ingests a ScubaGear JSON report, maps each policy result to the corresponding UIAO KSI, and produces normalized evidence objects. This is the primary M365 security posture assessment integration.

---

### 3.7 IR (Intermediate Representation) Pipeline

The IR pipeline is the analytical and governance core of UIAO. It transforms normalized adapter output (starting with SCuBA) through a deterministic chain: raw results → normalized IR objects → evidence bundles → governance actions → auditor packages. Every stage produces traceable, machine-readable artifacts. The IR layer enables drift detection, freshness tracking, POA&M generation, SSP narrative synthesis, and full auditor evidence packaging — all from a single source-of-truth pipeline.

| Command | Description | Pipeline Role |
|---------|-------------|---------------|
| ir-scuba-transform | Transform normalized SCuBA JSON → IR Evidence objects and print summary. | IR pipeline entry point; canonical evidence creation. |
| ir-evidence-bundle | Build a canonical EvidenceBundle from a SCuBA transform and print summary. | Evidence aggregation; auditor-consumable unit. |
| ir-poam-export | Export POA&M rows (FAIL + WARN only) from a SCuBA run and print summary. | Non-passing findings → actionable POA&M entries. |
| ir-drift-detect | Detect drift between two IR state JSON files and print classification. | Change detection; governance escalation trigger. |
| ir-governance-report | Run full governance pipeline: SCuBA → IR → Evidence → Actions → Report. | Comprehensive governance report synthesis. |
| ir-ssp-report | Generate SSP narrative + lineage from SCuBA → IR → Evidence → Governance. | SSP authoring with full provenance lineage. |
| ir-auditor-bundle | Run full pipeline and write all auditor artifacts to a directory. | Auditor-facing artifact packaging. |
| ir-diff | Diff two SCuBA runs: KSI changes, evidence hash deltas, status changes. | Trend analysis and regression detection. |
| ir-validate | Validate a normalized SCuBA JSON file for IR pipeline conformance. | Input validation gate for IR pipeline. |
| ir-freshness | Compute evidence freshness and generate refresh actions for stale evidence. | ConMon compliance; evidence currency enforcement. |
| ir-dashboard | Build IR governance dashboard: evidence freshness + governance action summary. | Capstone governance visibility; daily operational use. |

#### Details

**ir-scuba-transform** — The entry point of the IR pipeline. Takes normalized SCuBA adapter output and transforms it into canonical IR Evidence objects — typed, hashed, timestamped records suitable for governance processing.

**ir-evidence-bundle** — Aggregates individual IR Evidence objects into a canonical EvidenceBundle — a signed, timestamped collection with provenance metadata. The bundle is the unit of evidence for auditor consumption and governance reporting.

**ir-poam-export** — Extracts all FAIL and WARN findings from an IR pipeline run and formats them as POA&M (Plan of Action & Milestones) rows. Each row includes control mapping, severity, remediation timeline, and responsible party. Only non-passing results generate POA&M entries.

**ir-drift-detect** — Compares two IR state snapshots (e.g., consecutive SCuBA runs) and classifies changes: new findings, resolved findings, regressions, severity changes, and configuration drift. Drift classification drives governance escalation workflows.

**ir-governance-report** — The full governance pipeline in a single command. Ingests SCuBA output and runs it through every IR stage — transform, evidence bundling, action generation, and report synthesis. Produces a comprehensive governance report with findings, actions, and recommendations.

**ir-ssp-report** — Synthesizes an SSP (System Security Plan) narrative section with full provenance lineage — tracing every statement back through the governance pipeline to its source SCuBA finding. Designed for SSP authoring and ATO package preparation.

**ir-auditor-bundle** — The auditor-facing command. Runs the complete IR pipeline and writes every artifact — evidence bundles, POA&M exports, governance reports, SSP narratives, drift analyses — to a single directory structure suitable for auditor review.

**ir-diff** — A focused comparison tool for two SCuBA assessment runs. Reports KSI-level changes, evidence hash deltas (detecting content changes even when status is unchanged), and status transitions. Used for trend analysis and regression detection.

**ir-validate** — Validates that a normalized SCuBA JSON file conforms to the IR pipeline's input schema. Catches structural issues before they propagate through the pipeline — missing fields, invalid enumerations, schema violations.

**ir-freshness** — Evaluates the age of every evidence object against its required refresh interval. Produces a freshness report and generates actionable refresh tasks for any evidence that is stale or approaching staleness. Critical for ConMon compliance — evidence must be current to maintain ATO.

**ir-dashboard** — The capstone IR command. Produces a governance dashboard combining evidence freshness status, pending governance actions, drift alerts, and pipeline health metrics. Designed for daily operational governance and leadership visibility.

---

## 4. Pipeline Architecture

The UIAO-Core CLI implements a deterministic pipeline architecture. Every artifact produced by any command is traceable back to its canon YAML source-of-truth. The pipeline flows through the following stages:

```
Canon YAML (Source of Truth)
  → Core OSCAL Generation
  → Visual Rendering
  → Artifact Packaging
  → Continuous Monitoring
  → Adapter Ingestion
  → IR Pipeline
  → Governance Reporting
  → Auditor Delivery
```

The pipeline is designed to be **idempotent** — any stage can be re-run without side effects. Re-running a stage with identical inputs produces identical outputs. This property is essential for auditability and reproducibility.

The IR pipeline specifically enforces **provenance** by hashing evidence objects and tracking lineage through every transformation. Each IR Evidence object carries a content hash, a timestamp, and a reference to its source adapter output — creating an unbroken chain of custody from raw assessment data to auditor-facing artifacts.

---

## 5. Environment & Prerequisites

| Prerequisite | Details |
|--------------|---------|
| **Python** | Python 3.14+. The Pydantic V1 compatibility warning emitted by compliance-trestle is expected and non-blocking. |
| **compliance-trestle** | NIST compliance-trestle library for OSCAL Pydantic model validation. Required by validate-ssp. |
| **PlantUML** | Java runtime required for diagram rendering. Used by generate-visuals and generate-diagrams. |
| **GEMINI_API_KEY** | Environment variable required for AI-generated visuals via generate-gemini. |
| **Canon YAML** | Canon YAML files must be present and pass canon-check before any generation command is run. |

> **Environment Boundaries**
> - UIAO operates in Commercial Cloud as governed by FedRAMP unless specifically noted.
> - GCC-Moderate applies to Microsoft 365 SaaS services only (does not include Azure services).
> - Amazon Connect Contact Center is an explicit exception running in Commercial Cloud.

---

## 6. Canonical Rules

The following governance rules are authoritative and apply to all UIAO operations, artifacts, and communications:

1. **We are not FedRAMP High.** UIAO operates under FedRAMP governance at the applicable baseline; no artifacts, narratives, or communications should assert or imply FedRAMP High authorization.
2. **GCC-Moderate applies to Microsoft 365 SaaS services only.** Azure services, Amazon Web Services, and other cloud infrastructure operate under their respective Commercial Cloud authorizations.
3. **UIAO operates in Commercial Cloud as governed by FedRAMP unless specifically noted.** Exceptions (e.g., Amazon Connect) are explicitly documented.
4. **No references to any previous version in any context prior to the current version.** All artifacts are current-state only. Historical version references are not carried forward.
5. **Every artifact must be canonical, deterministic, and provenance-aligned.** Outputs are reproducible from canon YAML, traceable through the pipeline, and consistent across invocations.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
