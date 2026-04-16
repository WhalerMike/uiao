UIAO-Core Master Test Plan

**Document ID:** UIAO_MTP_001

**Version:** 1.0.0

**Classification:** Controlled

**Date:** 2026-04-11

**Repository:** uiao-core v2.0.0

**Author:** Michael Stratton, Canon Steward

**Status:** Active

1\. Purpose and Scope

This Master Test Plan (MTP) defines the test strategy, coverage requirements, test classification taxonomy, and validation criteria for the uiao-core repository. It maps every source module to its test suite, identifies coverage gaps, and establishes the quality gates enforced by CI.

1.1 In Scope

- All 21 source modules under src/uiao_core/

- All 35+ test files under tests/

- All 31 GitHub Actions workflows under .github/workflows/

- The 4-Plane pipeline architecture (SCuBA → KSI → Evidence → OSCAL)

- Cross-plane integration and end-to-end validation

- Determinism, hash stability, and reproducibility guarantees

- FedRAMP Moderate compliance validation

1.2 Out of Scope

- uiao-docs rendering pipeline (separate repository)

- Third-party dependency testing (ScubaGear, CISA tooling)

- Performance benchmarking (covered in future Performance Test Plan)

- Penetration testing (covered by ai-security-audit.yml workflow)

2\. Architecture Under Test

2.1 Four-Plane Pipeline

The core pipeline processes compliance data through four deterministic planes:

  ---------------------------------------------------------
  **Plane**   **Name**            **Module Path**
  ----------- ------------------- -------------------------
  Plane 1     SCuBA → IR          src/uiao_core/scuba/

  Plane 2     IR → KSI Evaluate   src/uiao_core/ksi/

  Plane 3     Evidence Build      src/uiao_core/evidence/

  Plane 4     OSCAL Generate      src/uiao_core/oscal/
  ---------------------------------------------------------

2.2 Source Module Inventory

  ---------------------------------------------------------------------------------------------------------------
  **\#**   **Module**     **Path**                      **Purpose**                               **Plane**
  -------- -------------- ----------------------------- ----------------------------------------- ---------------
  1        scuba          src/uiao_core/scuba/          ScubaGear JSON to IR transformation       Plane 1

  2        ksi            src/uiao_core/ksi/            IR to KSI control evaluation              Plane 2

  3        evidence       src/uiao_core/evidence/       Evidence bundle building + signing        Plane 3

  4        oscal          src/uiao_core/oscal/          OSCAL 1.1.2 artifact generation           Plane 4

  5        ir             src/uiao_core/ir/             Intermediate Representation core models   Cross-plane

  6        models         src/uiao_core/models/         Pydantic data models                      Cross-plane

  7        adapters       src/uiao_core/adapters/       Pluggable adapter framework               Ingest

  8        cli            src/uiao_core/cli/            Typer CLI commands                        Interface

  9        ssp            src/uiao_core/ssp/            SSP narrative + lineage exports           Output

  10       diff           src/uiao_core/diff/           Diff engine for change detection          Analysis

  11       dashboard      src/uiao_core/dashboard/      Governance dashboard rendering            Output

  12       freshness      src/uiao_core/freshness/      Evidence freshness grading                Analysis

  13       governance     src/uiao_core/governance/     Governance action framework               Enforcement

  14       coverage       src/uiao_core/coverage/       Control coverage export                   Analysis

  15       monitoring     src/uiao_core/monitoring/     Monitoring dashboard                      Observability

  16       auditor        src/uiao_core/auditor/        Auditor bundle packaging                  Output

  17       generators     src/uiao_core/generators/     Document + artifact generation            Output

  18       collectors     src/uiao_core/collectors/     Data collection framework                 Ingest

  19       validators     src/uiao_core/validators/     Input + schema validation                 Quality

  20       abstractions   src/uiao_core/abstractions/   Base classes and interfaces               Foundation

  21       onboarding     src/uiao_core/onboarding/     First-run onboarding flow                 Interface

  22       utils          src/uiao_core/utils/          Shared utilities                          Foundation
  ---------------------------------------------------------------------------------------------------------------

