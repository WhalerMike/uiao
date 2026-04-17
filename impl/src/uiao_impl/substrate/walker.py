"""Repo-walker: reads the canonical substrate manifest (UIAO_200) and
workspace contract (UIAO_201), then walks the declared module paths and
canon document registry to detect structural and provenance drift.

Drift classes reported (per docs/docs/16_DriftDetectionStandard.qmd):
  DRIFT-SCHEMA      — declared module path or registry path does not exist
  DRIFT-PROVENANCE  — canon document referenced by the registry is missing

Resolution order for the workspace root:
  1. Explicit `workspace_root` argument
  2. Environment variable UIAO_WORKSPACE_ROOT
  3. Git top-level (git rev-parse --show-toplevel) as a last-resort fallback
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

SUBSTRATE_MANIFEST = "core/canon/substrate-manifest.yaml"
WORKSPACE_CONTRACT = "core/canon/workspace-contract.yaml"
DOCUMENT_REGISTRY = "core/canon/document-registry.yaml"

# document-registry paths are core-relative by convention; resolve under core/
DOCUMENT_REGISTRY_BASE = "core"


@dataclass
class DriftFinding:
    drift_class: str
    severity: str
    path: str
    detail: str


@dataclass
class SubstrateReport:
    workspace_root: Path
    manifest_present: bool
    contract_present: bool
    modules_checked: int = 0
    documents_checked: int = 0
    findings: list[DriftFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def as_dict(self) -> dict:
        return {
            "workspace_root": str(self.workspace_root),
            "manifest_present": self.manifest_present,
            "contract_present": self.contract_present,
            "modules_checked": self.modules_checked,
            "documents_checked": self.documents_checked,
            "ok": self.ok,
            "findings": [
                {
                    "drift_class": f.drift_class,
                    "severity": f.severity,
                    "path": f.path,
                    "detail": f.detail,
                }
                for f in self.findings
            ],
        }


def resolve_workspace_root(explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env = os.environ.get("UIAO_WORKSPACE_ROOT")
    if env:
        return Path(env).resolve()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        )
        return Path(out.decode().strip()).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(
            "Cannot resolve workspace root. Set $UIAO_WORKSPACE_ROOT, "
            "pass --workspace-root, or run inside a git checkout."
        ) from exc


def _load_yaml(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with path.open() as fh:
        return yaml.safe_load(fh)


def walk_substrate(workspace_root: Optional[Path] = None) -> SubstrateReport:
    root = resolve_workspace_root(workspace_root)
    manifest_path = root / SUBSTRATE_MANIFEST
    contract_path = root / WORKSPACE_CONTRACT
    registry_path = root / DOCUMENT_REGISTRY

    manifest = _load_yaml(manifest_path)
    contract = _load_yaml(contract_path)
    registry = _load_yaml(registry_path)

    report = SubstrateReport(
        workspace_root=root,
        manifest_present=manifest is not None,
        contract_present=contract is not None,
    )

    if manifest is None:
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-SCHEMA",
                severity="P1",
                path=SUBSTRATE_MANIFEST,
                detail="substrate manifest is missing from the workspace",
            )
        )
        return report

    declared_modules = {m["name"]: m["path"] for m in manifest.get("modules", [])}
    for name, rel_path in declared_modules.items():
        resolved = root / rel_path
        report.modules_checked += 1
        if not resolved.is_dir():
            report.findings.append(
                DriftFinding(
                    drift_class="DRIFT-SCHEMA",
                    severity="P1",
                    path=rel_path,
                    detail=f"module '{name}' declared by substrate-manifest does not exist",
                )
            )

    if contract is not None:
        contract_modules = set(contract.get("module_paths", {}).values())
        manifest_modules = set(declared_modules.values())
        missing = contract_modules - manifest_modules
        for path in sorted(missing):
            report.findings.append(
                DriftFinding(
                    drift_class="DRIFT-SCHEMA",
                    severity="P2",
                    path=path,
                    detail="workspace-contract declares a module_path not listed in substrate-manifest",
                )
            )
        drift_roots = set(contract.get("drift_scan_roots", []))
        extra = drift_roots - contract_modules
        for path in sorted(extra):
            report.findings.append(
                DriftFinding(
                    drift_class="DRIFT-SCHEMA",
                    severity="P2",
                    path=path,
                    detail="workspace-contract drift_scan_root is not a declared module_path",
                )
            )

    if registry is not None:
        reg_base = root / DOCUMENT_REGISTRY_BASE
        for doc in registry.get("documents", []):
            report.documents_checked += 1
            doc_path = doc["path"]
            resolved = reg_base / doc_path
            if not resolved.exists():
                report.findings.append(
                    DriftFinding(
                        drift_class="DRIFT-PROVENANCE",
                        severity="P1",
                        path=f"{DOCUMENT_REGISTRY_BASE}/{doc_path}",
                        detail=f"canon document {doc['id']} referenced by document-registry is missing",
                    )
                )

    return report
