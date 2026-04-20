from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from uiao.impl.coverage.coverage import build_coverage_links
from uiao.impl.evidence.bundle import build_bundle_from_transform_result
from uiao.impl.evidence.poam import build_poam, poam_to_json
from uiao.impl.governance.actions import build_governance_actions
from uiao.impl.governance.report import format_governance_report
from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
from uiao.impl.ir.models.core import canonical_hash
from uiao.impl.ssp.lineage import build_lineage_index
from uiao.impl.ssp.narrative import build_control_narratives, format_ssp_markdown


def build_auditor_bundle(
    normalized_json_path: str,
    out_dir: str,
) -> Dict[str, Any]:
    """Orchestrate the full pipeline and write all auditor artifacts to out_dir.

    Returns a manifest dict with file paths and hashes.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = transform_scuba_to_ir(normalized_json_path)
    bundle = build_bundle_from_transform_result(result)
    actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    links = build_coverage_links(bundle.evidence)
    narratives = build_control_narratives(links, actions)

    artifacts: Dict[str, str] = {}

    gov_md = format_governance_report(actions)
    (out / "governance-report.md").write_text(gov_md, encoding="utf-8")
    artifacts["governance-report.md"] = canonical_hash(gov_md)

    ssp_md = format_ssp_markdown(narratives)
    (out / "ssp-narrative.md").write_text(ssp_md, encoding="utf-8")
    artifacts["ssp-narrative.md"] = canonical_hash(ssp_md)

    lineage = build_lineage_index(links, actions)
    lineage_json = json.dumps(lineage, indent=2, ensure_ascii=False)
    (out / "lineage.json").write_text(lineage_json, encoding="utf-8")
    artifacts["lineage.json"] = canonical_hash(lineage)

    bundle_json = bundle.to_canonical()
    (out / "evidence-bundle.json").write_text(bundle_json, encoding="utf-8")
    artifacts["evidence-bundle.json"] = canonical_hash(bundle_json)

    poam_rows = build_poam(bundle)
    (out / "poam.json").write_text(poam_to_json(poam_rows), encoding="utf-8")
    artifacts["poam.json"] = canonical_hash(poam_rows)

    manifest: Dict[str, Any] = {
        "run_id": result.run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "normalized_json": str(Path(normalized_json_path).resolve()),
        "artifacts": artifacts,
        "summary": {
            "evidence_total": len(bundle.evidence),
            "pass": bundle.pass_count,
            "warn": bundle.warn_count,
            "fail": bundle.fail_count,
            "governance_actions": len(actions),
            "poam_items": len(poam_rows),
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest

