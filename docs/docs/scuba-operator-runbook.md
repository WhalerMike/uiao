UIAO SCuBA Operator Runbook

**Document ID:** UIAO_SOR_001

**Version:** 1.0.0

**Classification:** Controlled

**Date:** 2026-04-11

1\. Daily Operations

1.1 Morning Check

\# 1. Verify nightly pipeline completed uiao scuba status \# 2. Check evidence freshness uiao evidence freshness \# 3. Review governance scorecard uiao governance scorecard \# 4. Check for drift uiao diff report \--since yesterday

1.2 Expected Healthy Output

SCuBA Status: Last run: 2026-04-11T02:00:00Z Status: SUCCESS Findings: 47 pass, 3 fail, 2 warn Pipeline: All 4 planes completed Evidence Freshness: Grade: FRESH (collected 6h ago) Next required: 2026-04-12T02:00:00Z Governance Scorecard: Overall: 89/100 Compliance: 92% Coverage: 78/325 automated Open POA&M items: 3

1.3 Alert Response Matrix

  -----------------------------------------------------------------------------------------------
  **Alert**              **Severity**   **Response**
  ---------------------- -------------- ---------------------------------------------------------
  Pipeline failure       Critical       Check logs, re-run pipeline, escalate if persists \> 1h

  Evidence expired       High           Trigger manual SCuBA assessment immediately

  New critical finding   High           Create POA&M item, notify ISSO within 4h

  Drift detected         Medium         Review diff report, assess impact, document response

  Evidence stale         Medium         Monitor; will auto-refresh at next nightly run

  Coverage decrease      Low            Investigate in weekly review

  Lint warnings          Low            Address in next development sprint
  -----------------------------------------------------------------------------------------------

2\. Weekly Operations

2.1 Weekly Compliance Review

\# 1. Generate weekly trend report uiao coverage trend \--period 7d \# 2. Review POA&M status uiao governance poam \--status open \# 3. Generate governance actions summary uiao governance actions \--since \"7 days ago\"

2.2 KSI Control Library Update

\# 1. Check for library updates uiao ksi validate \# 2. Enrich with latest threat data uiao ksi enrich \--source threat-intel \# 3. Re-evaluate all controls uiao ksi evaluate \--ir latest \--full

3\. Monthly Operations

3.1 Monthly ATO Package Generation

\# 1. Generate full OSCAL artifact set uiao oscal generate \--evidence latest \--full \# 2. Package auditor bundle uiao auditor bundle \--month current \# 3. Export SSP narrative uiao ssp narrative \--output monthly-ssp/ \# 4. Validate all artifacts uiao oscal validate \--dir monthly-ssp/

3.2 Evidence Retention Review

\# 1. List evidence by age uiao evidence freshness \--all \--sort age \# 2. Identify retention violations uiao governance actions \--type retention \# 3. Archive old evidence per policy uiao evidence archive \--older-than 90d

3.3 Control Coverage Trend Report

\# Generate 30-day trend uiao coverage trend \--period 30d \--output coverage-trend-monthly.json

4\. Ad-Hoc Operations

4.1 Running a Manual SCuBA Assessment

\# 1. Authenticate to M365 uiao scuba run \--authenticate \# 2. Execute assessment uiao scuba run \--products all \# 3. Transform to IR uiao scuba transform \--input results/ScubaResults.json \# 4. Run full pipeline uiao ksi evaluate \--ir latest uiao evidence build \--eval latest \# 5. Generate artifacts uiao oscal generate \--evidence latest

4.2 Generating an ATO Package

\# Single command for full ATO package uiao auditor bundle \--output ato-package/ \# Expected output: \# ato-package/ \# ├── oscal-ssp.json \# ├── oscal-poam.json \# ├── oscal-sar.json \# ├── evidence-bundle.json \# ├── evidence-bundle.sig \# ├── ssp-narrative.md \# ├── lineage-trace.json \# └── manifest.sha256

4.3 Investigating a Finding

\# 1. List findings by severity uiao ksi findings \--severity critical,high \# 2. Show finding details uiao ksi findings \--id MS.EXO.1.1v1 \--detail \# 3. Trace lineage to source uiao ssp lineage \--claim-id scuba.exo.MS.EXO.1.1v1 \# 4. Check historical trend uiao diff show \--finding MS.EXO.1.1v1 \--history

