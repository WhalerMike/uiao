---
document_id: QUICKSTART
title: "UIAO Quickstart: First Drift Report in 10 Minutes"
version: "1.0"
classification: DERIVED
created_at: "2026-04-24"
updated_at: "2026-04-24"
---

# Quickstart: first drift report in 10 minutes

This walks you from a fresh clone to a full auditor bundle (evidence,
POA&M, SSP narrative) in under 10 minutes using a synthetic M365
SCuBA assessment fixture. No Azure tenant, no API keys, no live data.

If you have Python 3.10+ and git, you have everything you need.

## 1. Install (2 minutes)

```bash
git clone https://github.com/WhalerMike/uiao
cd uiao
pip install -e .
```

Verify the CLI is reachable:

```bash
uiao --version
```

## 2. Transform a SCuBA assessment (1 minute)

UIAO ships a synthetic normalized SCuBA report at
[`examples/quickstart/scuba-normalized.json`](../../examples/quickstart/scuba-normalized.json).
It carries five KSI results — 2 PASS, 1 WARN, 2 FAIL, 1 unmapped —
enough to exercise every downstream code path.

Run the transform:

```bash
uiao ir scuba-transform examples/quickstart/scuba-normalized.json
```

Expected output:

```
Transforming SCuBA JSON: examples/quickstart/scuba-normalized.json...
Mapped 163 KSIs to IR Controls + Policies
SCuBA Transform
  Total KSI results : 5
  PASS              : 2
  WARN              : 1
  FAIL              : 2
  Unmapped KSIs     : 1 ['KSI-UNKNOWN-99']
```

## 3. Full auditor bundle (2 minutes)

One command runs the entire pipeline — transform → evidence bundle →
governance actions → POA&M → SSP narrative — and writes every
artifact a FedRAMP auditor would ask for:

```bash
uiao ir auditor-bundle examples/quickstart/scuba-normalized.json \
    --out-dir /tmp/uiao-quickstart
```

Expected output:

```
Building auditor bundle from: examples/quickstart/scuba-normalized.json...
Mapped 163 KSIs to IR Controls + Policies
Bundle written to /tmp/uiao-quickstart
  Evidence : 5
  Actions  : 5
  POA&M    : 3
```

You now have six artifacts under `/tmp/uiao-quickstart/`:

| File | Purpose |
|---|---|
| `evidence-bundle.json` | Canonical evidence bundle, content-hashed for provenance |
| `governance-report.md` | Per-KSI action list with SLA + owner assignment |
| `lineage.json` | Coverage map: KSI → NIST control → evidence → action |
| `manifest.json` | Bundle metadata (summary counts, aggregate hash) |
| `poam.json` | FedRAMP POA&M rows (FAIL + WARN only) |
| `ssp-narrative.md` | OSCAL SSP implementation narrative per control |

## 4. Inspect the governance report (1 minute)

```bash
head -20 /tmp/uiao-quickstart/governance-report.md
```

The top actions show per-KSI remediation planning:

```
- REMEDIATE | KSI-IA-02     | sev=Critical | owner=team-identity@...  | SLA=7d
- REMEDIATE | KSI-IA-01     | sev=High     | owner=team-identity@...  | SLA=14d
- REMEDIATE | KSI-AC-02     | sev=High     | owner=team-access@...    | SLA=14d
- MONITOR   | KSI-AC-01     | sev=Medium   | owner=team-access@...    | SLA=30d
- MONITOR   | KSI-UNKNOWN-99| sev=Low      | owner=team-compliance@...| SLA=60d
```

## 5. Drift detection between two runs (3 minutes)

Drift detection compares two SCuBA runs and reports KSI transitions,
evidence hash deltas, and status changes. Simulate a second run by
flipping one KSI from FAIL to PASS:

