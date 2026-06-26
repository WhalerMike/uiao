---
document_id: UIAO_206
title: "FedRAMP KSI Evidence Platform — Continuous Reporting Runbook"
version: "1.0"
status: Draft
owner: Michael Stratton
created_at: "2026-06-25"
updated_at: "2026-06-25"
mas-scope: "metadata-out-of-scope"
publish_to_site: true
publication_style: include
---

# FedRAMP KSI Evidence Platform — Continuous Reporting Runbook

> **Audience.** UIAO canon stewardship and federal-adoption teams.
> **Scope-classification (RFC-0005 MAS).** `metadata-out-of-scope` — this
> runbook operates the KSI *evidence platform*, which emits OSCAL metadata
> describing substrate compliance posture rather than handling federal
> information itself (consistent with the UIAO_133 §3.2 treatment of OSCAL
> generators and telemetry observability). The federal information the
> assessed systems hold is classified separately, per the assessed
> component's own `mas-scope`.

This runbook is the operational companion to the FedRAMP 20x evidence
surface: [UIAO_138](./specs/fedramp-3pao-evidence-interface.md) (3PAO
evidence interface), [UIAO_139](./specs/fedramp-gcc-moderate-realtime-boundary-impact.md)
(GCC-Moderate real-time boundary impact), and
[ADR-106](./adr/adr-106-fedramp-20x-integration.md) (FedRAMP 20x
integration — KSI emission and Minimum Assessment Scope adoption). Where
[UIAO_205](./specs/fedramp-20x-agency-registration.md) covers the agency-side
registration and pathway migration *ceremony*, UIAO_206 covers the
substrate-side *operations* that keep the KSI evidence continuous.

---

## 1. Purpose & scope

### 1.1 What "continuous-ness" means in this context

This runbook defines practical patterns to make the UIAO FedRAMP KSI
evidence platform (UIAO_138 / UIAO_139 + ADR-106) operate in a continuous
or near-continuous mode. Continuous-ness here includes:

- Scheduled or event-driven KSI evidence emission and tagging of OSCAL artifacts.
- Automated staleness detection and `DRIFT-EVIDENCE-STALE` event generation.
- On-demand or scheduled 3PAO evidence package generation.
- Continuous or periodic ADR-106 gate validation (dry-run).
- Queryable status, completeness, and drift dashboards via API.
- Durable multi-tenant persistence of evidence and drift events.
- Extensibility so other UIAO adapters and external applications can
  contribute to or consume the evidence surface.

### 1.2 Target audience & layers

- **CLI layer** — operators and automation engineers scheduling jobs on Windows/SSA environments.
- **Core platform layer** — developers extending emission, drift integration, and tagging.
- **SaaS / persistence layer** — platform engineers managing multi-tenant evidence stores.
- **Adapter & integration layer** — adapter authors and consuming applications.
- **Best practices** — canon stewards and architects.

### 1.3 Key references

- **UIAO_138** — FedRAMP 3PAO Evidence Interface (Draft).
- **UIAO_139** — FedRAMP GCC-Moderate Real-Time Boundary Impact (Draft).
- **ADR-106** — FedRAMP 20x Integration — KSI emission and Minimum
  Assessment Scope adoption. (The CR26 snapshot vendoring + pin discipline
  is **ADR-061**, which ADR-106 builds on.)
- **ADR-061** — FedRAMP CR26 Catalog Vendoring (authority posture, pin discipline).
- **UIAO_205** — FedRAMP 20x Agency Registration and Sponsor Onboarding.
- `EMISSION_MAP` in `src/uiao/oscal/ksi_emitter.py` (11 rows).
- FedRAMP 20x KSI evidence models and SaaS schema (`src/uiao/models/fedramp.py`, `src/uiao/saas/fedramp_schema.py`).

---

## 2. Continuous reporting architecture overview

### 2.1 High-level data flow

Upstream components (drift engines, telemetry, adapters, provenance) produce
payloads → the KSI emitter tags OSCAL artifacts with `fedramp:ksi-*` props
and builds stable `KsiEvidenceRecord` entries → records are written to a
local JSON store or SaaS tables → staleness detection runs on read or on
schedule → API/CLI surfaces expose status, completeness, drift events, and
3PAO packages for dashboards, auditors, and other applications.

### 2.2 Core continuous components

