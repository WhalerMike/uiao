UIAO-Core Configuration Reference

**Document ID:** UIAO_CFG_001

**Version:** 1.0.0

**Classification:** Controlled

**Date:** 2026-04-11

1\. Overview

UIAO-Core uses a layered configuration system. Configuration sources are resolved in the following priority order (highest first):

49. **CLI flags** --- Explicit command-line arguments

50. **Environment variables** --- UIAO\_\* prefixed variables

51. **YAML config files** --- Files in config/ directory

52. **Built-in defaults** --- Hardcoded in src/uiao_core/config.py

2\. KSI Control Library

2.1 Structure

\# generation-inputs/ksi/control-library.yaml version: \"2.0.0\" baseline: fedramp-moderate products: exo: name: Exchange Online rules: MS.EXO.1.1v1: title: \"External forwarding restricted\" description: \"Automatic forwarding to external domains SHALL be disabled.\" severity: high result_type: boolean control_mappings: - AC-4 - SC-7 evidence_type: configuration remediation: \"Disable automatic forwarding in Exchange admin center.\" aad: name: Azure Active Directory rules: MS.AAD.1.1v1: title: \"Legacy authentication blocked\" description: \"Legacy authentication SHALL be blocked.\" severity: critical result_type: boolean control_mappings: - AC-17(2) - IA-2(6) evidence_type: configuration remediation: \"Create conditional access policy to block legacy auth.\"

2.2 Field Reference

  --------------------------------------------------------------------------------------------------
  **Field**                   **Type**   **Required**   **Description**
  --------------------------- ---------- -------------- --------------------------------------------
  version                     str        Yes            Control library version (SemVer)

  baseline                    str        Yes            Compliance baseline identifier

  products                    dict       Yes            Product definitions keyed by short code

  products.\*.name            str        Yes            Human-readable product name

  products.\*.rules           dict       Yes            Rule definitions keyed by rule ID

  rules.\*.title              str        Yes            Short rule title

  rules.\*.description        str        Yes            Full rule description

  rules.\*.severity           str        Yes            critical, high, medium, low, informational

  rules.\*.result_type        str        Yes            boolean, numeric, enum

  rules.\*.control_mappings   list       Yes            NIST 800-53 control identifiers

  rules.\*.evidence_type      str        Yes            configuration, log, policy, procedure

  rules.\*.remediation        str        No             Recommended remediation steps
  --------------------------------------------------------------------------------------------------

2.3 Supported Products

  ----------------------------------------------------------------
  **Short Code**   **Product Name**         **ScubaGear Module**
  ---------------- ------------------------ ----------------------
  exo              Exchange Online          EXOConfig

  aad              Azure Active Directory   AADConfig

  defender         Microsoft Defender       DefenderConfig

  sharepoint       SharePoint Online        SPOConfig

  teams            Microsoft Teams          TeamsConfig

  powerbi          Power BI                 PowerBIConfig

  powerplatform    Power Platform           PowerPlatformConfig
  ----------------------------------------------------------------

2.4 Validation

\# Validate control library syntax uiao ksi validate \# Strict validation (fail on warnings) uiao ksi validate \--strict

Validation checks:

- YAML syntax validity

- Required fields present on every rule

- Severity values are in allowed set

- Control mappings reference valid NIST identifiers

- No duplicate rule IDs within a product

3\. Notification Configuration

3.1 Structure

