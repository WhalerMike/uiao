UIAO-Core API Reference

**Document ID:** UIAO_API_001

**Version:** 1.0.0

**Classification:** Controlled

**Date:** 2026-04-11

1\. CLI Commands

1.1 SCuBA Commands

uiao scuba run

Execute a ScubaGear assessment against the configured M365 tenant.

Usage: uiao scuba run \[OPTIONS\]

  ------------------------------------------------------------------------------------
  **Option**        **Type**   **Default**   **Description**
  ----------------- ---------- ------------- -----------------------------------------
  \--products       str        all           Comma-separated M365 products to assess

  \--output         Path       results/      Output directory for ScubaGear JSON

  \--authenticate   flag       false         Force re-authentication to M365

  \--tenant-id      str        env           Override M365 tenant ID
  ------------------------------------------------------------------------------------

uiao scuba transform

Transform ScubaGear JSON output to Intermediate Representation.

Usage: uiao scuba transform \[OPTIONS\]

  ------------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- ----------------------------------
  \--input     Path       required      Path to ScubaGear JSON file

  \--output    Path       ir/           Output directory for IR envelope

  \--format    str        json          Output format: json, yaml
  ------------------------------------------------------------------------

uiao scuba status

Show current assessment status and history.

Usage: uiao scuba status \[OPTIONS\]

  ------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- ----------------------------
  \--history   flag       false         Show all previous runs

  \--format    str        table         Output format: table, json
  ------------------------------------------------------------------

uiao scuba diff

Compare two SCuBA assessment runs.

Usage: uiao scuba diff \[OPTIONS\]

  -----------------------------------------------------------------------------
  **Option**    **Type**   **Default**   **Description**
  ------------- ---------- ------------- --------------------------------------
  \--baseline   str        required      Baseline run identifier

  \--current    str        latest        Current run identifier

  \--format     str        table         Output format: table, json, markdown
  -----------------------------------------------------------------------------

1.2 KSI Commands

uiao ksi evaluate

Evaluate IR against the KSI control library.

Usage: uiao ksi evaluate \[OPTIONS\]

  -----------------------------------------------------------------------------------------
  **Option**    **Type**   **Default**        **Description**
  ------------- ---------- ------------------ ---------------------------------------------
  \--ir         Path       latest             Path to IR envelope or "latest"

  \--library    Path       config             Path to control library YAML

  \--baseline   str        fedramp-moderate   Compliance baseline to evaluate against

  \--full       flag       false              Re-evaluate all controls (not just changed)
  -----------------------------------------------------------------------------------------

uiao ksi findings

List findings by severity or ID.

Usage: uiao ksi findings \[OPTIONS\]

  ----------------------------------------------------------------------------------------
  **Option**    **Type**   **Default**   **Description**
  ------------- ---------- ------------- -------------------------------------------------
  \--severity   str        all           Filter by severity: critical, high, medium, low

  \--id         str        none          Show specific finding by ID

  \--detail     flag       false         Show full finding details
  ----------------------------------------------------------------------------------------

uiao ksi enrich

Enrich KSI data with external threat intelligence.

Usage: uiao ksi enrich \[OPTIONS\]

  --------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- ------------------------------
  \--source    str        required      Enrichment source identifier

  \--output    Path       ksi/          Output directory
  --------------------------------------------------------------------

uiao ksi validate

Validate control library YAML syntax and semantics.

Usage: uiao ksi validate \[OPTIONS\]

  ------------------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- ----------------------------------------
  \--config    Path       default       Path to configuration file to validate

  \--strict    flag       false         Fail on warnings as well as errors
  ------------------------------------------------------------------------------

1.3 Evidence Commands

uiao evidence build

Usage: uiao evidence build \[OPTIONS\]

  ------------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- ----------------------------------
  \--eval      Path       latest        Path to KSI evaluation results

  \--output    Path       evidence/     Output directory

  \--sign      flag       true          Sign the bundle with HMAC-SHA256
  ------------------------------------------------------------------------

uiao evidence verify

