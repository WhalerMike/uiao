---
document_id: UIAO_203
title: "UIAO Token-Based Overlay Authorization Specification"
version: "1.0"
status: Draft
owner: "Michael Stratton"
created_at: "2026-06-22"
updated_at: "2026-06-22"
---

# UIAO Token-Based Overlay Authorization Specification

## 1. Overview

This spec defines the **token-based, per-call authorization unit** for the
`overlay` mission class. It is the first of the three downstream specs
mandated by [ADR-066](../adr/adr-066-application-aware-networking-and-token-bound-transport.md)
(Application-Aware Networking and Token-Bound Transport Plane) and
re-allocated from the squatted UIAO_122 slot to UIAO_203 by
[ADR-123](../adr/adr-123-transport-plane-reconciliation.md).

It is the canon counterpart to the doctrinal decision ADR-066 §Decision #2
ratified: *a "session" — any long-lived authorization context that survives
a single authorized intent — is no longer a canonical concept in UIAO.*
Every adapter call, evidence transfer, and overlay tunnel carries a
short-lived, audience-scoped token bound to four axes. This spec makes that
token a typed, validated, evidence-emitting object.

Its two companion specs:

- **UIAO_204** (Application-Aware Overlay Fabric Model) defines the
  `OverlayTunnel` object whose *lease* this token *bounds*. UIAO_203 is the
  authorization; UIAO_204 is the addressable path it authorizes.
- **UIAO_205** (Overlay-Plane Telemetry Contract) defines the flow telemetry
  that lets a `mission-class: overlay` conformance adapter observe whether
  the live path matches the token's declared binding.

### 1.1 Lane discipline (inherited from ADR-066)

UIAO **issues, validates, and logs** overlay tokens as a governance concern;
it does **not** terminate tunnels, route packets, or hold a data-plane
position. The `token-issuer` adapter (ADR-066 reserved slot,
`mission-class: overlay`) is a change-maker that *mints* tokens and emits
issuance records as evidence — it is not the network's authorization
enforcement point. Enforcement happens at the fabric the agency operates;
UIAO reconciles observed enforcement against the token record and emits
`DRIFT-OVERLAY` findings where they diverge.

## 2. The overlay token

### 2.1 Binding axes (required)

Every overlay token binds **all four** axes. A token missing any axis is
invalid at issuance and MUST be rejected by the issuer, not merely flagged.

| Axis | Source plane | Meaning |
|---|---|---|
| **Caller identity** | Identity | The authenticated principal (workforce or workload identity) making the call. |
| **Target application** | Identity (Application Identity, UIAO_129) | The specific governed object the call is *for* — not a host or subnet, an application identity. |
| **Device posture** | Endpoint + Telemetry | Compliance/health state of the originating device at issuance time. |
| **Location** | Addressing (orgPath / LocPath) | The orgPath-derived and LocPath-derived location the call originates from. |

The four axes are the **same evidence inputs** the Zero-Trust decision
envelope already consumes (UIAO_120 §Pillars). The overlay token is the
transport-plane projection of that envelope: it carries the decision to the
path instead of leaving the path to infer it.

### 2.2 Token format (doctrine, not vendor lock)

Per ADR-066 §Decision, this spec does **not** pick a single wire format. A
conforming token is any of the following, provided it carries the §2.1
binding axes as verifiable claims and meets the lifetime/scope/replay rules
below:

- a **SPIFFE SVID** (X.509 or JWT-SVID),
- a **signed JWT** (asymmetric signature; no `alg: none`), or
- a **PASETO** (v4.public).

The format is declared per deployment in `overlay-fabric.schema.json`
(UIAO_204) via the issuer's `token_format` field. Symmetric-secret tokens
(HMAC-shared-secret) are **non-conforming**: they cannot be validated at a
relying party without sharing the minting secret, which reintroduces the
standing-credential antipattern this spec exists to retire.

### 2.3 Required claims

| Claim | Maps to | Rule |
|---|---|---|
| `sub` | Caller identity | Stable principal identifier. |
| `aud` | Target application | Exactly one audience per token (§3.2). |
| `posture` | Device posture | Posture digest + source adapter ref. |
| `loc` | Location | orgPath + LocPath binding (UIAO_193 carriage). |
| `iat` / `exp` | Lifetime | `exp - iat` ≤ the canon maximum (§3.1). |
| `jti` | Replay defense | Unique per token; single-use (§3.4). |
| `iss` | Issuer | The governed `token-issuer` adapter identity (§4). |