| Component | Continuous role |
|---|---|
| `EMISSION_MAP` (11 rows) | Defines *what*, *who*, *which themes*, and *freshness cadence* for every evidence artifact. Stable contract for continuous emission. |
| `tag_artifact()` + `build_ksi_evidence_record()` | Lightweight, deterministic functions callable on every relevant OSCAL emission or on schedule. UUID5 ensures idempotency. |
| `staleness_report()` / `check_staleness()` | Core continuous-monitoring engine. Converts age vs cadence budget into `DRIFT-EVIDENCE-STALE` events (P0–P2). |
| CLI (`uiao fedramp *`) | Scriptable entry points for scheduled jobs: `ksi-run`, `dryrun`, `3pao-package`, `staleness`, `orgpath-scope`. |
| API (`/api/v1/fedramp`) | Read-oriented query surface for dashboards, external tools, and on-demand package generation. Supports polling or webhook patterns. |
| SaaS repository + tables | Durable, partitioned, multi-tenant store for evidence records and open drift events. Enables historical trending and tenant-specific continuous views. |

---

## 3. CLI layer — enabling continuous operation

### 3.1 Recommended scheduled jobs

On Windows (SSA/telework environment) use Task Scheduler. On Linux/containers
use cron or systemd timers. Recommended minimum set for a continuous posture:

| Job name | Command example | Recommended frequency & purpose |
|---|---|---|
| `KSI-Evidence-Emit` | `uiao fedramp ksi-run --ir %IR_PATH% --out %EVIDENCE_DIR%` | Every 15–60 min (or on workflow event). Produces fresh tagged evidence + staleness report. |
| `KSI-DryRun-Gate` | `uiao fedramp dryrun --evidence-dir %EVIDENCE_DIR% --out %DRYRUN_JSON% --cr26-sha c31eb04...` | Hourly or on major change. Validates the ADR-106 gate continuously; record result to tenant config. |
| `KSI-3PAO-Package` | `uiao fedramp 3pao-package --evidence-dir %EVIDENCE_DIR% --out %PACKAGE_JSON%` | Daily or on-demand before 3PAO engagement. Produces standardized auditor artifact. |
| `KSI-Staleness-Report` | `uiao fedramp staleness --evidence-dir %EVIDENCE_DIR% --format json` | Every 15–30 min. Feed into alerting/monitoring for P0/P1 events. |

### 3.2 PowerShell scheduling example (Windows Task Scheduler)

```powershell
# Example wrapper script: Invoke-KSIContinuous.ps1
$ErrorActionPreference = 'Stop'
$EvidenceDir = 'C:\UIAO\Evidence\FedRAMP'
$IR = 'C:\UIAO\IR\gcc-moderate-latest.json'

uiao fedramp ksi-run --ir $IR --out $EvidenceDir --baseline gcc-moderate
if ($LASTEXITCODE -ne 0) { Write-Error 'KSI emission failed' }

# Optional: trigger dry-run and capture for monitoring
$DryRunOut = Join-Path $EvidenceDir 'last-dryrun.json'
uiao fedramp dryrun --evidence-dir $EvidenceDir --out $DryRunOut
if ($LASTEXITCODE -ne 0) {
    # Escalate to enforcement workflow or alert
    Write-Warning 'ADR-106 gate check failed - investigate'
}
```

**Task Scheduler setup notes**

- Run as a service account with read access to the IR and write access to `EvidenceDir`.
- Use "Run whether user is logged on or not" + highest privileges.
- Trigger: on a schedule (15–60 min) + on event (if the drift engine writes a new IR).
- Action: start a program → `powershell.exe -File C:\UIAO\Scripts\Invoke-KSIContinuous.ps1`.
- Add logging redirection and email/Teams notification on failure for P0/P1 conditions.

---

## 4. Core platform layer — emission, detection & tagging

### 4.1 Making emission continuous

Any component that already emits OSCAL (`drift.engine.realtime`,
`telemetry.sentinel.health`, `adapters.*`, `cato.package.aggregator`, etc.)
can participate in continuous KSI reporting by calling the emitter utilities
at emission time or on a schedule.

```python
from uiao.oscal.ksi_emitter import tag_artifact, build_ksi_evidence_record, EMISSION_MAP
from uiao.models.fedramp import KsiEvidenceRecord

# Example inside an existing OSCAL generator or drift handler
def emit_with_ksi(artifact: dict, row: int, payload: dict):
    tagged = tag_artifact(artifact, row=row)          # injects fedramp:ksi-* props
    record = build_ksi_evidence_record(row, payload)  # stable UUID5 record
    # Persist record to local JSON or SaaS FedRampTenantRepository.upsert_evidence()
    return tagged, record
```

