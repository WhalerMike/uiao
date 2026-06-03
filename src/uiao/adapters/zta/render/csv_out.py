"""CSV worklist renderer."""

from __future__ import annotations

import csv
from pathlib import Path

from uiao.adapters.zta.applicability import derive_applicability, is_premium_gated, license_str
from uiao.adapters.zta.triage import Triage, id_namespace

_COLUMNS = [
    "TestId",
    "IdNamespace",
    "Pillar",
    "SfiPillar",
    "Category",
    "Title",
    "Risk",
    "Status",
    "Impact",
    "ImplementationCost",
    "MinimumLicense",
    "PremiumGated",
    "Applicability",
]


def worklist_rows(triage: Triage) -> list[dict[str, str]]:
    """Build the worklist as a list of string-keyed row dicts."""
    rows: list[dict[str, str]] = []
    for t in triage.worklist:
        rows.append(
            {
                "TestId": t.test_id,
                "IdNamespace": id_namespace(t.test_id),
                "Pillar": t.pillar,
                "SfiPillar": t.test_sfi_pillar or "",
                "Category": t.test_category or "",
                "Title": t.test_title,
                "Risk": t.test_risk,
                "Status": t.test_status,
                "Impact": t.test_impact,
                "ImplementationCost": t.test_implementation_cost,
                "MinimumLicense": license_str(t),
                "PremiumGated": "yes" if is_premium_gated(t) else "no",
                "Applicability": derive_applicability(t).value,
            }
        )
    return rows


def write_csv(triage: Triage, path: Path) -> Path:
    """Write the worklist to ``path`` as UTF-8 CSV; return the path."""
    rows = worklist_rows(triage)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path