4.4 Comparing Two Assessment Runs

\# 1. Identify available runs uiao scuba status \--history \# 2. Generate diff report uiao diff report \--baseline run-2026-04-04 \--current run-2026-04-11 \# 3. Export diff as JSON uiao diff report \--baseline run-2026-04-04 \--current run-2026-04-11 \--format json

5\. Governance Workflows

5.1 POA&M Lifecycle

State Machine: ┌──────────┐ create ┌──────────┐ assign ┌──────────────┐ │ DETECTED │ ───────────── │ OPEN │ ──────────── │ IN PROGRESS │ └──────────┘ └──────────┘ └──────────────┘ │ ┌───────────────────────────┤ │ remediate │ accept risk ▼ ▼ ┌──────────┐ ┌──────────────┐ │ CLOSED │ │ ACCEPTED │ └──────────┘ └──────────────┘ │ │ verify ▼ ┌──────────┐ │ VERIFIED │ └──────────┘

\# Create POA&M item uiao governance poam \--create \--finding MS.EXO.1.1v1 \# Transition state uiao governance poam-transition \--id POAM-2026-001 \--to in-progress uiao governance poam-transition \--id POAM-2026-001 \--to closed \--justification \"Config updated\" \# List open POA&M items uiao governance poam \--status open

5.2 Drift Response

20. Receive drift alert from drift-detection.yml or daily check

21. Run uiao diff report \--since \<baseline\> to identify changes

22. Classify drift: intentional change vs. configuration regression

23. If regression: create POA&M item and initiate remediation

24. If intentional: update baseline and document justification

25. Update governance scorecard and notify stakeholders

5.3 SLA Enforcement

  ---------------------------------------------------------------------------------
  **Severity**    **Detection SLA**   **Remediation SLA**   **Escalation**
  --------------- ------------------- --------------------- -----------------------
  Critical        ≤ 1 hour            ≤ 24 hours            ISSO + AO immediately

  High            ≤ 4 hours           ≤ 7 days              ISSO within 4 hours

  Medium          ≤ 24 hours          ≤ 30 days             Weekly review

  Low             ≤ 7 days            ≤ 90 days             Monthly review

  Informational   Next review         Best effort           Quarterly review
  ---------------------------------------------------------------------------------

5.4 BOD 25-01 Compliance Check

\# Run BOD 25-01 assessment uiao ksi evaluate \--ir latest \--baseline bod-25-01 \# Generate BOD compliance report uiao coverage export \--baseline bod-25-01 \--format json

6\. Maintenance Procedures

6.1 Canon Update

26. Pull latest canon definitions from repository

27. Run uiao ksi validate to check for breaking changes

28. Run pytest tests/ -v to validate all tests pass

29. Update golden files if intentional changes: git commit -m \"\[golden-update\] Canon v2.x changes\"

30. Deploy updated canon to production

6.2 ScubaGear Version Upgrade

31. Review ScubaGear release notes for breaking changes

32. Update ScubaGear version in environment

33. Run manual assessment against test tenant

34. Compare output format against existing adapter expectations

35. Update adapter if JSON schema changed

36. Run full test suite: pytest tests/ -v

37. Update fixture files with new version output

6.3 Evidence State Management

\# Re-sign evidence with new key uiao evidence re-sign \--bundle latest \--key-file /path/to/key \# Verify evidence signature uiao evidence verify \--bundle evidence-bundle.json \# Archive evidence older than retention period uiao evidence archive \--older-than 365d

6.4 Notification Configuration

\# Test notification channel uiao governance actions \--test-notify \--channel teams \# Update notification config \# Edit config/notifications.yaml \# Validate configuration uiao ksi validate \--config config/notifications.yaml

7\. Troubleshooting

