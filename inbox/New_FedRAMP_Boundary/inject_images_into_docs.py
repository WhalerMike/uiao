#!/usr/bin/env python3
"""
inject_images_into_docs.py
==========================
Finds `[[IMG_PLACEHOLDER:<id>]]` markers in DOCX files and replaces each with
the corresponding PNG from the images/ folder, embedded inline.

Approach
--------
1. Unzip the docx into a temp directory.
2. Walk word/document.xml.
3. For each placeholder paragraph (a w:p containing the marker run), replace
   the entire surrounding placeholder TABLE with two paragraphs: a centered
   image paragraph (referencing a new rId) followed by a centered caption.
4. Add the new image bytes under word/media/, register them in
   word/_rels/document.xml.rels, and add the PNG content type to
   [Content_Types].xml if not already present.
5. Re-zip into the output docx.

Caption text is preserved from the placeholder block (it's the italicized
paragraph that sits above the marker line in the placeholder cell).

Usage
-----
    python inject_images_into_docs.py \\
        --in  M365_GCC-Moderate_Telemetry_and_Boundary_Assessment_External.docx \\
        --out M365_GCC-Moderate_Telemetry_and_Boundary_Assessment_External_with_images.docx \\
        --images images/

    python inject_images_into_docs.py --in foo.docx           # writes foo_with_images.docx
        # If --out is omitted, "_with_images" is appended before the extension.

    python inject_images_into_docs.py --in foo.docx --width-inches 6.0
        # Override default width (6.5 in for portrait letter w/ 1" margins).

Each placeholder block in the source docx looks like:

    <w:tbl> ...
       <w:p> ... [[IMG_PLACEHOLDER:fig_combined_03]] ... </w:p>
       (preceded inside the same cell by Figure number + caption paragraphs)
    </w:tbl>

After injection, the entire placeholder table is replaced by:

    <w:p alignment=center> <w:drawing>...image rId...</w:drawing> </w:p>
    <w:p alignment=center italic> Figure N. <caption text> </w:p>

Image dimensions
----------------
Default width: 6.5 inches (full content width on US Letter / 1" margins).
For landscape sections, pass --width-inches 9.5 if needed; in this codebase
the only landscape page is the gap matrix table and no figures live there,
so the default is correct for every figure produced by the prompts file.
"""

from __future__ import annotations
import argparse
import io
import re
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# --- Namespaces ------------------------------------------------------------
# Register every namespace docx files routinely declare on the root element.
# ElementTree silently drops xmlns declarations whose URIs aren't registered,
# so even namespaces we never write (w14, w15, mc, etc.) need to be listed
# here to keep the round-tripped document.xml schema-valid.
NS = {
    "w":    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r":    "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a":    "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic":  "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "wp":   "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "ct":   "http://schemas.openxmlformats.org/package/2006/content-types",
    "rels": "http://schemas.openxmlformats.org/package/2006/relationships",
    # Additional namespaces commonly declared on the document.xml root:
    "mc":   "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "wpc":  "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas",
    "wp14": "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
    "wpg":  "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "wpi":  "http://schemas.microsoft.com/office/word/2010/wordprocessingInk",
    "wne":  "http://schemas.microsoft.com/office/word/2006/wordml",
    "wps":  "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "w14":  "http://schemas.microsoft.com/office/word/2010/wordml",
    "w15":  "http://schemas.microsoft.com/office/word/2012/wordml",
    "v":    "urn:schemas-microsoft-com:vml",
    "o":    "urn:schemas-microsoft-com:office:office",
    "w10":  "urn:schemas-microsoft-com:office:word",
    "m":    "http://schemas.openxmlformats.org/officeDocument/2006/math",
}
for prefix, uri in NS.items():
    if prefix not in ("ct", "rels"):
        ET.register_namespace(prefix, uri)
# `ct` and `rels` are each the *default* namespace inside their own respective
# files (Content_Types.xml and *.rels). They cannot both be registered with
# the empty prefix — only the last call wins, leaving the other to be
# serialized with an `ns0:` prefix that strict OOXML readers (LibreOffice)
# reject. Solve this by leaving both unregistered globally, and post-processing
# each file's serialized output to strip whatever ns0/ns1 prefix ET assigned.

W = "{%s}" % NS["w"]
R = "{%s}" % NS["r"]
CT = "{%s}" % NS["ct"]
RELS = "{%s}" % NS["rels"]

EMU_PER_INCH = 914400
PLACEHOLDER_RE = re.compile(r"\[\[IMG_PLACEHOLDER:([a-z0-9_]+)\]\]", re.IGNORECASE)


