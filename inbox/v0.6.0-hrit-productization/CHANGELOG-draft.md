## [0.6.0] — TBD

**Theme: HRIT Single-ATO Productization.** Closes the runtime gap deferred by
ADR-054 §Implementation: the Single-ATO Reciprocity Model now emits signed,
OSCAL-mapped, evidence-graph-anchored reciprocity records per consuming agency,
with ConMon SLA enforcement and configuration-latitude drift detection. A
maintainer operating a single-ATO platform (OPM Solicitation 24322626R0007
anchor) can onboard a consuming agency, receive a signed `reciprocity-record.json`
plus a scoped OSCAL component-definition, and walk the 15-minute quickstart
against the synthetic three-agency (OPM + Treasury + IRS) fixture.

### Added

#### Canon

- **ADR-058** (`src/uiao/canon/adr/adr-058-hrit-productization-mission.md`) —
  HRIT Single-ATO Productization as v0.6.0 Mission Theme. Status: Accepted.
  Ratifies the runtime emission contract, ConMon SLA cadences (30-day draft SSP,
  45-day final SSP, 30-day reauthorization window), and the KSI-RECIP-001..008
  accountability signals.
- **UIAO_143** (`src/uiao/canon/specs/hrit-productization.md`) — HRIT
  Productization Operational Spec. Expands ADR-058 into the full operational
  narrative: reciprocity record lifecycle, per-agency bundle aggregation,
  configuration-latitude drift detection, and KSI mapping table.
- **UIAO_113 v1.2** (amendment to `src/uiao/canon/specs/graph-schema.md`) —
  Evidence Graph schema bumped to v1.2. New node types: `ato-decision`,
  `reciprocity-record`. New edge types: `ato-decision → reciprocity-record`,
  `reciprocity-record → consuming-agency`.
- **`reciprocity-record.schema.json`**
  (`src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json`) —
  JSON Schema 2020-12. Required fields: `controlling_ato_id`,
  `consuming_agency_code`, `reciprocity_basis`, `legal_basis` (enum),
  `effective_at`, `expires_at`, `configuration_latitude_ref`, `signature`
  (HMAC-SHA256: `algorithm`, `value`, `signed_at`, `signer`), `provenance`.
- **KSI-RECIP-001..008** (`src/uiao/rules/ksi/KSI-RECIP-*.yaml`) — Eight new
  Key Security Indicators covering legal-basis citation, controlling-ATO
  existence, expiry enforcement, configuration-latitude remediation ownership,
  SSP cadence (30-day draft, 45-day final), reauthorization SLA, per-agency
  bundle signature verification, and evidence-graph edge completeness. Mapping
  registry appended in `src/uiao/rules/ksi/uiao-control-to-ksi-mapping.yaml`.
- **`22_HRITProductization.qmd`** (`docs/docs/22_HRITProductization.qmd`) —
  Operational narrative for the HRIT productization theme. Two Mermaid diagrams:
  reciprocity-record lifecycle and per-agency bundle aggregation flow.

#### Runtime — six new modules

- **`src/uiao/oscal/reciprocity_record.py`** — `emit_reciprocity_record()`:
  produces a schema-valid, HMAC-SHA256-signed reciprocity record with OSCAL
  component-definition projection scoped to the consuming agency. Provenance
  block cites UIAO_140 + ADR-054.
- **`src/uiao/oscal/reciprocity_bundle.py`** —
  `aggregate_per_agency_bundle()`: bundles reciprocity-record + scoped
  component-definition + scoped assessment-results + provenance manifest into
  a directory independently verifiable by the consuming agency AO.
- **`src/uiao/monitoring/ato_cadence.py`** — Enforces 30-day draft SSP,
  45-day final SSP, and 30-day reauthorization-window SLAs. Emits `PASS |
  WARN | FAIL` with named SLA breaches and optional JSON output for downstream
  tooling.
- **`src/uiao/governance/config_latitude.py`** — Diffs observed tenant
  configuration against the SSP's enumerated configuration-latitude table;
  emits `DRIFT-SCHEMA` (P2 default) for each out-of-bounds parameter.
- **`src/uiao/canon/queries/configuration-latitude-violations.yaml`** — CQL
  query filtering drift findings to the configuration-latitude class.
