UIAO SCuBA Architecture Guide

**Document ID:** UIAO_SAG_001

**Version:** 1.0.0

**Classification:** Controlled

**Date:** 2026-04-11

**Repository:** uiao-core v2.0.0

1\. Overview

UIAO wraps CISA\'s ScubaGear assessment tool inside a deterministic, provenance-first governance pipeline. Raw ScubaGear JSON output is transformed through four sequential planes into auditor-ready OSCAL artifacts.

2\. Four-Plane Pipeline Architecture

2.1 Pipeline Flow

\@startuml skinparam componentStyle rectangle package \"External\" { \[ScubaGear\] as SG \[M365 Tenant\] as M365 } package \"Plane 1 - SCuBA to IR\" { \[scuba/adapter.py\] as SA \[scuba/transformer.py\] as ST } package \"Plane 2 - IR to KSI\" { \[ksi/evaluate.py\] as KE \[ksi/control_library.py\] as KCL } package \"Plane 3 - Evidence Build\" { \[evidence/builder.py\] as EB \[evidence/bundle.py\] as EBU \[evidence/signing.py\] as ES } package \"Plane 4 - OSCAL Generate\" { \[oscal/generator.py\] as OG \[ssp/narrative.py\] as SN \[ssp/lineage.py\] as SL } package \"Outputs\" { \[Auditor Bundle\] as AB \[Governance Dashboard\] as GD \[CLI Reports\] as CR } M365 \--\> SG SG \--\> SA SA \--\> ST ST \--\> KE KCL \--\> KE KE \--\> EB EB \--\> EBU EBU \--\> ES ES \--\> OG OG \--\> SN OG \--\> SL SN \--\> AB SL \--\> AB OG \--\> GD OG \--\> CR \@enduml

2.2 Data Flow

\@startuml start :ScubaGear executes against M365 Tenant; :Raw JSON output captured; partition \"Plane 1: SCuBA to IR\" { :Adapter ingests ScubaGear JSON; :Transformer normalizes to NormalizedClaim\[\]; :IR envelope created with provenance; } partition \"Plane 2: IR to KSI Evaluate\" { :Load KSI control library (YAML); :Map claims to NIST 800-53 controls; :Evaluate pass/fail per control; :Generate KSI evaluation results; } partition \"Plane 3: Evidence Build\" { :Collect evaluation results; :Build evidence bundle; :Sign bundle with HMAC-SHA256; :Calculate stable hash; } partition \"Plane 4: OSCAL Generate\" { :Generate OSCAL SSP; :Generate OSCAL POA&M; :Generate OSCAL SAR; :Export SSP narrative + lineage; } :Output: Auditor Bundle, Dashboard, Reports; stop \@enduml

3\. Module Architecture

3.1 Source Tree

src/uiao_core/ ├── abstractions/ \# Base classes and interfaces ├── adapters/ \# Pluggable adapter framework ├── auditor/ \# Auditor bundle packaging ├── cli/ \# Typer CLI commands ├── collectors/ \# Data collection framework ├── coverage/ \# Control coverage export ├── dashboard/ \# Governance dashboard rendering ├── diff/ \# Diff engine for change detection ├── evidence/ \# Evidence bundle building + signing ├── freshness/ \# Evidence freshness grading ├── generators/ \# Document + artifact generation ├── governance/ \# Governance action framework ├── ir/ \# Intermediate Representation core models ├── ksi/ \# IR to KSI control evaluation ├── models/ \# Pydantic data models ├── monitoring/ \# Monitoring dashboard ├── onboarding/ \# First-run onboarding flow ├── oscal/ \# OSCAL 1.1.2 artifact generation ├── scuba/ \# ScubaGear JSON to IR transformation ├── ssp/ \# SSP narrative + lineage exports ├── utils/ \# Shared utilities ├── validators/ \# Input + schema validation └── config.py \# Root configuration

3.2 Module Dependency Diagram

