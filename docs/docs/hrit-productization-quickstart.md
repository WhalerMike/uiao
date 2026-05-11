---
document_id: HRIT-QUICKSTART
title: "UIAO v0.6.0 HRIT Productization: Quickstart — Three Signed Reciprocity Records in 10 Steps"
version: "0.6.0"
classification: DERIVED
created_at: "2026-05-11"
updated_at: "2026-05-11"
canon_refs:
  - UIAO_140
  - Spec2-D6.1-FederalHRITIntegrationRunbook.md
  - adr-054-single-ato-reciprocity.md
---

# HRIT Productization Quickstart

Walk from a fresh clone to three signed reciprocity records — one per
agency in the synthetic OPM / Treasury / IRS fixture — in under 10 minutes.
No live federal systems, no real credentials, no production data required.

> **CLI availability note:** The `uiao reciprocity` and `uiao conmon`
> commands introduced in this quickstart are delivered by Batch A
> workstreams WS-A2, WS-A4, WS-A5, WS-A6, and WS-A7. These commands
> are fully available after the `v0.6.0-rc1` tag is cut in Phase 2
> integration. If you are working on a pre-RC1 branch, some commands
> will display a "not yet implemented" stub.

---

## What you will do

You will exercise the UIAO Single-ATO Reciprocity Model (UIAO_140) against
a synthetic three-agency fixture that mirrors the structure of the OPM
Federal HRIT Modernization Platform (Solicitation 24322626R0007 Amd 4).
OPM is the controlling-ATO issuer; the Department of the Treasury (TREAS)
and the Internal Revenue Service (IRS) are consuming agencies under
reciprocity. All three agencies produce signed reciprocity records. Treasury
is fully conforming; IRS carries one intentional configuration-latitude
violation (`password_minimum_length: 10`) that the drift detector classifies
as a DRIFT-SCHEMA P2 finding. By the end of the walkthrough you will have
verified signatures, run a ConMon ATO-cadence check, and seen the IRS
finding surface in the output.

---

## Prerequisites

- Python 3.10 or later
- git
- No Azure tenant, no API keys, no network connectivity required

---

## Step 1 — Clone and install

```bash
git clone https://github.com/WhalerMike/uiao
cd uiao
pip install -e .
```

Verify the CLI is reachable:

```bash
uiao --version
```

Expected output (v0.6.0 or later):

```
uiao 0.6.0
```

---

## Step 2 — Confirm the fixture files parse cleanly

The synthetic fixture lives under
[`examples/hrit/opm-treas-irs/`](../../examples/hrit/opm-treas-irs/).
Confirm all files load without errors before running any commands:

```bash
python3 -c "
import yaml, json
for f in [
    'examples/hrit/opm-treas-irs/ssp-latitude-table.yaml',
    'examples/hrit/opm-treas-irs/tenant-treas-config.yaml',
    'examples/hrit/opm-treas-irs/tenant-irs-config.yaml',
]:
    yaml.safe_load(open(f))
json.load(open('examples/hrit/opm-treas-irs/controlling-ato.json'))
print('All fixture files parse OK')
"
```

Expected output:

```
All fixture files parse OK
```

---

## Step 3 — Set the signing key environment variable

The `uiao reciprocity onboard-agency` command signs each reciprocity record
with an HMAC-SHA256 key. In production this key is a hardware-backed secret
managed by the platform operator. For the quickstart, export any non-empty
string as the key:

```bash
export UIAO_SIGNING_KEY="quickstart-dev-key-change-in-production"
```

> **Security note:** Never use a predictable key in production. The ConMon
> pipeline (WS-A5) will emit a `WARN` if it detects the key matches a
> known-default value pattern.

---

## Step 4 — Onboard OPM as the controlling agency

OPM issues the controlling ATO and does not itself file a reciprocity record
(it is the authorizing official, not a consuming agency). Register the
controlling ATO so downstream commands can resolve it:

```bash
uiao reciprocity onboard-agency \
  --controlling-ato examples/hrit/opm-treas-irs/controlling-ato.json \
  --consuming-agency OPM \
  --role controlling \
  --legal-basis interagency-mou \
  --out-dir /tmp/hrit-recip
```

Expected output:

```
Registering controlling ATO: OPM-HRIT-2026-001
Platform: OPM Federal HRIT Modernization Platform
Controlling record written to /tmp/hrit-recip/OPM-controlling-ato.json
Signature: sha256:<hex>
```

