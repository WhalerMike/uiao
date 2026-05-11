---
title: "OrgTree Module — Python Implementation Surface"
status: Current
owner: Michael Stratton
updated_at: 2026-05-10
boundary: GCC-Moderate
---

# OrgTree Module — Python Implementation Surface

This module hosts the Python implementations that consume the OrgTree
canon (`UIAO_150`–`UIAO_176`, registered in
[`src/uiao/canon/document-registry.yaml`](../canon/document-registry.yaml)).
The canon documents themselves live under `src/uiao/canon/` like every
other UIAO canon artifact; this directory is the **executable
companion** — codebook loaders, dynamic-group rule resolvers,
administrative-unit binders, device-plane projectors, policy-target
renderers, and the drift-engine configuration glue.

Per [ADR-060](../canon/adr/adr-060-mod-namespace-flatten-into-uiao-canon.md),
the prior `MOD_xxx` namespace and its sibling `document-registry.yaml`
were retired. Documents previously addressed as `MOD_001` / `MOD_A` …
`MOD_Z` are now addressable as `UIAO_150` … `UIAO_176`. Each renamed
file's frontmatter carries a `provenance_flatten:` block recording its
prior slug (e.g., `prior_id: "MOD_A"`); use that as the source of truth
when chasing pre-2026-05-10 references.

## Module contents

| File | Bound canon | Purpose |
|---|---|---|
| `orgtree/codebook.py` | `UIAO_151` (codebook), `UIAO_158` (JSON Schema) | Canonical OrgPath codebook loader and validator. |
| `orgtree/dynamic_groups.py` | `UIAO_152` | Dynamic-group rule resolver and provisioning surface. |
| `orgtree/admin_units.py` | `UIAO_154` | Administrative Unit binder + scoped-role projector. |
| `orgtree/device_planes.py` | `UIAO_153` (attribute mapping), `UIAO_171` (boundary) | Device-plane OrgPath projector (Graph + ARM dual transport). |
| `orgtree/policy_targets.py` | `UIAO_164` | OrgTree policy-target renderer (Intune + Azure Policy). |
| `orgtree/drift_engine_config.py` | `UIAO_163` | Drift-engine configuration loader for the OrgTree corpus. |

## Boundary rules

- **GCC-Moderate** — M365 SaaS services only; does not include Azure
  services beyond Arc-projected hybrid resources.
- **Tenant-agnostic** — no tenant-specific identifiers in any artifact.
- **HR-driven** — identity lifecycle is sourced from the HR system of
  record per `UIAO_135` / `UIAO_136` Spec 2; the OrgTree corpus
  consumes the resulting attributes, it does not author them.

## Getting started

1. Read `UIAO_150_OrgTree_Modernization_Executive_Summary.md` for the
   architectural overview.
2. Review `UIAO_151_OrgPath_Codebook.md` to understand the OrgPath
   encoding.
3. Follow `UIAO_156_Migration_Runbook_OU_to_Entra.md` for the 8-phase
   migration sequence.
4. Use `UIAO_159_PowerShell_Validation_Module.md` for automated
   validation.