3\. Test Classification Taxonomy

3.1 Test Tiers

  --------------------------------------------------------------------------------------------------------
  **Tier**   **Name**      **Scope**                                     **Speed**      **CI Gate**
  ---------- ------------- --------------------------------------------- -------------- ------------------
  T0         Smoke         Does it import and respond?                   \< 5s total    Every push

  T1         Unit          Single function/class, mocked dependencies    \< 1s each     Every push

  T2         Integration   Multi-module interaction, real data models    \< 5s each     Every push

  T3         Plane         Full single-plane pipeline with fixtures      \< 10s each    Every push

  T4         End-to-End    All 4 planes, full pipeline, real fixtures    \< 30s each    Every push

  T5         Determinism   Same input produces identical output + hash   \< 15s each    Every push

  T6         Compliance    FedRAMP control mapping validation            \< 60s total   Weekly / release
  --------------------------------------------------------------------------------------------------------

3.2 Test Properties

  ----------------------------------------------------------------------------------------------
  **Property**         **Symbol**   **Definition**
  -------------------- ------------ ------------------------------------------------------------
  Deterministic        🔒           Same input always produces identical output and hash

  Isolated             🧱           No external dependencies, no network, no filesystem writes

  Provenance-tracked   📋           Output includes traceable source + timestamp metadata

  Idempotent           ♻            Running N times produces same result as running once
  ----------------------------------------------------------------------------------------------

4\. Existing Test Coverage Map

4.1 Plane Test Suites (Tier T3)

  -------------------------------------------------------------------------------------
  **Test File**                   **Plane**   **Tests**   **Added**    **Properties**
  ------------------------------- ----------- ----------- ------------ ----------------
  test_scuba_transform_plane.py   Plane 1     18          2026-04-10   🔒 🧱 📋

  test_ksi_eval_plane.py          Plane 2     23          2026-04-10   🔒 🧱 📋

  test_evidence_build_plane.py    Plane 3     27          2026-04-10   🔒 🧱 📋

  test_oscal_generate_plane.py    Plane 4     30          2026-04-10   🔒 🧱 📋
  -------------------------------------------------------------------------------------

**Plane Subtotal: 98 tests**

4.2 Core Module Tests (Tier T1/T2)

  -------------------------------------------------------------------------------------------
  **Test File**                           **Module Under Test**   **Tier**   **Properties**
  --------------------------------------- ----------------------- ---------- ----------------
  test_abstractions.py                    abstractions            T1         🧱

  test_adapters.py                        adapters                T1         🧱

  test_auditor_bundle.py                  auditor                 T2         🔒 🧱

  test_briefing.py                        generators              T1         🧱

  test_cli.py                             cli                     T2         🧱

  test_cli_ssp.py                         cli / ssp               T2         🧱

  test_control_library.py                 ksi                     T1         🔒 🧱

  test_coverage_export.py                 coverage                T1         🧱

  test_cyberark_sync.py                   collectors              T2         🧱

  test_diagrams.py                        generators              T1         🧱

  test_diff_engine.py                     diff                    T1         🔒 🧱

  test_drift_detection.py                 governance              T2         🧱

  test_evidence.py                        evidence                T1         🔒 🧱

  test_evidence_bundle.py                 evidence                T2         🔒 🧱 📋

  test_generate_diagrams.py               generators              T1         🧱

  test_generators.py                      generators              T1         🧱

  test_governance_actions.py              governance              T2         🧱

  test_ir_cli.py                          cli / ir                T2         🧱

  test_ir_dashboard.py                    dashboard               T2         🧱

  test_ir_freshness.py                    freshness               T1         🔒 🧱

  test_ir_freshness_schedule.py           freshness               T1         🔒 🧱

  test_ir_governance_cli.py               cli / governance        T2         🧱

  test_ir_hash_stability.py               ir                      T5         🔒 🧱

  test_ir_validator.py                    validators              T1         🧱

  test_local_sync.py                      collectors              T2         🧱

  test_models.py                          models                  T1         🔒 🧱

  test_monitoring_dashboard.py            monitoring              T2         🧱

  test_mover_logic.py                     utils                   T1         🧱

  test_narrative_loader.py                ssp                     T1         🧱

  test_overlay_loader.py                  ssp                     T1         🧱

  test_poam.py                            oscal                   T1         🔒 🧱

  test_poam_export.py                     oscal                   T2         🔒 🧱 📋

  test_sar.py                             oscal                   T1         🔒 🧱

  test_scuba_adapter.py                   adapters / scuba        T2         🔒 🧱

  test_scuba_transformer_determinism.py   scuba                   T5         🔒 🧱

  test_ssp_inject.py                      ssp                     T2         🧱

  test_ssp_lineage.py                     ssp                     T1         🔒 🧱 📋

  test_ssp_narrative.py                   ssp                     T1         🧱

  test_workflow_serialization.py          utils / ci              T1         🧱
  -------------------------------------------------------------------------------------------

