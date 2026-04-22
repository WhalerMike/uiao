# UIAO Customer Documents

> Wiki landing page for customer-facing UIAO documentation.
> The authoritative documentation site is the Quarto **UIAO Modernization Atlas** at
> https://whalermike.github.io/uiao/. This wiki page is a navigational pointer only.

## How to use this page

1. Scan the section list below.
2. Click through to the published Quarto URL for the section you need.
3. If a section link lands on an "index only" page with a "Content pending" note,
   that section is scaffolded but not yet authored — see the
   [Customer Documents Roadmap](https://whalermike.github.io/uiao/docs/customer-documents/ROADMAP.html)
   for planned delivery.

## Sections

### Canon-derived (authored)

- **[Adapter Technical Specifications](https://whalermike.github.io/uiao/docs/customer-documents/adapter-technical-specifications/index.html)**
  — 49 per-adapter operational specs, NIST control mappings.
  Derived from `src/uiao/canon/adapter-registry.yaml` +
  `modernization-registry.yaml`.
- **[Adapter Validation Suites](https://whalermike.github.io/uiao/docs/customer-documents/adapter-validation-suites/index.html)**
  — 49 per-adapter validation tests and evidence expectations.
  Same canon source as above.

### Scaffolded (content pending)

- **[Architecture Series](https://whalermike.github.io/uiao/docs/customer-documents/architecture-series/index.html)**
  — Customer-facing explainers for the six-plane architecture, drift
  engine, evidence chain, three-layer rule model, and boundary impact
  model. 5 stubs.
- **[Case Studies](https://whalermike.github.io/uiao/docs/customer-documents/case-studies/index.html)**
  — Applied UIAO scenarios (cloud boundary, federal modernization,
  identity modernization). 3 stubs.
- **[Executive Briefs](https://whalermike.github.io/uiao/docs/customer-documents/executive-briefs/index.html)**
  — Single-page CIO/CISO summaries for governance OS, drift engine,
  evidence fabric, modernization, zero-trust. 5 stubs.
- **[Executive Governance Series](https://whalermike.github.io/uiao/docs/customer-documents/executive-governance-series/index.html)**
  — 9-chapter book-length narrative, from introduction through executive
  summary.
- **[Modernization Technical Specifications](https://whalermike.github.io/uiao/docs/customer-documents/modernization-technical-specifications/index.html)**
  — Cross-adapter domain specs (cloud, identity, SASE, SD-WAN, telemetry,
  zero-trust). 6 domain stubs + 1 template.
- **[Modernization Validation Suites](https://whalermike.github.io/uiao/docs/customer-documents/modernization-validation-suites/index.html)**
  — Cross-adapter domain validation approach. 6 domain stubs + 1
  template.
- **[Whitepapers](https://whalermike.github.io/uiao/docs/customer-documents/whitepapers/index.html)**
  — Long-form position papers (modernization governance, ScubaGear
  integration, UIAO governance OS, zero-trust governance). 4 stubs.

## Provenance

All customer documents carry YAML frontmatter citing their canon source.
See the project-level
[`AGENTS.md`](https://github.com/WhalerMike/uiao/blob/main/AGENTS.md) for
the canon-change contract; canon lives in `src/uiao/canon/`. Any drift
between a customer document and its cited canon is detected by CI
(`metadata-validator`, `drift-scan`, `link-check`).

---

**Do not author customer content on this wiki page.** The SSOT is the
Quarto site backed by `docs/docs/customer-documents/` in the repo.