### 4.2 Continuous staleness & drift detection

Call `staleness_report()` on every read path (CLI/API) or on a background
timer. The function evaluates each record (`is_stale` + age) and returns the
new `DRIFT-EVIDENCE-STALE` events. Persist those events via
`FedRampTenantRepository.insert_drift_event()` so they survive restarts and
can be queried/closed.

### 4.3 Event-driven pattern (future / recommended)

When the UIAO drift or enforcement engine detects a material change, publish
an internal event. A lightweight subscriber can then:

- Re-run affected emission rows (or the full `ksi-run`).
- Update evidence records and re-evaluate staleness.
- Close resolved drift events.
- Optionally trigger a lightweight dry-run.

---

## 5. SaaS / persistence layer — durable multi-tenant store

### 5.1 Provisioning

At tenant onboarding (or first use), call `create_fedramp_schema(engine)`.
This is idempotent (`checkfirst=True`). Store the chosen baseline and CR26
snapshot SHA in `fedramp_tenant_config`.

### 5.2 Continuous write pattern

```python
# Example inside a scheduled or event-driven job
repo = FedRampTenantRepository(session_maker)
for rec in evidence_records:
    await repo.upsert_evidence(tenant_id, rec)
for event in new_drift_events:
    await repo.insert_drift_event(tenant_id, event)
await repo.record_dry_run(tenant_id, dry_run_result.summary())
```

### 5.3 Query patterns for continuous dashboards

- List open high-severity drift events for alerting.
- Retrieve latest evidence per row or per theme for completeness tiles.
- Historical trend of staleness age or theme coverage over time.
- Tenant-config `adr106_ratified` flag + `last_dry_run_at` for compliance status.

---

## 6. API layer — query, dashboard & integration

The FastAPI surface (mounted at `/api/v1/fedramp`) is intentionally
read-heavy. It is ideal for:

- Internal dashboards (AO, SecOps, governance).
- External 3PAO or auditor self-service (read-only).
- Other UIAO modules or external applications polling for KSI status or drift.
- Webhook-style integration: poll `/drift` or `/status` and act on P0/P1 events.

**Key endpoints for continuous use**

| Endpoint | Continuous use case |
|---|---|
| `GET /status` | Health tile + overall KSI completeness. Poll every 5–15 min for dashboard green/red status. |
| `GET /ksi/completeness` | Per-theme coverage with latest emitted timestamp and staleness flag. Drive theme-level widgets. |
| `GET /drift?min_severity=P1` | Open high-severity drift events. Feed into alerting or enforcement workflows. |
| `GET /3pao/package` | On-demand or nightly-refreshed standardized 3PAO artifact. Can be cached or versioned. |
| `POST /dryrun` | Lightweight in-process gate check. Use from CI or lightweight monitors. |

Additional read endpoints exist for completeness: `GET /evidence` and
`GET /evidence/{row}` (raw evidence records) and `GET /orgpath/scope`
(derive RFC-0005 MAS scope from OrgPath context).

---

## 7. Enabling adapters & other applications

### 7.1 How adapters contribute evidence

Any UIAO adapter (or external application that produces OSCAL or relevant
telemetry) can become a first-class participant in the continuous KSI
surface by following this pattern:

- **Import the emitter:** `from uiao.oscal.ksi_emitter import tag_artifact, build_ksi_evidence_record, EMISSION_MAP`.
- **Choose or request a row:** use an existing row whose `responsible_component`
  and themes align, or propose a new row via ADR if the component is
  genuinely new.
- **Tag at emission time:** call `tag_artifact(artifact_dict, row=N)` before
  persisting the OSCAL artifact.
- **Build & persist record:** `build_ksi_evidence_record(row, payload)` then
  upsert via `FedRampTenantRepository` or the local store.
- **Register MAS scope (if applicable):** use `classify_orgpath_scope()`
  (in `uiao.oscal.orgpath_evidence`) when the adapter touches new OrgPath
  units or systems.

### 7.2 How other apps consume the platform

- Query `/status` or `/ksi/completeness` for real-time compliance widgets inside their own dashboards.
- Call `/3pao/package` (or schedule the CLI) to obtain a standardized evidence bundle before assessments.
- Subscribe to `/drift` events (poll or future webhook) to react to evidence staleness in their own enforcement or notification systems.
- Use the SaaS repository (if they have DB access) or the API to read historical evidence for analytics/reporting.

