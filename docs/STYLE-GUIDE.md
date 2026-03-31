---
title: "Style-Guide"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Style Guide v1.0

> A unified writing, formatting, and architectural governance standard for all UIAO documents.

| Field | Value |
|---|---|
| **Version** | 1.0 |
| **Date** | 2026-03-26 |
| **Status** | Active |
| **Owner** | UIAO Architecture Team |
| **Scope** | All canon volumes, architecture specs, crosswalks, project plans, appendices, and leadership briefings |

---

## 1. Purpose

This guide establishes the canonical rules for writing, structuring, and formatting all UIAO documents. It ensures:

- Consistent terminology
- Consistent control-plane definitions
- Consistent narrative voice
- Consistent table and section structure
- Consistent crosswalk references
- Consistent compliance language
- Consistent diagrams and appendix placement

This is the governing style for all UIAO artifacts. No document may deviate without an explicit exemption recorded in `data/style-guide.yml`.

---

## 2. Narrative Voice and Tone

### 2.1 Voice

The UIAO voice is:

- **Authoritative** — federal architecture, not marketing
- **Clear and declarative** — no hedging
- **Technically precise** — correct terminology always
- **Narrative, not academic** — readable by executives and engineers
- **Zero hype, zero ambiguity**

Dry humor is permitted but must be subtle and never at the expense of clarity.

### 2.2 Tone

Tone must reflect:

- Confidence without arrogance
- Clarity without oversimplification
- Executive readability
- Engineering accuracy
- Governance discipline

### 2.3 Prohibited Tone

Never use:

- Marketing language
- Overly casual phrasing
- Speculative claims
- Vendor hype or product endorsements
- "Thought leadership" fluff

### 2.4 Style Examples

**Correct:**

> Identity becomes the authoritative source for addressing, certificates, and policy. Telemetry validates these decisions continuously.

**Incorrect:**

> Identity is super important and helps with a lot of things like routing and security.

---

## 3. Canonical Section Order

Every UIAO document must follow this structure unless explicitly exempt:

| Order | Section | Required |
|---|---|---|
| 1 | Title | Yes |
| 2 | Version + Date | Yes |
| 3 | Purpose | Yes |
| 4 | Scope | Yes |
| 5 | Control Plane Alignment | Yes |
| 6 | Core Concepts | Yes |
| 7 | Architecture Model | Conditional |
| 8 | Runtime Model | Conditional |
| 9 | Compliance Mapping | Yes |
| 10 | Dependencies and Sequencing | Yes |
| 11 | Governance and Drift Controls | Yes |
| 12 | Appendices | As needed |

This eliminates structural drift across the corpus.

---

## 4. Canonical Definitions (Frozen)

These definitions must appear identically across all documents. They are machine-enforced via `data/style-guide.yml`.

### 4.1 The Six Control Planes

1. Identity Control Plane
2. Network Control Plane
3. Addressing Control Plane
4. Telemetry and Location Control Plane
5. Security and Compliance Plane
6. Management Plane (ServiceNow + Intune)

### 4.2 The Seven Core Concepts

1. Conversation as the atomic unit
2. Identity as the root namespace
3. Deterministic addressing
4. Certificate-anchored overlay
5. Telemetry as control
6. Embedded governance and automation
7. Public service first

### 4.3 Runtime Model

A conversation is the atomic unit of operation:

1. Identity initiates.
2. Addressing binds.
3. Certificates authenticate.
4. Telemetry informs.
5. Policy evaluates continuously.

### 4.4 Determinism

Given the same identity, boundary, telemetry, and assurance inputs, the system must produce the same decision across clouds, agencies, and implementations.

---

## 5. Formatting Rules

### 5.1 Headings

- `#` (H1) for document title only
- `##` (H2) for major sections
- `###` (H3) for subsections
- `####` (H4) only for deep technical detail

### 5.2 Tables

All tables must follow this pattern:

```markdown
| Column A | Column B | Column C |
|---|---|---|
| data | data | data |
```

Rules:

- No vertical lines beyond standard Markdown
- No merged cells
- No decorative formatting
- Header row is always bold by default

### 5.3 Lists

- Use numbered lists for sequences and ordered steps
- Use bullet lists for unordered concepts
- Never mix bullets and numbers in the same list

### 5.4 Code, YAML, and JSON

- Always use fenced code blocks with language identifier
- Never inline large YAML or JSON
- Example:

```yaml
control_id: AC-4
title: Information Flow Enforcement
```

