# AAN Deck Style Notes — reverse-engineering record

Measured from the committed hand-built AAN briefing decks with `python-pptx`
1.0.2 on 2026-07-08. These are the exact numbers the canonical generator
(the host repo's `generators/aan_deck.py`) reproduces.

Decks introspected:

| Deck | Size | Shapes | Pics | Tables | Notes | Font |
|---|---|---|---|---|---|---|
| `Book_11_FedAAN_Vulnerability_Management.pptx` | 10.0 × 5.625 in | 462 (18.5/slide) | 0 | 4 | 25/25, avg 1953 ch | Arial + Consolas |
| `Book_10_FedAAN_Privileged_Access_Management.pptx` | 10.0 × 5.625 in | 518 (19.9/slide) | 0 | 2 | 26/26, avg 1910 ch | Arial |
| `Book_00_FedAAN_Executive_Summary.pptx` | 13.333 × 7.5 in | 183 (8.3/slide) | 19 | 1 | 22/22, avg 1754 ch | Calibri + Cambria |

**Book_10 / Book_11 are the canonical DNA** — native-shape composition,
Arial, exact house palette, zero embedded pictures. Book_00 is an older
outlier format (16:9 widescreen 13.333", Calibri, rasterized figures) and is
**not** the target. The generator targets the Book_10/Book_11 DNA.

## Slide size

- Width EMU `9144000` = **10.0 in**; height EMU `5143500` = **5.625 in** (16:9).

## Palette (exact hex, measured frequency)

INK colors (never used as a slide background):

| Role | Hex | Notes |
|---|---|---|
| Navy | `1F3A5F` | primary ink, titles, header-row fill |
| Teal | `1A9E8F` | accent / affirmative |
| Amber | `D4860B` | active-step ring, caution |
| Red | `C0392B` | failure / urgency |
| Body ink | `1E293B` | slate near-black body text (most frequent font color) |
| Muted | `5B6B7C` | secondary text, footers |
| Amber-dark | `8A6210` | amber text sitting on an amber tint |
| Border | `C9D4E0` | card / panel border, "upcoming" step dot |

Backgrounds / tints (white base, pastel tints for panels — never dark):

| Role | Hex |
|---|---|
| White (slide bg + cards) | `FFFFFF` |
| Navy tint (thesis/callout banner) | `EDF3F9` |
| Neutral panel | `F3F5F8` |
| Teal tint | `E6F5F2` |
| Amber tint (disclaimer / caution) | `FBF3E4` |
| Red tint (failure) | `F9EAE8` |

Accent → (ink, tint) map used by the generator:
`navy→(1F3A5F,EDF3F9)`, `teal→(1A9E8F,E6F5F2)`, `amber→(D4860B,FBF3E4)`,
`red→(C0392B,F9EAE8)`, `neutral→(5B6B7C,F3F5F8)`.

## Typography

- Primary font **Arial**; **Consolas** for code / mono fragments.
- Observed sizes (pt): title-slide title ~30, section/slide title **21–22**,
  kicker/eyebrow **11–13**, card titles **11–13**, body **9–10.5**, small
  chip labels **8–9.5**, footer/page-number **8**.

## Standard slide chrome (content, table, build slides)

- **Kicker / eyebrow** (ALL-CAPS): rect `L=0.55 T=0.28 W=9.0 H=0.30`, teal, ~12 pt bold.
- **Title**: rect `L=0.55 T=0.56 W=8.9 H=0.62`, navy, ~22 pt bold.
- **Footer**: rect `L=0.55 T=5.32 W=8.0 H=0.24`, muted, 8 pt.
- **Page number**: rect `L=9.20 T=5.32 W=0.35 H=0.24`, muted, 8 pt, right.
- Content region runs ~`T=1.35` → `T=5.20`.
- Every slide sets a solid **white** background.

## Title slide (slide 0)

- Series kicker `L=0.65 T=0.72 W=8.7 H=0.32` (teal).
- Big title `L=0.65 T=1.08 W=8.7 H=0.85` (navy, ~30 pt bold).
- Subtitle `L=0.65 T=1.98 W=8.5 H=0.70` (muted/ink).
- **Journey strip**: N mini step-cards at `T=3.0`, each `W≈2.1 H=0.95` rounded,
  white fill, `C9D4E0` border, a `0.14` colored dot (rotating palette), a label;
  thin `5B6B7C` connectors between them.
- **Date Code** line `L=0.65 T=4.52 W=8.7 H=0.26` — `Date Code: YYYY-MM-DD HH:MM ET`.
- **Draft disclaimer**: rounded rect `L=0.65 T=4.85 W=8.7 H=0.52`, fill `FBF3E4` (amber tint).

## Cards / panels (content slides)

- Numbered card: rounded rect `W≈4.42 H=1.52` (2×2 grid) or column `W≈2.94 H=2.7`
  (3-up), white or tinted fill, `C9D4E0` border. Each carries an oval **dot**
  (`0.32`, accent-colored) with a white bold **number** overlaid, a **card title**
  (~12 pt navy bold), and a **body** (~9 pt ink). 3-up columns add a bottom
  **status pill** (rounded rect, accent tint).
- **Callout / thesis banner**: full-width rounded rect (`W=9.0`), navy tint
  `EDF3F9` (or accent tint), ink text — anchors the slide's one-sentence point.

## Build sequence (progressive reveal) — slides 10–13 in Book_11

One slide **per active step**. Geometry per step slide:

- **Step strip** across the top at `T=1.42`, chips `H=0.85`, chip width
  `(9.0 − (N−1)·0.32)/N` starting at `L=0.55`, pitch = chipW + 0.32 gap.
- **Chip states**:
  - *completed* (`i < active`): white fill, accent-colored `0.14` dot.
  - *active* (`i == active`): white fill **plus an amber ring** — a rounded rect
    behind it, inflated `0.06` on each side (`W+0.12 H+0.12`), fill white,
    line `D4860B` at `0.035 in` (~2.5 pt); dot accent-colored.
  - *upcoming* (`i > active`): grey `F3F5F8` fill, grey `C9D4E0` dot, muted text.
  - Chip text: line 1 `"{n} — {label}"` (~9.5 pt bold), line 2 optional sub (~8 pt muted).
- **Connectors** between chips: those with index `< active` are dark `1E293B`
  (path traversed); the rest are grey `C9D4E0`.
- **Detail panel**: rounded rect `L=0.55 T=2.55 W=9.0 H=2.6`, fill = active
  step's accent **tint**, `C9D4E0` border; inner text `L=0.85 T=2.75 W=8.45 H=2.25`,
  ~11 pt ink prose. The panel deepens per step.

## Native table style (slide 7)

- Header row: fill **navy `1F3A5F`**, text white, **10 pt bold**.
- Body rows: **9 pt**; first column bold navy `1F3A5F`; other cells ink `1E293B`.
- Rows may be tinted per priority/severity using the accent tints
  (e.g. red-tint `F9EAE8` for P0/P1).
- Table sits at `L=0.55 T=1.4 W=9.0`; a callout banner often follows below.

## Speaker notes

- **Every** slide carries full presenter prose (Book_11: 25/25, ~1000–2800 ch).
- Slides that state vendor claims end notes with a single line:
  `Vendor sources: <url> | <url> | host repo: <path>`.
- The generator keeps the URL link-map in one `SRC` constant (deck spec may
  extend it via a `sources:` map); `vendor_sources` entries are either full
  URLs or `SRC` keys resolved against the merged map.

## No dark slides

No slide uses a dark or black background or a dark title/closing slide — the
last content slide ("WHERE THIS LEAVES US") is a normal white takeaways slide.
The generator enforces white backgrounds on every slide and offers a white
`closing` slide type, not a dark one.