Usage: uiao evidence verify \[OPTIONS\]

  -----------------------------------------------------------------
  **Option**    **Type**   **Default**   **Description**
  ------------- ---------- ------------- --------------------------
  \--bundle     Path       required      Path to evidence bundle

  \--key-file   Path       env           Path to signing key file
  -----------------------------------------------------------------

uiao evidence freshness

Usage: uiao evidence freshness \[OPTIONS\]

  --------------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- ------------------------------------
  \--all       flag       false         Show all evidence, not just latest

  \--sort      str        name          Sort by: name, age, grade
  --------------------------------------------------------------------------

uiao evidence re-sign

Usage: uiao evidence re-sign \[OPTIONS\]

  ----------------------------------------------------------------
  **Option**    **Type**   **Default**   **Description**
  ------------- ---------- ------------- -------------------------
  \--bundle     Path       latest        Path to evidence bundle

  \--key-file   Path       required      Path to new signing key
  ----------------------------------------------------------------

1.4 OSCAL Commands

uiao oscal generate

Usage: uiao oscal generate \[OPTIONS\]

  --------------------------------------------------------------------------------------
  **Option**    **Type**   **Default**   **Description**
  ------------- ---------- ------------- -----------------------------------------------
  \--evidence   Path       latest        Path to signed evidence bundle

  \--output     Path       oscal/        Output directory

  \--full       flag       false         Generate all artifact types (SSP, POA&M, SAR)

  \--format     str        json          Output format: json, xml
  --------------------------------------------------------------------------------------

uiao oscal validate

Usage: uiao oscal validate \[OPTIONS\]

  ----------------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- --------------------------------------
  \--dir       Path       required      Directory containing OSCAL artifacts

  \--schema    str        1.1.2         OSCAL schema version
  ----------------------------------------------------------------------------

1.5 SSP Commands

uiao ssp narrative

Usage: uiao ssp narrative \[OPTIONS\]

  ----------------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- --------------------------------------
  \--output    Path       ssp/          Output directory for narrative files

  \--format    str        markdown      Output format: markdown, docx
  ----------------------------------------------------------------------------

uiao ssp lineage

Usage: uiao ssp lineage \[OPTIONS\]

  ----------------------------------------------------------------------------
  **Option**    **Type**   **Default**   **Description**
  ------------- ---------- ------------- -------------------------------------
  \--claim-id   str        none          Trace lineage for specific claim ID

  \--output     Path       ssp/          Output directory

  \--format     str        json          Output format: json, markdown
  ----------------------------------------------------------------------------

1.6 Diff Commands

uiao diff report

Usage: uiao diff report \[OPTIONS\]

  ----------------------------------------------------------------------------------
  **Option**    **Type**   **Default**   **Description**
  ------------- ---------- ------------- -------------------------------------------
  \--baseline   str        required      Baseline run or date

  \--current    str        latest        Current run or date

  \--since      str        none          Alternative: show changes since date/time

  \--format     str        table         Output format: table, json, markdown
  ----------------------------------------------------------------------------------

uiao diff show

Usage: uiao diff show \[OPTIONS\]

  ----------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- --------------------------------
  \--finding   str        required      Finding ID to show details for

  \--history   flag       false         Show full historical trend
  ----------------------------------------------------------------------

1.7 Dashboard Commands

uiao dashboard export

Usage: uiao dashboard export \[OPTIONS\]

  -----------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- ---------------------------
  \--output    Path       dashboard/    Output directory

  \--format    str        html          Output format: html, json
  -----------------------------------------------------------------

1.8 Coverage Commands

uiao coverage export

Usage: uiao coverage export \[OPTIONS\]

  --------------------------------------------------------------------------------
  **Option**    **Type**   **Default**        **Description**
  ------------- ---------- ------------------ ------------------------------------
  \--baseline   str        fedramp-moderate   Compliance baseline

  \--format     str        json               Output format: json, csv, markdown

  \--output     Path       coverage/          Output directory
  --------------------------------------------------------------------------------

uiao coverage trend

Usage: uiao coverage trend \[OPTIONS\]

  ----------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- --------------------------------
  \--period    str        30d           Trend period: 7d, 30d, 90d, 1y

  \--output    Path       stdout        Output file path
  ----------------------------------------------------------------------

