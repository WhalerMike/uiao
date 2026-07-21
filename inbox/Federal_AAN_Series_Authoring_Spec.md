# Federal AAN Series — Authoring Spec

Conventions for all Federal Application-Aware Networking deliverables: the
`Book_NN_FedAAN_*` documents (`.qmd` sources in `inbox/`, rendered `.docx` /
`.html`), the `.pptx` briefings, and the copies staged in
`OneDrive\AAN_Federal_Series_Complete`.

## 1. Date Code — accurate to the minute

Every deliverable carries a **Date Code accurate to the day, hour, and
minute**. In a period of rapid, multi-session development, file-system
timestamps are unreliable (OneDrive sync, copies between machines, re-zips
reset them); the embedded Date Code is the single source of truth for which
version is latest.

### Format

```
YYYY-MM-DD HH:MM ET
```

- 24-hour clock, US Eastern Time.
- ISO-8601 field order so Date Codes sort correctly as plain text.
- Example: `2026-07-07 08:37 ET`

### Placement by artifact type

| Artifact | Where the Date Code lives |
|---|---|
| `.qmd` source | Frontmatter `date:` field set to the full code (Quarto accepts the string verbatim), **and** a visible `Date Code:` line inside the Draft Proposal callout at the top of the document |
| `.docx` (rendered) | Inherited from the `.qmd` render — verify the title block shows the full code after each render |
| `.html` (rendered) | Inherited from the `.qmd` `date:` field |
| `.pptx` briefing | Visible `Date Code:` line on the title slide (inside or beside the draft-proposal disclaimer) |
| `.zip` kit archive | Date Code **in the filename**, filename-safe form `YYYY-MM-DD_HHMMET` (e.g., `AAN_Federal_Series_Complete_2026-07-07_1202ET.zip`). Individual files inside keep plain names — their codes live in their content. Exactly one zip is kept per location; the rebuild deletes the previously-coded zip (newest code wins) |

### Update discipline

1. **Bump on every substantive content change** — set the Date Code to the
   moment of the edit session's final save, before rendering or distributing.
   *Ruling (2026-07-20, repo-review round 2):* repo-wide **mechanical
   sweeps** — renames, brand sweeps (e.g. AAN→OrgComp), link/alias fixes,
   formatting-only passes — do **not** bump the Date Code. The code answers
   "when did the substance of this deliverable last change," and a mechanical
   sweep that leaves the substance intact would otherwise erase that signal
   across the whole corpus at once. A sweep that *does* alter meaning in a
   book (changed claims, counts, controls) bumps that book like any edit.
2. **Render immediately after bumping** so source and derived artifacts carry
   the same code. Never distribute two artifacts with the same Date Code but
   different content.
3. **Newest code wins.** When two copies of a deliverable disagree, the one
   with the later Date Code is authoritative; the older copy is superseded and
   should be replaced, not merged.
4. Generator scripts (e.g., pptx build scripts) must take the Date Code from
   the clock at build time — never hard-code a stale value into a template.

### Scope of the convention

The Date Code convention (and its CI freshness gate,
`check_derivative_freshness.py`) is **deliberately scoped to the OrgComp
series** — measured 2026-07-20, no other customer-document series carries
Date Codes (0 of 522 `.qmd` across the eight other series), so there is
nothing there to gate. Extending the convention to another series is a
per-series adoption decision, not a gate change: add the codes first, then
widen the gate. Known intra-series gaps: `Vol_0_Book_00a` (Executive
Brief), `Vol_II_Book_02` (SQL Server Implementation Guide), and
`Vol_IV_Book_01` (Business Continuity) predate the convention and carry no
Date Code yet.

## 2. FedRAMP scope parameter — Moderate only

The series targets **FedRAMP Moderate exclusively** (SSA baseline: GCC
Moderate / FedRAMP Moderate). This is a hard scope parameter for every
deliverable:

1. **Never cite, map to, or claim FedRAMP High** — no High baselines, High
   control selections, or High inheritance claims anywhere in series text,
   tables, diagrams, or slides.
2. Where an underlying CSP region or service happens to hold a higher
   authorization, refer to it simply as **"FedRAMP-authorized"** without
   naming the High level. The series claims only what SSA's boundary
   targets: Moderate.
3. Control mappings use the **FedRAMP Moderate baseline** of NIST SP 800-53
   Rev 5.