```bash
cp examples/quickstart/scuba-normalized.json /tmp/run-b.json
# In /tmp/run-b.json, change KSI-IA-02 "status": "FAIL" to "PASS".
# Any editor works; the file is ~1 KB.
uiao ir diff examples/quickstart/scuba-normalized.json /tmp/run-b.json
```

You'll see a Markdown diff listing:
- KSI transitions (`FAIL → PASS` for KSI-IA-02)
- Evidence hash deltas (one entry changed)
- Status count summary (FAIL: 2 → 1, PASS: 2 → 3)

That diff is the raw input to the UIAO drift engine — which classifies
each transition into the [5-class drift taxonomy](16_DriftDetectionStandard.qmd)
(DRIFT-SCHEMA / SEMANTIC / PROVENANCE / AUTHZ / IDENTITY) at four
severities (P1–P4).

## What you just did

You ran the UIAO evidence pipeline end-to-end. With a real ScubaGear
assessment report from your tenant — the `M365BaselineConformance.json`
it produces — steps 2 through 5 run identically; only the input
changes.

## Want a REST API instead of the CLI?

Everything you ran through `uiao …` is also reachable as HTTP routes
behind FastAPI, gated under the `[api]` install extra so the heavy
dependencies (`fastapi`, `uvicorn`, `httpx`, `msal`) only land when
you ask for them:

```bash
pip install -e ".[api]"
uvicorn uiao.api.app:app --host 127.0.0.1 --port 8000
```

The available route surfaces (per [M5 public-surface audit](../reports/public-surface-audit-v0.5.0.md)):

| Module | Routes | Purpose |
|---|---|---|
| `/health` | `GET /health` | Liveness probe |
| `/auditor/…` | 9 routes | Evidence, findings, POA&M, OSCAL (SAR/SSP/POA&M/SAP), evidence-graph trace |
| `/survey/…` | `POST /run`, `POST /findings` | AD survey runner |
| `/orgpath/…` | `POST /assign` | OrgPath assignment |
| `/boundary/…` | `POST /run`, `GET /gaps` | GCC boundary feature probe |

Once running, browse the auto-generated OpenAPI surface at
`http://127.0.0.1:8000/docs`. The auth model is documented in
[`src/uiao/api/auth/`](../../src/uiao/api/auth/) — Windows Authentication
inbound (Kerberos via IIS Negotiate when deployed via the Windows IIS
runbook), MSAL client-credentials outbound for Microsoft Graph.

For a development-only smoke test that proves the API surface is
wired without launching a server:

```bash
python -m pytest tests/test_api_smoke.py -v
```

## Next steps

- **Explore the full command surface:** `uiao --help`. Every sub-app
  has its own `--help` (e.g., `uiao ir --help`, `uiao generate --help`).
- **Ingest your own ScubaGear report:**
  `uiao adapter run-scuba <path-to-M365BaselineConformance.json>`
  normalizes a raw ScubaGear output into the IR-ready shape consumed
  by step 2 above.
- **Generate an OSCAL SAR from your run:**
  `uiao ir generate-sar examples/quickstart/scuba-normalized.json --out /tmp/sar.json`
  produces a signed Assessment Results document.
- **Adapter reference:** [UIAO_008 CLI Reference](../../src/uiao/canon/UIAO_008_CLI_Reference_v1.0.md).
- **Drift taxonomy:** [DriftDetectionStandard](16_DriftDetectionStandard.qmd).
- **Contribute:** [`CONTRIBUTING.md`](../../CONTRIBUTING.md) walks through
  canon-change rules and the adapter-conformance test contract.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Error: No such command "ir-scuba-transform"` | You installed v0.4.0 or older. ADR-046 renamed commands for v0.5.0. | `git pull && pip install -e .` then use `uiao ir scuba-transform ...`. |
| `uiao: command not found` | Shell hasn't picked up the console script. | Re-open the terminal, or run the module directly: `python -m uiao.cli.app --help`. |
| Tests fail on import | Dev extras missing. | `pip install -e ".[dev]"`. |
