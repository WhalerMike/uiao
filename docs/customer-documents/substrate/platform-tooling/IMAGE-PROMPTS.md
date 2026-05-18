# Image Prompts — UIAO CLI Reference

> Companion catalog for `uiao-cli-reference.qmd`. One entry per
> `![...]` placeholder in the `.qmd` file. Generated images land in
> `./images/` with the exact filename referenced by the page.
>
> **Generation:** run `uiao generate gemini` with `GEMINI_API_KEY`
> exported; the generator reads this file, computes a SHA-256 of the
> prompt block, writes the PNG plus a JSON sidecar carrying the prompt
> hash + Gemini-model version. The sidecar makes regeneration
> deterministic — identical prompt → identical hash → cache hit.
>
> **Visual language.** All figures share the UIAO aesthetic:
>
> - **Palette:** dark navy `#0D1B2E` + teal `#1E8C8C` accents on white;
>   red `#C74040` reserved for failure/warning surfaces only.
> - **Typography:** clean sans-serif for labels; monospace for command
>   tokens, attribute values, and path fragments.
> - **Style:** diagrammatic / technical-illustration — not photographic,
>   not isometric-3D, not marketing-flat. Engineering-blueprint
>   aesthetic similar to high-quality cloud reference architectures.
> - **No human figures.** Infrastructure documentation, not lifestyle
>   imagery.
> - **Aspect ratio:** landscape 16:9 (e.g. 1600×900). Embedded at 85%
>   width in the `.qmd` file.
>
> **Canon compliance.** Every figure must respect UIAO canon:
> GCC-Moderate boundary visible where relevant; sub-app names spelled
> exactly per `src/uiao/cli/`; ADR-046 sub-app hierarchy honored
> (no flat top-level commands).

---

## IMAGE-01 — `uiao-cli-reference-image-01-cli-subapp-topology.png`

**Placement:** Top-of-page hero, immediately after the H1.

**Slug:** `cli-subapp-topology`

**Aspect:** 16:9 (1600×900)

**Prompt:**

