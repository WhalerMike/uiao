"""Shared access to the KSI rule library under ``uiao/rules/ksi/``.

The library carries two filename conventions (``ksi-ac-01.yaml`` for the
original NIST-family rules, ``KSI-CARK-001.yaml`` for the later
adapter-scoped waves) and two control-list dialects (``controls`` vs
``related_controls``). Loaders that glob a single case or read a single key
silently drop rules — ``ksi_to_ir`` mapped 163 of 191 rules for months
because of a lowercase-only glob. Every consumer should go through these
helpers instead.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

#: Library metadata files that live under rules/ksi/ but are not rules.
NON_RULE_FILES = frozenset({"index.yaml", "ksi_schema.yaml", "uiao-control-to-ksi-mapping.yaml"})


def iter_rule_files(ksi_root: Path) -> Iterator[Path]:
    """Yield every KSI rule file under *ksi_root*, both filename conventions."""
    for path in sorted(ksi_root.rglob("*.yaml")):
        if path.name not in NON_RULE_FILES:
            yield path


def rule_controls(rule: dict[str, Any]) -> list[str]:
    """The rule's NIST control list under either dialect."""
    for key in ("controls", "related_controls"):
        value = rule.get(key)
        if isinstance(value, list):
            return [str(c) for c in value]
    return []


__all__ = ["NON_RULE_FILES", "iter_rule_files", "rule_controls"]
