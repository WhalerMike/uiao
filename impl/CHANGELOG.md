# Changelog — uiao-impl

All notable changes to the UIAO implementation repository.

## [1.0.0] — 2026-04-16

### Added
- **15 adapter implementations** subclassing `DatabaseAdapterBase` — zero stubs remaining
  - Tier 1 (prior): entra-id, service-now, scuba, scubagear
  - Tier 2: m365, palo-alto, terraform
  - Tier 3: vuln-scan, stig-compliance, patch-state
  - Tier 4: cyberark, infoblox, intune
  - Tier 5: mainframe, pki-ca, siem
- **4 real parser modules** with vendor-format data handling:
  - `terraform_parser.py` — state (v4 JSON), plan JSON, HCL2 (via python-hcl2), three-way diff
  - `m365_parser.py` — Graph API entities, security policies, tenant config, baseline comparison
  - `paloalto_parser.py` — PAN-OS security rule XML, NAT rule XML, ruleset comparison
  - `vulnscan_parser.py` — scanner findings with CVE/CVSS, severity summarization
- **`adapter_to_oscal.py`** bridge module:
  - `claims_to_ir_evidence()` — adapter ClaimSet → IR Evidence
  - `drift_to_ir_states()` — adapter DriftReport → IR DriftState
  - `build_adapter_bundle()` — full adapter output → EvidenceBundle
  - `drift_to_poam_findings()` — DriftReport → POA&M findings
  - `build_adapter_poam()` — DriftReport → OSCAL POA&M
  - `build_adapter_ssp()` — ClaimSet → OSCAL SSP (with minimal skeleton)
  - `inject_adapter_evidence_into_ssp()` — generic SSP evidence injection
- **`remediation.py`** — POA&M → ServiceNow change request pipeline
- **`retry.py`** — shared exponential-backoff retry with rate-limit support
- **`conformance_check.py`** — automated 420-criteria conformance matrix runner
  - `--json` output for Evidence Fabric
  - `--markdown` output for AVS doc auto-generation
  - `--adapter=ID` for single-adapter targeting
- **`cli/adapter_oscal.py`** — CLI commands: `adapter-oscal sar/poam/ssp`
- **15 fixture files** with realistic vendor-format test data
- **`acceptance-tests.yml`** — Phase 4 CI workflow (auto-skip without credentials)
- **`adapter-conformance.yml`** — CI gate enforcing 420/420 on adapter PRs

### Changed
- `entra_adapter.py` — `ADAPTER_ID` fixed from `"entra"` to `"entra-id"` (matches canon registry)
- `entra_adapter.py` — `collect_evidence()` now returns `EvidenceObject` (was returning `dict`)
- `conftest.py` — removed `test_scuba_transformer_determinism` from skip list (16 tests re-enabled)
- `pyproject.toml` — added `python-hcl2>=4.0.0` dependency

### Tests
- 420/420 conformance criteria across 14 runtime adapters
- 37 end-to-end OSCAL pipeline tests (SAR 18 + POA&M 11 + SSP 8)
- 9 remediation pipeline tests (drift → POA&M → ServiceNow round-trip)
- 80+ behavioral tests against fixture data
- 10 retry utility tests
- 16 previously-skipped ScuBA transformer tests re-enabled
- 11 Phase 4 acceptance test stubs (auto-skip without credentials)
