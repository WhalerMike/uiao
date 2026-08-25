---
adr_id: adr-077
title: "Detached Signatures over Evidence Bundles and OSCAL Assessment Results — Non-Repudiation at the Compliance Edge"
status: PROPOSED
decided: TBD
deciders: Michael Stratton
updated: 2026-05-19
next_review: TBD
review_trigger: FedRAMP 20x signature requirements change; HSM key compromise event; OSCAL signing spec uplift; FIPS 140-3 transition milestone
impact: Closes the non-repudiation gap left by ADR-006 (hashes prove integrity but not provenance); makes ADR-076 AR submission-ready for FedRAMP 20x and RFC-0026
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: false
publication_style: include
published_at: TBD
---

# ADR-077: Detached Signatures over Evidence Bundles and OSCAL Assessment Results

## Status

**PROPOSED** — May 19, 2026

## Context

[ADR-006](../../src/uiao/canon/adr/adr-006-evidence-determinism.md) §4 mandates content hashes on every Evidence Fabric record, and [ADR-016](../../src/uiao/canon/adr/adr-016-evidence-bundle-lifecycle.md) makes bundles immutable at the SEALED transition. Together these guarantee **integrity**: a recipient can verify that the bytes they hold match the hash recorded at seal time.

Integrity is necessary but not sufficient for the compliance edge:

1. **Hashes prove "not modified relative to a recorded claim." Hashes do not prove "produced by UIAO at time T."** A malicious or compromised storage operator could replace a sealed bundle with a fabricated one and recompute the hash; downstream consumers see consistent integrity but the provenance claim is false.
2. **FedRAMP 20x submission and RFC-0026 CA-7 continuous monitoring expect detached signatures over submitted artifacts.** Assessors verify provenance independently of the submitter's infrastructure — that requires a signature, not a hash.
3. **[ADR-076](./adr-076-evidence-fabric-oscal-ar-projection.md) (companion) establishes byte-stable AR emission via JCS canonicalization.** Byte stability is the *precondition* for meaningful signing; without ADR-076, this ADR is impossible. With ADR-076, this ADR is the natural next step.
4. **Federal-personnel auth modernization ([ADR-068](../../src/uiao/canon/adr/adr-068-kerberos-ntlm-elimination.md) §3, [ADR-052](../../src/uiao/canon/adr/adr-052-piv-usaccess-adapter.md))** already commits the substrate to the Federal Common Policy CA G2 algorithm class (ECDSA P-384 / SHA-384). The substrate's own signing algorithm should match the federal-personnel chain, not diverge from it.

The canonical question is **what signing layer the substrate adopts**, and **where in the bundle lifecycle the signing event occurs**.

## Decision

**Seven canonical positions, in operational sequence:**

### 1. Bundle signature at SEAL transition

- Every Evidence Bundle MUST be accompanied by a detached **JWS signature over the bundle's hash-chain head** at the moment it transitions to SEALED.
- The SEAL transition is **not complete** until the signature exists. A bundle that fails to sign cannot enter SEALED state.
- The signature is itself recorded as an Evidence Fabric record (re-entrancy with ADR-006 §1: no silent drops).

### 2. AR signature at emission

- Every OSCAL Assessment Results document emitted via [ADR-076](./adr-076-evidence-fabric-oscal-ar-projection.md) MUST be accompanied by a **detached JWS signature over its JCS-canonicalized JSON**.
- The AR and its signature are emitted in the same transaction. A partially-emitted AR (document without signature, or signature without document) is treated as an emission failure and rolled back.

### 3. Algorithm: ES384

- Canonical signing algorithm: **ES384** (ECDSA over NIST P-384 with SHA-384).
- Matches the Federal Common Policy CA G2 algorithm class per [ADR-052](../../src/uiao/canon/adr/adr-052-piv-usaccess-adapter.md) and [ADR-068](../../src/uiao/canon/adr/adr-068-kerberos-ntlm-elimination.md) §3.
- RS256 / RS384 are **not** acceptable — diverges from the federal-personnel chain. PS384 (RSA-PSS) is acceptable as a transitional fallback only.