4.3 End-to-End Tests (Tier T4)

  -----------------------------------------------------------------
  **Test File**            **Description**               **Tier**
  ------------------------ ----------------------------- ----------
  test_e2e.py              Full pipeline smoke           T4

  test_e2e_atlas_flow.py   Atlas/Network enforcer flow   T4

  test_integration.py      Cross-module integration      T4
  -----------------------------------------------------------------

4.4 Coverage Summary

  -----------------------------------------------------------------------------
  **Category**            **Files**      **Tests**         **Status**
  ----------------------- -------------- ----------------- --------------------
  Plane suites            4 files        98 tests          Complete

  Core unit/integration   35 files       \~275 tests       Operational

  End-to-end              3 files        \~15 tests        Operational

  Determinism             2 files        \~10 tests        Operational

  **TOTAL**               **44 files**   **\~398 tests**   **379 last green**
  -----------------------------------------------------------------------------

5\. Gap Analysis

5.1 Critical Gaps (Must Build)

  ------------------------------------------------------------------------------------------------------------------------
  **ID**   **Test File**                      **Module**     **Tier**   **Reason**
  -------- ---------------------------------- -------------- ---------- --------------------------------------------------
  G1       test_cross_plane_determinism.py    All 4 planes   T5         No test validates full pipeline hash determinism

  G2       test_onboarding.py                 onboarding     T1         Module has zero test coverage

  G3       test_collectors.py                 collectors     T1         Only CyberArk tested

  G4       test_validators_comprehensive.py   validators     T1         Only IR validator tested

  G5       test_config.py                     config.py      T1         Root config has no tests
  ------------------------------------------------------------------------------------------------------------------------

5.2 Important Gaps (Should Build)

  -------------------------------------------------------------------------
  **ID**   **Test File**                    **Module**           **Tier**
  -------- -------------------------------- -------------------- ----------
  G6       test_scuba_nightly_workflow.py   scuba-nightly.yml    T2

  G7       test_ksi_enrichment.py           ksi enrichment       T2

  G8       test_adapter_registry.py         adapters registry    T2

  G9       test_evidence_signing.py         evidence signing     T1

  G10      test_retention_cleanup.py        utils / governance   T1
  -------------------------------------------------------------------------

5.3 BOD 25-01 / Compliance Gaps

  ----------------------------------------------------------------------------------
  **ID**   **Test File**                     **Module**                   **Tier**
  -------- --------------------------------- ---------------------------- ----------
  G11      test_bod_25_01_compliance.py      BOD 25-01 assessor           T6

  G12      test_leg2_policy_ingest.py        Inbound policy updates       T2

  G13      test_governance_event_engine.py   Event-driven governance      T2

  G14      test_multi_tenant_isolation.py    Tenant boundary separation   T2
  ----------------------------------------------------------------------------------

6\. Test Data and Fixtures

6.1 Fixture Inventory

  -------------------------------------------------------------
  **Location**         **Contents**
  -------------------- ----------------------------------------
  tests/fixtures/      ScubaGear JSON fixtures, IR snapshots

  tests/data/          mock_cyberark.json, other adapter data

  generation-inputs/   KSI YAML, control mappings, templates
  -------------------------------------------------------------