4. Vendor authorization claims state the CSO's actual level (e.g., InfoBlox
   BloxOne DDI Federal, CSO FR2017257053, FedRAMP **Moderate**) and are
   verified against the FedRAMP Marketplace at procurement time.

Rationale: keeps the procurement and authorization conversation inside SSA's
actual boundary target and avoids implying High-baseline obligations the
program is not signing up for.

## 3. Presentation speaker notes — full notes on every slide

Every slide in a `.pptx` deliverable carries **full speaker notes** — complete
presenter prose, not fragments or keyword lists. Notes must be sufficient for
a co-worker who did not build the deck to present the slide: what the slide
claims, why it matters, and any caveat or pending decision the presenter
should voice.

### Vendor sourcing rule

If a slide states vendor information — product capabilities, certifications,
FedRAMP authorizations, partnership claims, release features, pricing or
procurement vehicles — the notes for that slide **must include a link to the
vendor's own documentation** for the claim (or the authoritative third-party
source, e.g., the FedRAMP Marketplace listing). Conventions:

1. End the notes with a `Vendor sources:` line listing full URLs, one per
   claim category.
2. Prefer the vendor's product documentation or official blog over press
   coverage; prefer the FedRAMP Marketplace over vendor marketing for
   authorization claims.
3. Reuse the References table of the source Book where possible so decks and
   books cite the same URLs.
4. Claims sourced from internal UIAO documents (whitepapers, Books) cite the
   repo path instead of a URL.
5. Generator scripts keep the link map in one place (a `SRC` constant) so URLs
   are updated once, not per slide.

### Build sequences (progressive-reveal slides)

Technical content with three or more moving parts should be presented as a
**click-through build sequence**: one slide per step, completed steps shown
tinted/dimmed, the active step highlighted (amber ring), with a
plain-language detail panel for the active step. Each step slide carries its
own full speaker notes — the notes deepen per step rather than repeating.
Single dense "everything at once" slides are reserved for reference tables
the audience is expected to read, not be walked through.

## 4. Slide images flow back into the Books (PPTX → DOCX)

When a `.pptx` briefing is created or updated with images — diagrams, build
sequences, comparison layouts, or any slide visual — those images are
**incorporated into the corresponding Book's document**, either **replacing**
an existing figure or **augmenting** a section that lacks one.

1. **Replace** when the slide visual covers the same concept as an existing
   Book figure and is newer or clearer (house style: white background,
   navy/teal/amber/red ink). The old figure is removed, not left alongside.
2. **Augment** when the Book section has no figure for the concept the slide
   illustrates.
3. **Export mechanics:** export the slide as PNG at presentation resolution
   or higher (PowerPoint slide export, ≥ 1280×720). For build sequences,
   use the final step's slide (the complete state) unless an intermediate
   state carries independent explanatory value.
4. **Respect the render pipeline:** add the image to the Book's `.qmd`
   source as a Quarto figure (with descriptive `fig-alt` text) and
   re-render the `.docx` — do not hand-edit the `.docx` directly.
5. **Provenance + freshness:** the figure caption or `fig-alt` notes the
   originating deck and its Date Code, and the updated Book gets a new
   Date Code per §1 so document and deck stay traceably in sync.

The goal: the deck and the Book never diverge visually — whichever was
touched last feeds the other, and the Date Codes show which way the sync
last flowed.

### Trigger — this step is not optional

Creating or updating a `.pptx` with images **triggers this incorporation
step in the same work session**. The deck deliverable is not complete until:

1. Each deck visual has been dispositioned against the Book — *replace*,
   *augment*, or *skip* (skip only when an existing Book figure covers the
   same concept equally well or better; record the reasoning).
2. The chosen images are exported, added to the `.qmd`, and the `.docx`
   re-rendered.
3. Both artifacts carry fresh Date Codes.

Deferring the incorporation to "the next time the Book is touched" is not
permitted — that is exactly how deck and Book drift apart.

## 5. Existing conventions (carried forward)

- **Draft-proposal disclaimer** on every deliverable: CSI Team draft, not yet
  reviewed by the SSA CIO Office, OIS, or organizational leadership.
- **White backgrounds** for all diagrams and slides; navy `1F3A5F` / teal
  `1A9E8F` / amber `D4860B` / red `C0392B` as ink, never as background.
- No dark title or closing slides in presentations.
- Cross-book links use the `Book_NN_FedAAN_*` filenames.