> A horizontal engineering-blueprint diagram illustrating the UIAO
> command-line topology after ADR-046. At the center-top, a single
> rounded rectangle labelled `uiao` in monospace, painted dark navy
> (#0D1B2E) with white text. From that rectangle, thirteen labelled
> branches fan downward to thirteen smaller rounded rectangles, each
> in teal (#1E8C8C) with white monospace labels, in this order from
> left to right: `canon`, `generate`, `oscal`, `adapter`, `ir`,
> `conmon`, `reciprocity`, `cql`, `evidence`, `substrate`, `ksi`,
> `orchestrator`, `enforcement`. Beneath each sub-app, a short stack
> of two or three faint sub-command pills shows representative
> commands (e.g. under `generate`: `ssp`, `visuals`, `docx`; under
> `ir`: `scuba-transform`, `evidence-bundle`, `auditor-bundle`).
> Below the sub-app row, three horizontal lanes span the full width,
> labelled in small caps: `CANON-ANCHORED`, `ADAPTER-INGESTED`,
> `AUDITOR-DELIVERED`. Thin teal arrows connect the relevant sub-apps
> into each lane (e.g. `canon` and `generate` into CANON-ANCHORED;
> `adapter` and `ir` into ADAPTER-INGESTED; `evidence`,
> `orchestrator`, and `ir` into AUDITOR-DELIVERED). The bottom edge
> carries a thin grey ribbon labelled `pyproject.toml [project.scripts]
> uiao = "uiao.cli.app:app"` in monospace, with a small annotation
> "single entry point — Invariant I2". Clean white background, no
> gradients, no human figures, no vendor logos. Engineering-blueprint
> aesthetic, comparable in spirit to AWS / Azure reference-architecture
> diagrams but vendor-neutral.

**`fig-alt` (for accessibility, mirror in the `.qmd`):** A horizontal
blueprint-style diagram showing the `uiao` root entry point branching
into 13 named sub-apps: canon, generate, oscal, adapter, ir, conmon,
reciprocity, cql, evidence, substrate, ksi, orchestrator, enforcement.
Below the sub-apps, three lanes labelled 'Canon-anchored',
'Adapter-ingested', 'Auditor-delivered' connect to the substrate's
data flow. Clean engineering-blueprint aesthetic, dark navy and teal
on white, no human figures.

---

## IMAGE-02 — `uiao-cli-reference-image-02-pipeline-overview.png`

**Placement:** §1 Overview, after the introductory prose.

**Slug:** `pipeline-overview`

**Aspect:** 1600×600 (landscape)

**Generator:** `gemini-2.5-flash-image` (Gemini Nano Banana).

**Prompt:**

> Left-to-right engineering-blueprint pipeline diagram of the UIAO
> two-track CLI flow. Far-left root: a single dark-navy (#0D1B2E)
> rounded rectangle labelled `Canon YAML (src/uiao/canon/)` in
> monospace with white text. From that root, two parallel teal
> (#1E8C8C) tracks branch rightward. Top track (left to right):
> `generate ssp / oscal validate` → `generate visuals / diagrams /
> gemini` → `generate docx / pptx / artifacts`. Bottom track (left to
> right): `adapter run / run-scuba` → `ir scuba-transform /
> evidence-bundle / ...` → `conmon process / export-oa / dashboard`.
> Both tracks converge into a single right-side terminal box
> `ir auditor-bundle / evidence graph`, fed by both the top track's
> `generate docx` box and the bottom track's `ir scuba-transform` box.
> All command tokens in monospace. White background, no gradients, no
> human figures, no vendor logos. Engineering-blueprint aesthetic.

**`fig-alt`:** Pipeline overview: Canon YAML branches into two parallel
tracks. Top: generate ssp/oscal validate → generate visuals/diagrams/gemini
→ generate docx/pptx/artifacts. Bottom: adapter run/run-scuba → ir
scuba-transform/evidence-bundle → conmon process/export-oa/dashboard. Both
tracks converge into ir auditor-bundle/evidence graph.

---

## IMAGE-03 — `uiao-cli-reference-image-03-ir-pipeline.png`

**Placement:** §3.8 IR pipeline, after the introductory prose.

**Slug:** `ir-pipeline`

**Aspect:** 1600×600 (landscape)

**Generator:** `gemini-2.5-flash-image` (Gemini Nano Banana).

**Prompt:**

> Left-to-right engineering-blueprint diagram of the UIAO `ir`
> evidence-bundle pipeline. Far-left source box (rendered dark navy,
> #0D1B2E, white monospace text) labelled `adapter run-scuba
> (normalized JSON)`. The source feeds rightward through two
> sequential teal (#1E8C8C) processor boxes: `ir scuba-transform` →
> `ir evidence-bundle`. The `ir evidence-bundle` hub then fans out
> rightward to six parallel terminal boxes arranged in two stacked
> columns: top column — `ir poam-export`, `ir drift-detect / ir diff`,
> `ir governance-report` (which itself feeds an additional downstream
> box `ir ssp-report`); bottom column — `ir auditor-bundle`,
> `ir freshness / ir dashboard`. All six terminals (and the
> ssp-report downstream) are teal. All command tokens rendered in
> monospace. White background, no gradients, no human figures.
> Engineering-blueprint aesthetic.

**`fig-alt`:** IR pipeline: adapter run-scuba produces normalized JSON,
which feeds ir scuba-transform, which produces ir evidence-bundle. The
evidence bundle fans out to six terminal commands: ir poam-export, ir
drift-detect/ir diff, ir governance-report (which feeds ir ssp-report),
ir auditor-bundle, and ir freshness/ir dashboard.

---

## IMAGE-04 — `uiao-cli-reference-image-04-pipeline-architecture.png`

**Placement:** §6 Pipeline architecture, after the introductory prose.

**Slug:** `pipeline-architecture`

**Aspect:** 1200×1000 (portrait)

**Generator:** `gemini-2.5-flash-image` (Gemini Nano Banana).

**Prompt:**

> Top-down engineering-blueprint diagram of the full UIAO pipeline
> architecture. Single dark-navy (#0D1B2E) root box at top labelled
> `Canon YAML SSOT` in white monospace. From the root, two parallel
> vertical streams branch downward, both rendered in teal (#1E8C8C)
> with white monospace labels. Left stream (top to bottom): Core
> OSCAL Generation → Visual Rendering → Artifact Packaging →
> Continuous Monitoring. Right stream (top to bottom): Adapter
> Ingestion → IR Pipeline → Governance Reporting. Both streams
> converge at the bottom into a single red (#C74040) terminal box
> labelled `Auditor Delivery` (the auditor-delivery role is the
> single accountable sink — red signals critical-path importance,
> not failure). The Continuous Monitoring box (left stream bottom)
> connects directly into Auditor Delivery; the Governance Reporting
> box (right stream bottom) also connects into Auditor Delivery. All
> connecting arrows are thin teal directed edges. White background,
> portrait orientation, no gradients, no human figures.
> Engineering-blueprint aesthetic.

**`fig-alt`:** Full pipeline architecture, top-down. Canon YAML SSOT
branches into two streams. Stream one: Core OSCAL Generation → Visual
Rendering → Artifact Packaging → Continuous Monitoring. Stream two:
Adapter Ingestion → IR Pipeline → Governance Reporting. Both streams
converge into Auditor Delivery at the bottom.

---

## Generation notes

- **All four figures are now Gemini Nano Banana
  (`gemini-2.5-flash-image`).** Prior versions of this page used
  `mermaid-cli@11.12.0` for IMAGE-02 / 03 / 04; that path was retired
  because mermaid rendering in CI hung the Quarto DOCX pipeline on
  the headless-Chromium step. Existing PNGs were originally
  mermaid-rendered and remain valid; on next regen they will be
  produced by Gemini from the prompts above.
- **Regenerating an IMAGE-0N PNG.** Run `uiao generate gemini`
  with `GEMINI_API_KEY` exported (or trigger the `image-gen.yml`
  workflow with `commit_back: true`). The generator hashes the
  prompt block, calls `gemini-2.5-flash-image`, writes the PNG, and
  updates the `.png.json` sidecar's `sha256` and `model` fields.
- All four figures on this page are now Gemini-generated; there are
  no remaining mermaid-rendered diagrams.
- CI link-check tolerates missing images under `images/` by convention
  (see `.lycheeignore`).