6.2 Fixture Requirements

1.  **Realistic** --- Derived from actual tool output

2.  **Versioned** --- File names include source version

3.  **Minimal** --- Smallest dataset for the code path

4.  **Stable** --- Never modified after initial commit

5.  **Documented** --- README.md in each fixture directory

6.3 Missing Fixtures

  ---------------------------------------------------------------------------
  **Fixture**                     **Description**              **Priority**
  ------------------------------- ---------------------------- --------------
  scubagear-v5.4-full.json        Complete ScubaGear export    High

  ksi-enriched-tier2.yaml         Tier 2 enriched KSI data     High

  evidence-bundle-signed.json     Pre-signed evidence bundle   Medium

  oscal-poam-baseline.json        Known-good OSCAL POA&M       Medium

  multi-tenant-two-tenants.json   Two-tenant fixture           Low
  ---------------------------------------------------------------------------

7\. CI/CD Quality Gates

7.1 Workflow Inventory (31 workflows)

  -----------------------------------------------------------------------------------------------------------------------
  **Category**     **Workflows**                                                                       **Trigger**
  ---------------- ----------------------------------------------------------------------------------- ------------------
  Core CI          ci.yml, lint.yml                                                                    Every push/PR

  Security         ai-security-audit.yml, security-scan.yml, verify-signatures.yml                     Push + schedule

  Documentation    generate-docs.yml, generate-docx-exports.yml, deploy-docs.yml, docs.yml             Push to main

  Artifact Gen     generate-artifacts.yml, generate_artifacts.yml, render-and-insert-diagrams.yml      Push to main

  SCuBA Pipeline   adapter-run-scuba.yml, scuba-nightly.yml                                            Manual + nightly

  Compliance       compliance-mapping.yml, canon-validation.yml, crosswalk-regeneration.yml            Push + schedule

  Governance       drift-detection.yml, drift-scan.yml, dashboard-export.yml, metadata-validator.yml   Push + schedule

  Maintenance      changelog.yml, repo-hygiene.yml, rename-visuals.yml, appendix-sync.yml              Push

  Deployment       deploy.yml, publish.yml, push-adapters-workflow.yml                                 Tag/release

  Enrichment       ksi-enrichment.yml                                                                  Manual

  Utility          create-roadmap-issues.yml, validate-workflow-serialization.yml                      Manual
  -----------------------------------------------------------------------------------------------------------------------

7.2 CI Quality Gates

  -----------------------------------------------------------------------------------------------------------------------
  **Gate**            **Workflow**                          **Threshold**                 **Status**
  ------------------- ------------------------------------- ----------------------------- -------------------------------
  Tests pass          ci.yml                                100% pass rate                7--9/15 checks (needs repair)

  Lint clean          lint.yml                              Zero ruff errors              Active fixes ongoing

  Coverage floor      ci.yml                                ≥ 45% line coverage           Enforced

  Security scan       security-scan.yml                     Zero high-severity findings   Passing

  Workflow validity   validate-workflow-serialization.yml   All YAML parseable            Passing
  -----------------------------------------------------------------------------------------------------------------------

7.3 CI Health --- Current Issues

  --------------------------------------------------------------------------------------------------------------
  **Issue**                                 **Workflow**   **Root Cause**                    **Status**
  ----------------------------------------- -------------- --------------------------------- -------------------
  Pydantic Policy.scope.boundaries error    ci.yml         Model field mismatch              Fix committed

  \_stable_hash including volatile fields   ci.yml         Evidence hash non-deterministic   Fix committed

  ruff SIM108 ternary warnings              lint.yml       Style enforcement                 Fixes in progress

  noqa B008 on typer.Option defaults        lint.yml       False positives                   Fixes committed

  4 corrupted workflow YAML files           Various        CodeMirror corruption             Fixed
  --------------------------------------------------------------------------------------------------------------

8\. Test Execution Procedures

8.1 Local Development