### 5.5 Diagrams

All diagrams must be referenced by filename:

- PNG files: `docs/images/` or `assets/`
- DRAWIO source files: `assets/` or dedicated diagrams directory
- Never embed diagram images directly in prose without a file reference

---

## 6. Crosswalk Rules

### 6.1 Single Source of Truth

All FedRAMP, NIST, and KSI mappings must reference:

- `data/crosswalk-index.yml`
- `data/nist_crosswalk.yml`
- `data/ksi-mappings.yml`

No document may redefine control mappings independently. All mappings flow from the data layer.

### 6.2 Crosswalk Language

Use this exact phrasing pattern:

> Mapped to NIST 800-53 Rev 5 control [CONTROL-ID] via [mechanism] and [enforcement method].

Example:

> Mapped to NIST 800-53 Rev 5 control AC-4 via deterministic addressing and identity-bound policy enforcement.

Never improvise compliance language. All crosswalk statements must be traceable to `data/crosswalk-index.yml`.

---

## 7. Compliance Language Rules

### 7.1 FedRAMP

Always specify:

- **Baseline**: Moderate or High
- **FedRAMP 20x Class**: Class C (or as applicable)
- **Evidence source**: logs, APIs, dashboards, or artifact exports

Example:

> This control satisfies FedRAMP Moderate baseline requirements under the 20x Class C continuous monitoring framework. Evidence is sourced from Microsoft Sentinel workspace retention policies.

### 7.2 NIST Controls

Always cite:

- Control ID
- Control name
- Revision number

Example:

> Aligned to CM-8: System Component Inventory (NIST SP 800-53 Rev 5).

### 7.3 OSCAL References

When referencing OSCAL artifacts, always specify:

- The export format (JSON or XML)
- The source file in `exports/`
- The generating pipeline (if automated)

---

## 8. Governance and Drift Rules

Every document must include or reference:

| Element | Description |
|---|---|
| Source of Authority | Which data file or canon volume governs this content |
| Drift Detection | How deviations from the canonical definition are detected |
| Remediation Workflow | How drift is corrected (manual review, CI check, automation) |
| Telemetry Validation | Which monitoring source confirms runtime compliance |

This ensures the canon is self-governing. Documents without governance metadata are considered draft.

---

## 9. Document Interdependency Rules

Every document must declare:

| Declaration | Example |
|---|---|
| Control plane(s) it belongs to | Identity Control Plane, Telemetry and Location Control Plane |
| Crosswalk entries it references | `data/crosswalk-index.yml` entries AC-4, SC-7 |
| Diagrams it depends on | `docs/images/identity-flow.png` |
| Appendices it maps to | `data/appendices.yml` section 3 |

This prevents fragmentation and ensures every document is traceable within the architecture.

---

## 10. File Naming Conventions

| Type | Pattern | Example |
|---|---|---|
| Control narratives | `{CONTROL-ID}.yml` | `IA-3.yml` |
| Architecture docs | `snake_case_v{VERSION}.md` | `identity_plane_deep_dive_v1.0.md` |
| Data files | `snake_case.yml` | `parameters.yml` |
| Diagrams | `kebab-case.png` | `identity-control-flow.png` |
| Leadership briefings | `leadership_briefing_v{VERSION}.md` | `leadership_briefing_v1.0.md` |

---

## 11. Version Control and Change Management

- All changes to canonical definitions require a commit message prefixed with `feat:`, `fix:`, or `docs:`
- Breaking changes to frozen definitions (Section 4) require an Architecture Decision Record in `docs/adr/`
- Style guide updates increment the minor version (e.g., 1.0 to 1.1)
- Structural changes to the canonical section order (Section 3) increment the major version

---

## 12. Enforcement

This style guide is enforced through:

1. **CI validation** via GitHub Actions (structural checks)
2. **Manual review** during pull request approval
3. **Machine-readable rules** in `data/style-guide.yml`
4. **Periodic audit** against the full document corpus

Documents that do not comply are flagged as non-canonical and must be remediated before inclusion in any FedRAMP or OSCAL export.

---

## Related Files

| File | Purpose |
|---|---|
| `data/style-guide.yml` | Machine-readable style governance rules |
| `data/canon-spec.yml` | Canon specification and structure |
| `data/crosswalk-index.yml` | Authoritative control crosswalk mappings |
| `docs/glossary.md` | Term definitions |
| `CONTRIBUTING.md` | Contribution guidelines |
