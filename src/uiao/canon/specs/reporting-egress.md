---
document_id: UIAO_208
title: "Reporting-Egress Actuator — Design & Contract"
version: "0.1"
status: Draft
owner: "Michael Stratton"
created_at: "2026-07-09"
updated_at: "2026-07-09"
mas-scope: "in-scope"
related_adrs:
  - ADR-128
  - ADR-092
  - ADR-066
  - ADR-040
---

# UIAO_208 — Reporting-Egress Actuator: Design & Contract

> **Status: DRAFT.** Detailed design for [`ADR-128`](../adr/adr-128-reporting-egress-actuator.md).
> Implemented as a dry-run-safe scaffold; no live government endpoint is wired.

## 1. Purpose

Give UIAO the "file / transport" leg of continuous monitoring: submit
already-generated ConMon evidence outward to external federal destinations,
under a gate that never transmits without a live flag and a human approval.
Generation already exists (`uiao oscal bundle`, `uiao conmon export-oa`, the
ScubaDrift pipeline); this is the missing egress step.

## 2. Module layout

| Path | Role |
|---|---|
| `src/uiao/reporting_egress/models.py` | `Destination`, `Disposition`, `Approval`, `Submission`, `SubmissionResult` |
| `src/uiao/reporting_egress/drivers.py` | `EgressDriver` base + five stub drivers + registry (`get_driver`, `list_destinations`) |
| `src/uiao/reporting_egress/engine.py` | `submit()` — the gated engine (single public entry point) |
| `src/uiao/cli/report.py` | `uiao report` command group (`list-destinations`, `submit`) |
| `tests/test_reporting_egress.py` | happy-path + failure-mode tests (12) |

## 3. The engine contract (`submit`)

`submit(submission, *, live=False, approval=None, driver=None) -> SubmissionResult`

| Condition | Disposition | Transmits? |
|---|---|---|
| `live=False` (default) | `PLANNED` | no — validates and plans only |
| `live=True`, no/invalid `approval` | `BLOCKED` | no — **L3 gate** |
| `live=True` + approval, validation problems | `BLOCKED` | no — refuse malformed |
| `live=True` + approval, driver `configured=False` | `BLOCKED` | no — endpoint not wired |
| `live=True` + approval + configured + clean | `SUBMITTED` | **yes** — the only path |

`submit` always returns a `SubmissionResult` (never raises on a gate/validation
outcome), so every attempt yields an auditable disposition. There is no path
that transmits without both `live=True` and a valid `Approval` — i.e. no
autonomous (L4) submission at Moderate.

## 4. Destination drivers

Five stubs, each `configured=False` in the scaffold: `cdm`, `cyberscope`,
`fedramp-repo`, `cisa-sbom`, `cisa-incident`. Each declares the artifact types it
`accepts` and validates the submission against them. `CLAW` is intentionally
**not** a destination — raw telemetry stays on the native cloud pipe (ADR-128 §5).

A driver becomes live by (a) setting `configured=True` and (b) implementing
`transmit()` against a real endpoint with credentials + mutual TLS. That is a
per-destination landing task, gated on security review and the boundary decision.

## 5. Landing checklist (out of scaffold scope)

- [ ] Boundary decision: Platform Server (in-boundary) vs. SaaS (own FedRAMP ATO) — ADR-128 §7.
- [ ] Register the five drivers in `canon/modernization-registry.yaml` as `integration`-class actuators.
- [ ] Credential handling **outside** canon (canon stays read-only, UIAO-SSOT).
- [ ] Wire each live endpoint behind review; flip `configured` per destination.
- [ ] Record the `Approval` token in the immutable audit trail (SA-family).
- [ ] Set ADR-128 `publish_to_site: true` once a driver is live under review.

## 6. Non-goals

- Not a network data-plane position (no tunnels/routes/packets — ADR-066).
- Not autonomous submission (permanently L3-capped at Moderate — ADR-128 §3).
- Not a telemetry forwarder (CLAW stays native; UIAO attests the feed).
- Does not make the AO decision, the risk acceptance, or the independent assessment.