7.1 Common Issues

  -----------------------------------------------------------------------------------------------------------------------------------------------
  **Symptom**                             **Likely Cause**                         **Resolution**
  --------------------------------------- ---------------------------------------- --------------------------------------------------------------
  Pipeline hangs at Plane 1               ScubaGear JSON malformed                 Validate JSON with python -m json.tool

  Hash mismatch on re-run                 Volatile fields in hash                  Verify \_stable_hash excludes volatile fields

  OSCAL validation fails                  Schema version mismatch                  Check OSCAL version in config.yaml

  Evidence signature invalid              Key rotation or bundle tampering         Re-sign with current key; investigate if tampering suspected

  KSI evaluate returns zero controls      Control library not loaded               Verify generation-inputs/ksi/ contains YAML files

  CLI command not found                   Package not installed in editable mode   Run pip install -e \'.\[dev\]\'

  CI tests fail locally but pass remote   Environment differences                  Check Python version, dependencies, and fixture paths
  -----------------------------------------------------------------------------------------------------------------------------------------------

7.2 Log Locations

  -------------------------------------------------------------------------
  **Log**               **Location**          **Rotation**
  --------------------- --------------------- -----------------------------
  Pipeline execution    logs/pipeline.log     Daily, 30-day retention

  Evidence operations   logs/evidence.log     Daily, 90-day retention

  Governance actions    logs/governance.log   Daily, 365-day retention

  CI/CD workflow        GitHub Actions logs   Per GitHub retention policy
  -------------------------------------------------------------------------

7.3 Diagnostic Commands

\# Check Python environment python \--version pip show uiao-core \# Validate all configurations uiao ksi validate uiao oscal validate \--dir generation-inputs/ \# Run smoke test pytest tests/ -v -k \"T0\" \# Check pipeline end-to-end pytest tests/test_e2e.py -v

8\. Emergency Procedures

8.1 Evidence Chain Compromise

38. **Isolate:** Stop all pipeline runs immediately

39. **Assess:** Identify which evidence bundles are affected

40. **Notify:** Alert ISSO and AO within 1 hour

41. **Re-collect:** Run fresh ScubaGear assessment

42. **Re-sign:** Regenerate all evidence bundles with new signing key

43. **Verify:** Run full pipeline and compare against known-good baseline

8.2 Pipeline Determinism Failure

44. **Stop:** Halt nightly runs

45. **Diagnose:** Run pytest tests/test_scuba_transformer_determinism.py -v

46. **Isolate:** Identify which plane produces non-deterministic output

47. **Fix:** Check for volatile fields leaking into stable hash

48. **Validate:** Run full determinism suite before resuming nightly runs

8.3 Complete Pipeline Rebuild

\# 1. Clean environment pip uninstall uiao-core -y rm -rf .venv/ \# 2. Fresh install python -m venv .venv source .venv/bin/activate \# Linux/Mac pip install -e \'.\[dev\]\' \# 3. Validate pytest tests/ -v \--cov=src/uiao_core \# 4. Re-run pipeline uiao scuba run \--products all uiao ksi evaluate \--ir latest uiao evidence build \--eval latest uiao oscal generate \--evidence latest

9\. Operational Metrics

9.1 Key Performance Indicators

  ------------------------------------------------------------------------------------
  **KPI**                         **Target**   **Measurement**
  ------------------------------- ------------ ---------------------------------------
  Pipeline success rate           ≥ 99%        Successful nightly runs / total runs

  Evidence freshness              ≤ 24h        Time since last successful collection

  Mean time to detect (MTTD)      ≤ 4h         Time from change to drift alert

  Mean time to remediate (MTTR)   ≤ 7d         Time from detection to closure

  Open POA&M items                ≤ 5          Count of open items at any time

  Automated coverage              ≥ 30%        Automated controls / total controls

  Test pass rate                  100%         Passing tests / total tests
  ------------------------------------------------------------------------------------

9.2 Governance Scorecard Dimensions

  -------------------------------------------------------------------------
  **Dimension**        **Weight**   **Measurement**
  -------------------- ------------ ---------------------------------------
  Compliance posture   30%          Passing controls / total controls

  Evidence freshness   25%          Fresh evidence / total evidence

  POA&M health         20%          On-time closures / total closures

  Coverage breadth     15%          Automated controls / FedRAMP baseline

  Pipeline stability   10%          Successful runs / total runs
  -------------------------------------------------------------------------

Document Revision History

  ---------------------------------------------------------------
  **Version**   **Date**     **Author**         **Description**
  ------------- ------------ ------------------ -----------------
  1.0.0         2026-04-11   Michael Stratton   Initial release

  ---------------------------------------------------------------

> **

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
