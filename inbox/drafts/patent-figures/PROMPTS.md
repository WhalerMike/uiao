# Patent Figure Prompts — UIAO Provisional Application

Companion catalog for `../provisional-patent-application.md`. One entry per
figure referenced in the spec's "Brief Description of the Drawings" section.

**Generator:** `scripts/generate_patent_figures.py` (calls Gemini 2.5 Flash
Image / Nano Banana).

**Output:** `figure-NN.png` siblings of this file, sized for embedding into
the `.docx` rendering of the spec.

**Patent-figure visual language.** All 9 prompts share a base style block
intended to nudge Nano Banana toward USPTO drawing conventions:

> A formal patent figure illustration in the style of USPTO drawings.
> Pure black-and-white line drawing on a white background, crisp uniform
> line weight, no shading, no gradients, no color, no marketing flair.
> Plain sans-serif labels. Numbered reference indicators (e.g., 110, 120,
> 130) attached to elements via thin lead lines. Box-and-arrow diagram
> aesthetic. Portrait composition with clear margins. The word "FIG. N"
> appears as a label in the bottom margin.

Each figure prompt below extends that base with its specific content.

> **Note.** Nano Banana is a generative image model, not a vector-drawing
> tool. The output will be patent-figure-*styled* but won't have the
> formal numbered-reference-label discipline of a real patent drawing.
> Treat these as inventor-review placeholders; redraw formally before
> non-provisional filing.

---

## FIG-01 — `figure-01.png`

**Title:** System Overview

**Aspect:** 1600×1200 (portrait-ish)

**Prompt:**

> [Base style block above.] FIG. 1 — Three vertical columns connected by
> horizontal flow arrows, forming a block diagram of the UIAO system.
> **Left column** labelled "ON-PREMISES DEPENDENCIES (102)" stacks five
> labelled rectangles top-to-bottom: "Active Directory (110)", "PKI /
> Certificate Services (112)", "DNS / DHCP (114)", "RADIUS / NPS (116)",
> "LDAP Applications (118)". **Middle column** labelled "UIAO OVERLAY
> (106)" stacks six labelled rectangles: "Adapter Contract (130)",
> "Adapter Registry (132)", "Claim Pipeline (134)", "Raw Zone (136)",
> "Validation Engine (138)", "Multi-Plane Orchestrator (140)". **Right
> column** labelled "CLOUD IDENTITY TARGET (104)" stacks three labelled
> rectangles: "Microsoft Entra ID (160)", "Microsoft Intune (162)",
> "Microsoft Azure (164)". Solid horizontal arrows connect each left-column
> box rightward into the middle column; further arrows flow from the
> middle column rightward into the right column. A horizontal label
> "FIG. 1" appears centred in the bottom margin.

---

## FIG-02 — `figure-02.png`

**Title:** Adapter Contract Class Diagram

**Aspect:** 1600×1200 (landscape)

**Prompt:**

> [Base style block above.] FIG. 2 — A UML-style class diagram. A single
> central box at top labelled "DatabaseAdapterBase (200)" with three
> compartments: name, methods, abstract markers. Below the central box,
> seven smaller dataclass boxes arranged in two rows, each connected
> upward to the base class with a thin line indicating "returned by":
> Row 1: "ConnectionProvenance (210)", "SchemaMappingObject (212)",
> "QueryProvenance (214)", "ClaimObject (216)". Row 2: "ClaimSet (218)",
> "DriftReport (220)", "EvidenceObject (222)". Each box shows its field
> names below the title (e.g., ConnectionProvenance shows identity,
> auth_method, endpoint, tls_version, mtls_enabled, timestamp). A
> horizontal label "FIG. 2" appears centred in the bottom margin.

---

## FIG-03 — `figure-03.png`

**Title:** Canonical Claim Pipeline Sequence

**Aspect:** 1200×1600 (portrait)

**Prompt:**

