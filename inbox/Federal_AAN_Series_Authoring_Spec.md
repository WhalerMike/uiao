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

### Update discipline

1. **Bump on every content change** — set the Date Code to the moment of the
   edit session's final save, before rendering or distributing.
2. **Render immediately after bumping** so source and derived artifacts carry
   the same code. Never distribute two artifacts with the same Date Code but
   different content.
3. **Newest code wins.** When two copies of a deliverable disagree, the one
   with the later Date Code is authoritative; the older copy is superseded and
   should be replaced, not merged.
4. Generator scripts (e.g., pptx build scripts) must take the Date Code from
   the clock at build time — never hard-code a stale value into a template.

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

## 4. Existing conventions (carried forward)

- **Draft-proposal disclaimer** on every deliverable: CSI Team draft, not yet
  reviewed by the SSA CIO Office, OIS, or organizational leadership.
- **White backgrounds** for all diagrams and slides; navy `1F3A5F` / teal
  `1A9E8F` / amber `D4860B` / red `C0392B` as ink, never as background.
- No dark title or closing slides in presentations.
- Cross-book links use the `Book_NN_FedAAN_*` filenames.
