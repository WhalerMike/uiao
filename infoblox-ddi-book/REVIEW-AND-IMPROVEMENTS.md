# Constructive review & improvement roadmap

A candid, self-critical assessment of this volume — what it does well, where it is
weakest, and the highest-leverage work to make it production-trustworthy. Written to be
read alongside the volume, not to flatter it. Priorities are labeled **P0** (credibility /
correctness — do first), **P1** (completeness — do next), **P2** (polish / UX).

> **One-line verdict.** The volume is **structurally excellent and honestly scoped**, but
> it is *documentation with attached skeletons*, not *tested product*. Nothing here has
> been stood up and proven end-to-end, and the repo's own CI does not check the book's
> code. Close that gap first; everything else is enrichment.

---

## 1. What is genuinely strong (keep doing this)

- **Consistent skeleton.** The fixed 11-section chapter contract
  ([`_conventions.md`](./_conventions.md)) makes five platforms directly comparable — a
  reader can diff "DNS forwarding" across clouds by reading the same section number. That
  discipline is rare and valuable.
- **Scope honesty.** "Infoblox provides the DDI layer *inside* the landing zone, not the
  landing zone" is repeated everywhere and never overclaimed. The Stage-1 / Stage-2 /
  Stage-3 layering in each automation guide is a clean mental model.
- **Boundary discipline as a first-class control.** The `acknowledge_saas_boundary` guard,
  the "MID Server in-boundary" rule, and the GCC-Moderate-on-commercial (`.com`) framing
  are threaded consistently and mapped to FedRAMP control families. This is the most
  mature part of the volume.
- **One authoritative IPAM** as the organizing principle ([Chapter 6](./06-cross-platform-operations.md))
  is the correct spine for a multi-cloud DDI story.
- **ServiceNow now woven through the processes**, not bolted on — [Chapter 0](./00-introduction.md)
  §0.5, every chapter's §8, [Chapter 6](./06-cross-platform-operations.md) §6.9, each
  guide/runbook, and the importable [`servicenow-app/`](./servicenow-app/README.md).

---

## 2. P0 — Credibility & correctness gaps (do first)

### 2.1 The book's own code is not tested by CI — *partially addressed*
The repository has strong CI (schema validation, link-check), but **none of it validated
the volume's IaC or scripts**. A reader who copies a module had no assurance it even
initializes.

> **Applied in this PR:** a book-scoped workflow —
> [`.github/workflows/infoblox-ddi-book-checks.yml`](../.github/workflows/infoblox-ddi-book-checks.yml) —
> now runs on any change under `infoblox-ddi-book/`. **Blocking:** `bash -n` over all 22
> shell scripts and `node --check` over the Script Includes (both verified green locally).
> **Advisory (non-blocking to start, per the recommendation below):** `shellcheck` and
> `terraform fmt -check` + `terraform validate` across every module — they report status
> while the modules remain acknowledged skeletons, and flip to blocking once the gold
> exemplar (§2.2) hardens them.

Still open: `tflint`, and promoting the advisory checks to blocking.
- ~~No JS parse check~~ and ~~no `bash -n`~~ — **done** (blocking).
- `shellcheck` and `terraform fmt/validate` — **wired, advisory.**
- `tflint` — not yet added.
- **Why the offline subset was run here:** `terraform`/`shellcheck` aren't installable in
  this authoring sandbox (network-restricted), so they run on the CI runner; the checks
  that *could* run locally were run, and pass. Removing the stray `</content>` tags (see
  the diagram-cleanup work) is what makes the shell scripts pass `bash -n` at all.

### 2.2 Nothing has been deployed and validated end-to-end
Every claim is architecture-correct but **unproven**. There is no recorded run of a module
producing working DNS, no captured `discovery-sync` success, no screenshot/log of a
ServiceNow catalog request closing the loop.
- **Recommendation:** produce **one fully-worked, tested reference deployment** (suggest
  **Azure, `deployment_model = grid`**) with a committed `terraform.tfvars.example`, a
  captured validation transcript, and a short "verified against NIOS vX / provider vY on
  <date>" banner. Make it the **gold exemplar** the other four packages explicitly say they
  are patterned on. Truth-in-labeling: keep the "starter skeleton" banners on the rest.

### 2.3 The IaC skeletons carry placeholders that will not apply as-is
By design the modules leave `vnios_image` publisher/offer/sku/version and VM SKUs as
operator-supplied, and the Infoblox-provider (DDI-object) resources need a reachable WAPI
endpoint — a **two-phase apply** that no committed example wires up.
- **Recommendation:** commit a `terraform.tfvars.example` per package and a documented
  two-phase apply (infra first, DDI objects second) in `examples/`, so "what do I actually
  type" is answered by a file, not prose.

