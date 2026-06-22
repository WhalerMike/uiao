---
document_id: UIAO_204
title: "UIAO Application-Aware Overlay Fabric Model"
version: "1.0"
status: Draft
owner: "Michael Stratton"
created_at: "2026-06-22"
updated_at: "2026-06-22"
---

# UIAO Application-Aware Overlay Fabric Model

## 1. Overview

This spec promotes UIAO_001's "identity-derived, certificate-anchored tunnel
abstraction" from concept to a **typed canonical object** — the
`OverlayTunnel` — and defines the **overlay fabric configuration** the
substrate observes and reconciles. It is the second of the three downstream
specs mandated by [ADR-066](../adr/adr-066-application-aware-networking-and-token-bound-transport.md)
and re-allocated from the squatted UIAO_123 slot to UIAO_204 by
[ADR-123](../adr/adr-123-transport-plane-reconciliation.md).

Where its companions sit:

- **UIAO_203** (Token-Based Overlay Authorization) defines the **token** —
  the per-call authorization unit. UIAO_204 defines the **path** that token
  authorizes and the **lease** the token bounds.
- **UIAO_205** (Overlay-Plane Telemetry Contract) defines the **flow
  telemetry** that lets a conformance adapter detect when the observed path
  diverges from the `OverlayTunnel` record (the `DRIFT-OVERLAY` P4 case).

The machine-readable contract is
[`overlay-fabric.schema.json`](../../schemas/overlay-fabric/overlay-fabric.schema.json).

### 1.1 Lane discipline (inherited from ADR-066)

UIAO **observes, reconciles, and emits evidence** about the overlay fabric.
It does **not** terminate tunnels, route packets, modify routes, or hold a
data-plane position. An `OverlayTunnel` is a *record of a leased path*, not a
handle the substrate uses to move traffic.

## 2. The `OverlayTunnel` object

An `OverlayTunnel` carries `{identity, application, posture, location, token,
lease, certificate-chain}` (ADR-066 §Decision #3). Its four binding axes are
**the same four** the overlay token binds (UIAO_203 §2.1) — by construction,
because the tunnel is the path the token was minted for:

| Field | Source | Note |
|---|---|---|
| `identity` | token `sub` | Caller identity. |
| `application` | token `aud` | Target application (UIAO_129). |
| `posture` | token `posture` | Device/application posture at lease time. |
| `location` | token `loc` | orgPath + LocPath binding. |
| `token` | UIAO_203 | `{jti, exp}` of the authorizing token. |
| `lease` | this spec §4 | `{leased_at, expires_at}`. |
| `certificate_chain` | fabric | Optional anchoring chain. |

### 2.1 Tunnels are leased, not opened

A tunnel is **leased** for the lifetime of a single authorized intent, then
allowed to lapse. There is no long-lived tunnel that survives its token —
that would be the session model UIAO_203 §1 retires, wearing an overlay's
clothes. The canonical `OverlayTunnel` record is provenance-anchored to SSOT
and emitted as evidence; it is never the live data-plane object.

## 3. The overlay fabric configuration

`overlay-fabric.schema.json` constrains an overlay fabric document with three
parts (ADR-066 §"Adapter registry implications"):

### 3.1 Issuer configuration

The in-boundary token-issuer block carries the fields UIAO_203 references:

- `token_format` — one of `spiffe-svid-x509`, `spiffe-svid-jwt`, `jwt`,
  `paseto-v4-public` (UIAO_203 §2.2). Symmetric-secret formats are absent by
  design — they are non-conforming.
- `max_token_lifetime_seconds` — 1–300, the canon ceiling (UIAO_203 §3.1).
- `signing_key_rotation_days` — default 90 (UIAO_203 §3.3).
- `placement` — `in-boundary` (Path A, preferred) or `declared-exception`
  (Path B). Path B requires `exception_ref` to a
  `gcc-boundary-gap-registry.yaml` entry; the schema enforces this
  conditionally. UIAO_203 §4 **selects Path A**.
- `posture_source_ref` — the posture adapter feeding the posture axis.

### 3.2 Fabric entries

Each fabric entry declares `id`, `kind` (`sd-wan` / `sase` / `service-mesh`),
`mission-class: overlay` (const — distinct from the identity-plane
`*_transport` write seams), a `token_issuer_ref`, a `posture_source_ref`, and
a `status` (`reserved` / `proposed` / `active`). The reserved slots from
ADR-066 — `sdwan-fabric`, `sase-egress`, `service-mesh` — land here as
`status: reserved` until a deployment activates them.

### 3.3 The `OverlayTunnel` definition

The schema's `$defs/overlayTunnel` constrains the runtime tunnel record so
the telemetry and evidence pipelines (UIAO_205) validate observed tunnels
against a single shape.

## 4. Lease semantics (normative)

The **token bounds the lease**. The governing invariant:

> **UIAO_204 §4 invariant:** `lease.expires_at` ≤ `token.exp`.

A lease may be **shorter** than the token (a fabric may re-lease within a
token's life) but never **longer**. JSON Schema cannot express the cross-field
comparison, so it is enforced at reconciliation by the `mission-class: overlay`
conformance adapters and surfaced as drift (§5), not by the schema. A tunnel
observed with no authorizing token, or with `lease.expires_at` past, is not a
schema error — it is a **`DRIFT-OVERLAY` P2** finding.

## 5. Drift binding (`DRIFT-OVERLAY`, fabric side)

UIAO_203 §6 is SSOT for the **issuance-side** severities; this spec is SSOT
for the **fabric/path-side** severities. Both feed the taxonomy SSOT
(`docs/docs/16_DriftDetectionStandard.qmd`) as part of UIAO_205.

| Severity | Condition (fabric / path) |
|---|---|
| **P2** | `OverlayTunnel` observed without an issuing token, or with `lease.expires_at` past (lease outlived its token, §4). |
| **P4** | Path-policy variance — the observed flow's path diverges from the tunnel's `location` binding (reconciled via UIAO_205 telemetry). |

P1 (lifetime / audience) and P3 (issuance evidence gap) are issuance-side and
owned by UIAO_203 §6.

## 6. Conformance

An overlay fabric document conforms when it validates against
`overlay-fabric.schema.json` **and**:

1. Its issuer declares `placement: in-boundary` (UIAO_203 §4), or carries an
   `exception_ref` for a declared Path B.
2. Every fabric entry resolves its `token_issuer_ref` and `posture_source_ref`
   to declared adapters.
3. Every observed `OverlayTunnel` satisfies the §4 lease invariant; violations
   are emitted as `DRIFT-OVERLAY` P2, not suppressed.

## 7. References

- [ADR-066](../adr/adr-066-application-aware-networking-and-token-bound-transport.md)
  — doctrinal anchor (`OverlayTunnel`, lease semantics, lane discipline).
- [ADR-123](../adr/adr-123-transport-plane-reconciliation.md) — `overlay`
  naming; UIAO_123 → UIAO_204 re-allocation; this spec's slot of record.
- [UIAO_203](token-based-overlay-authorization.md) — the token this fabric's
  tunnels are leased against; issuer field definitions.
- **UIAO_205** (Overlay-Plane Telemetry Contract) — flow telemetry for P4
  reconciliation.
- [`overlay-fabric.schema.json`](../../schemas/overlay-fabric/overlay-fabric.schema.json)
  — the machine-readable contract.
- [UIAO_120](zero-trust.md) — Zero-Trust Integration Layer; the Overlay
  Fabric is the enforcement layer for the four ZT pillars.