\@startuml skinparam componentStyle rectangle package \"Foundation\" { \[abstractions\] \[models\] \[utils\] \[config\] } package \"Core Pipeline\" { \[scuba\] \[ksi\] \[evidence\] \[oscal\] \[ir\] } package \"Analysis\" { \[diff\] \[freshness\] \[coverage\] \[validators\] } package \"Output\" { \[ssp\] \[dashboard\] \[auditor\] \[generators\] \[monitoring\] } package \"Integration\" { \[adapters\] \[cli\] \[collectors\] \[governance\] \[onboarding\] } \' Foundation dependencies \[scuba\] \--\> \[abstractions\] \[scuba\] \--\> \[models\] \[ksi\] \--\> \[models\] \[evidence\] \--\> \[models\] \[oscal\] \--\> \[models\] \[ir\] \--\> \[models\] \' Pipeline flow \[scuba\] \--\> \[ir\] \[ksi\] \--\> \[ir\] \[evidence\] \--\> \[ksi\] \[oscal\] \--\> \[evidence\] \' Analysis dependencies \[diff\] \--\> \[ir\] \[freshness\] \--\> \[evidence\] \[coverage\] \--\> \[ksi\] \[validators\] \--\> \[models\] \' Output dependencies \[ssp\] \--\> \[oscal\] \[dashboard\] \--\> \[ksi\] \[dashboard\] \--\> \[evidence\] \[auditor\] \--\> \[oscal\] \[auditor\] \--\> \[evidence\] \[generators\] \--\> \[models\] \' Integration dependencies \[adapters\] \--\> \[abstractions\] \[cli\] \--\> \[scuba\] \[cli\] \--\> \[ksi\] \[cli\] \--\> \[evidence\] \[cli\] \--\> \[oscal\] \[collectors\] \--\> \[adapters\] \[governance\] \--\> \[ksi\] \[governance\] \--\> \[evidence\] \@enduml

4\. Plane Details

4.1 Plane 1: SCuBA → IR

  ---------------------------------------------------------------------------------------------------------------------------------------------------------
  **Attribute**   **Value**
  --------------- -----------------------------------------------------------------------------------------------------------------------------------------
  Module Path     src/uiao_core/scuba/

  Input           ScubaGear JSON export (ScubaResults.json)

  Process         1\. Adapter ingests raw JSON 2. Transformer normalizes each finding to NormalizedClaim 3. Claims wrapped in IR envelope with provenance

  Output          IR envelope containing NormalizedClaim\[\]

  Key Guarantee   Deterministic: same JSON always produces identical IR

  CLI Command     uiao scuba transform \--input \<path\>
  ---------------------------------------------------------------------------------------------------------------------------------------------------------

4.2 Plane 2: IR → KSI Evaluate

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Attribute**   **Value**
  --------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Module Path     src/uiao_core/ksi/

  Input           IR envelope + KSI control library (YAML)

  Process         1\. Load control library definitions 2. Map normalized claims to NIST 800-53 controls 3. Evaluate pass/fail per control requirement 4. Generate structured evaluation results

  Output          KSI evaluation results with control-level pass/fail

  Key Guarantee   Every claim maps to exactly one control; no orphans

  CLI Command     uiao ksi evaluate \--ir \<path\>
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

4.3 Plane 3: Evidence Build

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Attribute**   **Value**
  --------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Module Path     src/uiao_core/evidence/

  Input           KSI evaluation results

  Process         1\. Collect evaluation results into evidence items 2. Build evidence bundle with metadata 3. Sign bundle with HMAC-SHA256 4. Calculate stable hash (excluding volatile fields)

  Output          Signed evidence bundle (.json)

  Key Guarantee   Tamper-evident: any modification invalidates signature

  CLI Command     uiao evidence build \--eval \<path\>
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

4.4 Plane 4: OSCAL Generate

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Attribute**   **Value**
  --------------- ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Module Path     src/uiao_core/oscal/

  Input           Signed evidence bundle

  Process         1\. Generate OSCAL SSP with control implementations 2. Generate OSCAL POA&M for open findings 3. Generate OSCAL SAR with assessment results 4. Export SSP narrative and lineage traces

  Output          OSCAL 1.1.2 compliant SSP, POA&M, SAR

  Key Guarantee   Schema-valid OSCAL 1.1.2 output

  CLI Command     uiao oscal generate \--evidence \<path\>
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