> [Base style block above.] FIG. 3 — A UML sequence diagram with six
> vertical lifelines drawn as thin dashed downward lines, each headed by
> a labelled box at top: "Caller (300)", "Adapter (302)", "Source System
> (304)", "Schema Mapper (306)", "Claim Pipeline (308)", "Evidence
> Builder (310)". Time flows top-to-bottom. Numbered horizontal arrows
> between lifelines depict the sequence: (320) Caller→Adapter
> "connect()"; (322) Adapter→Source "authenticate via mTLS"; (324)
> Source→Adapter "ConnectionProvenance"; (326) Caller→Adapter
> "discover_schema()"; (328) Adapter→Schema Mapper "fetch + map"; (330)
> Schema Mapper→Caller "SchemaMappingObject"; (332) Caller→Adapter
> "execute_query()"; (334) Adapter→Source "vendor query"; (336)
> Source→Adapter "rows"; (338) Caller→Pipeline "normalize(rows)"; (340)
> Pipeline→Caller "ClaimSet with provenance_hash"; (342) Caller→Adapter
> "detect_drift()"; (344) Adapter→Caller "DriftReport"; (346)
> Caller→Builder "collect_evidence(ksi_id)"; (348) Builder→Caller
> "EvidenceObject". A horizontal label "FIG. 3" appears centred in the
> bottom margin.

---

## FIG-04 — `figure-04.png`

**Title:** Dual-Axis Adapter Registry

**Aspect:** 1600×1200 (landscape)

**Prompt:**

> [Base style block above.] FIG. 4 — A two-axis grid schematic. The
> horizontal axis is labelled "OPERATIONAL CLASS (402)" and divided into
> two columns at the top: "modernization (410)" on the left and
> "conformance (412)" on the right. The vertical axis is labelled
> "MISSION CLASS (404)" and divided into five rows from top to bottom:
> "identity (420)", "telemetry (422)", "policy (424)", "enforcement
> (426)", "integration (428)". This forms a 5-row × 2-column grid of 10
> cells. Each cell shows a representative example adapter name in plain
> text inside it (e.g., "entra-cloud-sync" in identity×modernization,
> "scubagear" in policy×conformance). A small legend box bottom-right
> labelled "(430)" notes "two orthogonal axes; each adapter declares
> exactly one value on each axis." A horizontal label "FIG. 4" appears
> centred in the bottom margin.

---

## FIG-05 — `figure-05.png`

**Title:** Adapter Lifecycle State Diagram

**Aspect:** 1600×900 (landscape)

**Prompt:**

> [Base style block above.] FIG. 5 — A state machine diagram with five
> elliptical state nodes arranged horizontally left-to-right and
> connected by labelled directed arrows: "reserved (510)" →
> "proposed (512)" → "active (514)" → "deprecated (516)" → "retired
> (518)". Each transition arrow carries a label naming the trigger:
> reserved→proposed "design draft committed (520)"; proposed→active
> "governance-board approval (522)"; active→deprecated "successor named
> (524)"; deprecated→retired "evidence retention elapsed (526)". A small
> note at the bottom labelled "(530)" reads "id is immutable across all
> transitions". A horizontal label "FIG. 5" appears centred in the
> bottom margin.

---

## FIG-06 — `figure-06.png`

**Title:** Five-Stage Migration Pipeline

**Aspect:** 1600×1000 (landscape)

**Prompt:**

> [Base style block above.] FIG. 6 — A flowchart of the five-stage
> migration pipeline. Five large rectangular blocks arranged left-to-
> right with thick directional arrows between each: "Discover (610)" →
> "Normalize (612)" → "Map (614)" → "Migrate (616)" → "Validate (618)".
> Between each adjacent pair of stages, a small diamond labelled
> "Governance Gate (620, 622, 624, 626)" sits on the arrow representing
> the gate check; each diamond has a label such as "evidence fresh and
> passing?". Below each stage block, a brief description in small text
> describes what happens at that stage. A horizontal label "FIG. 6"
> appears centred in the bottom margin.

---

## FIG-07 — `figure-07.png`

**Title:** Immutable Raw Zone Storage Layout

**Aspect:** 1600×1200 (portrait-ish)

**Prompt:**

