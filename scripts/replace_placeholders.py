#!/usr/bin/env python3
"""Replace [IMAGE-NN: ...] / [DIAGRAM-NN: ...] / [FIGURE-NN: ...] placeholders
in .qmd/.md source files with rendered markdown image references.

Reads the manifest JSON written by generate_images.py to build the
mapping of (document, placeholder_id) -> image filename, then performs
in-place substitution in each source document.

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


def truncate_alt(body, maxlen=80):
    alt = body.strip().split(".")[0].strip()
    alt = re.sub(r"\s+", " ", alt)
    if len(alt) > maxlen:
        alt = alt[:maxlen].rsplit(" ", 1)[0] + "..."
    return alt


def main():
    parser = argparse.ArgumentParser(description="Replace image placeholders with rendered PNGs.")
    parser.add_argument("--dry-run", action="store_true", help="Preview replacements without writing.")
    args = parser.parse_args()

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
            alt_text = truncate_alt(body)
            replacement = "![" + alt_text + "](images/" + img_filename + ")"

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