### 4. Keys in Azure Key Vault Managed HSM

- Signing private keys live exclusively in **Azure Key Vault Managed HSM (FIPS 140-2 Level 3)**.
- No private-key material is ever exportable from the HSM. Signing is performed via the HSM's sign API.
- Key rotation cadence: 12 months (target), 24 months (maximum). Rotation requires a grace-period overlap during which the previous public key remains published for verification of historical artifacts.

### 5. Verification path is independent of UIAO infrastructure

- A verifier needs only **the artifact (bundle hash-chain head or AR JSON), the detached signature, and the public key**. No UIAO runtime, database, or service dependency.
- Public keys + key IDs are published to a **stable canonical URL** (e.g., a JWKS document at a UIAO-controlled but infrastructure-minimal endpoint).
- Verification CLI (`uiao oscal verify <ar.json> <ar.jws>`) is the reference implementation and is open-source / clean-room re-implementable.

### 6. Signing-as-evidence (re-entrancy)

- Every signing event produces an Evidence Fabric record naming: the artifact signed, the signing key ID, the timestamp, and the JWS itself.
- The substrate signs its own attestations and records the signing event — closing the meta-attestation loop.
- An auditor can challenge: "show me the signing record for AR X" → substrate returns the Evidence Fabric record → auditor independently verifies.

### 7. Optional parallel sigstore/cosign attestation

- A second signature using **sigstore / cosign keyless attestation** MAY be emitted in parallel for OSS-friendly verification.
- Sigstore is **not** a substitute for the HSM-backed JWS — FedRAMP submission requires the HSM signature. Sigstore is purely additive for ecosystems that prefer transparency-log-backed verification.

## Rationale

1. **Hashes prove integrity; signatures prove origin.** The compliance edge needs both. Conflating them — as ADR-006 alone effectively does today — leaves a real gap that FedRAMP 20x submission will surface.
2. **JWS detached mode (RFC 7797) preserves the original document byte-for-byte.** `compliance-trestle`, NIST validators, and external OSCAL tooling continue to work unchanged — they ignore the `.jws` sidecar and process the original JSON.
3. **ES384 + P-384 aligns the substrate's own crypto with the federal-personnel auth chain.** Choosing the same algorithm class the substrate already mandates for PIV/CAC means one less FIPS validation conversation and one less algorithm to deprecate.
4. **HSM-bound keys bound the threat model.** Key exfiltration requires physical compromise of a Microsoft-operated FIPS 140-2 Level 3 HSM. The substrate is not in the business of defending key material itself — that's delegated to a validated boundary.
5. **Signing-as-evidence closes the meta-loop.** Without recording the signing event, an auditor must trust the substrate's attestation that signing happened. With it, the substrate provides cryptographic evidence of its own evidence emission — the regress terminates at the HSM.
6. **The verification path independence is what makes the signature compliance-grade.** A signature that requires UIAO infrastructure to verify is not a signature — it's a system-internal authentication token. Detached JWS + published JWKS makes verification a one-line cryptographic operation the auditor performs offline.
7. **SEAL becomes a non-free transition.** SEAL today is a free state change. After this ADR, SEAL carries cryptographic cost (HSM round-trip). This is an operationally accepted cost: SEAL is the moment at which the bundle becomes externally attestable; that's the right time to incur the signing cost.

## Implementation Plan

