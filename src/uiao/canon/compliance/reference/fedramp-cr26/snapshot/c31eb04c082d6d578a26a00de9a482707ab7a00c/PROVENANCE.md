# Provenance — FedRAMP CR26 Snapshot c31eb04

Vendored snapshot of the unofficial Palladium CR26 OSCAL generator
output, governed by [`ADR-061`](../../../../adr/adr-061-fedramp-cr26-catalog-vendoring.md).

This snapshot is **immutable**. Local edits are not permitted. Updates
land under a new sibling `snapshot/<upstream-sha>/` directory; see
ADR-061 D2.

## Upstream

| Field | Value |
|---|---|
| Repository | `Palladium-Innovations/fedramp-cr26-oscal` |
| URL | https://github.com/Palladium-Innovations/fedramp-cr26-oscal |
| Pinned commit | `c31eb04c082d6d578a26a00de9a482707ab7a00c` |
| Commit date | 2026-05-06 |
| Commit message | "Initial FedRAMP CR26 OSCAL artifacts" |
| Parent commit | none (initial commit) |
| License at SHA | CC0 1.0 Universal (verified — see `./LICENSE`) |
| Vendored on | 2026-05-10 |
| Vendoring PR | WhalerMike/uiao#360 |

The "Parent commit: none" status means the upstream repository's first
and only commit at the time of vendoring is the SHA above. ADR-061 D2's
"not force-pushed away from its parent" requirement is trivially
satisfied — there is no parent to be force-pushed away from.

## Files vendored

11 files totaling ~1.16 MB. Per-file SHA-256 hashes are recorded in
`SHA256SUMS` and verifiable with `sha256sum -c SHA256SUMS` from this
directory.

| Path | Bytes | Source |
|---|---:|---|
| `catalog/xml/FedRAMP_CR26_catalog.xml` | 334853 | upstream `out/FedRAMP/catalog/xml/...` |
| `catalog/json/FedRAMP_CR26_catalog.json` | 409569 | upstream `out/FedRAMP/catalog/json/...` |
| `catalog/yaml/FedRAMP_CR26_catalog.yaml` | 331206 | upstream `out/FedRAMP/catalog/yaml/...` |
| `profile/20x/xml/FedRAMP_20x_profile.xml` | 12031 | upstream `out/FedRAMP/profile/20x/xml/...` |
| `profile/20x/json/FedRAMP_20x_profile.json` | 6118 | upstream `out/FedRAMP/profile/20x/json/...` |
| `profile/20x/yaml/FedRAMP_20x_profile.yaml` | 6903 | upstream `out/FedRAMP/profile/20x/yaml/...` |
| `profile/rev5/xml/FedRAMP_rev5_profile.xml` | 10330 | upstream `out/FedRAMP/profile/rev5/xml/...` |
| `profile/rev5/json/FedRAMP_rev5_profile.json` | 5429 | upstream `out/FedRAMP/profile/rev5/json/...` |
| `profile/rev5/yaml/FedRAMP_rev5_profile.yaml` | 5984 | upstream `out/FedRAMP/profile/rev5/yaml/...` |
| `mapping/xml/FedRAMP_CR26_to_NIST_SP-800-53_rev5_mapping-collection.xml` | 31955 | upstream `out/FedRAMP/mapping/xml/...` |
| `LICENSE` | 2249 | upstream root `LICENSE` (CC0 1.0) |

## Catalog shape (at this SHA)

| Element | Value |
|---|---|
| `catalog.uuid` | `092dc25a-18ca-51d9-ab85-744e5435405e` |
| `catalog.metadata.title` | "FedRAMP Consolidated Rules for 2026 - Unofficial OSCAL Catalog" |
| `catalog.metadata.version` | `0.1.0` |
| Top-level groups | `FRR` (15 subgroups) · `KSI` (10 subgroups) |

### KSI subgroups and control counts

| KSI theme | Title | Controls |
|---|---|---:|
| `KSI-CMT` | Change Management | 4 |
| `KSI-CNA` | Cloud Native Architecture | 8 |
| `KSI-CED` | Cybersecurity Education | 1 |
| `KSI-IAM` | Identity and Access Management | 6 |
| `KSI-INR` | Incident Response | 3 |
| `KSI-MLA` | Monitoring, Logging, and Auditing | 5 |
| `KSI-PIY` | Policy and Inventory | 5 |
| `KSI-RPL` | Recovery Planning | 4 |
| `KSI-SVC` | Service Configuration | 8 |
| `KSI-SCR` | Supply Chain Risk | 2 |
| **Total** | | **46** |

The KSI theme IDs above are the surface that
[`UIAO_133 §2.1`](../../../../specs/fedramp-20x-integration.md)
`fedramp:ksi-themes` props enumerate. The catalog at this SHA is the
first concrete machine-readable enumeration of those themes uiao has
access to.

## Pre-commit verification

The vendored XML and JSON were validated as well-formed at fetch time
(`xmllint --noout` for XML; `jq` parse for JSON). YAML was not
re-parsed; treat it as a derived format and prefer JSON or XML as the
machine-readable source of truth.

`oscal-cli` round-trip validation per ADR-061 D4 is **not** performed
in this PR. If a CI workflow is added later, it lives at
`.github/workflows/fedramp-cr26-roundtrip.yml`.

## How to refresh

To advance the pin to a newer upstream commit:

1. Confirm the target commit is published on the upstream's `main` and
   not force-pushed.
2. Confirm the `LICENSE` at the new SHA is still CC0 1.0 (or compatible).
3. Create a new sibling `snapshot/<new-sha>/` directory and download
   the same file set.
4. Compute `SHA256SUMS` and write a new `PROVENANCE.md` for the new
   snapshot.
5. Update the top-level `../../README.md` `Pinned commit` row.
6. Retain the prior snapshot for one cycle so the conformance adapter
   (ADR-061 D3) can compute drift, then remove it in a follow-up PR.
