"""Unit tests for ``docs/filters/customer-canon-links.lua``.

Runs the Lua filter through pandoc on representative customer-document links and
asserts each rewrites to the correct published site URL or GitHub-blob source.
The full site only renders on ``main``, so this pins the rewrite logic itself.
Skips when pandoc is unavailable (a CI job without the Quarto toolchain).

Both output formats are covered. DOCX matters independently of HTML: Quarto
rewrites nothing for the docx writer, and Word resolves a relative hyperlink
against the .docx file's own location on disk, so any target left relative is
dead for every reader of a downloaded Word bundle. Before this filter was
extended to docx, all ten hyperlinks in ``modernization-journey.docx`` were
relative.
"""

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FILTER = REPO / "docs" / "filters" / "customer-canon-links.lua"

MARKDOWN = """\
- [a](docs/customer-documents/orgcomp-series/boundary/B1-gcc-moderate-boundary-model.qmd)
- [b](B1-3-rebuilding-boundary-blocked-analytics.qmd)
- [c](src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/methodology.md)
- [d](src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml)
- [e](../../../docs/14_TIC3_F5RetirementRoadmap.qmd)
- [f](../../../../src/uiao/canon/adr/adr-057-thousandeyes-networks-pillar-scope.md)
- [g](../../../../inbox/drafts/charter-restoration-plan.md)
- [h](B1-3-rebuilding-boundary-blocked-analytics.qmd#x)
- [i](https://example.com/x)
- [j](#heading)
"""

SITE = "https://whalermike.github.io/uiao/"
BA = "customer-documents/orgcomp-series/boundary/"
BLOB = "https://github.com/WhalerMike/uiao/blob/main/"

EXPECTED = [
    f'href="{SITE}{BA}B1-gcc-moderate-boundary-model.html"',
    f'href="{SITE}{BA}B1-3-rebuilding-boundary-blocked-analytics.html"',
    f'href="{BLOB}src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/methodology.md"',
    f'href="{BLOB}src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml"',
    f'href="{SITE}docs/14_TIC3_F5RetirementRoadmap.html"',
    f'href="{SITE}adr/adr-057-thousandeyes-networks-pillar-scope.html"',
    f'href="{BLOB}inbox/drafts/charter-restoration-plan.md"',
    f'href="{SITE}{BA}B1-3-rebuilding-boundary-blocked-analytics.html#x"',
    'href="https://example.com/x"',
    'href="#heading"',
]


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not available")
def test_customer_canon_links_rewrites() -> None:
    result = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "html", f"--lua-filter={FILTER}"],
        input=MARKDOWN,
        capture_output=True,
        text=True,
        check=True,
    )
    out = result.stdout
    for expected in EXPECTED:
        assert expected in out, f"missing rewrite: {expected}\n--- rendered ---\n{out}"


def _docx_hyperlink_targets(path: Path) -> list[str]:
    """External hyperlink targets from a .docx, in document.xml.rels order."""
    with zipfile.ZipFile(path) as z:
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    return re.findall(r'hyperlink" Id="[^"]+" Target="([^"]+)"', rels)


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not available")
def test_customer_canon_links_rewrites_for_docx(tmp_path: Path) -> None:
    """The same rewrites must reach the Word bundle, as absolute URLs.

    A relative target in a .docx is dead: Word resolves it against wherever the
    file happens to sit on the reader's disk.
    """
    out = tmp_path / "out.docx"
    subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "docx", f"--lua-filter={FILTER}", "-o", str(out)],
        input=MARKDOWN,
        capture_output=True,
        text=True,
        check=True,
    )
    targets = _docx_hyperlink_targets(out)

    relative = [t for t in targets if not re.match(r"^[a-z]+:", t) and not t.startswith("#")]
    assert not relative, f"relative targets are dead in Word: {relative}"

    for expected in EXPECTED:
        href = expected.split('href="', 1)[1].rstrip('"')
        if href.startswith("#"):
            continue  # a bare anchor stays intra-document in docx too
        assert href in targets, f"missing docx rewrite: {href}\n--- targets ---\n{targets}"
