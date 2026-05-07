---
id: ADR-049
title: "Microsoft Modernization Adapter Coverage Expansion — Defender Suite, Azure Migrate, Azure Policy for Arc, Entra Governance, Entra Workload ID, Intune-Modernization"
status: accepted
date: 2026-04-30
accepted: 2026-04-30
deciders:
  - governance-steward
  - identity-engineer
  - security-steward
supersedes: []
related_adrs:
  - ADR-027
  - ADR-035
  - ADR-036
  - ADR-037
  - ADR-038
  - ADR-039
  - ADR-040
canon_refs:
  - UIAO_003_Adapter_Segmentation_Overview
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID
  - UIAO_135_identity-directory-transformation-inventory
  - UIAO_136_priority1-transformation-project-plans
---

# ADR-049: Microsoft Modernization Adapter Coverage Expansion

## Status

ACCEPTED — 2026-04-30

## Context

UIAO's positioning is to **leverage Microsoft-native tooling** for the
identity / device / server / application planes, **provide the SSOT
governance shell** (canon, schemas, registries, drift detection), and
**fill the cross-plane gaps** Microsoft does not provide. The existing
modernization-registry covers Microsoft surfaces well for the OrgTree
program (Entra ID, M365 tenant config, the four MOD_B/C/D/N OrgTree
adapters, the OrgTree drift engine, ADR-035–ADR-040), but a coverage
audit against Microsoft's published AD-retirement guidance and the
Defender / Azure Arc product surface reveals eight Microsoft tools that
the modernization track relies on operationally yet are **not declared
as adapters** in either registry.

### What is already declared

`canon/modernization-registry.yaml` (16 active entries):

* Identity / M365: `entra-id`, `m365`, `entra-dynamic-groups`,
  `entra-admin-units`, `entra-device-orgpath`, `entra-policy-targeting`,
  `orgtree-drift-engine`, `active-directory`
* Security baseline: `scuba`
* Network / IPAM: `palo-alto`, `infoblox`, `bluecat-address-manager`
* Other: `service-now`, `terraform`, `cyberark`, `mainframe`

`canon/adapter-registry.yaml` (10 entries, conformance):

* Active: `scubagear`
* Reserved: `vuln-scan`, `stig-compliance`, `patch-state`, `intune`,
  `pki-ca`, `siem`, `uiao-git-server`, `vdr-bir`, `ccm-bir`

### What is missing

The following Microsoft surfaces are referenced by UIAO_007, UIAO_135,
UIAO_136, and the Phase 2 substrate work, but have no registry entry on
either axis:

| # | Microsoft surface | Operational role for UIAO |
|---|---|---|
| 1 | **Microsoft Defender for Endpoint** (MDE) | Device exposure score, vulnerability inventory, software inventory, attack-path analysis — primary risk feed for the device plane. |
| 2 | **Microsoft Defender for Cloud Apps** (MDCA) | OAuth app governance, Shadow IT discovery, app risk scoring, session controls, Conditional Access App Control — primary signal source for the application plane. |
| 3 | **Microsoft Defender for Servers** (MDfS) | Arc-server EDR, posture and vulnerability management for hybrid servers — primary risk feed for the server plane. |
| 4 | **Azure Migrate** | Server / application dependency mapping (port + protocol + service-to-service call graph) — Microsoft's native discovery for domain-retirement sequencing. |
| 5 | **Azure Policy for Arc** (compliance + remediation) | Hybrid-server policy initiatives, compliance evaluation, remediation tasks. The existing `entra-policy-targeting` adapter (MOD_N) binds *targeting only* — policy bodies and remediation are explicitly out of MOD_N scope. |
| 6 | **Microsoft Entra ID Governance** | Access Reviews, Entitlement Management, Lifecycle Workflows, Privileged Identity Management, Separation-of-Duties policies. Functionally adjacent to `entra-id` but not enumerated in its `scope`. |
| 7 | **Microsoft Entra Workload Identity** | Workload identities, workload identity federation, app credential hygiene reports — the change-making surface that retires legacy AD service accounts (MOD_F-adjacent). |
| 8 | **Microsoft Intune (modernization side)** | Device configuration profile and compliance-policy *body* writes. The conformance-side `intune` adapter is reserved (not active); the modernization side has no allocation at all, even though `src/uiao/adapters/intune_adapter.py` exists as in-flight code. |