5\. Cross-Cutting Modules

5.1 IR (Intermediate Representation)

The IR module provides 6 core model types:

  --------------------------------------------------------
  **Model**          **Purpose**
  ------------------ -------------------------------------
  NormalizedClaim    Standardized compliance finding

  IREnvelope         Wrapper with provenance metadata

  Provenance         Source, timestamp, and run tracking

  ControlMapping     Claim-to-control relationship

  EvaluationResult   Pass/fail per control

  EvidenceItem       Single piece of compliance evidence
  --------------------------------------------------------

5.2 Diff Engine

The diff engine produces 4 result types:

  ------------------------------------------------------
  **Result Type**   **Description**
  ----------------- ------------------------------------
  Added             New finding not in baseline

  Removed           Finding resolved since baseline

  Changed           Finding status or severity changed

  Unchanged         Finding identical to baseline
  ------------------------------------------------------

5.3 Freshness Engine

  ---------------------------------------------------------------
  **Grade**   **Age**              **Meaning**
  ----------- -------------------- ------------------------------
  Fresh       ≤ 24 hours           Evidence is current

  Stale       24 hours -- 7 days   Evidence needs refresh

  Expired     \> 7 days            Evidence must be recollected
  ---------------------------------------------------------------

5.4 Governance Actions

  -------------------------------------------------------------
  **Action Type**   **Description**
  ----------------- -------------------------------------------
  Remediate         Fix non-compliant configuration

  Accept            Accept risk with documented justification

  Mitigate          Apply compensating control

  Transfer          Assign responsibility to another party
  -------------------------------------------------------------

5.5 Adapters

The adapter framework uses an Abstract Base Class (ComplianceAdapter) pattern. Each adapter implements ingest(), normalize(), validate(), metadata(), and capabilities() methods. Adapters are registered via YAML configuration or Python entry points.

6\. CLI Architecture

uiao ├── scuba │ ├── run \# Execute ScubaGear assessment │ ├── transform \# Transform ScubaGear JSON to IR │ ├── status \# Show current assessment status │ └── diff \# Compare two assessment runs ├── ksi │ ├── evaluate \# Evaluate IR against control library │ ├── findings \# List findings by severity │ ├── enrich \# Enrich KSI with external data │ └── validate \# Validate control library YAML ├── evidence │ ├── build \# Build evidence bundle │ ├── verify \# Verify evidence signature │ ├── freshness \# Check evidence freshness │ └── re-sign \# Re-sign evidence bundle ├── oscal │ ├── generate \# Generate OSCAL artifacts │ └── validate \# Validate OSCAL against schema ├── ssp │ ├── narrative \# Export SSP narrative │ └── lineage \# Export SSP lineage traces ├── diff │ ├── report \# Generate diff report │ └── show \# Show specific diff details ├── dashboard │ └── export \# Export governance dashboard ├── coverage │ ├── export \# Export control coverage │ └── trend \# Show coverage trend ├── governance │ ├── scorecard \# Generate governance scorecard │ ├── actions \# List governance actions │ ├── poam \# Generate POA&M │ └── poam-transition \# Transition POA&M item state └── auditor └── bundle \# Package auditor bundle

7\. CI/CD Architecture

\@startuml start :Developer pushes to branch; fork :ci.yml - Run tests; fork again :lint.yml - Run ruff; fork again :security-scan.yml - Security check; fork again :canon-validation.yml - Validate canon; end fork if (All checks pass?) then (yes) :Merge to main; fork :generate-docs.yml - Build documentation; fork again :generate-artifacts.yml - Build artifacts; fork again :render-and-insert-diagrams.yml - Render diagrams; end fork else (no) :Block merge, notify developer; stop endif if (Nightly schedule?) then (yes) :scuba-nightly.yml - Run SCuBA assessment; :drift-detection.yml - Check for drift; :dashboard-export.yml - Update dashboard; endif if (Tag/release created?) then (yes) :publish.yml - Publish to PyPI; :deploy.yml - Deploy artifacts; endif stop \@enduml

