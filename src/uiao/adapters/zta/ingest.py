"""Load a Zero Trust Assessment report from ``.json`` or ``.html``.

The HTML report the tool opens by default embeds the full dataset as a
JavaScript assignment ``reportData = { … }`` — the *same* object as the JSON
export. We locate that assignment and parse exactly one JSON value with a
JSON-aware decoder (no brittle regex over a 3 MB minified blob).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from uiao.adapters.zta.model import ZtReport

# ``reportData`` assignment in the report's bundled script. The data object
# reliably begins with the "ExecutedAt" key, used as a fallback anchor.
_ASSIGNMENT_RE = re.compile(r"reportData\s*=\s*(?=\{)")
_ROOT_ANCHOR = '{"ExecutedAt"'


class ZtIngestError(ValueError):
    """Raised when a file is not a recognizable Zero Trust Assessment report."""


def extract_report_data(html: str) -> dict[str, Any]:
    """Extract and parse the embedded ``reportData`` object from report HTML."""
    candidates: list[int] = []
    match = _ASSIGNMENT_RE.search(html)
    if match is not None:
        candidates.append(match.end())
    anchor = html.find(_ROOT_ANCHOR)
    if anchor >= 0:
        candidates.append(anchor)

    decoder = json.JSONDecoder()
    for start in candidates:
        brace = html.find("{", start)
        if brace < 0:
            continue
        try:
            obj, _ = decoder.raw_decode(html, brace)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "Tests" in obj:
            return obj
    raise ZtIngestError("could not locate an embedded `reportData` object in the HTML report")


def _load_dict(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".html", ".htm"}:
        return extract_report_data(text)
    if suffix == ".json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ZtIngestError(f"{path} does not contain a JSON object")
        return data
    # Unknown extension: sniff the content.
    stripped = text.lstrip()
    if stripped.startswith("{"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ZtIngestError(f"{path} does not contain a JSON object")
        return data
    return extract_report_data(text)


def load_report(path: Path) -> ZtReport:
    """Load a report from a ``.json`` export or an ``.html`` report file."""
    if not path.exists():
        raise FileNotFoundError(path)
    data = _load_dict(path)
    if "Tests" not in data:
        raise ZtIngestError(f"{path} has no `Tests` array — not a Zero Trust Assessment report")
    return ZtReport.model_validate(data)
