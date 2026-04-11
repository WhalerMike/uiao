# UIAO Commercialization & Packaging Layer

## Overview

The UIAO Commercialization & Packaging Layer defines how UIAO stops being "an architecture" and becomes a product line: clean SKUs, clear value fences, and packaging that maps directly to the planes and capabilities already defined.

---

## 1. Product Line Structure

Three primary editions, each a strict subset of the next:

### UIAO Observe

- Evidence ingestion (Plane 1)
- Normalization + KSI evaluation (Plane 2)
- Drift detection (read-only)
- Read-only dashboards and reports

### UIAO Assure

- Everything in Observe
- Evidence bundles (Plane 3)
- OSCAL artifacts (Plane 4)
- POA&M automation
- Auditor API

### UIAO Enforce

- Everything in Assure
- Enforcement runtime + adapters
- EPL policies
- Enforcement safety + rollback
- Closed-loop drift -> enforcement -> evidence -> OSCAL

Each higher edition is a strict superset of the previous - no cross-cutting confusion.

---

## 2. Packaging by Control Surface

Within each edition, add-on packs map to control domains:

| Control Pack | Coverage |
|-------------|----------|
| M365 FedRAMP Pack | Microsoft 365 FedRAMP controls |
| Zero-Trust Identity Pack | Identity and access management controls |
| SaaS Posture Pack | Third-party SaaS compliance posture |
| Data Protection Pack | Data classification and protection controls |

Each pack includes:
- A control pack bundle
- A set of KSI rules
- Optional plugins and adapters

This lets you price by surface area (how much of the environment UIAO governs).

---

## 3. Tenant and Environment Mapping

Per-tenant license includes:
- Edition (Observe / Assure / Enforce)
- Enabled control packs
- Environment scope (dev/stage/prod)

**Regulated tenants must:**
- Be on Assure or Enforce
- Use LTS + FIPS-aligned channels
- Not use uncertified plugins

---

## 4. Commercial Levers

Three clean pricing levers:

| Lever | What It Controls |
|-------|------------------|
| Edition | Depth of capability (Observe -> Assure -> Enforce) |
| Surface | Number and type of control packs enabled |
| Scale | Number of tenants / identities / workloads covered |

Everything else (plugins, HA, geo-replication) is implementation detail, not SKU clutter.

---

## 5. Architecture to SKU Mapping

| Architecture Component | SKU |
|------------------------|-----|
| Planes 1-2 | UIAO Observe |
| Planes 1-4 | UIAO Assure |
| Planes 1-4 + Enforcement Model | UIAO Enforce |
| Control packs | Add-ons |
| Plugins | Mostly included; some premium (e.g., niche SaaS) |
| GCC-M deployment | Environment uplift, not a different product |

---

## Summary: What This Layer Provides

| Component | Purpose |
|-----------|--------|
| Product Line | Three-tier edition model (Observe / Assure / Enforce) |
| Control Surface Packs | Add-on bundles by compliance domain |
| Tenant/Environment Mapping | Per-tenant license with edition, packs, and scope |
| Commercial Levers | Edition, Surface, Scale - three clean pricing dimensions |
| Architecture Mapping | Direct plane-to-SKU alignment with no SKU clutter |

---

## Next Layer

The next layer is the **UIAO Go-To-Market & Narrative Layer**, covering:
- Positioning and messaging pillars
- Proof stories
- How to present UIAO to CISOs, Authorizing Officials, and VCs