| Phase | Deliverable | Owner |
|---|---|---|
| **A** | Signing-key provisioning in Azure Key Vault Managed HSM + JWKS publication endpoint | Crypto team |
| **A** | Signing service: takes (hash, key-id) → returns detached JWS | Crypto team |
| **A** | Verification CLI (`uiao oscal verify`) + clean-room reference verifier | Tools team |
| **B** | SEAL-transition gate: bundle SEAL not complete until signing succeeds | Substrate team |
| **B** | OSCAL AR signer integration with [ADR-076](./adr-076-evidence-fabric-oscal-ar-projection.md) projector | Compliance team |
| **B** | Signing-event Evidence Fabric record schema + emission | Substrate team |
| **B** | NIST OSCAL metaschema validation in CI continues to pass against signed AR (sidecar `.jws` does not perturb the JSON) | Compliance team |
| **C** | Key rotation procedure + grace-period overlap policy (previous public key remains published for historical verification) | Crypto + Compliance teams |
| **C** | Optional sigstore/cosign parallel attestation pipeline | Tools team |
| **C** | Re-attestation procedure for the (rare) HSM key compromise scenario: re-sign historical bundles under a new key without modifying their content (per ADR-006 §2 — corrections append, never overwrite) | Crypto + Compliance teams |

## Consequences

**Positive:**
- Non-repudiation at the compliance edge — auditors can verify provenance independent of UIAO infrastructure.
- FedRAMP 20x and RFC-0026 CA-7 submission requirements are met natively.
- Signing-as-evidence enables third-party challenge: any party can demand the signing record, verify it, and independently confirm "this AR was produced by UIAO at time T."
- Algorithm parity with the federal-personnel auth chain (ES384/P-384) consolidates the substrate's crypto posture.
- HSM-bound keys mean key compromise is a defined, narrow threat with a documented response procedure rather than an open question.

**Negative:**
- HSM key rotation becomes a compliance-bearing event. Lost or compromised keys force re-attestation of historical bundles — recoverable per ADR-006 §2 (append corrections) but operationally non-trivial.
- HSM round-trip adds latency to SEAL. Continuous-monitoring throughput is bounded by HSM signing throughput (typically thousands of signs/sec; not a concern at expected bundle cadence).
- Key Vault Managed HSM cost is a recurring operational expense, not free as record-level hashing is.
- A dual-signature world (HSM JWS + optional sigstore) doubles the surface area of verification UX. Documentation must be clear that only the HSM signature is FedRAMP-required.

**Operationally accepted:** SEAL is no longer a free state transition. Every bundle now carries a cryptographic cost at seal time, and every AR carries one at emission. The compliance edge is now load-bearing on the HSM availability SLA; HSM outage means no new bundles can SEAL (existing sealed bundles remain verifiable). This is the right trade — the alternative is FedRAMP non-submittability.

## References

- [ADR-006](../../src/uiao/canon/adr/adr-006-evidence-determinism.md) — Evidence Determinism (hash-chain head is this ADR's input)
- [ADR-016](../../src/uiao/canon/adr/adr-016-evidence-bundle-lifecycle.md) — Evidence Bundle Lifecycle (SEAL transition is the signing trigger)
- [ADR-043](../../src/uiao/canon/adr/adr-043-fedramp-rfc-0026-ca7-integration.md) — FedRAMP RFC-0026 CA-7 Integration (continuous monitoring submission consumer)
- [ADR-106](../../src/uiao/canon/adr/adr-106-fedramp-20x-integration.md) — FedRAMP 20x Integration (submission pathway)
- [ADR-052](../../src/uiao/canon/adr/adr-052-piv-usaccess-adapter.md) — PIV/USAccess Adapter (Federal Common Policy CA G2 algorithm alignment)
- [ADR-068](../../src/uiao/canon/adr/adr-068-kerberos-ntlm-elimination.md) — Kerberos/NTLM Elimination (CBA + FIPS posture)
- [ADR-076](./adr-076-evidence-fabric-oscal-ar-projection.md) — companion: byte-stable AR projection (precondition for meaningful signing)
- RFC 7515 — JSON Web Signature (JWS)
- RFC 7517 — JSON Web Key (JWK) — for the published JWKS document
- RFC 7797 — JWS Unencoded Payload Option (detached signature mode)
- RFC 8785 — JSON Canonicalization Scheme (JCS, inherited from ADR-076)
- FIPS 140-2 Level 3 — Azure Key Vault Managed HSM validation
- Sigstore / cosign specification — https://docs.sigstore.dev/ (optional parallel layer)
