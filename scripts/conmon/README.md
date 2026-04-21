# UIAO ConMon aggregation tooling

This directory holds the Python glue that powers
[`.github/workflows/conmon-aggregate.yml`](../../.github/workflows/conmon-aggregate.yml).
It is the operational realization of **ADR-025 D3** (third ConMon
workflow: POA&M CSV + dashboard JSON rollup + regression issue filing)
and the delivery vehicle for **ADR-043 D2 / D4** (72-hour critical SLA
gate + RFC-0026 dashboard card) and **UIAO_132 §2 / §5 / §7 O5**.

## Contents

| File | Role |
|---|---|
| `aggregate.py` | Reads every CA-7-tagged conformance adapter's latest `findings.json`, cross-walks to the RFC-0026 advisory block in `src/uiao/canon/adapter-registry.yaml`, and emits three artifacts (POA&M CSV, dashboard JSON, SLA issue payloads). |
| `__init__.py` | Package marker. |
| `README.md` | This file. |

## Artifacts produced

Under `exports/conmon/`:

| Artifact | Purpose | Consumer |
|---|---|---|
| `conmon-poam.csv` | Monthly POA&M rollup in FedRAMP-shaped columns (subset of the full template; see UIAO_132 §7 O1). | Manual upload to Connect.gov; automation deferred until RFC-0026 ratifies. |
| `conmon-aggregate-summary.json` | RFC-0026 dashboard card per adapter: requirement, pathway, last run, finding counts by severity, SLA breach count. | Monthly ConMon meeting (agenda §2–§3); future UIAO compliance dashboard. |
| `conmon-sla-issues.json` | Governance-issue payloads for any CRITICAL finding beyond the 72-hour acknowledgement SLA. | `conmon-aggregate.yml` opens one GitHub issue per entry with the `conmon-cure` label, per [`docs/docs/conmon-corrective-action-playbook.qmd`](../../docs/docs/conmon-corrective-action-playbook.qmd). |

## Inputs

- **`src/uiao/canon/adapter-registry.yaml`** — the source of CA-7
  adapter enumeration and the RFC-0026 pathway metadata (currently in
  `notes` free-text per ADR-043 N1).
- **`evidence/conformance/<adapter-id>/<run-id>/findings.json`** — per-run
  adapter output. The aggregator walks every adapter directory and
  picks the newest `findings.json` by mtime.

Missing evidence trees are **not** errors. Reserved-slot adapters
(`vuln-scan`, `stig-compliance`, `patch-state`, `intune`,
`uiao-git-server`) have no findings today; their dashboard cards render
with `last_run_at: null` and zero finding counts. This is the expected
steady state until Phase 2 conformance adapters come online.

## Finding shape

The aggregator is permissive but expects each finding to look roughly
like:

```json
{
  "id": "some-stable-id",
  "rule": "SCUBA.AAD.2.1",
  "control": "CA-7",
  "severity": "critical|high|medium|low|info",
  "title": "one-line summary",
  "description": "long-form",
  "target": "tenant-or-object",
  "detected_at": "2026-07-03T14:22:00Z",
  "acknowledged_at": null,
  "status": "open"
}
```

Only `severity`, `detected_at`, and (optionally) `acknowledged_at` are
load-bearing for SLA gating. The rest flow verbatim into the POA&M row.

## Local run

```bash
pip install pyyaml
python scripts/conmon/aggregate.py \
  --registry src/uiao/canon/adapter-registry.yaml \
  --evidence-root evidence/conformance \
  --output-dir exports/conmon
```

## Tests

Smoke test under `tests/conmon/test_aggregate_smoke.py` exercises the
registry-only (no evidence) path plus a synthetic critical-finding SLA
breach.

## Related canon

- **ADR-025** — the original ConMon program.
- **ADR-043** — RFC-0026 CA-7 integration; D2 (72-hour SLA), D4
  (dashboard card), D5 (corrective action).
- **UIAO_132** — operational spec mapping RFC-0026 deliverables to
  uiao substrate; §7 tracks remaining open items (O1 Connect.gov,
  O2 schema promotion, O4 Pathway-1 migration ADR).
- **`docs/docs/conmon/index.qmd`** — monthly meeting landing page.
- **`docs/docs/conmon-corrective-action-playbook.qmd`** — 45-day cure.
- **`docs/docs/conmon/templates/2026-07-agenda.md`** — first post-effective-date dry-run agenda.
