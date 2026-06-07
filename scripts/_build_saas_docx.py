"""One-off: render the SaaS docs to house-style .docx (with embedded figures).

Not part of CI — a local deliverable builder. Uses pypandoc (pandoc 3.x) with
the repo's reference template. Frontmatter is stripped and replaced with a
title/subtitle; the operator guide's ASCII diagrams are swapped for the
authored house-style PNG figures; the ADR gets the architecture figure.
"""

from __future__ import annotations

import pathlib
import re

import pypandoc

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "saas-docx"
OUT.mkdir(parents=True, exist_ok=True)
REFERENCE = ROOT / "docs" / "assets" / "reference-mslearn.docx"
IMG = ROOT / "docs" / "customer-documents" / "platform" / "images"

ARCH_PNG = IMG / "saas-architecture.png"
LIFE_PNG = IMG / "saas-tenant-lifecycle.png"

FM = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
SHORTCODE = re.compile(r"\{\{<.*?>\}\}\s*\n?")


def _strip_frontmatter(text: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    m = FM.match(text)
    if m:
        block = m.group(0).strip().strip("-").strip()
        for line in block.splitlines():
            if ":" in line and not line.startswith(" "):
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip().strip('"')
        text = text[m.end() :]
    return meta, text


def _heading(meta: dict[str, str], fallback: str) -> str:
    title = meta.get("title", fallback)
    sub = meta.get("subtitle", "")
    head = f"# {title}\n\n"
    if sub:
        head += f"*{sub}*\n\n"
    return head


def _swap_ascii_diagrams(body: str) -> str:
    """Replace the operator guide's two ASCII diagram fences with figures."""
    # Architecture fence: the one containing the Entra → Container App topology.
    body = re.sub(
        r"```\n {12}Entra ID.*?```",
        f"![Figure 1 — UIAO Azure SaaS architecture.]({ARCH_PNG.as_posix()})",
        body,
        count=1,
        flags=re.DOTALL,
    )
    # Lifecycle fence: the PENDING → ACTIVE → ... state machine.
    body = re.sub(
        r"```\nPENDING.*?```",
        f"![Figure 2 — Tenant lifecycle state machine.]({LIFE_PNG.as_posix()})",
        body,
        count=1,
        flags=re.DOTALL,
    )
    return body


def _render(md: str, out_name: str, resource_path: pathlib.Path | None = None) -> None:
    out_path = OUT / out_name
    extra = [f"--reference-doc={REFERENCE}", "--toc", "--toc-depth=3"]
    if resource_path is not None:
        extra.append(f"--resource-path={resource_path}")
    pypandoc.convert_text(
        md,
        to="docx",
        format="markdown+fenced_divs+pipe_tables",
        outputfile=str(out_path),
        extra_args=extra,
    )
    print(f"wrote {out_path.relative_to(ROOT)}  ({out_path.stat().st_size:,} bytes)")


def build_operator_guide() -> None:
    docdir = ROOT / "docs/customer-documents/platform"
    src = (docdir / "azure-saas.qmd").read_text()
    meta, body = _strip_frontmatter(src)
    body = SHORTCODE.sub("", body)
    # The page now embeds the authored figures via relative images/ refs;
    # --resource-path lets pandoc find and embed them. (The legacy ASCII-swap
    # is kept as a no-op fallback for older revisions of the page.)
    body = _swap_ascii_diagrams(body)
    # Drop the duplicate first H1 from the body (we re-emit from frontmatter).
    body = re.sub(r"^# UIAO Azure SaaS \{\.unnumbered\}\s*\n", "", body, count=1)
    _render(
        _heading(meta, "UIAO Azure SaaS") + body,
        "01-UIAO-Azure-SaaS-Operator-Guide.docx",
        resource_path=docdir,
    )


def build_adr() -> None:
    src = (ROOT / "src/uiao/canon/adr/adr-096-azure-saas-architecture.md").read_text()
    meta, body = _strip_frontmatter(src)
    body = SHORTCODE.sub("", body)
    # Insert the architecture figure right after the first H1 in the body.
    fig = f"\n\n![UIAO Azure SaaS architecture.]({ARCH_PNG.as_posix()})\n\n"
    body = re.sub(r"(^# ADR-096:.*?\n)", r"\1" + fig, body, count=1, flags=re.MULTILINE)
    _render(body, "02-ADR-096-Azure-SaaS-Architecture.docx")


def build_cli_reference() -> None:
    src = (ROOT / "docs/docs/cli-reference.qmd").read_text()
    meta, body = _strip_frontmatter(src)
    body = SHORTCODE.sub("", body)
    _render(_heading(meta, "UIAO CLI Reference") + body, "03-UIAO-CLI-Reference.docx")


def build_deploy_readme() -> None:
    src = (ROOT / "deploy/azure/README.md").read_text()
    meta, body = _strip_frontmatter(src)
    body = SHORTCODE.sub("", body)
    _render(body, "04-Azure-Deploy-README.docx")


if __name__ == "__main__":
    build_operator_guide()
    build_adr()
    build_cli_reference()
    build_deploy_readme()
    print("\nAll .docx written to", OUT.relative_to(ROOT))