# --- Image loading ---------------------------------------------------------
def load_image_as_png(path: Path) -> tuple[bytes, int, int, str]:
    """
    Load an image file (any format Pillow understands) and return
    (png_bytes, width_px, height_px, original_format).

    Gemini's image generation API can return JPEG, WebP, or PNG depending on
    the prompt and model; the SDK saves whatever bytes came back to whatever
    filename the caller asked for, so a `.png` extension does not guarantee
    PNG content. We sniff the actual format with Pillow and re-encode as PNG
    in memory if needed, so the embedding pipeline can stay PNG-only.
    """
    try:
        from PIL import Image  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "Pillow is required. Install with: pip install pillow"
        ) from e

    raw = path.read_bytes()
    img = Image.open(io.BytesIO(raw))
    img.load()  # force decode so format is populated
    width, height = img.size
    fmt = (img.format or "UNKNOWN").upper()

    if fmt == "PNG":
        return raw, width, height, fmt

    # Re-encode to PNG, preserving alpha when present.
    buf = io.BytesIO()
    if img.mode in ("RGBA", "LA"):
        img.save(buf, format="PNG")
    elif img.mode == "P":
        img.convert("RGBA").save(buf, format="PNG")
    else:
        img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue(), width, height, fmt


# --- Document walker -------------------------------------------------------
def find_placeholder_tables(root: ET.Element) -> list[tuple[ET.Element, ET.Element, str, str]]:
    """
    Locate each placeholder block. Returns a list of tuples:
      (parent_element, table_element, placeholder_id, caption_text)

    A placeholder block is a w:tbl whose only cell contains a paragraph with the
    [[IMG_PLACEHOLDER:<id>]] token. The italic caption paragraph appears just
    before that token paragraph inside the same cell.
    """
    found = []
    # Build a parent map so we can replace tables in place.
    parent_map = {child: parent for parent in root.iter() for child in parent}

    for tbl in root.iter(W + "tbl"):
        # Look for any w:t in the table containing the marker
        marker_id = None
        caption_text = None
        for t in tbl.iter(W + "t"):
            text = t.text or ""
            m = PLACEHOLDER_RE.search(text)
            if m:
                marker_id = m.group(1)
                # Capture the caption: the preceding paragraph in the same cell
                # whose w:t text isn't "Figure N" and isn't the marker itself.
                # Strategy: collect every w:t in the table, then pick the one
                # whose text is the longest non-marker, non-"Figure N" string.
                candidates = []
                for tt in tbl.iter(W + "t"):
                    tx = (tt.text or "").strip()
                    if not tx:
                        continue
                    if PLACEHOLDER_RE.search(tx):
                        continue
                    if re.match(r"^Figure\s+\d+\s*$", tx, re.IGNORECASE):
                        continue
                    candidates.append(tx)
                if candidates:
                    # Take the longest — that's the caption sentence.
                    caption_text = max(candidates, key=len)
                break
        if marker_id:
            parent = parent_map.get(tbl)
            if parent is None:
                continue
            found.append((parent, tbl, marker_id, caption_text or ""))
    return found


# --- New element builders --------------------------------------------------
def new_run_text(text: str, **rpr_attrs) -> ET.Element:
    r = ET.Element(W + "r")
    if rpr_attrs:
        rpr = ET.SubElement(r, W + "rPr")
        for k, v in rpr_attrs.items():
            ET.SubElement(rpr, W + k, v if isinstance(v, dict) else {W + "val": str(v)})
    t = ET.SubElement(r, W + "t")
    t.text = text
    if text != text.strip():
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return r

