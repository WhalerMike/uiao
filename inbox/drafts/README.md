# inbox/drafts/

Agent-authored drafts written for iteration before they become canon,
narrative, or code in the substrate. Pair with [`inbox/`](../README.md):

- **`inbox/`** — raw inputs you drop (Word docs, PDFs, spreadsheets, exports).
- **`inbox/drafts/`** — Markdown drafts the agent writes in response.

Together they form a bi-directional scratch surface outside the
substrate. Nothing here is canon. Nothing here renders on the website.
Nothing here is referenced by anything under `core/`, `docs/`, or
`impl/`.

## Contract

1. **Not canon.** The substrate manifest does not list this directory
   as a module. The substrate walker does not scan it. The metadata
   validator does not inspect it.
2. **Markdown tracked; binaries ignored.** `.md` files in this
   directory are git-tracked so drafts can ride on scratch branches
   without `git add --force`. All binary formats listed in
   `inbox/.gitignore` remain ignored.
3. **Transient.** A draft finishes one of three ways:
   - Promoted into canon via a proper canon PR (UIAO_NNN, frontmatter,
     registry entry). The draft is deleted from `inbox/drafts/` in
     the same PR.
   - Promoted into a narrative page under `docs/narrative/` with a
     provenance block. Draft deleted.
   - Abandoned. Draft deleted.
4. **No inbound references.** Nothing outside `inbox/` may link to a
   file here.

## CoPilot roundtrip workflow

The intended collaborative loop for drafting canon or series content:

```
Agent    → inbox/drafts/UIAO_NNN-skeleton.md       (outline, structure, voice-neutral)
User     → CoPilot (prompt: "expand to match the style of Section 1")
User     → inbox/<exported>.docx or .md            (CoPilot output)
User     → scratch branch push
Agent    → reconcile style + structure + canon checks
Agent    → inbox/drafts/UIAO_NNN-final.md          (ready for canon PR)
User     → green-light
Agent    → canon PR with provenance block
```

Neither tool owns the full loop. The skeleton is authored by the agent
(for canon alignment); the voice expansion is CoPilot's (for style
continuity with existing series); reconciliation is the agent's again
(for drift-free landing).

## Filename convention

- Canon drafts: `UIAO_NNN-<slug>-<stage>.md` (e.g. `UIAO_129-app-identity-v1.md`)
- ADR drafts: `adr-NNN-<slug>-<stage>.md` (e.g. `adr-030-v3-reconciliation-v1.md`)
- Series drafts: `series-N-article-MM-<slug>-<stage>.md`
- Narrative drafts: `narrative-<slug>-<stage>.md`

`<stage>` is one of: `skeleton`, `v1`, `v2`, `final`.

## What this directory is *not*

- Not a publishing location.
- Not a staging area for canon PRs (each canon PR authors the canonical
  file directly in `core/canon/` with proper frontmatter).
- Not a long-term archive. Drafts promoted into canon or narrative are
  deleted from here.