> [Base style block above.] FIG. 7 — A storage layout diagram showing a
> hierarchical directory tree. Top-level container box labelled "Raw Zone
> (700)". Inside it, an expanded folder tree drawn with traditional
> tree-structure indentation lines: lake_root/ (710) → adapter_id/
> (712) → run_id/ (714) → containing artefacts "evidence.json (716)",
> "claims.json (718)", "drift.json (720)". To the right of the
> run_id/ directory, a barrier symbol (a vertical bar with diagonal
> stripes) labelled "Write-Once Enforcement / RawZoneViolation (730)"
> indicates that the directory is sealed once written. A small annotation
> box below labelled "(740)" reads "retention enforced by archive
> manager per per-adapter retention-years declaration". A horizontal
> label "FIG. 7" appears centred in the bottom margin.

---

## FIG-08 — `figure-08.png`

**Title:** Validation Engine Flowchart

**Aspect:** 1200×1600 (portrait)

**Prompt:**

> [Base style block above.] FIG. 8 — A flowchart of the validation engine.
> Top: a rounded rectangle labelled "Input: EvidenceObject (800)". Arrow
> down to a diamond decision labelled "Within Freshness Window? (810)".
> No-branch on right exits to a terminal labelled "Status: stale (820)".
> Yes-branch continues down to a rectangle labelled "Evaluate Against
> Governance Indicator (830)". Arrow down to a diamond labelled
> "Indicator Match? (840)". Yes-branch exits to "Status: pass (850)";
> No-branch exits to "Status: fail (852)". A separate input from the side
> labelled "Pipeline Error (854)" feeds an exit terminal labelled
> "Status: error (856)". All four terminal status nodes converge at the
> bottom into a rectangle labelled "Output: ValidationResult with
> drift_indicators (860)". A horizontal label "FIG. 8" appears centred in
> the bottom margin.

---

## FIG-09 — `figure-09.png`

**Title:** Eleven AD Dependency Categories and Adapter Mapping

**Aspect:** 1600×2000 (portrait)

**Prompt:**

> [Base style block above.] FIG. 9 — A tabular figure. The table has a
> header row in bold: "# | Dependency Category | Failure Mode Without
> Governance | Adapter Family". Below the header, 11 numbered data rows:
> (1) Users / Identities | Orphaned accounts, privilege drift |
> identity-modernization (910); (2) Computers / Devices | Unmanaged
> endpoints, missing patches | device-management (912); (3) Service
> Accounts | Silent outages, lost Kerberos delegation | ldap-proxy (914);
> (4) Security Groups | Permission sprawl, lost inheritance |
> identity-modernization (916); (5) Group Policy Objects | Configuration
> drift, baseline gaps | device-management (918); (6) DNS / DHCP |
> Name-resolution failure, split-brain DNS | ipam (920); (7) PKI /
> Certificates | Silent certificate expiration | pki (922); (8) RADIUS /
> 802.1X | Network access failure, VPN outage | radius (924); (9) LDAP
> Applications | Application login failure | ldap-proxy (926); (10) SPNs
> / Kerberos | Single sign-on breakage | ldap-proxy (928); (11) Trust
> Relationships | Cross-domain authentication failure | architectural
> (930). Cell borders are thin uniform black lines on white. A horizontal
> label "FIG. 9" appears centred in the bottom margin.

---

## Regeneration

```bash
export GEMINI_API_KEY="<your-key>"
python scripts/generate_patent_figures.py            # generate missing
python scripts/generate_patent_figures.py --regenerate   # force regen all
python scripts/generate_patent_figures.py --dry-run      # report only

# Then rebuild the .docx with embedded figures:
cd inbox/drafts/
pandoc provisional-patent-application.md \
    -o provisional-patent-application.docx \
    --metadata title="Provisional Patent Application — UIAO" \
    --metadata author="[Inventor Full Legal Name]" \
    --toc --toc-depth=3
```

Cost: 9 figures × ~$0.039 per generation ≈ **$0.35 per full regeneration**.

PNGs land at `inbox/drafts/patent-figures/figure-NN.png` and are gitignored
per `inbox/.gitignore` — local-only by design.