1.9 Governance Commands

uiao governance scorecard

Usage: uiao governance scorecard \[OPTIONS\]

  ------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- ----------------------------
  \--format    str        table         Output format: table, json

  ------------------------------------------------------------------

uiao governance actions

Usage: uiao governance actions \[OPTIONS\]

  ------------------------------------------------------------------------------------------------------------
  **Option**       **Type**   **Default**   **Description**
  ---------------- ---------- ------------- ------------------------------------------------------------------
  \--since         str        none          Show actions since date/time

  \--type          str        all           Filter by type: remediate, accept, mitigate, transfer, retention

  \--test-notify   flag       false         Send test notification

  \--channel       str        none          Notification channel for test
  ------------------------------------------------------------------------------------------------------------

uiao governance poam

Usage: uiao governance poam \[OPTIONS\]

  -----------------------------------------------------------------------------------
  **Option**   **Type**   **Default**   **Description**
  ------------ ---------- ------------- ---------------------------------------------
  \--status    str        all           Filter: open, closed, in-progress, accepted

  \--create    flag       false         Create new POA&M item

  \--finding   str        none          Finding ID for new POA&M item
  -----------------------------------------------------------------------------------

uiao governance poam-transition

Usage: uiao governance poam-transition \[OPTIONS\]

  ---------------------------------------------------------------------------------------------------------
  **Option**         **Type**   **Default**   **Description**
  ------------------ ---------- ------------- -------------------------------------------------------------
  \--id              str        required      POA&M item identifier

  \--to              str        required      Target state: open, in-progress, closed, accepted, verified

  \--justification   str        none          Justification for state change
  ---------------------------------------------------------------------------------------------------------

1.10 Auditor Commands

uiao auditor bundle

Usage: uiao auditor bundle \[OPTIONS\]

  ------------------------------------------------------------------------------------
  **Option**            **Type**   **Default**       **Description**
  --------------------- ---------- ----------------- ---------------------------------
  \--output             Path       auditor-bundle/   Output directory

  \--month              str        current           Target month: current, YYYY-MM

  \--include-evidence   flag       true              Include signed evidence bundles
  ------------------------------------------------------------------------------------

2\. Python API

2.1 Pipeline Entry Points

from uiao_core.scuba.transformer import ScubaTransformer from uiao_core.ksi.evaluate import KSIEvaluator from uiao_core.evidence.builder import EvidenceBuilder from uiao_core.oscal.generator import OSCALGenerator \# Plane 1: SCuBA to IR transformer = ScubaTransformer() ir_envelope = transformer.transform(scuba_json_path=\"results/ScubaResults.json\") \# Plane 2: IR to KSI evaluator = KSIEvaluator(library_path=\"generation-inputs/ksi/\") eval_results = evaluator.evaluate(ir_envelope) \# Plane 3: Evidence Build builder = EvidenceBuilder(signing_key=os.environ\[\"UIAO_SIGNING_KEY\"\]) evidence_bundle = builder.build(eval_results) \# Plane 4: OSCAL Generate generator = OSCALGenerator() oscal_artifacts = generator.generate(evidence_bundle)

2.2 Core Data Models

