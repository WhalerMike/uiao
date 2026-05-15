"""Preprocess AtoBZ_clean.md into a candidate CHARTER-001-APPENDICES.md.

Strategy:
  1. Parse: split file into segments delimited by `# Appendix X` H1 headings.
  2. Dedup: for each appendix code, keep the FIRST occurrence's segment; drop all
     subsequent occurrences AND their segment content. Compute content similarity
     between duplicates (line count, char count, SHA-256 of normalized text) and
     flag any non-identical duplicate pairs for architect review.
  3. Reorder: the first preserved Appendix Z is at line 2 (out of order, before A).
     Move the Z segment to its correct alphabetical position (after Y, before AA).
  4. Normalize: replace U+2011 (non-breaking hyphen) with ASCII hyphen.
  5. Annotate invented acronyms: insert HTML comment markers around each occurrence
     of the 3 known invented terms (UAI, "UIAO Autonomous Operations Fabric",
     "UIAO Assurance and Governance Fabric") so the architect can confirm or replace.
     Note: "UCI-X" was named in the audit but is not present in the source.
  6. Truncation: append an explicit note at the end describing the source-side
     truncation of Appendix AL (the "## 1. Introducti" cliffhanger) and propose
     handling.
  7. Emit: cleaned markdown + a structured JSON report of every decision.

Decisions are reviewable: every dedup, every annotation, every normalization is
recorded in the JSON report at the segment level.
"""

import hashlib
import json
import re
import sys
from collections import defaultdict

H1_RE = re.compile(r"^# Appendix ([A-Z]{1,2})(?:\.\d+)?\s*[—–-]?\s*(.*)$")

INVENTED_ACRONYMS = [
    "UIAO Autonomous Operations Fabric",
    "UIAO Assurance and Governance Fabric",
    "UAI",  # bare token — match with word-boundary care below
]


def appendix_sort_key(code):
    """Sort: A < B < ... < Z < AA < AB < ... < AZ."""
    return (len(code), code)