def new_image_paragraph(rid: str, cx_emu: int, cy_emu: int, image_name: str) -> ET.Element:
    """
    Construct a centered paragraph containing a w:drawing with an inline image.
    """
    p = ET.Element(W + "p")
    pPr = ET.SubElement(p, W + "pPr")
    # NOTE: per OOXML schema, <w:pPr> child order is:
    # pStyle, numPr, spacing, ind, jc, rPr (last). Don't reorder these.
    spc = ET.SubElement(pPr, W + "spacing")
    spc.set(W + "before", "120")
    spc.set(W + "after", "60")
    jc = ET.SubElement(pPr, W + "jc")
    jc.set(W + "val", "center")

    r = ET.SubElement(p, W + "r")
    drawing = ET.SubElement(r, W + "drawing")
    inline = ET.SubElement(drawing, "{%s}inline" % NS["wp"])
    inline.set("distT", "0"); inline.set("distB", "0"); inline.set("distL", "0"); inline.set("distR", "0")
    extent = ET.SubElement(inline, "{%s}extent" % NS["wp"])
    extent.set("cx", str(cx_emu)); extent.set("cy", str(cy_emu))
    ET.SubElement(inline, "{%s}effectExtent" % NS["wp"], {"l":"0","t":"0","r":"0","b":"0"})
    docPr = ET.SubElement(inline, "{%s}docPr" % NS["wp"])
    docPr.set("id", "1"); docPr.set("name", image_name)
    cNvGraphicFramePr = ET.SubElement(inline, "{%s}cNvGraphicFramePr" % NS["wp"])
    ET.SubElement(cNvGraphicFramePr, "{%s}graphicFrameLocks" % NS["a"], {"noChangeAspect": "1"})

    graphic = ET.SubElement(inline, "{%s}graphic" % NS["a"])
    graphicData = ET.SubElement(graphic, "{%s}graphicData" % NS["a"], {"uri": NS["pic"]})
    pic = ET.SubElement(graphicData, "{%s}pic" % NS["pic"])

    nvPicPr = ET.SubElement(pic, "{%s}nvPicPr" % NS["pic"])
    cNvPr = ET.SubElement(nvPicPr, "{%s}cNvPr" % NS["pic"])
    cNvPr.set("id", "0"); cNvPr.set("name", image_name)
    ET.SubElement(nvPicPr, "{%s}cNvPicPr" % NS["pic"])

    blipFill = ET.SubElement(pic, "{%s}blipFill" % NS["pic"])
    blip = ET.SubElement(blipFill, "{%s}blip" % NS["a"])
    blip.set(R + "embed", rid)
    stretch = ET.SubElement(blipFill, "{%s}stretch" % NS["a"])
    ET.SubElement(stretch, "{%s}fillRect" % NS["a"])

    spPr = ET.SubElement(pic, "{%s}spPr" % NS["pic"])
    xfrm = ET.SubElement(spPr, "{%s}xfrm" % NS["a"])
    ET.SubElement(xfrm, "{%s}off" % NS["a"], {"x": "0", "y": "0"})
    ET.SubElement(xfrm, "{%s}ext" % NS["a"], {"cx": str(cx_emu), "cy": str(cy_emu)})
    prstGeom = ET.SubElement(spPr, "{%s}prstGeom" % NS["a"], {"prst": "rect"})
    ET.SubElement(prstGeom, "{%s}avLst" % NS["a"])

    return p

def new_caption_paragraph(figure_num: str, caption_text: str) -> ET.Element:
    """
    Centered, italic caption: "Figure N. <text>"
    """
    p = ET.Element(W + "p")
    pPr = ET.SubElement(p, W + "pPr")
    # spacing before jc per OOXML schema element ordering
    spc = ET.SubElement(pPr, W + "spacing")
    spc.set(W + "before", "0")
    spc.set(W + "after", "240")
    jc = ET.SubElement(pPr, W + "jc")
    jc.set(W + "val", "center")

    # "Figure N." bold
    r1 = ET.SubElement(p, W + "r")
    rpr1 = ET.SubElement(r1, W + "rPr")
    ET.SubElement(rpr1, W + "b")
    ET.SubElement(rpr1, W + "i")
    ET.SubElement(rpr1, W + "color", {W + "val": "595959"})
    ET.SubElement(rpr1, W + "sz", {W + "val": "20"})
    ET.SubElement(rpr1, W + "rFonts", {W + "ascii": "Calibri", W + "hAnsi": "Calibri"})
    t1 = ET.SubElement(r1, W + "t")
    t1.text = f"Figure {figure_num}. "
    t1.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    # Caption body italic (no bold)
    r2 = ET.SubElement(p, W + "r")
    rpr2 = ET.SubElement(r2, W + "rPr")
    ET.SubElement(rpr2, W + "i")
    ET.SubElement(rpr2, W + "color", {W + "val": "595959"})
    ET.SubElement(rpr2, W + "sz", {W + "val": "20"})
    ET.SubElement(rpr2, W + "rFonts", {W + "ascii": "Calibri", W + "hAnsi": "Calibri"})
    t2 = ET.SubElement(r2, W + "t")
    t2.text = caption_text
    return p


# --- Relationships + content types -----------------------------------------
def next_rid(rels_root: ET.Element) -> str:
    used = set()
    for rel in rels_root.findall(RELS + "Relationship"):
        rid = rel.get("Id", "")
        if rid.startswith("rId"):
            try:
                used.add(int(rid[3:]))
            except ValueError:
                pass
    n = 1
    while n in used:
        n += 1
    return f"rId{n}"

