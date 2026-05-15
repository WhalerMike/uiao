# recover-narrative-codeblocks

Recover code blocks from OneDrive `.docx` source files into pandoc-converted
`.qmd` chapters when the original conversion flattened code into prose.

## Why this exists

When the OrgPath Narrative chapters were converted from Word `.docx` to
Markdown via Pandoc 3.9, the converter dropped two style classes:

- **Heading styles** (`Heading1`/`Heading2`/`Heading3`) — fixed by
  [`inbox/drafts/complete-narrative/promote_headings.py`](../../inbox/drafts/complete-narrative/promote_headings.py)
  in [PR #348](https://github.com/WhalerMike/uiao/pull/348).
- **Code-block styles** (paragraphs in monospace runs) — fixed by these
  scripts.

Pages 05 (`orgpath-and-intune`) and 09 (`orgpath-and-azure-policy-guest-config`)
contained large PowerShell DSC, ARM JSON, and KQL blocks that ended up as
single prose paragraphs with `\$`, `\#`, `\|` escapes everywhere. These
scripts reconstruct them from the `.docx` source where the original line
breaks and monospace formatting are intact.

## When to run

Run when:

- A new narrative chapter is added with code-block content.
- An existing chapter is re-derived from an updated `.docx` source.
- You spot the symptom: a single paragraph longer than ~400 characters
  with `\$`, `\#`, `\|`, `\*` escapes.

Skip when:

- The source `.docx` already has zero monospace paragraphs (per the audit
  in PR #348, most narrative chapters are pure prose).

## Usage

Source `.docx` files live in OneDrive at:

```
C:\Users\whale\OneDrive\UAIO-NewDocs\UIAO Governance OS — The Complete Narrative\
```

The OneDrive path contains em-dashes — copy the `.docx` to an ASCII path
first to avoid shell-encoding problems:

```bash
cp "$ONEDRIVE/<chapter>.docx" inbox/_audit-input/<short-name>.docx
```

Then:

```bash
# Inspect — list all monospace-majority code blocks the script will extract
python scripts/recover-narrative-codeblocks/extract_codeblocks.py \
    inbox/_audit-input/<short-name>.docx

# Apply — surgically replace flattened blocks in the .qmd; writes a new file
python scripts/recover-narrative-codeblocks/apply_codeblocks.py \
    inbox/_audit-input/<short-name>.docx \
    docs/customer-documents/orgpath-narrative/<chapter>.qmd \
    inbox/_audit-input/<chapter>-fixed.qmd

# Diff and promote
diff docs/customer-documents/orgpath-narrative/<chapter>.qmd \
     inbox/_audit-input/<chapter>-fixed.qmd | less
cp inbox/_audit-input/<chapter>-fixed.qmd \
   docs/customer-documents/orgpath-narrative/<chapter>.qmd
```

## How it works

1. `.docx` is a zip; `word/document.xml` carries the body.
2. For each `<w:p>`, sum monospace-font character share across runs. A
   paragraph is "code" if monospace share exceeds 50%.
3. Consecutive code paragraphs become one block; intra-paragraph `<w:br/>`
   become newlines.
4. Each block gets a fingerprint (first 80 chars after collapsing whitespace
   and de-escaping pandoc backslash-escapes).
5. The `.qmd` is walked line by line. For any "long" line (> 400 chars OR
   starting with code-block markers like `\<#`, `\#`, `{`, `//`), apply
   the same fingerprint. On match, replace the line with a fenced code
   block; otherwise leave it alone.
6. Language tag (`powershell`, `json`, `kql`) is detected from leading
   content of each block.

## Dependencies

Stdlib only — no `python-docx`, no `lxml`. Tested on CPython 3.13+.

## Known limitations

- Single-paragraph code snippets (e.g., one-line dynamic membership rules)
  may end up as broken `### ...` headings when pandoc misclassifies them
  as headings. The apply script will not match these — they need a manual
  edit. PR #500 fixed one such case in chapter 05.
- The fingerprint comparison is sensitive to leading whitespace; if the
  source `.docx` uses leading tabs and the `.qmd` flattened them, manual
  intervention may be needed.
