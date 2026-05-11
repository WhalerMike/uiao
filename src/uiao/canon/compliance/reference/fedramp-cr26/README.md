# FedRAMP CR26 OSCAL Reference Materials

This folder vendors the unofficial Palladium CR26 OSCAL generator
output that gives uiao a stable KSI / control-ID surface to anchor
against while the underlying FedRAMP CR26 source data is still in
Public Preview. The pinned snapshot lives under
[`snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/`](snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/);
its [`PROVENANCE.md`](snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/PROVENANCE.md)
records upstream metadata, the file manifest, and per-file SHA-256
hashes verifiable via `sha256sum -c SHA256SUMS`.

This material is **not canon authority**. It is reference input, in the
same sense as `../fedramp-rev5/`. Doctrinal alignment (which KSI themes
the substrate emits, what counts as `DRIFT-EVIDENCE-STALE`) lives in
[`UIAO_133`](../../../specs/fedramp-20x-integration.md) and
[`ADR-047`](../../../adr/adr-047-fedramp-20x-integration.md). The
authority posture, snapshot pin discipline, and conformance-adapter
slot for vendored CR26 artifacts are governed by
[`ADR-061`](../../../adr/adr-061-fedramp-cr26-catalog-vendoring.md).

## Source

| Field | Value |
|---|---|
| Repository | `Palladium-Innovations/fedramp-cr26-oscal` |
| URL | https://github.com/Palladium-Innovations/fedramp-cr26-oscal |
| Pinned commit | `c31eb04c082d6d578a26a00de9a482707ab7a00c` (2026-05-06) |
| License | CC0 1.0 Universal (public domain dedication) |
| Authority | **Unofficial** — explicitly not affiliated with FedRAMP, GSA, NIST, or the OSCAL project |
| Status | Experimental; treats CR26 Public Preview as draft analysis input |

## What the snapshot contains

Vendored from the Palladium generator (XML primary; JSON/YAML derived
via NIST `oscal-cli`). All paths below are relative to the pinned
snapshot directory.

| Path | Artifact |
|---|---|
| `catalog/{xml,json,yaml}/FedRAMP_CR26_catalog.{ext}` | CR26 control catalog (catalog.uuid `092dc25a-18ca-51d9-ab85-744e5435405e`, version `0.1.0`) |
| `profile/20x/{xml,json,yaml}/FedRAMP_20x_profile.{ext}` | FedRAMP 20x profile shell |
| `profile/rev5/{xml,json,yaml}/FedRAMP_rev5_profile.{ext}` | FedRAMP rev5 profile shell |
| `mapping/xml/FedRAMP_CR26_to_NIST_SP-800-53_rev5_mapping-collection.xml` | CR26 ↔ SP 800-53 rev5 mapping collection |
| `LICENSE` | Upstream CC0 1.0 dedication at the pinned SHA |
| `PROVENANCE.md`, `SHA256SUMS` | Vendoring record and integrity manifest |

The catalog at this SHA exposes 10 KSI subgroups
(`KSI-CMT`, `KSI-CNA`, `KSI-CED`, `KSI-IAM`, `KSI-INR`, `KSI-MLA`,
`KSI-PIY`, `KSI-RPL`, `KSI-SVC`, `KSI-SCR`) totaling 46 controls — the
first concrete machine-readable enumeration of the KSI themes
[`UIAO_133`](../../../specs/fedramp-20x-integration.md) references.

The profile shells are exactly that — shells. They do not yet provide
Low / Moderate / High baseline tailoring. uiao's GCC-Moderate boundary
(see `../gcc-moderate-boundary-assessment/`) supplies that tailoring.

## How uiao uses this snapshot

1. **KSI ID anchoring.** `UIAO_133 §2.1` requires every emitted OSCAL
   artifact to carry a `fedramp:ksi-mapping-source` prop. The
   authoritative source remains the UIAO_NNN canon row that names the
   KSI theme; the snapshot is the navigational surface that lets
   emitters resolve the theme to a stable CR26 control ID inside the
   pinned catalog file (per ADR-061 D1).

2. **CR26 ↔ rev5 control translation.** The mapping collection above is
   the canonical translation surface for emitters that need to express
   the same control claim in both vocabularies (CR26 for 20x packages,
   SP 800-53 rev5 for legacy rev5 packages running in parallel during
   the 20x adoption window per ADR-047 D4).

3. **Drift surface.** When the pin advances, the prior snapshot is
   retained for one cycle (ADR-061 D2) so the
   `fedramp-cr26-catalog` conformance adapter (ADR-061 D3) can compare
   catalogs and emit `DRIFT-SCHEMA` / `DRIFT-PROVENANCE` per
   `UIAO_133 §2`.

## Attribution

CC0 1.0 dedication waives copyright; no attribution is legally
required. uiao retains an attribution line in `docs/governance/NOTICE`
as a courtesy and for provenance audit clarity.

## Local handling

Do not modify any file under `snapshot/<upstream-sha>/` by hand;
snapshots are immutable per ADR-061 D2. Local modifications belong
under `overlays/<purpose>/` (this directory does not exist yet —
create it when the first overlay is needed). To advance the pin to a
newer upstream commit, follow the refresh procedure in the snapshot's
[`PROVENANCE.md`](snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/PROVENANCE.md#how-to-refresh).
