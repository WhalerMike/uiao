# OPM / Treasury / IRS — Synthetic Three-Agency HRIT Fixture

This directory contains a **synthetic three-agency fixture** for the OPM
Federal HRIT Modernization Platform (Solicitation 24322626R0007 Amd 4). It
exercises the UIAO v0.6.0 Single-ATO Reciprocity Model (UIAO_140) with one
controlling agency (OPM) and two consuming agencies (Treasury, IRS). The IRS
configuration intentionally violates one SSP latitude constraint so the
WS-A7 drift detector and WS-A9 tests have a known-bad fixture to exercise.

No live systems, real credentials, or production data are present. All values
are synthetic.

---

## Files

| File | Description |
|---|---|
| `controlling-ato.json` | OPM controlling ATO record (`OPM-HRIT-2026-001`). Fields match the reciprocity-record schema fields `controlling_ato_id`, `ssp_ref`, `expires_at`, etc. |
| `ssp-latitude-table.yaml` | SSP configuration-latitude table for `ssp-opm-hrit-platform-v1`. Enumerates 10 settings with `allowed_values` or `allowed_pattern` constraints. Consuming agencies must elect values from within this table. |
| `tenant-treas-config.yaml` | Treasury consuming-agency configuration. All 10 settings present; all values conform to the latitude table. Expected drift findings: **0**. |
| `tenant-irs-config.yaml` | IRS consuming-agency configuration. Nine settings conform; `password_minimum_length: "10"` violates the `^(1[2-9]|[2-9][0-9])$` pattern (requires 12+). Expected drift findings: **1 × DRIFT-SCHEMA P2**. |

---

## Agency summary

| Agency | Role | Conformance | Findings |
|---|---|---|---|
| OPM | Controlling ATO issuer | N/A | N/A |
| TREAS | Consuming agency | Conforming | 0 |
| IRS | Consuming agency | Configuration-latitude violation | 1 × DRIFT-SCHEMA P2 |

---

## How WS-A9 tests use this fixture

`tests/test_hrit_productization_smoke.py` (WS-A9) loads this fixture to:

1. Parse `controlling-ato.json` and assert required fields are present.
2. Load `ssp-latitude-table.yaml` and validate each latitude setting has
   either `allowed_values` or `allowed_pattern`.
3. Run the WS-A7 configuration-latitude drift detector against
   `tenant-treas-config.yaml` and assert **0** DRIFT-SCHEMA findings.
4. Run the drift detector against `tenant-irs-config.yaml` and assert
   **exactly 1** DRIFT-SCHEMA P2 finding on `password_minimum_length`.
5. Exercise the lapsed-ATO path by cloning `controlling-ato.json` and
   setting `expires_at` to a past date; assert the ConMon cadence check
   emits a `FAIL` verdict.

---

## How the quickstart uses this fixture

`docs/docs/hrit-productization-quickstart.md` walks through a 10-step
end-to-end flow:

1. Clone and install UIAO.
2. Verify the fixture files parse cleanly.
3. Set a signing key environment variable.
4. Run `uiao reciprocity onboard-agency` for OPM (controlling), TREAS,
   and IRS — producing three signed reciprocity records.
5. Verify each record's HMAC-SHA256 signature with `uiao reciprocity verify`.
6. Run `uiao conmon ato-cadence-check` against `controlling-ato.json`.
7. Inspect the IRS DRIFT-SCHEMA P2 finding emitted by the drift detector.
8. Aggregate per-agency bundles with `uiao reciprocity bundle`.

The known-answer table in the quickstart doc maps directly to the three
agencies in this directory.

---

## Canon references

| Document | Title |
|---|---|
| UIAO_140 | Single-ATO Reciprocity Model |
| Spec2-D6.1 | Federal HRIT Integration Runbook |
| ADR-054 | Single-ATO Reciprocity (authorizing ADR) |
