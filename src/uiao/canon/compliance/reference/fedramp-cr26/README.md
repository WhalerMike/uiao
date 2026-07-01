# FedRAMP CR26 Reference Materials

This folder vendors two complementary CR26 reference sources:

1. **`official/`** — The official FedRAMP/rules JSON (`version 2026.06.24.01`),
   published 2026-06-24 by FedRAMP as the Consolidated Rules for 2026 stable
   release. **This is the primary rules authority** (ADR-126 D1). US Government
   work; public domain.

2. **`snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/`** — Unofficial
   Palladium CR26 OSCAL generator output (CC0 1.0). The OSCAL-format KSI
   catalog, profile shells, and CR26 ↔ SP 800-53 rev5 mapping collection.
   Secondary source for OSCAL-format consumption until FedRAMP publishes an
   official OSCAL derivation (ADR-126 D2).

Neither source is canon authority. Both are reference material, parallel to
`../fedramp-rev5/`. Doctrinal alignment (which KSI themes the substrate emits,
what counts as `DRIFT-EVIDENCE-STALE`) lives in
[`UIAO_133`](../../../specs/fedramp-20x-integration.md) and
[`ADR-106`](../../../adr/adr-106-fedramp-20x-integration.md). Authority posture
and governance for both sources are documented in
[`ADR-126`](../../../adr/adr-126-fedramp-cr26-official-rules-adoption.md) and
[`ADR-061`](../../../adr/adr-061-fedramp-cr26-catalog-vendoring.md).

The full CR26 rules assessment — FRR coverage, KSI summary, gap items — is at
[`UIAO_207`](../../../specs/fedramp-cr26-rules-assessment.md).

---

## Official source (`official/`)

| Field | Value |
|---|---|
| Repository | `FedRAMP/rules` |
| URL | https://github.com/FedRAMP/rules |
| Version | `2026.06.24.01` |
| Last updated | `2026-06-24` |
| Retrieved | `2026-07-01` |
| License | US Government work — public domain (17 U.S.C. § 105) |
| Authority | **Official** — published by GSA / FedRAMP PMO |
| SHA-256 | `48d1fb4c1674c15f1a966f94c9f519b246af377d2ff51845083131ad99da8c60` |

The official JSON contains:
- **FRD**: 75 defined terms (Stakeholder, Certification, Vulnerability, Assessment, Incident, Significant Changes, Information Resource, Accounts, Customer Effect)
- **FRR**: 17 rule categories / 29 variants (all / 20x / rev5)
- **KSI**: 10 themes / 46 indicators with NIST SP 800-53 anchors
- **CTL**: 14 NIST control families

Effective dates: optional adoption 2026-07-04; mandatory 2027-01-01; no new Rev5
certifications after 2027-06-11.

See [`official/PROVENANCE.md`](official/PROVENANCE.md) for the full manifest and
[`official/SHA256SUMS`](official/SHA256SUMS) for integrity verification.

---

## Palladium OSCAL snapshot (`snapshot/c31eb04…/`)

The pinned snapshot lives under
[`snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/`](snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/);
its [`PROVENANCE.md`](snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/PROVENANCE.md)
records upstream metadata, the file manifest, and per-file SHA-256
hashes verifiable via `sha256sum -c SHA256SUMS`.

| Field | Value |
|---|---|
| Repository | `Palladium-Innovations/fedramp-cr26-oscal` |
| URL | https://github.com/Palladium-Innovations/fedramp-cr26-oscal |
| Pinned commit | `c31eb04c082d6d578a26a00de9a482707ab7a00c` (2026-05-06) |
| License | CC0 1.0 Universal (public domain dedication) |
| Authority | **Unofficial** — not affiliated with FedRAMP, GSA, NIST, or the OSCAL project |

Contents: OSCAL XML/JSON/YAML catalog, 20x/rev5 profile shells, CR26 ↔ SP 800-53
rev5 mapping collection. The catalog at this SHA exposes all 10 KSI subgroups,
46 controls — confirmed consistent with the official JSON (ADR-126 §D1 note).

### How uiao uses this snapshot

1. **OSCAL KSI catalog.** The `fedramp-cr26-catalog` conformance adapter (ADR-061
   D3) reads the OSCAL catalog for KSI ID resolution and DRIFT-SCHEMA checks.
   The official JSON's `KSI` section is the primary ID surface (ADR-126 D3);
   the OSCAL catalog is the shape validator.

2. **CR26 ↔ rev5 control translation.** The mapping collection is the translation
   surface for emitters that need to express control claims in both vocabularies
   during the 20x adoption window.

3. **Drift surface.** When the pin advances (ADR-061 D2), the prior snapshot is
   retained for one cycle so the adapter can emit `DRIFT-SCHEMA` / `DRIFT-PROVENANCE`.

### Local handling

Do not modify any file under `snapshot/<upstream-sha>/` by hand;
snapshots are immutable per ADR-061 D2. Local modifications belong
under `overlays/<purpose>/`. To advance the pin to a newer upstream commit,
follow the refresh procedure in
[`snapshot/c31eb04…/PROVENANCE.md`](snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/PROVENANCE.md#how-to-refresh).