\# config/notifications.yaml version: \"1.0.0\" channels: teams: type: webhook url: \"\${UIAO_NOTIFY_WEBHOOK}\" enabled: true smtp: type: email host: \"\${UIAO_SMTP_HOST}\" port: 587 username: \"\${UIAO_SMTP_USER}\" password: \"\${UIAO_SMTP_PASS}\" from: \"uiao-pipeline@example.gov\" to: - \"isso@example.gov\" - \"ao@example.gov\" enabled: true alerts: pipeline_failure: severity: critical channels: \[teams, smtp\] template: \"Pipeline failed: {{ error_message }}\" evidence_expired: severity: high channels: \[teams, smtp\] template: \"Evidence expired: last collected {{ last_collected }}\" drift_detected: severity: medium channels: \[teams\] template: \"Drift detected: {{ change_count }} changes since {{ baseline }}\" coverage_decrease: severity: low channels: \[teams\] template: \"Coverage decreased: {{ old_coverage }}% -\> {{ new_coverage }}%\" poam_sla_breach: severity: high channels: \[teams, smtp\] template: \"POA&M SLA breach: {{ poam_id }} overdue by {{ overdue_days }} days\"

3.2 Field Reference

  --------------------------------------------------------------------------------------------
  **Field**             **Type**   **Required**   **Description**
  --------------------- ---------- -------------- --------------------------------------------
  version               str        Yes            Config file version

  channels              dict       Yes            Notification channel definitions

  channels.\*.type      str        Yes            Channel type: webhook, email

  channels.\*.url       str        Cond.          Webhook URL (required for webhook type)

  channels.\*.host      str        Cond.          SMTP host (required for email type)

  channels.\*.port      int        No             SMTP port (default: 587)

  channels.\*.enabled   bool       No             Enable/disable channel (default: true)

  channels.\*.from      str        Cond.          Sender email (required for email type)

  channels.\*.to        list       Cond.          Recipient emails (required for email type)

  alerts                dict       Yes            Alert definitions

  alerts.\*.severity    str        Yes            Alert severity level

  alerts.\*.channels    list       Yes            Channels to deliver alert to
  --------------------------------------------------------------------------------------------

4\. Retention Policy Configuration

4.1 Structure

\# config/retention.yaml version: \"1.0.0\" policies: evidence_bundles: retention_days: 365 archive_after_days: 90 delete_after_days: 730 ir_envelopes: retention_days: 180 archive_after_days: 60 delete_after_days: 365 oscal_artifacts: retention_days: 730 archive_after_days: 365 delete_after_days: 1825 diff_reports: retention_days: 90 archive_after_days: 30 delete_after_days: 180 pipeline_logs: retention_days: 30 archive_after_days: 14 delete_after_days: 90 governance_actions: retention_days: 1825 archive_after_days: 365 delete_after_days: 2555 schedule: cleanup_interval: daily cleanup_time: \"03:00\" safety: require_confirmation: true dry_run_first: true

4.2 Field Reference

  ----------------------------------------------------------------------------------------------------
  **Field**                        **Type**   **Required**   **Description**
  -------------------------------- ---------- -------------- -----------------------------------------
  version                          str        Yes            Config file version

  policies                         dict       Yes            Retention policy definitions

  policies.\*.retention_days       int        Yes            Minimum retention in days

  policies.\*.archive_after_days   int        Yes            Move to archive after N days

  policies.\*.delete_after_days    int        Yes            Permanent deletion after N days

  schedule.cleanup_interval        str        Yes            daily, weekly, monthly

  schedule.cleanup_time            str        Yes            Time of day for cleanup (24h format)

  safety.require_confirmation      bool       No             Require manual confirmation for deletes

  safety.dry_run_first             bool       No             Run dry-run before actual cleanup
  ----------------------------------------------------------------------------------------------------

5\. Adapter Registry Configuration

5.1 Structure

\# config/adapters.yaml version: \"1.0.0\" adapters: scuba: module: uiao_core.adapters.scuba_adapter class: ScubaAdapter enabled: true priority: 1 defender_vuln: module: uiao_core.adapters.defender_vuln class: DefenderVulnAdapter enabled: true priority: 2 purview: module: uiao_core.adapters.purview class: PurviewAdapter enabled: false priority: 3 generic_csv: module: uiao_core.adapters.generic_csv class: GenericCSVAdapter enabled: true priority: 99 discovery: auto_discover: true entry_point_group: \"uiao_core.adapters\"

5.2 Field Reference

  ----------------------------------------------------------------------------------------------------
  **Field**                     **Type**   **Required**   **Description**
  ----------------------------- ---------- -------------- --------------------------------------------
  version                       str        Yes            Config file version

  adapters                      dict       Yes            Adapter definitions keyed by name

  adapters.\*.module            str        Yes            Python module path

  adapters.\*.class             str        Yes            Class name within module

  adapters.\*.enabled           bool       No             Enable/disable adapter (default: true)

  adapters.\*.priority          int        No             Loading priority (lower = higher priority)

  discovery.auto_discover       bool       No             Auto-discover via entry points

  discovery.entry_point_group   str        No             Entry point group name
  ----------------------------------------------------------------------------------------------------

6\. Pipeline Configuration

6.1 EnvelopeConfig Fields

  ------------------------------------------------------------------------------------
  **Field**            **Type**   **Default**        **Description**
  -------------------- ---------- ------------------ ---------------------------------
  system_name          str        required           System name for OSCAL artifacts

  system_id            UUID       auto               Unique system identifier

  baseline             str        fedramp-moderate   Compliance baseline

  oscal_version        str        1.1.2              Target OSCAL schema version

  organization         str        required           Organization name

  isso_name            str        required           ISSO name for artifacts

  isso_email           str        required           ISSO email for notifications

  hash_algorithm       str        sha256             Hash algorithm for stable hash

  signing_algorithm    str        hmac-sha256        Evidence signing algorithm

  deterministic_mode   bool       true               Enforce deterministic output
  ------------------------------------------------------------------------------------

6.2 Loading Order

53. config/pipeline.yaml --- Base pipeline configuration

54. config/pipeline.local.yaml --- Local overrides (gitignored)

55. Environment variables (UIAO\_\*)

56. CLI flags (highest priority)

7\. Scheduled Runner Configuration

7.1 Windows Task Scheduler

\<Task xmlns=\"http://schemas.microsoft.com/windows/2004/02/mit/task\"\> \<Triggers\> \<CalendarTrigger\> \<StartBoundary\>2026-04-11T02:00:00\</StartBoundary\> \<Repetition\> \<Interval\>P1D\</Interval\> \</Repetition\> \</CalendarTrigger\> \</Triggers\> \<Actions\> \<Exec\> \<Command\>C:\\uiao\\.venv\\Scripts\\python.exe\</Command\> \<Arguments\>-m uiao_core.cli scuba run \--products all\</Arguments\> \<WorkingDirectory\>C:\\uiao\</WorkingDirectory\> \</Exec\> \</Actions\> \</Task\>

7.2 Linux Cron

\# /etc/cron.d/uiao-nightly 0 2 \* \* \* uiao-svc cd /opt/uiao && .venv/bin/uiao scuba run \--products all 2\>&1 \| logger -t uiao

7.3 GitHub Actions

\# .github/workflows/scuba-nightly.yml name: SCuBA Nightly Assessment on: schedule: - cron: \'0 2 \* \* \*\' workflow_dispatch: jobs: assess: runs-on: ubuntu-latest steps: - uses: actions/checkout@v4 - name: Run SCuBA assessment run: \| pip install -e \'.\[dev\]\' uiao scuba run \--products all uiao ksi evaluate \--ir latest uiao evidence build \--eval latest uiao oscal generate \--evidence latest

8\. Environment Variable Reference

See Section 4 of the API Reference (docs/api-reference.md) for the complete environment variable table. All variables use the UIAO\_ prefix and support .env file loading in development environments.

Document Revision History

  ---------------------------------------------------------------
  **Version**   **Date**     **Author**         **Description**
  ------------- ------------ ------------------ -----------------
  1.0.0         2026-04-11   Michael Stratton   Initial release

  ---------------------------------------------------------------

> **

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