\# Full suite pytest tests/ -v \# Individual plane testing pytest tests/test_scuba_transform_plane.py -v pytest tests/test_ksi_eval_plane.py -v pytest tests/test_evidence_build_plane.py -v pytest tests/test_oscal_generate_plane.py -v \# Determinism validation pytest tests/test_scuba_transformer_determinism.py -v pytest tests/test_ir_hash_stability.py -v \# Coverage report pytest tests/ -v \--cov=src/uiao_core \--cov-report=html \# Tier-specific filtering pytest tests/ -v -k \"T1\" \# Unit tests only pytest tests/ -v -k \"T3\" \# Plane tests only pytest tests/ -v -k \"T5\" \# Determinism tests only

8.2 CI Execution

\# 1. Install pip install -e \'.\[dev\]\' \# 2. Lint ruff check src/ tests/ \# 3. Test pytest tests/ -v \--cov=src/uiao_core \--cov-fail-under=45 \# 4. Report \# Coverage uploaded as artifact

8.3 Nightly SCuBA Assessment

6.  Authenticate to M365 tenant

7.  Execute ScubaGear assessment

8.  Run full 4-plane pipeline

9.  Compare against previous baseline

10. Generate drift report

11. Notify on failures

9\. Determinism Validation Protocol

9.1 Determinism Test Requirements

  ---------------------------------------------------------------------
  **Requirement**               **Test File**
  ----------------------------- ---------------------------------------
  SCuBA transform determinism   test_scuba_transformer_determinism.py

  IR hash stability             test_ir_hash_stability.py

  Cross-plane determinism       **GAP G1** --- needs building
  ---------------------------------------------------------------------

9.2 Hash Stability Contract

+-----------------------------------------------------------------------------+
| **Hash Stability Contract**                                                 |
|                                                                             |
| **Given:** ScubaGear export *S* at time *T*                                 |
|                                                                             |
| **When:** Pipeline runs at T+0 and T+N                                      |
|                                                                             |
| **Then:** hash(output_T0) == hash(output_TN) for all N where S is unchanged |
+-----------------------------------------------------------------------------+

**Fields excluded from hash (volatile):**

- provenance.collected_at

- provenance.run_id

- metadata.pipeline_version

10\. FedRAMP Moderate Compliance Test Matrix

10.1 NIST 800-53 Control Families

  --------------------------------------------------------------------------------------------------------
  **Family**   **Controls**         **Pipeline Coverage**            **Primary Test**
  ------------ -------------------- -------------------------------- -------------------------------------
  AC           AC-1 through AC-25   Plane 2 KSI evaluation           test_ksi_eval_plane

  AU           AU-1 through AU-16   Plane 3 Evidence + Plane 2 KSI   test_evidence_build_plane

  CA           CA-1 through CA-9    Plane 4 OSCAL SAR                test_sar, test_oscal_generate_plane

  CM           CM-1 through CM-11   Plane 1 SCuBA + Plane 2 KSI      test_scuba_transform_plane

  IA           IA-1 through IA-12   Plane 2 KSI evaluation           test_ksi_eval_plane

  SC           SC-1 through SC-44   Plane 2 KSI evaluation           test_ksi_eval_plane

  SI           SI-1 through SI-16   Plane 1 SCuBA + Plane 2 KSI      test_scuba_transform_plane
  --------------------------------------------------------------------------------------------------------

10.2 Compliance Validation Tests

  ---------------------------------------------------------------------------------------------------------------------
  **\#**   **Scenario**                             **What It Proves**                                  **Status**
  -------- ---------------------------------------- --------------------------------------------------- ---------------
  1        ScubaGear JSON → IR transform            All SCuBA findings are captured without data loss   Passing

  2        KSI evaluation against control library   Every M365 control maps to NIST 800-53              Passing

  3        Evidence bundle generation + signing     Evidence chain is intact and tamper-evident         Passing

  4        OSCAL SSP generation                     SSP meets OSCAL 1.1.2 schema                        Passing

  5        OSCAL POA&M generation                   Open findings correctly populate POA&M items        Passing

  6        OSCAL SAR generation                     Assessment results meet FedRAMP SAR format          Passing

  7        BOD 25-01 requirement mapping            All 11 BOD requirements are evaluated               **GAP** (G11)
  ---------------------------------------------------------------------------------------------------------------------

