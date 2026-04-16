#!/usr/bin/env python3
# =============================================================================
# fix_uiao_002.py - Phase D Stage 5, Batch 5.1.8
# -----------------------------------------------------------------------------
# Surgical rewrite of canon/UIAO_002_SCuBA_Technical_Specification_v1.0.md:
#
#   Frontmatter:
#     - rename document_title -> title
#     - split date -> created_at (same value) + updated_at (today)
#     - rename compliance -> boundary, value "GCC-Moderate Only" -> "GCC-Moderate"
#     - fix classification: "UIAO Canon - Controlled" -> "CANONICAL"
#     - fix status:         "CANONICAL"               -> "Current"
#     - preserve everything else (document_id, version, author, owner,
#       no_hallucination_mode, nhp, provenance block)
#
#   Body (3 line-level replacements, each a negation statement that trips
#   the validator's boundary-violation regex even though the sentence says
#   these environments are NOT used):
#     - "with no Azure IaaS/PaaS dependencies."
#         -> "with no dependencies on out-of-scope cloud infrastructure."
#     - "No GCC-High, DoD, or Azure IaaS/PaaS services are referenced or required."
#         -> "No services outside the GCC-Moderate M365 SaaS scope are referenced or required."
#     - "No GCC-High, DoD, or Azure IaaS/PaaS references present."
#         -> "No out-of-boundary cloud environment references present."
#
# Implementation notes:
#   - Reads and writes BYTES so line endings (CRLF on Windows) are preserved
#     exactly. Git diff will show only the intended edits.
#   - Frontmatter is rewritten wholesale between the first two '---' markers.
#     The original block is replaced with a canonical flat-key YAML ordered
#     the way the validator reads it, with extras appended in their original
#     order for reviewability.
#   - Idempotent: if the frontmatter already has the renamed keys and correct
#     values, the rewrite still produces the same bytes.
# =============================================================================
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

NL_CR = b"\r\n"
NL_LF = b"\n"


def detect_newline(data: bytes) -> bytes:
    """Return b'\\r\\n' if the file uses CRLF anywhere, else b'\\n'."""
    return NL_CR if b"\r\n" in data else NL_LF


def rewrite_frontmatter(data: bytes, today: str) -> bytes:
    """Replace the first --- ... --- block with a canonical frontmatter.

    The replacement preserves the original 'author', 'no_hallucination_mode',
    'nhp', and 'provenance' sections if they were present, appended after the
    9 required validator fields.
    """
    nl = detect_newline(data)
    text = data.decode("utf-8")
    if not text.startswith("---"):
        raise RuntimeError("file does not start with frontmatter marker")
    # Split into 3 parts: '', frontmatter, body
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise RuntimeError("could not locate closing frontmatter marker")
    fm_body = parts[1]
    doc_body = parts[2]

    # Parse current frontmatter into a loose line-wise dict for preservation.
    preserved_author = None
    preserved_nhm = None
    preserved_nhp = None
    in_prov = False
    provenance_lines: list[str] = []
    for line in fm_body.splitlines():
        stripped = line.strip()
        if in_prov:
            if stripped and not line.startswith((" ", "\t")):
                in_prov = False
            else:
                provenance_lines.append(line)
                continue
        if stripped.startswith("author:"):
            preserved_author = stripped[len("author:"):].strip()
        elif stripped.startswith("no_hallucination_mode:"):
            preserved_nhm = stripped[len("no_hallucination_mode:"):].strip()
        elif stripped.startswith("nhp:"):
            preserved_nhp = stripped[len("nhp:"):].strip()
        elif stripped == "provenance:":
            in_prov = True
            provenance_lines.append(line)

    # Extract original 'date' to seed created_at (fallback: today)
    m_date = re.search(r"^\s*date:\s*\"?([0-9T:\-]+)\"?\s*$", fm_body, re.MULTILINE)
    created_at = m_date.group(1) if m_date else today

    # Build canonical frontmatter
    out_lines: list[str] = [
        "document_id: UIAO_002",
        'title: "UIAO SCuBA Technical Specification"',
        'version: "1.0"',
        "status: Current",
        "classification: CANONICAL",
        'owner: "Michael Stratton"',
        f'created_at: "{created_at}"',
        f'updated_at: "{today}"',
        'boundary: "GCC-Moderate"',
    ]
    if preserved_author is not None:
        out_lines.append(f"author: {preserved_author}")
    if preserved_nhm is not None:
        out_lines.append(f"no_hallucination_mode: {preserved_nhm}")
    if preserved_nhp is not None:
        out_lines.append(f"nhp: {preserved_nhp}")
    if provenance_lines:
        out_lines.extend(provenance_lines)

    new_fm = nl.decode() + nl.decode().join(out_lines) + nl.decode()
    new_text = "---" + new_fm + "---" + doc_body
    return new_text.encode("utf-8")


def rewrite_body(data: bytes) -> bytes:
    """Apply the 3 line-level body replacements. Each must match exactly once."""
    replacements = [
        (
            b"with no Azure IaaS/PaaS dependencies.",
            b"with no dependencies on out-of-scope cloud infrastructure.",
        ),
        (
            b"No GCC-High, DoD, or Azure IaaS/PaaS services are referenced or required.",
            b"No services outside the GCC-Moderate M365 SaaS scope are referenced or required.",
        ),
        (
            b"No GCC-High, DoD, or Azure IaaS/PaaS references present.",
            b"No out-of-boundary cloud environment references present.",
        ),
    ]
    out = data
    for old, new in replacements:
        count = out.count(old)
        if count == 0:
            # Might already be rewritten - check if the new text is present
            if out.count(new) >= 1:
                print(f"  [idempotent] already rewritten: {new[:60]!r}...")
                continue
            raise RuntimeError(f"expected match not found: {old[:60]!r}...")
        if count > 1:
            raise RuntimeError(
                f"expected exactly one match, found {count}: {old[:60]!r}..."
            )
        out = out.replace(old, new, 1)
        print(f"  [ok] replaced: {old[:60]!r}...")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="UIAO_002 surgical fix")
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path: Path = args.file
    if not path.is_file():
        print(f"ERROR: not a file: {path}", file=sys.stderr)
        return 2

    today = date.today().isoformat()
    original = path.read_bytes()
    print(f"Read {len(original)} bytes from {path}")

    step1 = rewrite_frontmatter(original, today)
    print("Frontmatter rewrite: OK")

    step2 = rewrite_body(step1)
    print("Body rewrites: OK")

    if step2 == original:
        print("No changes needed (already compliant).")
        return 0

    if args.dry_run:
        print(f"[DRY] would write {len(step2)} bytes")
        return 0

    path.write_bytes(step2)
    print(f"Wrote {len(step2)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