---

## Step 5 — Onboard Treasury as a conforming consuming agency

```bash
uiao reciprocity onboard-agency \
  --controlling-ato examples/hrit/opm-treas-irs/controlling-ato.json \
  --consuming-agency TREAS \
  --tenant-config examples/hrit/opm-treas-irs/tenant-treas-config.yaml \
  --ssp-latitude examples/hrit/opm-treas-irs/ssp-latitude-table.yaml \
  --legal-basis interagency-mou \
  --out-dir /tmp/hrit-recip
```

Expected output:

```
Onboarding consuming agency: TREAS
Controlling ATO  : OPM-HRIT-2026-001 (expires 2027-04-15)
Latitude check   : PASS — 10/10 settings conforming, 0 findings
Reciprocity record written to /tmp/hrit-recip/TREAS-reciprocity-record.json
Signature: sha256:<hex>
```

---

## Step 6 — Onboard IRS as a consuming agency with one violation

```bash
uiao reciprocity onboard-agency \
  --controlling-ato examples/hrit/opm-treas-irs/controlling-ato.json \
  --consuming-agency IRS \
  --tenant-config examples/hrit/opm-treas-irs/tenant-irs-config.yaml \
  --ssp-latitude examples/hrit/opm-treas-irs/ssp-latitude-table.yaml \
  --legal-basis interagency-mou \
  --out-dir /tmp/hrit-recip
```

Expected output:

```
Onboarding consuming agency: IRS
Controlling ATO  : OPM-HRIT-2026-001 (expires 2027-04-15)
Latitude check   : FINDINGS — 9/10 settings conforming, 1 finding
  DRIFT-SCHEMA P2  password_minimum_length=10 does not match pattern ^(1[2-9]|[2-9][0-9])$ (requires 12+)
Reciprocity record written to /tmp/hrit-recip/IRS-reciprocity-record.json (with finding annotation)
Signature: sha256:<hex>
```

The reciprocity record is still emitted and signed — the finding is recorded
in the record's `findings` array and surfaces in ConMon dashboards.

---

## Step 7 — Verify each record's signature

```bash
for agency in OPM TREAS IRS; do
  uiao reciprocity verify \
    --record /tmp/hrit-recip/${agency}-reciprocity-record.json
done
```

Expected output (one block per agency):

```
Verifying OPM-controlling-ato.json ... OK  algorithm=HMAC-SHA256 signer=platform-operator
Verifying TREAS-reciprocity-record.json ... OK  algorithm=HMAC-SHA256 signer=platform-operator
Verifying IRS-reciprocity-record.json  ... OK  algorithm=HMAC-SHA256 signer=platform-operator
```

A non-zero exit code and `FAIL` status indicate tampering or key mismatch.

---

## Step 8 — Run the ATO-cadence check against the controlling ATO

The ConMon cadence validator (WS-A5) checks whether the controlling ATO is
within its valid window and whether SSP submission deadlines have been met:

```bash
uiao conmon ato-cadence-check \
  --controlling-ato examples/hrit/opm-treas-irs/controlling-ato.json \
  --reference-date 2026-05-11
```

Expected output:

```
ATO Cadence Check — OPM-HRIT-2026-001
  Decision date    : 2026-04-15
  Expires          : 2027-04-15
  Days remaining   : 339
  Reauth window    : opens 2027-03-16 (30 days before expiry)
  SSP draft SLA    : PASS (submitted within 30 days of award)
  SSP final SLA    : PASS (submitted within 45 days of award)
  ATO status       : PASS — active, 339 days remaining
```

---

## Step 9 — Inspect the IRS configuration-latitude finding

List findings scoped to the IRS reciprocity record:

```bash
uiao reciprocity list-records \
  --out-dir /tmp/hrit-recip \
  --agency IRS \
  --show-findings
```

Expected output:

```
IRS — reciprocity record OPM-HRIT-2026-001 / IRS
  Status   : ACTIVE (findings present)
  Findings : 1
  -----------------------------------------------
  ID       : DRIFT-SCHEMA-0001
  Class    : DRIFT-SCHEMA
  Severity : P2
  Field    : password_minimum_length
  Observed : "10"
  Pattern  : ^(1[2-9]|[2-9][0-9])$  (requires 12+)
  Message  : Tenant value does not satisfy SSP latitude constraint.
             Remediation: update IRS tenant config to password_minimum_length >= 12.
```