11\. Test Plan for Gap Modules

11.1 BOD 25-01 Compliance Assessor

**Target:** src/uiao_core/compliance/bod_25_01.py

  ----------------------------------------------------------------------------------------------------------
  **\#**   **Scenario**                                      **Type**   **Expected Result**
  -------- ------------------------------------------------- ---------- ------------------------------------
  1        All 11 BOD requirements present in assessment     T6         Complete requirement coverage

  2        SCuBA findings map to BOD requirements            T2         Correct cross-reference

  3        Non-compliant finding generates remediation       T1         Remediation action created

  4        Compliant finding generates passing status        T1         Status set to SATISFIED

  5        Missing SCuBA data generates partial assessment   T1         Graceful degradation with warnings
  ----------------------------------------------------------------------------------------------------------

11.2 Leg 2 Inbound Policy Engine

**Target:** src/uiao_core/governance/leg2_engine.py

  -----------------------------------------------------------------------------------------------
  **\#**   **Scenario**                                **Type**   **Expected Result**
  -------- ------------------------------------------- ---------- -------------------------------
  1        Valid policy YAML ingested successfully     T1         Policy loaded into registry

  2        Malformed policy rejected with error        T1         ValidationError raised

  3        Policy update triggers re-evaluation        T2         Affected controls re-assessed

  4        Conflicting policies resolved by priority   T1         Higher-priority policy wins

  5        Policy version history maintained           T1         Previous versions accessible
  -----------------------------------------------------------------------------------------------

11.3 Governance Event Engine

**Target:** src/uiao_core/governance/event_engine.py

  -----------------------------------------------------------------------------------------------------
  **\#**   **Scenario**                               **Type**   **Expected Result**
  -------- ------------------------------------------ ---------- --------------------------------------
  1        Drift event triggers governance action     T2         Action created and queued

  2        SLA breach event escalates notification    T2         Escalation path followed

  3        Duplicate events deduplicated              T1         Single action for N identical events

  4        Event ordering preserved under load        T1         FIFO ordering maintained

  5        Event replay produces idempotent results   T5         Same state after replay
  -----------------------------------------------------------------------------------------------------

11.4 Multi-Tenant Isolation

**Target:** src/uiao_core/governance/multi_tenant.py

  -----------------------------------------------------------------------------------------------------
  **\#**   **Scenario**                                     **Type**   **Expected Result**
  -------- ------------------------------------------------ ---------- --------------------------------
  1        Tenant A data invisible to Tenant B              T2         Zero cross-tenant data leakage

  2        Tenant-scoped query returns only own data        T1         Correct tenant filtering

  3        Cross-tenant aggregation requires admin role     T2         PermissionError for non-admin

  4        Tenant creation initializes isolated namespace   T1         Empty namespace created

  5        Tenant deletion removes all associated data      T1         Complete cleanup verified
  -----------------------------------------------------------------------------------------------------

12\. Regression Test Strategy

12.1 Golden File Testing

tests/golden/ ├── plane1_scuba_ir_output.json ├── plane2_ksi_eval_output.json ├── plane3_evidence_bundle.json ├── plane4_oscal_ssp.json ├── plane4_oscal_poam.json └── full_pipeline_hash.sha256

**Update protocol:** Only via explicit PR with \[golden-update\] commit message.

12.2 Regression Detection

def test_plane1_regression(): \"\"\"Compare Plane 1 output against golden file.\"\"\" result = run_plane1(fixture=\"scubagear-v5.4.json\") golden = load_golden(\"plane1_scuba_ir_output.json\") assert result == golden, ( f\"Plane 1 regression detected.\\n\" f\"Diff: {diff_json(golden, result)}\" )

13\. Coverage Targets