def add_image_relationship(rels_root: ET.Element, rid: str, target: str) -> None:
    rel = ET.SubElement(rels_root, RELS + "Relationship")
    rel.set("Id", rid)
    rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
    rel.set("Target", target)

def ensure_png_content_type(ct_root: ET.Element) -> None:
    for d in ct_root.findall(CT + "Default"):
        if d.get("Extension", "").lower() == "png":
            return
    d = ET.SubElement(ct_root, CT + "Default")
    d.set("Extension", "png")
    d.set("ContentType", "image/png")


# --- Figure-number sequencing ----------------------------------------------
def figure_number_for(img_id: str, doc_index: dict) -> str:
    """
    Convert a placeholder ID like 'fig_combined_03' or 'fig_te_01' into '3' / '1'.
    """
    m = re.search(r'_(\d+)$', img_id)
    if m:
        return str(int(m.group(1)))
    # Fallback: assign ascending per document
    doc_index["counter"] = doc_index.get("counter", 0) + 1
    return str(doc_index["counter"])


# --- Main injection --------------------------------------------------------
def inject(in_path: Path, out_path: Path, images_dir: Path, width_inches: float) -> None:
    if not in_path.exists():
        raise FileNotFoundError(in_path)
    images_dir = images_dir.resolve()
    if not images_dir.exists():
        raise FileNotFoundError(images_dir)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        with zipfile.ZipFile(in_path, "r") as z:
            z.extractall(td)

        document_path = td / "word" / "document.xml"
        rels_path = td / "word" / "_rels" / "document.xml.rels"
        ct_path = td / "[Content_Types].xml"
        media_dir = td / "word" / "media"
        media_dir.mkdir(exist_ok=True)

        # Capture the original document.xml root opening tag verbatim. ElementTree
        # drops xmlns declarations for namespaces that aren't used in element
        # tags (e.g. w14, w15, wp14 — declared on the root only because the
        # mc:Ignorable attribute references them). We splice the original tag
        # back in after serialization so those declarations survive.
        original_doc_bytes = document_path.read_bytes()
        m = re.search(rb"<w:document\b[^>]*>", original_doc_bytes)
        original_root_open = m.group(0) if m else None

        # Our injected drawing elements use xmlns:a, xmlns:pic, xmlns:wp. If the
        # original root didn't declare them (the source doc had no images),
        # add them now to the root tag so the injected elements resolve.
        if original_root_open is not None:
            REQUIRED_NS = {
                b"a":   b"http://schemas.openxmlformats.org/drawingml/2006/main",
                b"pic": b"http://schemas.openxmlformats.org/drawingml/2006/picture",
                b"wp":  b"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
            }
            for prefix, uri in REQUIRED_NS.items():
                decl = b'xmlns:' + prefix + b'="' + uri + b'"'
                if decl not in original_root_open:
                    # Insert before the closing '>' of the open tag
                    original_root_open = original_root_open[:-1] + b" " + decl + b">"

        doc_tree = ET.parse(document_path)
        rels_tree = ET.parse(rels_path)
        ct_tree = ET.parse(ct_path)

        ensure_png_content_type(ct_tree.getroot())

        placeholders = find_placeholder_tables(doc_tree.getroot())
        if not placeholders:
            print(f"[info] no placeholders found in {in_path.name}")
            shutil.copyfile(in_path, out_path)
            return

        print(f"[info] found {len(placeholders)} placeholder(s) in {in_path.name}")

        doc_index: dict = {}
        for parent, tbl, img_id, caption_text in placeholders:
            png_path = images_dir / f"{img_id}.png"
            if not png_path.exists():
                print(f"[skip]  {img_id}: image not found at {png_path}; leaving placeholder in place")
                continue

            try:
                png_bytes, pix_w, pix_h, src_fmt = load_image_as_png(png_path)
            except Exception as e:
                print(f"[skip]  {img_id}: cannot load image ({e})")
                continue
            if src_fmt != "PNG":
                print(f"[note]  {img_id}: source was {src_fmt}, re-encoded to PNG for embedding")

            # Compute display size: fix width, scale height proportionally
            cx_emu = int(width_inches * EMU_PER_INCH)
            aspect = pix_h / pix_w if pix_w else 0.5625
            cy_emu = int(cx_emu * aspect)

            # Copy image into media folder
            target_filename = f"{img_id}.png"
            (media_dir / target_filename).write_bytes(png_bytes)

            # Add relationship
            rid = next_rid(rels_tree.getroot())
            add_image_relationship(
                rels_tree.getroot(),
                rid,
                f"media/{target_filename}",
            )

            # Build replacement paragraphs
            figure_num = figure_number_for(img_id, doc_index)
            img_para = new_image_paragraph(rid, cx_emu, cy_emu, target_filename)
            cap_para = new_caption_paragraph(figure_num, caption_text)

            # Replace the placeholder table with image + caption paragraphs
            idx = list(parent).index(tbl)
            parent.remove(tbl)
            parent.insert(idx, img_para)
            parent.insert(idx + 1, cap_para)

            print(f"[ok]    {img_id} -> Figure {figure_num} ({pix_w}x{pix_h} -> {cx_emu/EMU_PER_INCH:.2f}\"x{cy_emu/EMU_PER_INCH:.2f}\")")

        # Write back. ElementTree.write() doesn't accept standalone=, so we
        # serialize via tostring() and prepend the declaration ourselves. For
        # document.xml we additionally splice the original root opening tag
        # back in to preserve all xmlns declarations (see comment near
        # original_root_open above).
        def write_xml(tree: ET.ElementTree, path: Path) -> None:
            body = ET.tostring(tree.getroot(), encoding="UTF-8", xml_declaration=False)
            decl = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            path.write_bytes(decl + body)

        write_xml(doc_tree, document_path)

        if original_root_open is not None:
            # Replace whatever ET produced for the <w:document ...> tag with
            # the verbatim original tag. This preserves every xmlns declaration
            # and the mc:Ignorable attribute exactly as Word wrote them.
            new_doc_bytes = document_path.read_bytes()
            new_doc_bytes = re.sub(
                rb"<w:document\b[^>]*>",
                original_root_open,
                new_doc_bytes,
                count=1,
            )
            document_path.write_bytes(new_doc_bytes)

        write_xml(rels_tree, rels_path)
        write_xml(ct_tree, ct_path)

        # ElementTree assigns ns0:/ns1: prefixes to namespaces that aren't
        # registered with a specific prefix. For Content_Types.xml and the
        # *.rels files, the OOXML spec requires those namespaces be the
        # *default* (unprefixed) namespace. Strip the prefix textually.
        def strip_default_ns_prefix(path: Path, ns_uri: str) -> None:
            data = path.read_bytes()
            # Find which prefix ET assigned to this URI (e.g. ns0, ns1)
            m = re.search(
                rb'xmlns:(ns\d+)="' + re.escape(ns_uri.encode("utf-8")) + rb'"',
                data,
            )
            if not m:
                return
            prefix = m.group(1)
            # Replace `xmlns:nsN="URI"` with `xmlns="URI"` and strip every `nsN:` token
            data = data.replace(b'xmlns:' + prefix + b'=', b'xmlns=')
            data = data.replace(prefix + b':', b'')
            path.write_bytes(data)

        strip_default_ns_prefix(ct_path, NS["ct"])
        strip_default_ns_prefix(rels_path, NS["rels"])

        # Re-zip
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in td.rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(td).as_posix())

        print(f"[done] wrote {out_path}")


# --- CLI -------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Inject generated images into DOCX placeholders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--in", dest="in_paths", action="append", required=True,
                    metavar="DOCX", help="Input DOCX (may be repeated to process multiple)")
    ap.add_argument("--out", dest="out_paths", action="append", default=[], metavar="DOCX",
                    help="Output DOCX (must match --in count if used; otherwise auto-named)")
    ap.add_argument("--images", default="images", help="Directory containing generated PNGs (default: %(default)s)")
    ap.add_argument("--width-inches", type=float, default=6.5,
                    help="Display width in inches (default: %(default)s)")
    args = ap.parse_args()

    in_paths = [Path(p) for p in args.in_paths]
    if args.out_paths:
        if len(args.out_paths) != len(in_paths):
            print("[fatal] --out count must match --in count", file=sys.stderr)
            return 2
        out_paths = [Path(p) for p in args.out_paths]
    else:
        out_paths = [
            p.with_name(p.stem + "_with_images" + p.suffix) for p in in_paths
        ]

    images_dir = Path(args.images)
    rc = 0
    for ip, op in zip(in_paths, out_paths):
        try:
            inject(ip, op, images_dir, args.width_inches)
        except Exception as e:  # noqa: BLE001
            print(f"[fail] {ip}: {e}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