### Why the gaps matter

Three concrete consequences of leaving these surfaces undeclared:

1. **Drift is invisible at the registry layer.** The substrate walker
   and `substrate drift` exit-code summary scan declared adapters; an
   undeclared adapter contributes no `DRIFT-PROVENANCE` signal even
   when its evidence is consumed downstream (e.g., MDE risk feeding
   device-cohort sequencing, MDCA discovery feeding SSO migration
   priority).
2. **OrgPath ingestion is implicit.** The "discovery feeders to
   OrgPath" (Entra logs, AD logs, MDE, MDCA, Azure Migrate, Arc
   inventory) are referenced in the inbox modernization docs but have
   no canonical mapping from registry adapter → OrgPath registry input.
3. **The "what Microsoft does not provide" articulation is informal.**
   UIAO's gap-fill mission rests on four claims Microsoft tooling does
   not deliver — cross-plane dependency graph, multi-plane drift
   engine, GPO→Intune sequencing, deterministic domain-retirement
   sequencing — and these are stated in inbox material rather than
   canonical doctrine.

## Decision

1. **Declare eight new adapter entries** across the conformance and
   modernization registries per the table below. Per-axis assignment
   follows UIAO_003 §4.2–§4.7 and resolved ODA-15: read-only signal
   sources go to `canon/adapter-registry.yaml`; change-making surfaces
   go to `canon/modernization-registry.yaml` with
   `mission-class: integration`.

   | Adapter id | Registry | class | mission-class | Initial status |
   |---|---|---|---|---|
   | `defender-for-endpoint` | conformance | conformance | telemetry | reserved |
   | `defender-for-cloud-apps` | conformance | conformance | telemetry | reserved |
   | `defender-for-cloud-apps-actions` | modernization | modernization | integration | reserved |
   | `defender-for-servers` | conformance | conformance | telemetry | reserved |
   | `azure-migrate` | conformance | conformance | telemetry | reserved |
   | `azure-policy-arc` | modernization | modernization | integration | reserved |
   | `entra-id-governance` | modernization | modernization | integration | reserved |
   | `entra-workload-identity` | modernization | modernization | integration | reserved |
   | `intune` (modernization side) | modernization | modernization | integration | reserved |

   The `defender-for-cloud-apps` surface is split because OAuth-app
   governance and session-control writes are change-making while
   discovery and risk scoring are read-only; one id per axis preserves
   the dual-registry invariant.

2. **Promote the "four gaps Microsoft does not provide" to canonical
   doctrine.** Add a new canon document
   `UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md` (allocated in
   `document-registry.yaml`) that records:

   * the cross-plane dependency graph as UIAO's responsibility,
     anchored in the OrgPath canon (ADR-035, ADR-038);
   * the multi-plane drift engine as UIAO's responsibility, anchored
     in ADR-040;
   * GPO → Intune mapping with operational sequencing as a gap UIAO
     owns (no current adapter; future work);
   * domain-retirement sequencing as a gap UIAO owns, served by the
     OrgPath dependency graph and the modernization registries.

3. **Document the OrgPath ingestion contract.** Add a single canonical
   "discovery feeders → OrgPath" mapping section in UIAO_007 (or as a
   sibling MOD specification under
   `src/uiao/canon/modernization/`) that names, per OrgPath input
   stream, which adapter id is the authoritative source. This replaces
   the inbox-document `RB-ID-AD_Extract` / `RB-ID-Graph_Extract`
   runbook framing with an adapter-anchored mapping that the substrate
   walker can verify.

4. **No registry edits in this ADR.** Each new adapter ships in a
   follow-on PR that:

   * appends the entry to the appropriate registry YAML;
   * passes `schema-validation.yml` against
     `schemas/adapter-registry/adapter-registry.schema.json`;
   * lands while `status: reserved` until implementation begins, at
     which point a per-adapter ADR (modeled on ADR-035 / ADR-040)
     promotes it to `active` and binds it to its canon module.