13.1 Coverage Goals by Phase

  ------------------------------------------
  **Version**   **Target**      **Date**
  ------------- --------------- ------------
  v2.0.0        45% (current)   Now

  v2.1.0        60%             2026-05-01

  v2.2.0        75%             2026-06-01

  v3.0.0        85%             2026-08-01
  ------------------------------------------

13.2 Per-Module Coverage Targets

  --------------------------------------------------------------
  **Module**   **Current (est.)**   **Target**   **Priority**
  ------------ -------------------- ------------ ---------------
  scuba        70%                  90%          High

  ksi          65%                  90%          High

  evidence     60%                  85%          High

  oscal        55%                  85%          High

  ir           50%                  80%          Medium

  models       45%                  80%          Medium

  governance   40%                  75%          Medium

  ssp          55%                  80%          Medium

  onboarding   0%                   60%          High (Gap G2)

  validators   20%                  70%          High (Gap G4)
  --------------------------------------------------------------

14\. Test Naming Conventions

  ------------------------------------------------------------------------------------------------
  **Element**   **Convention**                            **Example**
  ------------- ----------------------------------------- ----------------------------------------
  File          test\_{module}\_{aspect}.py               test_scuba_transform_plane.py

  Function      test\_{what}\_{condition}\_{expected}()   test_transform_valid_json_returns_ir()

  Class         Test{Module}{Aspect}                      TestScubaTransformPlane
  ------------------------------------------------------------------------------------------------

15\. Appendices

Appendix A: Test Execution Checklist (Pre-Release)

12. All T0--T4 tests pass locally

13. All T5 determinism tests pass

14. Coverage ≥ target for current version

15. No ruff lint errors

16. Golden file comparison passes

17. CI pipeline green on main branch

18. Security scan shows zero high-severity findings

19. Changelog updated with test changes

Appendix B: Test File to Module Traceability Matrix

  ----------------------------------------------------------------------------------------------------------------------------
  **\#**   **Source Module**   **Primary Test File**           **Secondary Test File(s)**
  -------- ------------------- ------------------------------- ---------------------------------------------------------------
  1        scuba               test_scuba_transform_plane.py   test_scuba_adapter.py, test_scuba_transformer_determinism.py

  2        ksi                 test_ksi_eval_plane.py          test_control_library.py

  3        evidence            test_evidence_build_plane.py    test_evidence.py, test_evidence_bundle.py

  4        oscal               test_oscal_generate_plane.py    test_poam.py, test_poam_export.py, test_sar.py

  5        ir                  test_ir_hash_stability.py       test_ir_cli.py, test_ir_validator.py

  6        models              test_models.py                  ---

  7        adapters            test_adapters.py                test_scuba_adapter.py

  8        cli                 test_cli.py                     test_cli_ssp.py, test_ir_cli.py, test_ir_governance_cli.py

  9        ssp                 test_ssp_narrative.py           test_ssp_lineage.py, test_ssp_inject.py, test_cli_ssp.py

  10       diff                test_diff_engine.py             ---

  11       dashboard           test_ir_dashboard.py            ---

  12       freshness           test_ir_freshness.py            test_ir_freshness_schedule.py

  13       governance          test_governance_actions.py      test_drift_detection.py, test_ir_governance_cli.py

  14       coverage            test_coverage_export.py         ---

  15       monitoring          test_monitoring_dashboard.py    ---

  16       auditor             test_auditor_bundle.py          ---

  17       generators          test_generators.py              test_briefing.py, test_diagrams.py, test_generate_diagrams.py

  18       collectors          test_cyberark_sync.py           test_local_sync.py

  19       validators          test_ir_validator.py            ---

  20       abstractions        test_abstractions.py            ---

  21       onboarding          **GAP G2** --- no tests         ---

  22       utils               test_mover_logic.py             test_workflow_serialization.py
  ----------------------------------------------------------------------------------------------------------------------------

Appendix C: Document Revision History

  ---------------------------------------------------------------
  **Version**   **Date**     **Author**         **Description**
  ------------- ------------ ------------------ -----------------
  1.0.0         2026-04-11   Michael Stratton   Initial release

  ---------------------------------------------------------------

> **

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
