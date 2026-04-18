---
document_id: UIAO_124
title: "UIAO Adapter Operations Runbook"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-16"
updated_at: "2026-04-16"
boundary: "GCC-Moderate"
---

# UIAO Adapter Operations Runbook

Operational procedures for running, monitoring, and troubleshooting
UIAO adapters in production.

---

## 1. Adapter Inventory

### 1.1 Current Adapters (16 registered, 15 implemented)

| Adapter | Class | Mission | Runner | Status | Controls |
|---------|-------|---------|--------|--------|----------|
| entra-id | modernization | integration | github-hosted | active | CM-8, IA-2, IA-4, AC-2 |
| m365 | modernization | integration | github-hosted | active | CM-2, CM-3, CM-8 |
| service-now | modernization | integration | github-hosted | active | IR-4, IR-5, IR-6, CM-3 |
| palo-alto | modernization | integration | on-prem | active | SC-7, CM-7, AC-4 |
| scuba | modernization | integration | github-hosted | active | CM-2, CM-6, CM-7 |
| terraform | modernization | integration | github-hosted | active | CM-2, CM-3, CM-6, CM-8, CA-7 |
| cyberark | modernization | integration | on-prem | reserved | IA-5, AC-2, AC-6 |
| infoblox | modernization | integration | on-prem | reserved | SC-20, SC-21, CM-8 |
| mainframe | modernization | integration | on-prem | reserved | CM-8, AC-2, AU-2 |
| scubagear | conformance | policy | github-hosted | active | CA-2, CA-5, CA-7, CM-6, CM-8, RA-5 |
| vuln-scan | conformance | telemetry | github-hosted | reserved | RA-5, CA-7, SI-2 |
| stig-compliance | conformance | policy | github-hosted | reserved | CM-6, CM-7, CA-7 |
| patch-state | conformance | telemetry | github-hosted | reserved | SI-2, CM-8, CA-7 |
| intune | conformance | telemetry | github-hosted | reserved | CM-8, SI-2, CA-7, SC-7 |
| pki-ca | conformance | telemetry | github-hosted | reserved | IA-5, SC-12, SC-13 |
| siem | conformance | telemetry | github-hosted | reserved | AU-2, AU-3, AU-6, SI-4 |

---

## 2. Running Adapters

### 2.1 CLI Commands

```bash
# Generate OSCAL SAR from adapter data
uiao adapter-oscal sar terraform path/to/terraform.tfstate --controls CM-2,CM-8

# Generate POA&M from drift
uiao adapter-oscal poam terraform path/to/plan.json --controls CM-3

# Generate SSP from claims
uiao adapter-oscal ssp terraform path/to/terraform.tfstate --system-name "My System"

# Run conformance check
python -m uiao.impl.adapters.conformance_check
python -m uiao.impl.adapters.conformance_check --json > report.json
python -m uiao.impl.adapters.conformance_check --markdown --adapter=terraform
```

### 2.2 Programmatic Usage

```python
from uiao.impl.adapters.terraform_adapter import TerraformAdapter

adapter = TerraformAdapter({"workspace": "prod"})
claims = adapter.extract_terraform_state("path/to/terraform.tfstate")
drift = adapter.consume_terraform_plan(plan_json)
evidence = adapter.generate_terraform_evidence(state_snapshot=state)
```

---

## 3. Monitoring

### 3.1 Health Checks

| Check | Frequency | Method | Alert on |
|-------|-----------|--------|----------|
| Conformance | Every PR | CI gate | Any criterion fails |
| Evidence freshness | Daily | Scheduler | Last evidence > 24h old |
| API connectivity | Hourly | Heartbeat | Connection failure |
| Credential expiry | Weekly | Cert check | < 30 days to expiry |

### 3.2 Key Metrics

| Metric | Target | Source |
|--------|--------|--------|
| Conformance score | 420/420 | conformance_check.py |
| Evidence latency | < 30s per adapter | Adapter timing |
| Drift detection rate | > 95% coverage | DriftReport analysis |
| OSCAL generation success | 100% | Pipeline tests |

---

## 4. Troubleshooting

### 4.1 Common Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Conformance < 30/30 | Method returns wrong type | Check return type matches base class |
| `NotImplementedError` | Extension method not implemented | Implement the method; zero stubs allowed |
| Empty ClaimSet | Fixture/API returns no data | Check fixture path; verify API credentials |
| Hash mismatch | Non-deterministic serialization | Use `self._hash()` with sorted keys |
| Rate limit (429) | API throttling | Use `from .retry import with_retry` |
| Connection refused | Wrong endpoint or network | Check config endpoint + runner network |
| Credential error | Expired or wrong secret | Rotate in GitHub Secrets |

### 4.2 Debugging Commands

```bash
# Run single adapter conformance with detail
python -m uiao.impl.adapters.conformance_check --adapter=terraform

# Run specific test file with verbose output
pytest tests/test_terraform_adapter.py -v --tb=long

# Generate JSON report for analysis
python -m uiao.impl.adapters.conformance_check --json | python -m json.tool
```

---

## 5. Credential Management

### 5.1 Credential Storage

ALL adapter credentials stored as GitHub Actions secrets. NEVER in code.

| Adapter | Secret name pattern | Rotation |
|---------|-------------------|----------|
| Entra ID | `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET` | 90 days |
| M365 | Same as Entra (same Graph API) | 90 days |
| ServiceNow | `SERVICENOW_TOKEN` | 90 days |
| Palo Alto | `PANOS_API_KEY` | 180 days |
| CyberArk | `CYBERARK_TOKEN` | 30 days |
| Terraform | `TF_TOKEN` (Terraform Cloud) | 90 days |

### 5.2 Rotation Procedure

1. Generate new credential from vendor portal
2. Update GitHub Secret in repository settings
3. Trigger a test run to verify
4. Log rotation in change management

---

## 6. Incident Response

### 6.1 Adapter Failure

1. Check CI: is the conformance gate green?
2. Check credentials: have they expired?
3. Check vendor API: is the service healthy?
4. Check network: can the runner reach the endpoint?
5. Roll back to last known-good state if needed

### 6.2 Data Quality Issue

1. Run conformance check on the specific adapter
2. Compare claim hashes against expected values
3. Check fixture file for corruption
4. Re-run with `--verbose` for detailed output

### 6.3 Security Incident

1. Immediately revoke any exposed credentials
2. Check Evidence Fabric for unauthorized evidence
3. Review adapter logs for anomalous activity
4. File incident report per IR-4 procedures

---

*End of Runbook — UIAO Adapter Operations Runbook v1.0*