8\. Data Classification

  -------------------------------------------------------------------------------------------------------------------------------------------
  **Classification**   **Scope**                                             **Handling**
  -------------------- ----------------------------------------------------- ----------------------------------------------------------------
  Controlled           Architecture docs, test plans, internal procedures    Internal use; version-controlled in private repo

  Public               README, API docs, open-source components              Published to documentation site

  Tenant-Specific      ScubaGear output, evidence bundles, OSCAL artifacts   Scoped to tenant; encrypted at rest; retention policy enforced
  -------------------------------------------------------------------------------------------------------------------------------------------

+-----------------------------------------------------------------------------------+
| **Canon Rule**                                                                    |
|                                                                                   |
| Public repository. GCC Moderate classification applies to M365 SaaS services only. |
+-----------------------------------------------------------------------------------+

9\. Key Architectural Decisions

  ----------------------------------------------------------------------------------------------------------------------------
  **Decision**                             **Rationale**
  ---------------------------------------- -----------------------------------------------------------------------------------
  4-Plane sequential pipeline              Clear separation of concerns; each plane independently testable and deterministic

  Pydantic for all data models             Runtime validation, serialization, and schema generation built-in

  HMAC-SHA256 for evidence signing         Tamper-evident without requiring PKI infrastructure

  YAML for control library configuration   Human-readable, diffable, version-controllable

  Typer for CLI framework                  Type-safe, auto-documented, minimal boilerplate

  OSCAL 1.1.2 as output format             FedRAMP standard; machine-readable; interoperable

  Adapter pattern for data ingestion       Extensible to new compliance data sources without core changes

  Stable hash excludes volatile fields     Enables determinism verification across runs

  Golden file regression testing           Detects unintended output changes at the byte level
  ----------------------------------------------------------------------------------------------------------------------------

10\. Security Architecture

10.1 Evidence Integrity Chain

ScubaGear JSON │ ▼ Plane 1: Normalize → IR Envelope (provenance attached) │ ▼ Plane 2: Evaluate → KSI Results (control mapping) │ ▼ Plane 3: Build → Evidence Bundle │ └── HMAC-SHA256 signature │ └── SHA-256 stable hash ▼ Plane 4: Generate → OSCAL Artifacts └── Lineage traces back to source

10.2 Trust Boundaries

  -------------------------------------------------------------------------------------------------------------------------------
  **Boundary**         **Description**                                **Controls**
  -------------------- ---------------------------------------------- -----------------------------------------------------------
  External → Plane 1   Untrusted ScubaGear output enters pipeline     Schema validation, input sanitization, adapter isolation

  Plane 3 → Storage    Signed evidence written to disk                HMAC signing, file permissions, retention policy

  Plane 4 → Auditor    OSCAL artifacts provided to external parties   Schema validation, lineage verification, bundle packaging
  -------------------------------------------------------------------------------------------------------------------------------

11\. Glossary

  -----------------------------------------------------------------------------
  **Term**    **Definition**
  ----------- -----------------------------------------------------------------
  SCuBA       Secure Cloud Business Applications (CISA program)

  ScubaGear   CISA\'s PowerShell assessment tool for M365

  KSI         Key Security Indicator --- a control evaluation metric

  IR          Intermediate Representation --- normalized pipeline data format

  OSCAL       Open Security Controls Assessment Language (NIST)

  SSP         System Security Plan

  POA&M       Plan of Action and Milestones

  SAR         Security Assessment Report

  FedRAMP     Federal Risk and Authorization Management Program

  BOD 25-01   Binding Operational Directive 25-01 (CISA)

  ConMon      Continuous Monitoring

  Canon       Authoritative configuration and document standards for UIAO
  -----------------------------------------------------------------------------

Document Revision History

  ---------------------------------------------------------------
  **Version**   **Date**     **Author**         **Description**
  ------------- ------------ ------------------ -----------------
  1.0.0         2026-04-11   Michael Stratton   Initial release

  ---------------------------------------------------------------

> **

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
