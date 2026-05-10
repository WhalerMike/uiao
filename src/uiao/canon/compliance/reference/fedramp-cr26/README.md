# FedRAMP CR26 OSCAL Reference Materials (Provenance Pointer)

This folder is a **provenance pointer**, not a vendor mirror. It pins the
upstream third-party generator that produces machine-readable OSCAL
artifacts for FedRAMP Consolidated Rules 2026 (CR26). Pinning gives uiao
emitters a stable KSI / control-ID surface to anchor against while the
underlying FedRAMP CR26 source data is still in Public Preview.

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

## What the upstream generator produces

The Palladium generator consumes CR26 Public Preview JSON and emits
OSCAL artifacts (XML primary; JSON/YAML derived via NIST `oscal-cli`):

| Upstream path | Artifact |
|---|---|
| `out/FedRAMP/catalog/{xml,json,yaml}/FedRAMP_CR26_catalog.{ext}` | CR26 control catalog |
| `out/FedRAMP/profile/20x/{xml,json,yaml}/` | FedRAMP 20x profile shell |
| `out/FedRAMP/profile/rev5/{xml,json,yaml}/` | FedRAMP rev5 profile shell |
| `out/FedRAMP/mapping/xml/FedRAMP_CR26_to_NIST_SP-800-53_rev5_mapping-collection.xml` | CR26 ↔ SP 800-53 rev5 mapping collection |

The profile shells are exactly that — shells. They do not yet provide
Low / Moderate / High baseline tailoring. uiao's GCC-Moderate boundary
(see `../gcc-moderate-boundary-assessment/`) supplies that tailoring.

## How uiao uses this pointer

1. **KSI ID anchoring.** `UIAO_133 §2.1` requires every emitted OSCAL
   artifact to carry a `fedramp:ksi-mapping-source` prop. Today that
   resolves to a UIAO_NNN canon row; once a CR26 snapshot is vendored
   into this folder under the pinned SHA, the prop can additionally
   resolve to a stable CR26 control ID inside the catalog file.

2. **CR26 ↔ rev5 control translation.** The mapping collection above is
   the canonical translation surface for emitters that need to express
   the same control claim in both vocabularies (CR26 for 20x packages,
   SP 800-53 rev5 for legacy rev5 packages running in parallel during
   the 20x adoption window per ADR-047 D4).

3. **Drift surface.** When a future commit advances this pointer, the
   substrate-drift workflow can compare the new catalog's control set
   against the prior snapshot and emit `DRIFT-SCHEMA` (catalog shape
   changed) or `DRIFT-PROVENANCE` (a previously-cited control ID no
   longer resolves) per `UIAO_133 §2`.

## Why this is a pointer, not a mirror

The CR26 source data is Public Preview and the Palladium generator is
explicitly experimental. ADR-061 records the policy that lets a
snapshot land here without conferring canon authority on the upstream:
snapshots live under `snapshot/<upstream-sha>/` and are immutable;
local modifications are expressed as overlays under `overlays/`; the
adapter described in ADR-061 D3 is the only consumer that bridges
vendored CR26 IDs to substrate KSI rules.

## Attribution

CC0 1.0 dedication waives copyright; no attribution is legally
required. uiao retains an attribution line in `docs/governance/NOTICE`
as a courtesy and for provenance audit clarity.

## Local handling

Do not modify any file under this folder by hand. It exists to record
upstream pinning. Vendored snapshots land under
`snapshot/<upstream-sha>/`; local modifications live under
`overlays/<purpose>/`. See ADR-061 D2 for snapshot pin discipline.
