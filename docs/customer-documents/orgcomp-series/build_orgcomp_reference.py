#!/usr/bin/env python3
"""Build orgcomp-reference.docx from lz-reference.docx by adding AAN house-style
callout + FOUO-banner paragraph styles (shading, left border, palette colors).

Pandoc's docx writer can only apply paragraph shading/borders through NAMED styles
in the reference doc — so the `orgcomp-callouts.lua` filter maps each Quarto callout /
banner div to one of these styles. This gives the AAN callout boxes in a pandoc
render when Quarto itself is unavailable. Run once; commit orgcomp-reference.docx.
"""

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor

# AAN palette (ink / tint) per OrgComp_DECK_STYLE_NOTES.md.
CALLOUTS = {
    # style name       fill(tint)  border(ink)  bold-title-color
    "CalloutWarning": ("FBF3E4", "D4860B", "8A6210"),  # amber (draft/caution)
    "CalloutImportant": ("EDF3F9", "1F3A5F", "1F3A5F"),  # navy
    "CalloutNote": ("F3F5F8", "5A6B7B", "1F3A5F"),  # neutral
    "CalloutTip": ("E6F5F2", "1A9E8F", "1A9E8F"),  # teal (closure-necessity)
    "CalloutCaution": ("F9EAE8", "C0392B", "C0392B"),  # red
    "ExecSummary": ("EDF3F9", "1F3A5F", "1F3A5F"),  # navy (executive summary box)
}


def _shade(pPr, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


def _left_border(pPr, color):
    pbdr = OxmlElement("w:pBdr")
    for edge in ("top", "left", "bottom", "right"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "24" if edge == "left" else "4")
        e.set(qn("w:space"), "6")
        e.set(qn("w:color"), color if edge == "left" else "C9D4E0")
        pbdr.append(e)
    pPr.append(pbdr)


def _spacing(pPr):
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:before"), "60")
    sp.set(qn("w:after"), "60")
    pPr.append(sp)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "120")
    ind.set(qn("w:right"), "120")
    pPr.append(ind)


def main():
    doc = Document("lz-reference.docx")
    styles = doc.styles
    existing = {s.style_id for s in styles}

    for name, (fill, border, _title_color) in CALLOUTS.items():
        if name in existing:
            continue
        st = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        try:
            st.base_style = styles["Body Text"]
        except KeyError:
            st.base_style = styles["Normal"]
        st.font.color.rgb = RGBColor.from_string("2A2A2A")
        st.font.size = None
        pPr = st.element.get_or_add_pPr()
        _shade(pPr, fill)
        _left_border(pPr, border)
        _spacing(pPr)

    # FOUO banner — centered, bold, red tint.
    if "FouoBanner" not in existing:
        st = styles.add_style("FouoBanner", WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = styles["Normal"]
        st.font.bold = True
        st.font.color.rgb = RGBColor.from_string("C0392B")
        pPr = st.element.get_or_add_pPr()
        _shade(pPr, "F9EAE8")
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), "center")
        pPr.append(jc)
        _spacing(pPr)

    doc.save("orgcomp-reference.docx")
    print(
        "wrote orgcomp-reference.docx with",
        len(CALLOUTS) + 1,
        "AAN callout/banner styles:",
        ", ".join(sorted(CALLOUTS) + ["FouoBanner"]),
    )


if __name__ == "__main__":
    main()