- **`src/uiao/evidence/graph.py`** (if new) — Runtime traversal support for
  UIAO_113 v1.2 node and edge types added in this release.

#### CLI

- **`uiao reciprocity` sub-app** (`src/uiao/cli/reciprocity.py`, registered in
  `cli/app.py`): three commands:
  - `uiao reciprocity onboard-agency` — emit a signed reciprocity record for
    a consuming agency.
  - `uiao reciprocity list-records` — enumerate registered reciprocity records.
  - `uiao reciprocity verify` — verify a record's HMAC-SHA256 signature.
  All commands carry a runnable `Example::` block in `--help`.
- **`uiao conmon ato-cadence-check`** (new command in `cli/conmon.py`) —
  ConMon SLA cadence validator; wraps `src/uiao/monitoring/ato_cadence.py`.

#### Fixtures + quickstart

- **`examples/hrit/opm-treas-irs/`** — Synthetic three-agency fixture: OPM as
  controlling ATO, Treasury and IRS as consuming agencies. Includes one
  intentional configuration-latitude violation for drift-detector demonstration.
  Known-answer table per agency included.
- **`docs/docs/hrit-productization-quickstart.md`** — 10-step quickstart from
  `git clone` to three signed reciprocity records. Runs in <15 minutes on the
  synthetic fixture; no live Azure tenant or API keys required.

#### Tests

- **`tests/test_hrit_productization_smoke.py`** — End-to-end smoke against the
  WS-A8 three-agency fixture. Covers happy-path, lapsed-ATO (record past
  `expires_at` flagged), and configuration-latitude drift. Schema-validation
  assertions on every emitted record. Target: <60 seconds.
- **`tests/test_reciprocity_*.py`** — Unit tests for emitter (golden-file
  regression + signature verification), bundle aggregator (round-trip
  emit → re-validate from disk), and ConMon SLA cadence (four threshold
  cases: 28 d / 32 d / 46 d / 100 d with deterministic verdicts).
- **`tests/test_cli_help_smoke.py`** — Extended to cover `uiao reciprocity`
  sub-app (three new commands) and `uiao conmon ato-cadence-check`.
- **`tests/test_quickstart_smoke.py`** — Extended to cover the HRIT quickstart.

### Local verification (pre-0.6.0 cut)

```
$ python -m ruff check .
All checks passed!

$ python -m ruff format --check .
<N> files already formatted

$ python -m mypy src/uiao
Success: no issues found in <N> source files

$ python -m pytest -q
<N> passed, 156 skipped

$ uiao substrate drift
PASS — 0 P1 findings

$ python3 -c "
import re, pathlib
idx = pathlib.Path('src/uiao/canon/adr/index.md').read_text()
for m in re.finditer(r'\(adr-([0-9]+)[^)]*\.md\)', idx):
    p = pathlib.Path('src/uiao/canon/adr') / m.group(0)[1:-1]
    assert p.exists(), f'Missing: {p}'
print('OK — all ADR refs resolve')
"
OK — all ADR refs resolve
```

### Public-surface coverage

| Feature | v0.5.0 | v0.6.0 |
|---|---|---|
| Auditor API | ✅ | ✅ |
| CQL Engine | ✅ | ✅ |
| Evidence Graph (UIAO_113) | ✅ v1.1 | ✅ v1.2 (`ato-decision`, `reciprocity-record`) |
| Terraform adapter | ✅ | ✅ |
| Compliance Orchestrator | ✅ | ✅ |
| Enforcement Runtime | ✅ `uiao enforcement run` | ✅ |
| **Reciprocity record emission** | ❌ doctrine only | ✅ `uiao reciprocity onboard-agency` |
| **Per-agency OSCAL bundle** | ❌ | ✅ `aggregate_per_agency_bundle()` |
| **ConMon SLA cadence enforcement** | ❌ | ✅ `uiao conmon ato-cadence-check` |
| **Configuration-latitude drift detection** | ❌ | ✅ `DRIFT-SCHEMA` via `config_latitude.py` |
| **KSI-RECIP-001..008** | ❌ | ✅ 8 new accountability signals |