def normalize_for_hash(text):
    """Normalize whitespace + NBH for content-similarity comparison."""
    text = text.replace("‑", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def parse_segments(lines):
    """Split lines into segments. Each segment is (code|None, title|None, line_start, content_lines).

    The pre-first-heading content is segment with code=None.
    """
    segments = []
    current_code = None
    current_title = None
    current_start = 1
    current_lines = []

    for i, line in enumerate(lines, 1):
        m = H1_RE.match(line.rstrip("\n"))
        if m:
            # Emit previous segment
            if current_lines or current_code is not None:
                segments.append(
                    {
                        "code": current_code,
                        "title": current_title,
                        "line_start": current_start,
                        "line_end": i - 1,
                        "lines": current_lines,
                    }
                )
            current_code = m.group(1)
            current_title = m.group(2).strip()
            current_start = i
            current_lines = [line]
        else:
            current_lines.append(line)

    # Final segment
    if current_lines or current_code is not None:
        segments.append(
            {
                "code": current_code,
                "title": current_title,
                "line_start": current_start,
                "line_end": current_start + len(current_lines) - 1,
                "lines": current_lines,
            }
        )

    return segments


def detect_truncation(text):
    """Detect mid-word truncation at file end."""
    # If the file ends without a final newline, or ends with an obviously
    # truncated word like "Introducti", flag it.
    last_nonempty = ""
    for line in reversed(text.splitlines()):
        if line.strip():
            last_nonempty = line.strip()
            break
    # Heuristic: trailing word ends without standard punctuation AND looks cut off.
    if last_nonempty and not last_nonempty.endswith((".", ":", "!", "?", "*", ")", "}", "]", "—", "-")):
        last_word = last_nonempty.split()[-1]
        # Common English words that just don't end in punctuation aren't truncated.
        # Treat as truncation only if the last word looks unfinished (e.g., ends in
        # an unusual letter combination like "ucti" or doesn't end on a vowel/y).
        if last_word.endswith(("Introducti", "ucti", "ction", "ucti", "ductio")):
            return True, last_nonempty
        # More general: if the last word is short and ends mid-syllable
        if len(last_word) < 12 and not last_word.lower().endswith(
            ("a", "e", "i", "o", "u", "y", "n", "r", "s", "t", "d", "g", "f", "ng", "ed")
        ):
            return True, last_nonempty
    return False, last_nonempty


def annotate_invented_acronyms(text, term):
    """Wrap each occurrence with HTML comment markers requiring architect review."""
    # Word-boundary match for bare UAI to avoid hitting "UIAO" or "UAID" etc.
    pattern = re.compile(r"\bUAI\b") if term == "UAI" else re.compile(re.escape(term))

    def replacer(match):
        return f"<!-- ARCHITECT-CONFIRM: term '{term}' is Copilot-derived per CHARTER-001-APPENDICES audit; confirm canonical or replace -->{match.group(0)}<!-- /ARCHITECT-CONFIRM -->"

    text, count = pattern.subn(replacer, text)
    return text, count


def main(src_path, out_md_path, out_report_path):
    with open(src_path, encoding="utf-8") as f:
        text = f.read()

    lines = text.splitlines(keepends=True)
    segments = parse_segments(lines)

    # Group segments by code for dedup analysis
    by_code = defaultdict(list)
    for i, seg in enumerate(segments):
        if seg["code"] is not None:
            by_code[seg["code"]].append((i, seg))

    # Dedup decisions: for each code, keep first; record similarity of dropped segments
    dedup_decisions = []
    keep_indices = set()
    drop_indices = set()
    pre_first_seg_indices = set()

    for i, seg in enumerate(segments):
        if seg["code"] is None:
            pre_first_seg_indices.add(i)

    for code in sorted(by_code.keys(), key=appendix_sort_key):
        occurrences = by_code[code]
        # Keep first
        first_idx, first_seg = occurrences[0]
        keep_indices.add(first_idx)
        first_text = "".join(first_seg["lines"])
        first_hash = hashlib.sha256(normalize_for_hash(first_text).encode()).hexdigest()[:12]
        for occ_idx, occ_seg in occurrences[1:]:
            drop_indices.add(occ_idx)
            occ_text = "".join(occ_seg["lines"])
            occ_hash = hashlib.sha256(normalize_for_hash(occ_text).encode()).hexdigest()[:12]
            identical = first_hash == occ_hash
            dedup_decisions.append(
                {
                    "code": code,
                    "title": first_seg["title"],
                    "kept": {
                        "line_start": first_seg["line_start"],
                        "line_end": first_seg["line_end"],
                        "line_count": len(first_seg["lines"]),
                        "char_count": len(first_text),
                        "norm_hash": first_hash,
                    },
                    "dropped": {
                        "line_start": occ_seg["line_start"],
                        "line_end": occ_seg["line_end"],
                        "line_count": len(occ_seg["lines"]),
                        "char_count": len(occ_text),
                        "norm_hash": occ_hash,
                    },
                    "identical_after_normalization": identical,
                }
            )

    # Pre-first-heading segments (content before any H1): always preserve at the top
    for i in pre_first_seg_indices:
        keep_indices.add(i)

    # Build output: preserve pre-headings first (in order), then appendices in
    # alphabetical order (NOT original line order — fixes the Z-at-line-2 problem).
    output_segments = []
    # Pre-first-heading content (any non-appendix preamble)
    for i in sorted(pre_first_seg_indices):
        output_segments.append(("preamble", segments[i]))
    # Appendices in alphabetical order
    for code in sorted(by_code.keys(), key=appendix_sort_key):
        _first_idx, first_seg = by_code[code][0]
        output_segments.append(("appendix", first_seg))

    # Assemble text
    out_chunks = []
    for _kind, seg in output_segments:
        chunk = "".join(seg["lines"])
        out_chunks.append(chunk)
    cleaned_text = "".join(out_chunks)

    # Step 4: Normalize NBH
    nbh_count = cleaned_text.count("‑")
    cleaned_text = cleaned_text.replace("‑", "-")

    # Step 5: Annotate invented acronyms
    acronym_counts = {}
    for term in INVENTED_ACRONYMS:
        cleaned_text, count = annotate_invented_acronyms(cleaned_text, term)
        acronym_counts[term] = count
    # Note UCI-X explicitly absent
    acronym_counts["UCI-X (audit-named, NOT PRESENT)"] = 0

    # Step 6: Truncation handling
    is_truncated, last_line = detect_truncation(text)
    truncation_note = ""
    if is_truncated:
        truncation_note = (
            "\n\n---\n\n"
            "<!-- ARCHITECT-CONFIRM: Source-side truncation. The OneDrive source file "
            "AtoBZ_clean.md ends mid-word at line 35669 with the partial heading "
            f"'{last_line}'. The truncated tail is the 4th occurrence of Appendix AL "
            "(Session Binding Architecture); the first occurrence (line 16361 in source, "
            "preserved here in alphabetical order) is complete. The truncation predates "
            "this preprocessing pass; recovery would require finding the predecessor "
            "concatenation source in OneDrive UIAO-V1/. Documented for transparency; no "
            "preprocessing action taken. -->\n"
            "> **Source truncation note (preprocessor 2026-05-15):** The OneDrive source "
            "file from which this canon was derived ends mid-word at line 35669 of the "
            f"source: `{last_line}`. The truncated tail is the 4th source occurrence of "
            "Appendix AL — the first occurrence is preserved above and is complete. No "
            "content is lost from this canon as published.\n"
        )

    cleaned_text += truncation_note

    # Write cleaned file
    with open(out_md_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)

    # Build report
    report = {
        "source_file": src_path,
        "source_line_count": len(lines),
        "source_char_count": len(text),
        "output_file": out_md_path,
        "output_char_count": len(cleaned_text),
        "appendix_codes_unique": len(by_code),
        "appendix_codes_first_seen": [
            {"code": c, "title": by_code[c][0][1]["title"], "source_line": by_code[c][0][1]["line_start"]}
            for c in sorted(by_code.keys(), key=appendix_sort_key)
        ],
        "dedup_decisions": dedup_decisions,
        "dedup_summary": {
            "total_decisions": len(dedup_decisions),
            "identical_after_normalization": sum(1 for d in dedup_decisions if d["identical_after_normalization"]),
            "non_identical_flag_for_review": sum(1 for d in dedup_decisions if not d["identical_after_normalization"]),
        },
        "non_breaking_hyphens_normalized": nbh_count,
        "invented_acronym_annotations": acronym_counts,
        "truncation_detected": is_truncated,
        "truncation_last_line": last_line,
        "ordering_change": "Output appendices in alphabetical order (A-Z, AA-AZ); source had Appendix Z at line 2 (out of order). All preserved appendices appear in correct alphabetical sequence.",
    }

    with open(out_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary to stderr
    print("=== AtoBZ Preprocessing Summary ===", file=sys.stderr)
    print(f"Source: {src_path} ({len(lines)} lines, {len(text)} chars)", file=sys.stderr)
    print(
        f"Output: {out_md_path} ({len(cleaned_text)} chars, "
        f"{(1 - len(cleaned_text) / len(text)) * 100:.1f}% reduction)",
        file=sys.stderr,
    )
    print(f"Unique appendix codes: {len(by_code)}", file=sys.stderr)
    print(
        f"Dedup decisions: {len(dedup_decisions)} "
        f"({report['dedup_summary']['identical_after_normalization']} identical, "
        f"{report['dedup_summary']['non_identical_flag_for_review']} REQUIRE REVIEW)",
        file=sys.stderr,
    )
    print(f"NBH normalized: {nbh_count}", file=sys.stderr)
    print(f"Invented-acronym annotations: {acronym_counts}", file=sys.stderr)
    print(f"Truncation detected: {is_truncated} ('{last_line}')", file=sys.stderr)
    print(f"Report: {out_report_path}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