5. **No new registry schemas required.** All nine entries are expected
   to validate against the existing
   `schemas/adapter-registry/adapter-registry.schema.json` (schema
   version `1.0.0`). If any entry surfaces a schema gap during the
   follow-on PR, that gap is a schema ADR in its own right (not folded
   back into this one).

6. **Reject the parallel-structure proposal.** External input
   documents reviewed during the analysis that prompted this ADR
   (Intune / Entra / Arc integration draft material, not in the
   repository) propose a root-level `tracks/ + artifacts/ART-ID-Ex +
   registries/REG-ID-0x.csv + runbooks/RB-ID-x` tree with a separate
   identifier scheme. That structure is **not adopted**. UIAO's
   canonical shape is `src/uiao/canon/` with UIAO_NNN allocations,
   YAML registries validated by JSON Schema, and adapters under
   `src/uiao/adapters/`. The valuable content from those documents —
   the Microsoft-tools gap inventory
   and the four-gaps framing — lands as the entries above and as
   UIAO_009; the proposed CSV registries, the artifact ID scheme, and
   the narrative track document are explicitly out of scope.

## Consequences

### Positive

* Registry-layer visibility for every Microsoft surface UIAO depends
  on. Substrate walker and `substrate drift` see the full dependency
  set; undeclared usage becomes a `DRIFT-PROVENANCE` finding instead
  of a silent assumption.
* The OrgPath ingestion contract becomes inspectable: each input
  stream traces to a named adapter id, not to a runbook.
* Doctrine on what Microsoft does and does not provide moves from
  inbox material to a canonical UIAO_NNN document, citable from ADRs
  and from the SSOT.
* The dual-axis taxonomy is exercised more thoroughly — eight new
  entries split intentionally across conformance and modernization
  illustrate the boundary in practice.

### Negative / costs

* Eight new `reserved` entries enlarge the registry surface that
  schema validation, the substrate walker, and reviewers must scan.
  Mitigated by the `reserved` status (no runtime, no CI workflow,
  no live trust anchor obligations until promoted).
* The split of `defender-for-cloud-apps` across both registries adds
  a precedent that some Microsoft surfaces require sibling entries
  under the same vendor product. The split is justified by
  ODA-15 (modernization = change-making), but it is a new pattern.
* UIAO_009 expands canon by one document. Allocation cost is one
  UIAO_NNN slot; review cost is one Governance Board pass.

### Risks

* If a future Microsoft product reorganization merges or deprecates
  one of these surfaces (e.g., MDCA folding into MDE), the reserved
  entry must be retired per ADR-027. This is a known cost of
  declaring surfaces eagerly; the alternative — declaring only at
  implementation time — leaves the substrate walker blind in the
  meantime.

## Follow-on work

1. PR #1 — append nine new `reserved` entries to the two registries
   (no per-adapter ADR yet; reserved entries do not require an ADR
   per ADR-027).
2. PR #2 — allocate UIAO_009 and write
   `UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md` capturing
   the four-gaps framing.
3. PR #3 — add the "discovery feeders → OrgPath" section to UIAO_007
   (or sibling MOD spec).
4. Per-adapter ADRs (one each, modeled on ADR-035) when any reserved
   entry promotes to `active`. Activation order is an
   implementation-track decision and is not fixed by this ADR.
5. Update `src/uiao/canon/adr/index.md` to list ADR-049 under the
   appropriate theme (Adapter Model or Modernization Track).

## Notes

* This ADR is deliberately registry-shaped, not implementation-shaped.
  No Python code, schema, or CSV is created here. Activation is left
  to per-adapter follow-on ADRs because adapter activation is the
  governance boundary that requires Board review per ADR-027 (adapter
  retirement) and the implicit symmetric rule for adapter activation
  in the three-stage lifecycle (canon → docs scaffold → impl code).
* The external draft documents that prompted this ADR (Intune / Entra
  / Arc integration material reviewed during the analysis pass) are
  not committed to the repository, consistent with the inbox invariant
  ("Nothing here is canon"). Their valuable content is extracted by
  this ADR and by UIAO_009; the source documents themselves are not
  promoted.
