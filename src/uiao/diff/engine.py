from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from uiao.adapters.scuba.ir.transformer import SCuBATransformResult


@dataclass
class KSIDiff:
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)


@dataclass
class EvidenceDiff:
    ksi_id: str
    hash_a: str
    hash_b: str
    changed: bool


@dataclass
class RunDiff:
    run_id_a: str
    run_id_b: str
    ksi_diff: KSIDiff
    evidence_diffs: List[EvidenceDiff] = field(default_factory=list)
    status_changes: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.ksi_diff.added or self.ksi_diff.removed or any(d.changed for d in self.evidence_diffs))


def diff_runs(result_a: SCuBATransformResult, result_b: SCuBATransformResult) -> RunDiff:
    """Diff two SCuBATransformResults deterministically."""
    ksis_a: Set[str] = {e.data.get("ksi_id", "") for e in result_a.evidence}
    ksis_b: Set[str] = {e.data.get("ksi_id", "") for e in result_b.evidence}

    ksi_diff = KSIDiff(
        added=sorted(ksis_b - ksis_a),
        removed=sorted(ksis_a - ksis_b),
        unchanged=sorted(ksis_a & ksis_b),
    )

    hash_a: Dict[str, str] = {e.data.get("ksi_id", ""): e.hash() for e in result_a.evidence}
    hash_b: Dict[str, str] = {e.data.get("ksi_id", ""): e.hash() for e in result_b.evidence}

    evidence_diffs: List[EvidenceDiff] = []
    for ksi_id in ksi_diff.unchanged:
        ha, hb = hash_a.get(ksi_id, ""), hash_b.get(ksi_id, "")
        evidence_diffs.append(EvidenceDiff(ksi_id=ksi_id, hash_a=ha, hash_b=hb, changed=(ha != hb)))

    status_a = {e.data.get("ksi_id", ""): e.data.get("status", "") for e in result_a.evidence}
    status_b = {e.data.get("ksi_id", ""): e.data.get("status", "") for e in result_b.evidence}
    status_changes: List[Dict[str, Any]] = [
        {"ksi_id": k, "from": status_a[k], "to": status_b[k]}
        for k in ksi_diff.unchanged
        if status_a.get(k) != status_b.get(k)
    ]

    return RunDiff(
        run_id_a=result_a.run_id,
        run_id_b=result_b.run_id,
        ksi_diff=ksi_diff,
        evidence_diffs=evidence_diffs,
        status_changes=status_changes,
    )


def format_diff_markdown(diff: RunDiff) -> str:
    """Render a RunDiff as human-readable Markdown."""
    lines = [
        "# IR Run Diff",
        "",
        f"Run A: {diff.run_id_a}  ",
        f"Run B: {diff.run_id_b}",
        "",
        "## KSI Changes",
        f"- Added   : {len(diff.ksi_diff.added)}",
        f"- Removed : {len(diff.ksi_diff.removed)}",
        f"- Common  : {len(diff.ksi_diff.unchanged)}",
        "",
    ]
    if diff.ksi_diff.added:
        lines += ["### New KSIs"] + [f"- {k}" for k in diff.ksi_diff.added] + [""]
    if diff.ksi_diff.removed:
        lines += ["### Removed KSIs"] + [f"- {k}" for k in diff.ksi_diff.removed] + [""]
    changed = [d for d in diff.evidence_diffs if d.changed]
    lines += [f"## Evidence Hash Changes: {len(changed)}", ""]
    for d in changed:
        lines.append(f"- {d.ksi_id}: {d.hash_a[:12]} -> {d.hash_b[:12]}")
    if changed:
        lines.append("")
    lines += [f"## Status Changes: {len(diff.status_changes)}", ""]
    for sc in diff.status_changes:
        lines.append(f"- {sc['ksi_id']}: {sc['from']} -> {sc['to']}")
    return "\n".join(lines)


def format_diff_json(diff: RunDiff) -> str:
    """Render a RunDiff as canonical JSON."""
    return json.dumps(
        {
            "run_id_a": diff.run_id_a,
            "run_id_b": diff.run_id_b,
            "has_changes": diff.has_changes,
            "ksi_diff": {
                "added": diff.ksi_diff.added,
                "removed": diff.ksi_diff.removed,
                "unchanged_count": len(diff.ksi_diff.unchanged),
            },
            "evidence_hash_changes": [
                {"ksi_id": d.ksi_id, "hash_a": d.hash_a, "hash_b": d.hash_b} for d in diff.evidence_diffs if d.changed
            ],
            "status_changes": diff.status_changes,
        },
        indent=2,
    )