## 3. Token lifecycle

### 3.1 Lifetime

A token's lifetime (`exp - iat`) is **bounded by canon**, not by the
relying party. The canon-declared maximum is the value against which the
`DRIFT-OVERLAY` **P1** finding fires (ADR-066 §"Drift taxonomy extension":
*token lifetime exceeds canon-declared maximum*).

- **Default maximum:** **300 seconds** (5 minutes). A token is sized to
  cover a single authorized intent plus clock-skew tolerance, not a working
  session.
- **Skew allowance:** validators accept `iat` up to **60 seconds** in the
  past and reject any token whose `exp` is already passed at validation.
- **Per-deployment override:** the maximum may be lowered (never raised
  above 300s without a superseding ADR) via the issuer's
  `max_token_lifetime_seconds` field in `overlay-fabric.schema.json`.

The lifetime **bounds the `OverlayTunnel` lease** (UIAO_204): a tunnel whose
lease outlives its issuing token is a `DRIFT-OVERLAY` **P2** finding
(*`OverlayTunnel` observed without an issuing token, or with an expired
lease*).

### 3.2 Scope / audience

Every token is **audience-scoped to exactly one target application** (`aud`,
§2.1). A token validated outside its declared audience is a `DRIFT-OVERLAY`
**P1** finding (ADR-066: *token validated outside its declared audience
scope*). Wildcard or multi-audience tokens are non-conforming — they are the
session model wearing a token's clothes.

### 3.3 Rotation

Because lifetimes are ≤ 300s, **rotation is re-issuance, not refresh**.
There is no long-lived refresh token. The caller re-presents its identity,
posture, and location to the issuer for each new intent; the issuer mints a
fresh token. The **signing keys** of the issuer rotate on a declared cadence
(`signing_key_rotation_days`, default **90**), with overlapping validity
windows so in-flight tokens validate across a rotation boundary. Key-rotation
agility is the post-quantum readiness hook ADR-066 §"Executive-order
alignment" ties to EO 14144 (algorithm rotation).

### 3.4 Revocation and replay defense

Short lifetimes make **expiry the primary revocation mechanism**: a
compromised token is worthless within 300 seconds. For the residual window:

- **Single-use `jti`.** The relying party (or the `flow-telemetry` /
  `posture-telemetry` conformance adapters on its behalf) records each
  `jti`; a second presentation of the same `jti` is rejected and raises a
  `DRIFT-OVERLAY` **P2** (replayed token).
- **Issuer revocation list.** The `token-issuer` adapter MAY publish a
  short-TTL revocation set (revoked `jti`s within their un-expired window)
  for relying parties that need sub-lifetime revocation. The set is
  evidence-emitting like every other issuer output (§5).
- **Posture-change invalidation.** A posture transition that fails the
  policy that authorized the token (device falls out of compliance) is a
  re-evaluation trigger; existing tokens are not refreshed, and the next
  issuance request fails closed.

## 4. Issuer placement — Path A (in-boundary)

ADR-066 §"GCC-Moderate boundary impact" required this spec to **select
Path A or document a Path B exception**. This spec **selects Path A**.

> **Decision (UIAO_203 §4): the overlay `token-issuer` runs inside the
> GCC-Moderate boundary.** No boundary exception is requested or required.

### 4.1 Rationale

- **No new boundary exception.** Path B (issuer outside the boundary) would
  require a discrete declared exception in `gcc-boundary-gap-registry.yaml`
  alongside the existing Amazon Connect and SailPoint carve-outs, each of
  which is encoded as a schema enum in lockstep with an authorizing ADR
  (per the cloud-boundary doctrine). Minting the credential that authorizes
  *every overlay path* is precisely the function that should not sit on the
  far side of a boundary it is meant to protect.
- **Key material stays in-boundary.** The issuer's signing keys live in an
  in-boundary key-management surface (an HSM, an in-boundary certificate
  authority, a verified-credential service, or an in-boundary SPIFFE/SPIRE
  deployment). The specific surface is a deployment choice declared in
  `overlay-fabric.schema.json`; that it is in-boundary is canon.
- **Issuance evidence stays in-boundary.** Per §5 every issuance is an
  evidence record; keeping the issuer in-boundary keeps that evidence inside
  the same authorization boundary as the canon it derives from (operating
  principle: canon-anchored evidence).