### 7.3 Extension points

- **New emission rows:** submit an ADR with justification, responsible
  component, themes, cadence, and `mapping_source`. Update `EMISSION_MAP`
  and tests.
- **New drift classes:** extend the `DriftClass` enum and handling if
  evidence-staleness patterns evolve.
- **Richer MAS classification:** extend `classify_orgpath_scope` logic for
  new asset classes or OrgPath facets.

---

## 8. Recommended best practices

### 8.1 Cadence & scheduling

- Align emission cadence with the `FreshnessCadence` defined in `EMISSION_MAP` for that row.
- Use `real-time-critical` or `continuous` only where upstream data genuinely changes that frequently.
- Combine scheduled jobs with event triggers (e.g., a new IR written by the drift engine) for efficiency.

### 8.2 Idempotency & stability

- Always use `build_ksi_evidence_record()` — its UUID5 guarantees the same payload + row produces the same record ID.
- Use upsert patterns in the SaaS repository so repeated runs are safe.

### 8.3 Observability & alerting

- Log every `ksi-run`, dry-run result, and new drift event with correlation IDs.
- Escalate P0/P1 `DRIFT-EVIDENCE-STALE` events to existing UIAO enforcement workflows or Microsoft Teams/Sentinel alerts.
- Monitor the monitor: schedule a meta-dry-run that checks whether the last scheduled jobs succeeded and evidence is fresh.

### 8.4 Security & compliance (GCC-Moderate)

- All core paths remain offline / no live tenant calls (as designed).
- Store evidence and drift events with appropriate classification and access controls.
- Keep the CR26 snapshot SHA and baseline pinned in tenant config; update only via a controlled process.

### 8.5 Canon & change management

- Any change to `EMISSION_MAP`, models, or cadence budgets must be reflected in UIAO_138/139 and tested via dry-run.
- Update `document-registry.yaml` and the customer-docs status after changes.
- Version the runbook and CLI/API surfaces together with the platform.

---

## 9. Quick-start implementation guide (minimal viable continuous)

**Day 1 — minimal scheduled posture**

- Create `EvidenceDir` and grant the service account permissions.
- Implement `Invoke-KSIContinuous.ps1` (or equivalent) calling `ksi-run` + `dryrun`.
- Create two Task Scheduler jobs: `KSI-Evidence-Emit` (every 30 min) and `KSI-DryRun-Gate` (hourly).
- Verify `last-dryrun.json` shows passed and no P0/P1 events.
- Expose `/status` and `/drift` in an internal dashboard or monitoring tile.

**Week 1 — add durability & visibility**

- Provision the FedRAMP schema for target tenants.
- Migrate scheduled jobs to use `FedRampTenantRepository.upsert_evidence()` + `insert_drift_event()`.
- Add a `/3pao/package` tile or nightly job.
- Configure alerting on P0/P1 drift events.

**Ongoing — extend adapters & event-driven**

- Update 2–3 high-value adapters to call `tag_artifact` + persist records at emission time.
- Prototype an event-driven subscriber that reacts to new drift findings.
- Document new emission rows or MAS extensions via ADR.

---

## 10. References & related canon

- `src/uiao/models/fedramp.py` — all Pydantic models.
- `src/uiao/oscal/ksi_emitter.py` — `EMISSION_MAP` and tagging logic.
- `src/uiao/cli/fedramp.py` — the five continuous-ready commands.
- `src/uiao/api/routes/fedramp.py` — query surface.
- `src/uiao/saas/fedramp_schema.py` — multi-tenant tables & repository.
- [UIAO_138](./specs/fedramp-3pao-evidence-interface.md), [UIAO_139](./specs/fedramp-gcc-moderate-realtime-boundary-impact.md), [ADR-106](./adr/adr-106-fedramp-20x-integration.md), [ADR-061](./adr/adr-061-fedramp-cr26-catalog-vendoring.md), [UIAO_205](./specs/fedramp-20x-agency-registration.md) (FedRAMP 20x registration).
- `document-registry.yaml` — current status of UIAO_138/139.

This runbook is a living canon artifact. Update it whenever the emission
contract, SaaS schema, or continuous patterns evolve. All changes should be
reflected in UIAO_138/139 and tested via the dry-run gate.
