"""Unit test for ``docs/filters/customer-canon-links.lua``.

Runs the Lua filter through pandoc on representative customer-document links and
asserts each rewrites to the correct published site URL or GitHub-blob source.
The full site only renders on ``main``, so this pins the rewrite logic itself.
Skips when pandoc is unavailable (a CI job without the Quarto toolchain).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FILTER = REPO / "docs" / "filters" / "customer-canon-links.lua"

MARKDOWN = """\
- [a](docs/customer-documents/federal-aan-series/boundary/B1-gcc-moderate-boundary-model.qmd)
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
BA = "customer-documents/federal-aan-series/boundary/"
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