This is the finding the WS-A9 smoke tests assert against (class = DRIFT-SCHEMA,
severity = P2, field = password_minimum_length).

---

## Step 10 — Aggregate per-agency bundles

The bundle aggregator (WS-A6) packages each agency's reciprocity record,
scoped OSCAL component-definition, and provenance manifest into a
self-contained artifact that the consuming agency's AO can verify
independently — without access to the UIAO platform:

```bash
for agency in TREAS IRS; do
  uiao reciprocity bundle \
    --controlling-ato examples/hrit/opm-treas-irs/controlling-ato.json \
    --agency ${agency} \
    --records-dir /tmp/hrit-recip \
    --out-dir /tmp/hrit-bundles/${agency}
  echo "Bundle written to /tmp/hrit-bundles/${agency}/"
done
```

Expected artifacts per agency:

```
/tmp/hrit-bundles/TREAS/
  reciprocity-record.json          # signed record
  component-definition.json        # OSCAL component-definition scoped to TREAS
  assessment-results.json          # tenant-scoped ConMon evidence
  provenance-manifest.json         # bundle hash + signing metadata

/tmp/hrit-bundles/IRS/
  reciprocity-record.json          # signed record (with finding annotation)
  component-definition.json        # OSCAL component-definition scoped to IRS
  assessment-results.json          # tenant-scoped ConMon evidence (DRIFT-SCHEMA P2)
  provenance-manifest.json         # bundle hash + signing metadata
```

---

## Known-answer table

Cross-reference your run output against the expected results below.

| Agency | Role | Conformance | Findings |
|---|---|---|---|
| OPM (controlling) | Controlling ATO issuer | N/A | N/A |
| TREAS | Consuming agency | Conforming | 0 |
| IRS | Consuming agency | Configuration-latitude violation | 1 × DRIFT-SCHEMA P2 |

The single IRS finding is on `password_minimum_length: "10"` against the
SSP latitude pattern `^(1[2-9]|[2-9][0-9])$` (requires 12+). All other
IRS settings are conforming.

---

## What you just did

You ran the full UIAO Single-ATO Reciprocity Model pipeline:

- Registered a controlling ATO (OPM).
- Onboarded two consuming agencies (TREAS conforming, IRS with one violation).
- Verified HMAC-SHA256 signatures on all three records.
- Ran ConMon ATO-cadence enforcement against the controlling ATO.
- Surfaced the IRS DRIFT-SCHEMA P2 finding from the configuration-latitude detector.
- Produced independently-verifiable per-agency bundles.

With a real OPM HRIT platform ATO and tenant configurations, steps 2
through 10 run identically; only the input files change.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Error: No such command "reciprocity"` | Running a pre-RC1 branch before Batch A workstreams are merged. | Check out `v0.6.0-rc1` or later: `git checkout v0.6.0-rc1 && pip install -e .` |
| `UIAO_SIGNING_KEY not set` | Environment variable not exported before running onboard. | `export UIAO_SIGNING_KEY="<your-key>"` |
| `Signature verification FAIL` | Key used to verify differs from key used to sign. | Ensure the same `UIAO_SIGNING_KEY` value is set in both signing and verification environments. |
| `yaml.safe_load` parse error on fixture files | File encoding or line-ending issue. | `file examples/hrit/opm-treas-irs/*.yaml` — ensure UTF-8, LF endings. |
| All fixture files parse OK but commands not found | Dev extras missing. | `pip install -e ".[dev]"` |

---

## Next steps

- **Full CLI surface:** `uiao --help`. Every sub-app has its own `--help`
  (e.g., `uiao reciprocity --help`, `uiao conmon --help`).
- **KSI rules for reciprocity:** See `src/uiao/rules/ksi/KSI-RECIP-*.yaml`
  (WS-A10) for the eight KSIs that govern the reciprocity lifecycle.
- **Narrative doc:** `docs/docs/22_HRITProductization.qmd` (WS-A10) covers
  the full operational narrative with Mermaid record-lifecycle and
  bundle-aggregation diagrams.
- **Canon references:**
  - [UIAO_140](../../src/uiao/canon/specs/single-ato-reciprocity-model.md) — Single-ATO Reciprocity Model
  - [Spec2-D6.1](../../src/uiao/canon/specs/Spec2-D6.1-FederalHRITIntegrationRunbook.md) — Federal HRIT Integration Runbook
  - [ADR-054](../../src/uiao/canon/adr/) — Single-ATO Reciprocity authorizing ADR
