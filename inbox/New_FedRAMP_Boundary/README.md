# FedRAMP Moderate External Assessment — Image Pipeline

Five files plus a `docx_build_source/` folder for the docx-js sources.

## What's here

| File | Purpose |
|---|---|
| `M365_GCC-Moderate_Telemetry_and_Boundary_Assessment_External.docx` | Externalized combined assessment, 7 image placeholders embedded. |
| `GCC-Moderate_Boundary_and_ThousandEyes_Assessment_External.docx` | Externalized ThousandEyes memo, 2 image placeholders embedded. |
| `IMAGE-PROMPTS-fedramp-moderate.md` | All 9 prompts in your established format. |
| `generate_images_from_prompts.py` | Nano Banana Pro / 2 caller with hash-based caching. |
| `inject_images_into_docs.py` | Replaces `[[IMG_PLACEHOLDER:fig_xxx_NN]]` markers with the generated PNGs. |
| `docx_build_source/` | docx-js sources if you want to shift placeholders later. |

## Workflow

```powershell
# 1. Set the API key once per session (NEVER commit this)
$env:GEMINI_API_KEY = "<your-key>"

# 2. Install SDK
pip install google-genai pillow

# 3. Generate images. Defaults to Nano Banana Pro (gemini-3-pro-image-preview).
python generate_images_from_prompts.py
#   -> images/fig_combined_01.png ... fig_te_02.png + manifest.json

# 4. Inject into both docs in one call
python inject_images_into_docs.py `
  --in M365_GCC-Moderate_Telemetry_and_Boundary_Assessment_External.docx `
  --in GCC-Moderate_Boundary_and_ThousandEyes_Assessment_External.docx `
  --images images/
```

Output: `*_with_images.docx` next to each input.

## Useful flags

- `generate_images_from_prompts.py --model flash` — use Nano Banana 2 (cheaper, faster).
- `generate_images_from_prompts.py --force fig_combined_03` — regenerate one image only.
- `generate_images_from_prompts.py --force-all` — ignore cache.
- `generate_images_from_prompts.py --dry-run` — parse prompts and report what would be generated.
- Edit a prompt body → its SHA-256 changes → that one image regenerates on the next run; everything else stays cached.

## Image plan (all 9 figures)

**Combined assessment:**
1. End of §0 — FedRAMP Moderate boundary overview
2. Start of §5 — Telemetry blocked at the boundary (SI-4/AU-2/AU-3/SC-7)
3. §7.5 — MITRE Chain A flow
4. §7.5 — MITRE Chain B flow
5. End of §8 — ZTMM pillar maturity ceiling
6. End of §12 — MAS 2026 boundary refinement (before/after)
7. End of §13.2 — Compensating-architecture stack

**ThousandEyes memo:**
1. §1 — Three GCC-Moderate boundary postures
2. End of §2.1 — ThousandEyes pillar coverage (1 of 7 ZTMM pillars)

## Notes

- API key is read from `GEMINI_API_KEY` env var only; never hardcode it.
- Both scripts run on Python 3.8+ (`google-genai`, `pillow`).
- Both .docx files validate against the OOXML schema and render correctly in LibreOffice. Word will render them as well — Word is more permissive than LibreOffice.
- `inject_images_into_docs.py` is idempotent: if you regenerate one image and re-run inject, it will rebuild from the original placeholder doc cleanly. Don't run inject against an already-injected doc — always run it from the placeholder version.

## On `.qmd` files (your earlier question)

Quarto `.qmd` files reference images by path (e.g., `![Caption](images/figure1.png){#fig-id}`); the image bytes don't live inside the `.qmd`. The renderer pulls them in at build time — embedded into the `.docx` zip when targeting Word, base64-embedded or linked when targeting HTML. The image PNGs need to exist at the referenced paths *before* you render. So if you ever switch this pipeline to a `.qmd` source, the same `generate_images_from_prompts.py` runs first, then `quarto render report.qmd --to docx` (or `--to html`) handles the embedding.
