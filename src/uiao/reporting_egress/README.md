# `uiao.reporting_egress` — Gated Reporting-Egress Actuator

Implements the *transport* leg of continuous monitoring: submit already-generated
ConMon evidence outward to external federal destinations, under a gate that never
transmits without an explicit live flag **and** a human approval token.

- **Doctrine:** [`ADR-128`](../canon/adr/adr-128-reporting-egress-actuator.md)
- **Design & contract:** [`UIAO_208`](../canon/specs/reporting-egress.md)
- **CLI:** `uiao report` (see [`UIAO_008`](../canon/UIAO_008_CLI_Reference_v1.0.md) §3.4)

## Why this exists

UIAO already **generates** evidence (`uiao oscal bundle`, `uiao conmon export-oa`,
the ScubaDrift pipeline) and writes it to local files. It did not **transport** that
evidence to the destinations that consume it. This package adds that step —
correctly, as an ADR-092 *actuation*, not as a network-data-plane position.

## Invariants (enforced in `engine.submit`)

| Condition | Disposition | Transmits? |
|---|---|---|
| `live=False` (default) | `PLANNED` | no — dry-run, validate only |
| `live=True`, no/invalid approval | `BLOCKED` | no — **L3 gate** |
| `live=True` + approval, validation problems | `BLOCKED` | no — refuse malformed |
| `live=True` + approval, driver unconfigured | `BLOCKED` | no — endpoint not wired |
| `live=True` + approval + configured + valid | `SUBMITTED` | **yes — the only path** |

There is no code path that transmits without both a live flag and a valid
`Approval`. No autonomous (L4) submission at Moderate. `CLAW` is intentionally not a
destination — raw telemetry stays on the native pipe (ADR-066).

## Layout

| File | Role |
|---|---|
| `models.py` | `Destination`, `Disposition`, `Approval`, `Submission`, `SubmissionResult` |
| `drivers.py` | `EgressDriver` base + 5 drivers + registry (`get_driver`, `list_destinations`) |
| `engine.py` | `submit()` — the gated engine (single public entry point) |

## Usage

```python
from pathlib import Path
from uiao.reporting_egress import Approval, Destination, Submission, submit

sub = Submission(Destination.CISA_SBOM, Path("out/sbom.json"), "cyclonedx-sbom")

# Dry-run (default): validate and plan, transmit nothing.
result = submit(sub)                       # -> PLANNED

# Live: requires an approval token (the L3 gate).
approval = Approval(approver="jane.isso", approved_at="...", operation="submit:cisa-sbom")
result = submit(sub, live=True, approval=approval)   # -> BLOCKED unless a live endpoint is wired
```

CLI:

```bash
uiao report list-destinations
uiao report submit -d cisa-sbom -a out/sbom.json -t cyclonedx-sbom            # dry-run
UIAO_CISA_SBOM_ENDPOINT=https://... \
  uiao report submit -d cisa-sbom -a out/sbom.json -t cyclonedx-sbom \
    --live --approver "jane.isso"                                            # L3-gated live
```

## Wiring a live destination

Drivers ship `configured=False`. To make one live:

1. Implement `transmit()` against the real endpoint (URL, credentials, mutual TLS).
   `CisaSbomDriver` is the reference — it POSTs to `UIAO_CISA_SBOM_ENDPOINT`.
2. Ensure `configured` returns True only when an endpoint is set.
3. Keep credentials **out of canon** (canon is read-only, UIAO-SSOT).
4. Record the `Approval` token in the immutable audit trail (SA-family).

This is gated on the in/out-of-boundary decision — see ADR-128 §7.

## Tests

- `tests/test_reporting_egress.py` — engine + CLI invariants (12).
- `tests/test_reporting_egress_live_demo.py` — live `SUBMITTED` against a local
  `http.server` (2). Standard library only; no network egress.
