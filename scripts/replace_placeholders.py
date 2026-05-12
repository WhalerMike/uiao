#!/usr/bin/env python3
"""Replace [IMAGE-NN: ...] / [DIAGRAM-NN: ...] / [FIGURE-NN: ...] placeholders
in .qmd/.md source files with rendered Quarto figure references.

Reads the manifest JSON written by generate_images.py to build the
mapping of (document, placeholder_id) -> image filename, then performs
in-place substitution in each source document.

Emitted syntax (Quarto figure with caption, accessible alt text, stable
cross-reference label, and explicit width):

    ![Customer-facing caption](images/foo.png){#fig-doc-stem-image-01 \\
        fig-alt="Full visual description for screen readers" width="85%"}

Caption is the first sentence of the placeholder body, with any leading
"Figure N.N - " prefix stripped so Quarto's auto-numbering produces a
clean "Figure 1: ..." render. fig-alt carries the remaining visual
description. fig-id is derived from the document stem + placeholder id
and is stable across re-runs.

Usage (run from repo root):
    python scripts/replace_placeholders.py              # live replacement
    python scripts/replace_placeholders.py --dry-run    # preview only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(os.environ.get("UIAO_REPO_ROOT") or SCRIPT_DIR.parent)
MANIFEST_PATH = SCRIPT_DIR / "images" / ".image-manifest.json"

PLACEHOLDER_RE = re.compile(r"\[(?P<kind>IMAGE|DIAGRAM|FIGURE)-(?P<num>\d{2,3}):\s*(?P<body>[^\]]+)\]", re.MULTILINE)


def _fenced_code_ranges(text):
    ranges = []
    offset = 0
    in_fence = False
    fence_start = 0
    for line in text.split("\n"):
        line_bytes = len(line) + 1
        stripped = line.lstrip()
        if stripped.startswith("```"):
            if not in_fence:
                fence_start = offset
                in_fence = True
            else:
                ranges.append((fence_start, offset + line_bytes))
                in_fence = False
        offset += line_bytes
    if in_fence:
        ranges.append((fence_start, len(text)))
    return ranges


def in_fence(offset, ranges):
    for start, end in ranges:
        if start <= offset < end:
            return True
    return False


FIGURE_PREFIX_RE = re.compile(r"^\s*Figure\s+\d+(?:\.\d+)?\s*[—–\-:]\s*", re.IGNORECASE)


def strip_figure_prefix(text):
    """Remove a leading 'Figure N' or 'Figure N.N - ' prefix so Quarto's
    auto-numbering renders cleanly without 'Figure 1: Figure 0.1 - ...'."""
    return FIGURE_PREFIX_RE.sub("", text).strip()


def split_caption_alt(body, caption_max=220):
    """Split a placeholder body into (caption, alt_text).

    Caption: the first sentence of the body, used as the visible figure
    caption. Capped at caption_max chars to avoid runaway captions.
    Alt text: everything after the first sentence, used as fig-alt for
    screen readers. Falls back to the caption when no remainder exists.
    """
    body = re.sub(r"\s+", " ", body.strip())
    m = re.search(r"\.\s+", body)
    if m:
        caption = body[: m.start()].strip()
        rest = body[m.end() :].strip()
    else:
        caption, rest = body, ""
    if len(caption) > caption_max:
        caption = caption[:caption_max].rsplit(" ", 1)[0] + "..."
    if not rest:
        rest = caption
    return caption, rest


def make_fig_id(doc_path, placeholder_id):
    """Stable fig-id from document stem + placeholder id.

    Example: docs/.../aodim-architecture.qmd + IMAGE-01 -> fig-aodim-architecture-image-01.
    The id is lowercased and slug-safe. Collisions between identically-named
    files in different directories are possible but rare; Quarto will warn at
    render time if they occur.
    """
    stem = re.sub(r"[^a-z0-9]+", "-", doc_path.stem.lower()).strip("-")
    pid = re.sub(r"[^a-z0-9]+", "-", placeholder_id.lower()).strip("-")
    return f"fig-{stem}-{pid}"


def escape_md_brackets(text):
    """Escape ] in alt/caption text so the ![...] syntax isn't broken."""
    return text.replace("\\", "\\\\").replace("]", "\\]")