### 4.2 What a future Path B would cost

If a deployment ever requires an out-of-boundary issuer, this spec is
**superseded by an ADR**, not amended in place. That ADR must (a) add a
discrete exception enum to `gcc-boundary-gap-registry.yaml` with the same
rigor as the Amazon Connect entry, (b) define the compensating controls for
out-of-boundary key custody, and (c) re-rationalize the issuance-evidence
provenance chain. Until such an ADR exists, an observed out-of-boundary
issuer is a `DRIFT-AUTHZ` finding.

## 5. Evidence contract

Every issuance is an **evidence record**, canon-anchored to this spec
(UIAO_203 v1.0). The `token-issuer` adapter emits, per token:

| Field | Content |
|---|---|
| `jti` | The token's unique id (the token body itself is **not** logged). |
| `sub` / `aud` | Caller identity and target application. |
| `posture_ref` | Reference to the posture evidence that gated issuance. |
| `loc` | orgPath + LocPath binding at issuance. |
| `iat` / `exp` | Issuance and expiry timestamps. |
| `decision` | `issued` or `denied`, with the policy id that decided. |
| `content_hash` | Provenance hash binding the record to issuer inputs. |

The token **secret/signature is never written to evidence** — only the
non-secret claims and the decision. Denied issuances are logged with the
same schema (`decision: denied`) so the evidence graph can trace
fail-closed events, not just successes.

## 6. Drift binding (`DRIFT-OVERLAY`)

This spec is the SSOT for the **issuance-side** severities of the
`DRIFT-OVERLAY` class introduced by ADR-066 and renamed by ADR-123. The
full taxonomy lands in `docs/docs/16_DriftDetectionStandard.qmd` as part of
the cross-cutting UIAO_205 work; the issuance-side rows are:

| Severity | Condition (issuance/authorization) |
|---|---|
| **P1** | Token lifetime exceeds the canon maximum (§3.1), **or** a token is validated outside its declared `aud` scope (§3.2). |
| **P2** | `OverlayTunnel` observed without an issuing token, an expired lease, or a replayed `jti` (§3.4). |
| **P3** | Issuance evidence gap exceeds the freshness window for an active `token-issuer` adapter. |
| **P4** | Path-policy variance between the token's `loc` binding and the observed flow (reconciled via UIAO_205 telemetry). |

P4 detection depends on UIAO_205 flow telemetry and is specified there; it
is listed here for taxonomy completeness.

## 7. Conformance

An adapter claiming `mission-class: overlay` with a token-issuance role
(the reserved `token-issuer` slot) conforms to this spec when it:

1. Mints tokens carrying **all four** §2.1 binding axes and the §2.3 claims.
2. Rejects issuance when any axis is absent or its policy fails closed.
3. Enforces `exp - iat` ≤ the canon maximum and single `aud` per token.
4. Runs **in-boundary** (§4) with in-boundary key custody.
5. Emits a §5 evidence record for every issuance, including denials.
6. Declares its `token_format`, `max_token_lifetime_seconds`, and
   `signing_key_rotation_days` in `overlay-fabric.schema.json` (UIAO_204).

Relying-party / conformance adapters (`flow-telemetry`, `posture-telemetry`)
conform when they record `jti` for replay detection and surface the §6
findings.

## 8. References

- [ADR-066](../adr/adr-066-application-aware-networking-and-token-bound-transport.md)
  — doctrinal anchor (sixth mission class; token-bound per-call
  authorization; `OverlayTunnel`; EO 14028 §3 / EO 14144 / NIST SP 800-207
  citation chain).
- [ADR-123](../adr/adr-123-transport-plane-reconciliation.md) — `transport`
  → `overlay` rename; UIAO_122 → UIAO_203 re-allocation; this spec's slot of
  record.
- **UIAO_204** (Application-Aware Overlay Fabric Model) — the `OverlayTunnel`
  object and `overlay-fabric.schema.json` this spec's fields populate.
- **UIAO_205** (Overlay-Plane Telemetry Contract) — flow telemetry for P4
  reconciliation.
- [UIAO_120](zero-trust.md) — Zero-Trust Integration Layer; the four binding
  axes are the transport-plane projection of its decision envelope.
- [UIAO_129](application-identity-model.md) — Application Identity, the
  `aud` target.
- UIAO_193 — OrgPath multi-cloud binding carriage for the `loc` claim.