from uiao_core.models import NormalizedClaim claim = NormalizedClaim( claim_id=\"scuba.exo.MS.EXO.1.1v1\", source=\"scubagear\", product=\"exo\", rule_id=\"MS.EXO.1.1v1\", result=\"fail\", severity=\"high\", title=\"External forwarding restricted\", description=\"Automatic forwarding to external domains SHALL be disabled.\", control_mappings=\[\"AC-4\", \"SC-7\"\], collected_at=\"2026-04-11T02:00:00Z\" )

2.3 Adapter Interface

from uiao_core.abstractions import ComplianceAdapter class MyAdapter(ComplianceAdapter): def ingest(self, source_path: str) -\> dict: \"\"\"Load raw data from source.\"\"\" \... def normalize(self, raw_data: dict) -\> list\[NormalizedClaim\]: \"\"\"Convert to NormalizedClaim objects.\"\"\" \... def validate(self, claims: list\[NormalizedClaim\]) -\> bool: \"\"\"Validate normalized claims.\"\"\" \... def metadata(self) -\> dict: \"\"\"Return adapter metadata.\"\"\" \... def capabilities(self) -\> list\[str\]: \"\"\"Return supported products/features.\"\"\" \...

2.4 Diff Engine

from uiao_core.diff.engine import DiffEngine engine = DiffEngine() diff_result = engine.compare(baseline=ir_old, current=ir_new) for change in diff_result.changes: print(f\"{change.type}: {change.claim_id} - {change.description}\")

3\. Error Codes

  --------------------------------------------------------------------
  **Code**       **Module**   **Description**
  -------------- ------------ ----------------------------------------
  UIAO-SCB-001   scuba        ScubaGear JSON file not found

  UIAO-SCB-002   scuba        ScubaGear JSON parse error

  UIAO-SCB-003   scuba        ScubaGear schema version mismatch

  UIAO-SCB-004   scuba        ScubaGear product not recognized

  UIAO-KSI-001   ksi          Control library YAML not found

  UIAO-KSI-002   ksi          Control library YAML parse error

  UIAO-KSI-003   ksi          Unmapped claim: no matching control

  UIAO-KSI-004   ksi          Enrichment source unavailable

  UIAO-EVD-001   evidence     Evidence bundle build failed

  UIAO-EVD-002   evidence     Evidence signature verification failed

  UIAO-EVD-003   evidence     Evidence bundle expired

  UIAO-EVD-004   evidence     Signing key not configured

  UIAO-OSC-001   oscal        OSCAL schema validation failed

  UIAO-OSC-002   oscal        OSCAL generation error

  UIAO-OSC-003   oscal        Unsupported OSCAL schema version

  UIAO-SSP-001   ssp          Narrative template not found

  UIAO-SSP-002   ssp          Lineage trace broken

  UIAO-GOV-001   governance   POA&M state transition invalid

  UIAO-GOV-002   governance   Governance action creation failed

  UIAO-GOV-003   governance   Notification delivery failed

  UIAO-CFG-001   config       Configuration file not found

  UIAO-CFG-002   config       Configuration validation error

  UIAO-ADP-001   adapters     Adapter registration failed
  --------------------------------------------------------------------

4\. Environment Variables

  -----------------------------------------------------------------------------------------------------
  **Variable**              **Required**   **Default**   **Description**
  ------------------------- -------------- ------------- ----------------------------------------------
  UIAO_CONFIG_PATH          No             config/       Path to configuration directory

  UIAO_SIGNING_KEY          Yes            ---           HMAC-SHA256 signing key for evidence bundles

  UIAO_EVIDENCE_DIR         No             evidence/     Default evidence output directory

  UIAO_OSCAL_DIR            No             oscal/        Default OSCAL output directory

  UIAO_LOG_LEVEL            No             INFO          Logging level: DEBUG, INFO, WARNING, ERROR

  UIAO_M365_TENANT_ID       Yes            ---           M365 tenant identifier

  UIAO_M365_CLIENT_ID       Yes            ---           Azure AD application client ID

  UIAO_M365_CLIENT_SECRET   Yes            ---           Azure AD application client secret

  UIAO_SCUBAGEAR_PATH       No             auto          Override path to ScubaGear installation

  UIAO_RETENTION_DAYS       No             365           Evidence retention period in days

  UIAO_NOTIFY_WEBHOOK       No             ---           Teams webhook URL for notifications

  UIAO_SMTP_HOST            No             ---           SMTP server for email notifications

  UIAO_SMTP_PORT            No             587           SMTP server port

  UIAO_SMTP_USER            No             ---           SMTP authentication username

  UIAO_SMTP_PASS            No             ---           SMTP authentication password
  -----------------------------------------------------------------------------------------------------

Document Revision History

  ---------------------------------------------------------------
  **Version**   **Date**     **Author**         **Description**
  ------------- ------------ ------------------ -----------------
  1.0.0         2026-04-11   Michael Stratton   Initial release

  ---------------------------------------------------------------

> **

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
