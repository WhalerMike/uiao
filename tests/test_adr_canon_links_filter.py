"""Unit tests for ``docs/filters/adr-canon-links.lua``.

The ADR wrapper pages embed canon ADR source verbatim via ``{{< include >}}``,
whose relative links Quarto does not rewrite. This filter resolves them against
the canon dir and emits a working target.

It is the one filter whose output is **format-dependent**, which is what these
tests pin:

* **HTML** — sibling ADRs and docs pages stay site-relative (``adr-NNN.html``,
  ``../<path>.html``), because the published page sits at a known depth.
* **DOCX** — both become absolute ``https://`` URLs. Word resolves a relative
  hyperlink against the .docx file's own location on the reader's disk, so a
  relative target is simply dead in a downloaded Word bundle.

The GitHub-blob branch is already absolute and is shared by both formats.

Skips when pandoc is unavailable (a CI job without the Quarto toolchain).
"""

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FILTER = REPO / "docs" / "filters" / "adr-canon-links.lua"

SITE = "https://whalermike.github.io/uiao/"
BLOB = "https://github.com/WhalerMike/uiao/blob/main/"

MARKDOWN = """\
- [sibling adr](adr-092-active-governance.md)
- [docs page](../../../../docs/customer-documents/whitepapers/modernization-journey.qmd)
- [canon spec](../specs/Platform-Overview.md)
- [no wrapper](adr-000-adr-process.md)
- [sibling with anchor](adr-092-active-governance.md#decision)
- [external](https://example.com/x)
- [anchor](#heading)
"""

# Targets that do not depend on the output format.
FORMAT_INDEPENDENT = [
    f"{BLOB}src/uiao/canon/specs/Platform-Overview.md",
    f"{BLOB}src/uiao/canon/adr/adr-000-adr-process.md",
    "https://example.com/x",
]

HTML_ONLY = [
    "adr-092-active-governance.html",
    "../customer-documents/whitepapers/modernization-journey.html",
    "adr-092-active-governance.html#decision",
]

DOCX_ONLY = [
    f"{SITE}adr/adr-092-active-governance.html",
    f"{SITE}customer-documents/whitepapers/modernization-journey.html",
    f"{SITE}adr/adr-092-active-governance.html#decision",
]


def _run(fmt: str, out: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = ["pandoc", "-f", "markdown", "-t", fmt, f"--lua-filter={FILTER}"]
    if out is not None:
        cmd += ["-o", str(out)]
    return subprocess.run(cmd, input=MARKDOWN, capture_output=True, text=True, check=True)


def _docx_hyperlink_targets(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    return re.findall(r'hyperlink" Id="[^"]+" Target="([^"]+)"', rels)


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not available")
def test_html_keeps_site_relative_targets() -> None:
    out = _run("html").stdout
    for expected in FORMAT_INDEPENDENT + HTML_ONLY:
        assert f'href="{expected}"' in out, f"missing html rewrite: {expected}\n{out}"
    # The absolute site form belongs to docx only; HTML must not acquire it.
    assert SITE not in out, f"html should not emit absolute site URLs:\n{out}"


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not available")
def test_docx_emits_absolute_targets(tmp_path: Path) -> None:
    out = tmp_path / "out.docx"
    _run("docx", out)
    targets = _docx_hyperlink_targets(out)

    relative = [t for t in targets if not re.match(r"^[a-z]+:", t) and not t.startswith("#")]
    assert not relative, f"relative targets are dead in Word: {relative}"

    for expected in FORMAT_INDEPENDENT + DOCX_ONLY:
        assert expected in targets, f"missing docx rewrite: {expected}\n{targets}"
