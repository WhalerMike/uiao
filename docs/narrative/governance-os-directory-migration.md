---
title: "Directory Migration as Governed Modernization"
description: "How the consolidated UIAO substrate governs AD → Entra ID + M365 directory migrations through the canonical modernization adapter framework."
uiao.id: narrative-directory-migration
uiao.status: Current
uiao.owner: WhalerMike
uiao.tags: [adapter, identity, integration, modernization, narrative]
provenance:
  source_commit: main
  derived_from:
    - core/canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md
    - core/canon/modernization-registry.yaml
    - core/canon/adr/adr-028-monorepo-consolidation-gos-integration.md
  derived_at: "2026-04-17"
  derived_by: "narrative rewrite (closes ADR-028 doctrinal loop)"
---

# Directory Migration as Governed Modernization

Active Directory was never just an identity store. For decades it was the implicit governance model for every network service in the enterprise: DNS, DHCP, PKI, RADIUS, LDAP authentication, GPO device policy, file services, Kerberos SPNs, and cross-forest trust. When an organization migrates to Entra ID and M365, those systems don't move; they have to be **re-governed** — with the same guarantees about identity, drift detection, and evidence that every other modernization adapter in UIAO provides.

This document explains how the consolidated UIAO substrate treats enterprise directory migration as a first-class modernization domain, governed by the same canon and schemas as every other change-making adapter.

## What makes migration a modernization-class problem

Per the Adapter Segmentation Overview (UIAO_003 §4.2–§4.7), every externally-facing connector in UIAO is classified along two orthogonal axes:

- **Operational class** — `modernization` (change-making) or `conformance` (read-only).
- **Mission class** — `identity | telemetry | policy | enforcement | integration`.

Directory migration is **modernization + integration** by construction: it performs change-making actions against a target environment (Entra ID tenant, M365 services, IPAM fabric) to reconcile live state with the canonical source of truth. The canonical constraints that apply to every modernization adapter apply equally here:

- `gcc-boundary: gcc-moderate` — Microsoft 365 SaaS boundary, Amazon Connect exception noted per-adapter.
- `ssot-mutation: never` — adapters consume and emit against SSOT but never mutate it.
- `certificate-anchored: true` — every transaction is tied to an identity certificate, provenance chain immutable.
- `object-identity-only: true` — adapters act on identities, not on opaque infrastructure references.

These are enforced by the JSON Schema at `core/schemas/adapter-registry/adapter-registry.schema.json` and validated by the `schema-validation` CI gate on every PR touching `core/canon/modernization-registry.yaml`.

## The objects governed

Directory migration governs every object AD was holding together:

| Object class | Examples | Target mapping |
|---|---|---|
| Identities | Users, computers, service accounts | Entra ID user / device / workload-identity objects |
| Authorization | Security groups, role-based ACLs | Entra ID groups + RBAC |
| Policy | GPOs, device compliance | Intune configuration profiles, Conditional Access policies |
| Network services | DNS, DHCP, IPAM | Infoblox NIOS / BlueCat Address Manager (registered adapters) |
| Cryptography | PKI/Certificate Services, Kerberos SPNs | Entra Certificate Authority, Workload Identity Federation |
| Authentication | LDAP, RADIUS, 802.1X | Microsoft Entra domain services, NPS extensions |
| Trust | Cross-domain / cross-forest trusts | Entra external identities, B2B federation |

The two registered reference implementations today are the IPAM adapters — the network-services tier:

- **`infoblox`** (`core/canon/modernization-registry.yaml`) — Infoblox NIOS ≥ 8.0. FedRAMP-Moderate authorized, CDM-integrated, federal-preferred.
- **`bluecat-address-manager`** — BlueCat Address Manager. Not FedRAMP-authorized; commercial-variant sibling of the infoblox adapter.

Both declare `mission-class: integration` per resolved ODA-15 (UIAO_003 §4.7) and conform to the same schema as every other modernization adapter.

## Governed phases