### 2.4 The ServiceNow app is source records, not an importable/tested app
[`servicenow-app/`](./servicenow-app/README.md) is honest about being "un-signed source
records," but the practical gaps are real:
- The Flow is a **prose blueprint** ([`flow/flow-blueprint.md`](./servicenow-app/flow/flow-blueprint.md)),
  not an exported `sys_hub_flow`.
- The REST Message XML is **illustrative and untested**; endpoints are placeholders.
- **No ATF (Automated Test Framework) tests**, and it is not packaged as a **signed scoped
  application / update set** you can import in one step.
- **Recommendation:** build one importable, ATF-covered update set for the Azure exemplar;
  keep the others as documented blueprints until proven.

---

## 3. P1 — Completeness gaps (do next)

| Area | Gap | Suggested fix |
|---|---|---|
| **DHCP** | Thin across the board (correctly noted as platform-managed in cloud), but hybrid **DHCP failover**, option-code design, and DHCP fingerprinting are absent — including on VMware/NSX where Infoblox DHCP is real. | A short "DHCP where it matters" section per platform; a worked NSX + Infoblox DHCP example. |
| **IPv6 / dual-stack** | Essentially uncovered — IPAM for v6, RA/DHCPv6, reverse zones. | A dual-stack subsection in the shared reference architecture + each IPAM section. |
| **Cost & licensing** | Sizing→SKU and licensing tiers are repeatedly deferred to the vendor; there is no cost model. | A per-platform sizing/cost table (instance class, disk, Universal DDI subscription tier, query-rate guidance) with "estimate, verify with account team." |
| **Multi-region anycast** | Conceptual only; no worked BGP / route-health-injection config. | One concrete anycast example (advertisement, withdrawal on failure, per-cloud specifics). |
| **DR** | Conceptual; no tested GM-promotion runbook with RTO/RPO. | A game-day runbook with steps, expected timings, and rollback. |
| **GovCloud / sovereign** | Only `.com` / GCC-Moderate-on-commercial is built; Azure Government, AWS GovCloud, etc. are named but not implemented. | A GovCloud variant of the Azure exemplar (endpoints, image availability, boundary deltas). |
| **Brownfield / migration** | "Extend an existing on-prem Grid" is asserted but there is no coexistence/cutover runbook. | A migration chapter: parallel-run, delegation cutover, decommissioning native zones. |
| **Observability** | Monitoring is mentioned; no dashboards, metrics, or alert thresholds. | Concrete metric list + example Sentinel/Grafana alerts (query rate, member health, sync staleness, Threat Defense hits). |

---

## 4. P2 — Polish & UX

- **Glossary / acronym appendix.** DDI, NIOS, vNIOS, GM/GMC, CSP (both meanings!), RPZ,
  EA, SoD, ATO, MID, CPG, AVM — define once, link from chapter 0.
- **Combined volume build.** The docx export is **per-file** (dozens of documents). A single
  bound Word/PDF "volume" (with a generated figure list and TOC) would make distribution
  and review far easier than a zip of many files.
- **Link durability.** The volume leans heavily on external vendor URLs; the link-check is
  correspondingly brittle and vendor docs move. Recommend periodic revalidation, preferring
  stable landing pages over deep-linked doc anchors, and recording a "links verified on
  <date>" note.
- **Version currency banner.** Product names and version-specific facts (NIOS SKUs,
  "Universal DDI, formerly BloxOne") will age. Add a "verified against / as of <date>"
  banner per chapter.
- **Figure captions.** The AAN-style long alt-text captions are great for accessibility but
  heavy inline; consider a short visible caption + full alt text. The figure set is now
  consistent (reference architecture, discovery/IPAM, DNS resolution, ServiceNow loop);
  keep that four-figure rhythm per platform.
- **Worked examples with realistic values.** One annotated end-to-end example (real-ish
  CIDRs, names, tags) is worth several pages of prose.

---

## 5. Suggested roadmap (in order)

1. **Add book-scoped CI** — `terraform validate`/`tflint`, `shellcheck`, JS lint (P0.1).
   Cheap, immediate credibility. **✅ Started in this PR** (bash + JS blocking; shellcheck +
   terraform advisory); remaining: `tflint` and promoting the advisory checks to blocking.
2. **Ship the Azure gold exemplar** — tested deployment, `tfvars.example`, validation
   transcript, signed + ATF-tested ServiceNow update set, "verified against" banner
   (P0.2–2.4). Label the other four as patterned on it.
3. **Fill the P1 content** — cost/sizing, IPv6, DHCP depth, one anycast + one DR runbook.
4. **Build the combined volume** — single Word/PDF + glossary + version banners (P2).
5. **GovCloud variant** of the Azure exemplar as the sovereign reference (P1).

Doing #1 and #2 converts the volume from "very good documentation" into "documentation you
can trust enough to deploy from." That is the single most valuable next investment.

---

*Self-assessment, part of the volume and independent of UIAO governance canon. Kept under
`infoblox-ddi-book/` with everything it critiques.*
