---
document_id: UIAO_127
title: "UIAO Project Plans Program — Internal Roadmap & Agency Templates"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-17"
updated_at: "2026-04-17"
boundary: "GCC-Moderate"
---

# UIAO Project Plans Program

The UIAO substrate ships two kinds of project plan: the **internal
roadmap** that drives substrate development, and **agency templates**
that an external operator instantiates to deploy UIAO against their
environment. Both are canonical — both are governed from this
document.

---

## 1. Audience

- **Internal** — substrate maintainers, canon stewards, release
  managers. The internal roadmap is the authoritative list of
  what the substrate will do next and how priorities were set.
- **External** — agencies and integrators adopting UIAO. The
  agency templates give a deterministic, canon-anchored path from
  "empty clone" to "first OSCAL artifact rendered."

---

## 2. Internal Roadmap

The internal roadmap is versioned and ADR-anchored. Any entry on
the roadmap traces to an ADR that authorized the work; any entry
retired traces to an ADR that retired it.

### 2.1 Cadence

- Quarterly planning increment. Each increment opens with an ADR
  recording the scope and closes with an ADR recording the
  outcome.
- Weekly triage. New issues are labeled and categorized via the
  release-drafter taxonomy (`feature`, `fix`, `canon`, `docs`,
  `ci`, `dependencies`, `chore`).

### 2.2 Structure

Each roadmap item carries:

1. **Intent** — what changes about the substrate.
2. **Canon touch** — which canon documents / schemas / registries
   are affected.
3. **Drift impact** — whether the change introduces a new drift
   class, severity, or detector.
4. **Definition of done** — the blocking CI workflows that must
   be green, plus a link to the ADR.

### 2.3 Source of truth

Roadmap items live as GitHub issues labeled `roadmap`, tracked
through the release-drafter into versioned draft releases. The
ADR that authorized the increment is the canonical artifact; the
issue list is the operational projection of it.

---

## 3. Agency Templates

An agency adopting UIAO does not invent a deployment plan — it
instantiates one of the canonical templates and parameterizes it
for its environment. Templates live under
`core/canon/specs/program-project-plans/` (filled variants) or
directly in this document (the template skeletons).

### 3.1 Template catalog

| Template | Scope | Canon anchors |
|---|---|---|
| Greenfield adopt | Agency is standing up UIAO for the first time | UIAO_101, UIAO_125, UIAO_200, UIAO_201 |
| Directory-migration modernization | Agency is using UIAO adapters to migrate a directory service | ADR-028, modernization-registry entries |
| SCuBA conformance rollout | Agency is running SCuBA on its M365 tenant through UIAO | UIAO_002, UIAO_117 |
| OSCAL ATO preparation | Agency is generating SAR / POA&M / SSP for an ATO package | UIAO_107, UIAO_113 |

### 3.2 Template contents

Each template declares:

1. Preconditions — what must exist in the agency environment
   before the plan can run (tenant, accounts, network boundary).
2. Canon inputs — which registries / schemas / canon documents
   are consumed, by version.
3. Overlays — the agency-specific configuration layer that
   parameterizes the template without modifying canon.
4. Drift scan points — the gates the operator runs at each
   milestone (walker, drift, schema validation).
5. Exit criteria — the evidence bundle produced at the end.

### 3.3 Parameterization

Workspace root is always `$UIAO_WORKSPACE_ROOT` — never a
hardcoded path. Environmental values (tenant IDs, connector
credentials) are supplied via the overlay configuration and
resolved at runtime against the adapter manifest. No plan may
require editing a canon file.

---

## 4. Plan-Entry Rules

1. A new template is a canonical artifact with its own frontmatter
   and an entry in `document-registry.yaml`. It may share the
   UIAO_127 ID bucket with this parent spec as numbered appendices
   (UIAO_127-A, UIAO_127-B …) or receive its own UIAO_NNN if its
   scope warrants.
2. An agency-filled template is **not** canon. It is operational
   evidence. It is stored outside `core/` (typically under
   `impl/` fixtures for testing or inside the agency's own
   repository).
3. Changes to a template follow the canon change protocol: ADR
   for doctrinal changes, schema update for structural changes,
   drift scan always.

---

## 5. Execution

The internal roadmap executes continuously against `main`. Agency
templates execute on-demand in the agency environment. Both use
the same CLI and the same schemas — a template is just a scripted
path through the substrate walker, drift engine, adapter
conformance, and OSCAL generator.

---

## 6. Maintenance

A roadmap item that ships becomes an ADR outcome and is removed
from the active list. A template that is retired moves to
`Deprecated` with a supersession pointer. The catalog in §3.1 is
the single canonical index; no template lives outside it.

---

## 7. Cross-References

- UIAO_101 — Platform Overview
- UIAO_200 — Substrate Manifest
- UIAO_201 — Workspace Contract
- UIAO_125 — Training Program
- UIAO_126 — Test Plans Program
- UIAO_128 — Education Program
- ADR-028 — Monorepo Consolidation & GOS Integration
- ADR-029 — Substrate v1 Ready for Release