Treating a migration as a governed pipeline rather than a rip-and-replace project is the architectural win. Five phases, each with canon-anchored evidence:

1. **Discover** — enumerate the live AD governance graph. Every GPO, every SPN, every DHCP scope, every cross-forest trust becomes a canonical `ClaimObject`. Output: a claim set with provenance.
2. **Normalize** — reconcile decades of organic growth. Duplicates collapsed; inherited state made explicit; object-identity-only constraint applied. Output: a normalized governance model.
3. **Map** — translate X.500/LDAP semantics into Entra ID equivalents using crosswalks declared in canon. The crosswalk itself is a canonical artifact; mappings drift-scanned on every change.
4. **Migrate** — execute change-making actions through the registered modernization adapter(s). Every mutation certificate-anchored, every evidence bundle retained per `retention-years`.
5. **Attest** — emit OSCAL-shaped evidence (SSP updates, POA&M entries) through the same generators used for any other modernization run.

Drift is detected at two layers:

- **At rest** — the substrate walker (`uiao substrate walk`) validates that every declared module path and every canon document exists (`DRIFT-SCHEMA`, `DRIFT-PROVENANCE`). Runs on every PR via `.github/workflows/substrate-drift.yml`.
- **Runtime** — per-resource drift detection (`impl/src/uiao/impl/governance/drift.py`) classifies field-level deltas between expected canonical state and live target state. Integrated into the governance pipeline.

The five-class drift taxonomy (`DRIFT-SCHEMA`, `DRIFT-SEMANTIC`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY`) defined in `docs/docs/16_DriftDetectionStandard.qmd` applies uniformly to directory-migration runs as to any other adapter.

## Why this is not a commercial product

An earlier version of this substrate treated the directory-migration work as a firewalled commercial product (`uiao-gos`, see ADR-025 §D7). ADR-028 retired that framing. The argument is simple:

- Migration adapters have the **same canonical constraints** as every other modernization adapter. Enforcing a different set would be drift by design.
- The **same schemas, registries, and CI gates** apply. Building parallel infrastructure for a single adapter family invites divergence.
- **Consumers select by manifest field, not by repository boundary.** A GCC-Moderate agency picks the `infoblox` adapter (FedRAMP-authorized); a commercial deployment picks `bluecat-address-manager`. The operational axis already encodes that choice.

The commercial-firewall framing is preserved in the canon archive (ADR-025 §D7 with its SUPERSEDED callout; ADR-028) for historical record. Runtime behavior is now uniform.

## Where to find the artifacts

| Concern | Location |
|---|---|
| Substrate manifest | `core/canon/substrate-manifest.yaml` (UIAO_200) |
| Workspace contract | `core/canon/workspace-contract.yaml` (UIAO_201) |
| Modernization adapter registry | `core/canon/modernization-registry.yaml` |
| Adapter schema | `core/schemas/adapter-registry/adapter-registry.schema.json` |
| IPAM adapter reference docs | `impl/src/uiao/impl/directory_migration/adapters/ipam/` |
| Drift engine (runtime) | `impl/src/uiao/impl/governance/drift.py` |
| Substrate walker (at rest) | `impl/src/uiao/impl/substrate/walker.py` |
| Drift detection standard | `docs/docs/16_DriftDetectionStandard.qmd` |
| Adapter Segmentation Overview | `core/canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md` |
| Integration decision record | `core/canon/adr/adr-028-monorepo-consolidation-gos-integration.md` |

## What ships next

The two current IPAM adapters are the seed of a broader directory-migration adapter family. Adapters for the remaining object classes (users, GPOs, PKI, RADIUS, Kerberos) will be promoted from `status: reserved, phase: phase-planning` to `active/phase-1` as implementations land in `impl/src/uiao/impl/adapters/` and pass the test-coverage rule (`impl/.claude/rules/test-coverage.md`). Each registration is a canon PR; the canon/CI machinery surrounding modernization adapters needs no change.