def escape_attr(text):
    """Escape a string for use inside a Quarto attribute value."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


BASIC_IMG_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<path>images/[^)]+\.(?:png|jpg|jpeg|svg))\)(?!\{)",
    re.IGNORECASE,
)
PIPELINE_NAMED_RE = re.compile(r"^.+?-image-(?P<num>\d+)-", re.IGNORECASE)

# Pages that document the pipeline itself contain literal example syntax
# (![alt](images/foo.png), ![caption](images/<filename>.png)) that must
# NOT be auto-upgraded — doing so would corrupt the docs that teach users
# what the unmodified syntax looks like.
UPGRADE_EXCLUSIONS = frozenset(
    {
        "docs/academy/document-generation-guide.qmd",
        "docs/academy/image-pipeline-guide.qmd",
    }
)


def _fallback_placeholder_id(png_path):
    """Recover IMAGE-NN from pipeline-named PNGs; fall back to a short slug."""
    m = PIPELINE_NAMED_RE.match(png_path.stem)
    if m:
        return f"IMAGE-{int(m.group('num')):02d}"
    # Stable per-png fallback that won't collide with pipeline ids.
    slug = re.sub(r"[^a-z0-9]+", "-", png_path.stem.lower()).strip("-")[:40]
    return f"LEGACY-{slug}"


def upgrade_existing_lines(repo_root, dry_run):
    """Codemod: walk docs/**/*.qmd and upgrade existing
    ![alt](images/*.png) lines to full Quarto figure syntax.

    Source of truth for fig-id is the sibling .png.json sidecar (which
    carries placeholder_id and document). When the sidecar is missing,
    falls back to parsing IMAGE-NN out of the pipeline-named PNG filename.

    Skips refs that already have a {} attribute block immediately after,
    and skips matches inside fenced code blocks.
    """
    docs_root = repo_root / "docs"
    qmd_files = sorted(docs_root.rglob("*.qmd"))

    upgraded_total = 0
    files_modified = 0

    for q in qmd_files:
        try:
            rel_check = str(q.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            rel_check = str(q).replace("\\", "/")
        if rel_check in UPGRADE_EXCLUSIONS:
            continue

        text = q.read_text(encoding="utf-8")
        fence_ranges = _fenced_code_ranges(text)
        new_text = text
        upgraded_in_file = 0

        # Reverse so earlier offsets stay valid as we splice.
        for m in reversed(list(BASIC_IMG_RE.finditer(text))):
            if in_fence(m.start(), fence_ranges):
                continue
            alt = m.group("alt").strip()
            rel_path = m.group("path")
            if not alt:
                # No alt = nothing usable as caption; skip rather than guess.
                continue
            if "<" in rel_path or ">" in rel_path:
                # Template marker in path (e.g., images/<filename>.png) — skip.
                continue

            png_path = (q.parent / rel_path).resolve()
            sidecar_path = png_path.with_suffix(png_path.suffix + ".json")
            placeholder_id = None
            if sidecar_path.exists():
                try:
                    with open(sidecar_path, encoding="utf-8") as f:
                        sidecar = json.load(f)
                    placeholder_id = sidecar.get("placeholder_id")
                except (OSError, json.JSONDecodeError):
                    pass
            if not placeholder_id:
                placeholder_id = _fallback_placeholder_id(png_path)

            caption = strip_figure_prefix(alt)
            fig_id = make_fig_id(q, placeholder_id)
            replacement = (
                f"![{escape_md_brackets(caption)}]({rel_path})"
                f'{{#{fig_id} fig-alt="{escape_attr(caption)}" width="85%"}}'
            )

            try:
                rel = q.relative_to(repo_root)
            except ValueError:
                rel = q

            if dry_run:
                if upgraded_in_file == 0:
                    print(f"  -> {rel}")
                print(f"    - {m.group(0)[:90]}")
                print(f"    + {replacement[:140]}")
            else:
                new_text = new_text[: m.start()] + replacement + new_text[m.end() :]
            upgraded_in_file += 1

        if upgraded_in_file > 0:
            try:
                rel = q.relative_to(repo_root)
            except ValueError:
                rel = q
            if not dry_run:
                q.write_text(new_text, encoding="utf-8")
                print(f"  OK {rel}: {upgraded_in_file} ref(s) upgraded")
            upgraded_total += upgraded_in_file
            files_modified += 1

    action = "would upgrade" if dry_run else "upgraded"
    print("\n=== Upgrade summary ===")
    print(f"Files modified:       {files_modified}")
    print(f"References {action}: {upgraded_total}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Replace image placeholders with rendered PNGs.")
    parser.add_argument("--dry-run", action="store_true", help="Preview replacements without writing.")
    parser.add_argument(
        "--upgrade-existing",
        action="store_true",
        help=(
            "Codemod mode: walk docs/**/*.qmd and rewrite existing basic "
            "![alt](images/*.png) lines to full Quarto figure syntax. "
            "Independent of the manifest — uses sibling .png.json sidecars."
        ),
    )
    args = parser.parse_args()

    if args.upgrade_existing:
        return upgrade_existing_lines(REPO_ROOT, args.dry_run)

    if not MANIFEST_PATH.exists():
        print("Error: Manifest not found at " + str(MANIFEST_PATH), file=sys.stderr)
        print("Run generate_images.py first.", file=sys.stderr)
        return 1

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    doc_local = manifest.get("doc_local", [])
    if not doc_local:
        print("No doc-local entries in manifest. Nothing to replace.")
        return 0

    lookup = {}
    for entry in doc_local:
        doc_rel = entry.get("document")
        pid = entry.get("placeholder_id")
        img_rel = entry.get("image_file")
        if not all([doc_rel, pid, img_rel]):
            continue
        doc_path = str((REPO_ROOT / doc_rel).resolve())
        img_filename = Path(img_rel).name
        lookup[(doc_path, pid)] = img_filename

    print("Loaded " + str(len(lookup)) + " image mapping(s) from manifest.\n")

    docs = {}
    for (doc_path, pid), _ in lookup.items():
        docs.setdefault(doc_path, []).append(pid)

    replaced_total = 0
    files_modified = 0

    for doc_path_str, _pids in sorted(docs.items()):
        doc_path = Path(doc_path_str)
        if not doc_path.exists():
            print("  SKIP (missing): " + str(doc_path))
            continue

        text = doc_path.read_text(encoding="utf-8")
        fence_ranges = _fenced_code_ranges(text)
        new_text = text
        replaced_in_file = 0

        matches = list(PLACEHOLDER_RE.finditer(text))
        for m in reversed(matches):
            if in_fence(m.start(), fence_ranges):
                continue

            kind = m.group("kind")
            num = m.group("num")
            body = m.group("body").strip()

            if body.upper() == "AUTO" or body.upper().startswith("UIAO-FIG-"):
                continue

            pid = kind + "-" + num
            key = (doc_path_str, pid)

            if key not in lookup:
                continue

            img_filename = lookup[key]
            caption, alt_text = split_caption_alt(body)
            caption = strip_figure_prefix(caption)
            fig_id = make_fig_id(doc_path, pid)
            replacement = (
                f"![{escape_md_brackets(caption)}](images/{img_filename})"
                f'{{#{fig_id} fig-alt="{escape_attr(alt_text)}" width="85%"}}'
            )

            if args.dry_run:
                try:
                    rel = doc_path.relative_to(REPO_ROOT)
                except ValueError:
                    rel = doc_path
                print("  [dry-run] " + str(rel) + ":" + pid)
                print("    - " + m.group()[:80] + "...")
                print("    + " + replacement)
                replaced_in_file += 1
            else:
                new_text = new_text[: m.start()] + replacement + new_text[m.end() :]
                replaced_in_file += 1

        if replaced_in_file > 0:
            try:
                rel = doc_path.relative_to(REPO_ROOT)
            except ValueError:
                rel = doc_path

            if not args.dry_run:
                doc_path.write_text(new_text, encoding="utf-8")
                print("  OK " + str(rel) + ": " + str(replaced_in_file) + " placeholder(s) replaced")
            else:
                print("  -> " + str(rel) + ": " + str(replaced_in_file) + " placeholder(s) would be replaced\n")

            replaced_total += replaced_in_file
            files_modified += 1

    print("\n=== Summary ===")
    action = "would replace" if args.dry_run else "replaced"
    print("Files modified:       " + str(files_modified))
    print("Placeholders " + action + ": " + str(replaced_total))

    return 0


if __name__ == "__main__":
    sys.exit(main())
