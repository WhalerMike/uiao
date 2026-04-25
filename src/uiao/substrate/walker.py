"""Repo-walker: reads the canonical substrate manifest (UIAO_200) and
workspace contract (UIAO_201), then walks the declared module paths and
canon document registry to detect structural and provenance drift.

Drift classes reported (per docs/docs/16_DriftDetectionStandard.qmd):
  DRIFT-SCHEMA      — declared module path or registry path does not exist
  DRIFT-PROVENANCE  — canon document referenced by the registry is missing,
                      OR a canon document cites a code path under src/uiao/
                      (or the retired impl/ prefix) that does not resolve.

Resolution order for the workspace root:
  1. Explicit `workspace_root` argument
  2. Environment variable UIAO_WORKSPACE_ROOT
  3. Git top-level (git rev-parse --show-toplevel) as a last-resort fallback
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

SUBSTRATE_MANIFEST = "src/uiao/canon/substrate-manifest.yaml"
WORKSPACE_CONTRACT = "src/uiao/canon/workspace-contract.yaml"
DOCUMENT_REGISTRY = "src/uiao/canon/document-registry.yaml"
MODERNIZATION_REGISTRY = "src/uiao/canon/modernization-registry.yaml"
ADAPTER_REGISTRY = "src/uiao/canon/adapter-registry.yaml"

# Paths inside document-registry.yaml are workspace-relative (e.g.
# `src/uiao/canon/UIAO-SSOT.md`), so the resolve base is the workspace root.
DOCUMENT_REGISTRY_BASE = "."

# Canon-to-code provenance scan: match references in canon prose to code
# paths with a recognized file extension. Two prefixes are tracked:
#   - `src/uiao/`     — current canonical package layout (post-ADR-032)
#   - `impl/`         — retired pre-ADR-032 prefix; any surviving citation
#                       is by definition dangling and should be flagged
#                       until the narrative is cleaned up.
# Trailing punctuation is trimmed by the finditer output via the pattern
# boundaries.
CANON_ROOT = "src/uiao/canon"
DOCS_ROOT = "docs"
CODE_REF_PATTERN = re.compile(r"\b(?:src/uiao|impl)/[\w./\-]+\.(?:py|md|yaml|yml|json|toml|lua|sh|ini|cfg)\b")


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
    code_refs_checked: int = 0
    findings: list[DriftFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Truthy when there are no findings of any severity."""
        return not self.findings

    @property
    def blocking(self) -> bool:
        """Truthy when there is at least one P1 finding. Drives CI exit code."""
        return any(f.severity == "P1" for f in self.findings)

    @property
    def warnings(self) -> list[DriftFinding]:
        return [f for f in self.findings if f.severity != "P1"]

    @property
    def blockers(self) -> list[DriftFinding]:
        return [f for f in self.findings if f.severity == "P1"]

    def as_dict(self) -> dict:
        return {
            "workspace_root": str(self.workspace_root),
            "manifest_present": self.manifest_present,
            "contract_present": self.contract_present,
            "modules_checked": self.modules_checked,
            "documents_checked": self.documents_checked,
            "code_refs_checked": self.code_refs_checked,
            "ok": self.ok,
            "blocking": self.blocking,
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
        out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL)
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
        return yaml.safe_load(fh)  # type: ignore[no-any-return]


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
                        path=doc_path,
                        detail=f"canon document {doc['id']} referenced by document-registry is missing",
                    )
                )

    _scan_canon_code_refs(root, report)
    _scan_docs_code_refs(root, report)
    _scan_consent_envelope(root, report)
    _scan_issuer_chain(root, report)
    _scan_ztmm_pillars(root, report)

    return report


def _scan_ztmm_pillars(root: Path, report: SubstrateReport) -> None:
    """UIAO_120 / §3.6 ZTMM pillar declaration scan.

    Every active adapter SHOULD declare ``ztmm-pillars:`` so the
    ZTMMScoreCalculator can attribute the adapter's evidence to the
    right CISA ZTMM v2.0 pillar(s). Missing declarations don't break
    anything at runtime — the calculator simply scores any undeclared
    pillar at TRADITIONAL maturity — but the substrate-status dashboard
    understates coverage.

    Tagged ``DRIFT-SCHEMA`` because the gap is structural canon
    metadata: the registry entry is missing a declared field, not an
    identity-trust-chain failure.

    Severity policy:
        - active adapter, no ``ztmm-pillars:`` key → P3 (advisory)
        - active adapter, ``ztmm-pillars: []`` → skipped (informational
          adapter; explicit empty list is a valid declaration)
        - reserved/inactive adapters → skipped
    """
    mod_path = root / MODERNIZATION_REGISTRY
    adapter_path = root / ADAPTER_REGISTRY
    for path in (mod_path, adapter_path):
        if not path.is_file():
            continue
        try:
            doc = _load_yaml(path)
        except yaml.YAMLError:
            continue
        if not doc:
            continue
        adapters = doc.get("adapters") or doc.get("modernization_adapters") or []
        if not isinstance(adapters, list):
            continue
        rel = str(path.relative_to(root))
        for entry in adapters:
            if not isinstance(entry, dict):
                continue
            adapter_id = str(entry.get("id", "")).strip()
            if not adapter_id:
                continue
            status = str(entry.get("status", "")).strip().lower()
            if status != "active":
                continue
            if "ztmm-pillars" not in entry:
                report.findings.append(
                    DriftFinding(
                        drift_class="DRIFT-SCHEMA",
                        severity="P3",
                        path=f"{rel}#{adapter_id}",
                        detail=(
                            f"active adapter '{adapter_id}' has no ztmm-pillars: "
                            "declaration; ZTMM pillar attribution unavailable"
                        ),
                    )
                )


def _scan_issuer_chain(root: Path, report: SubstrateReport) -> None:
    """UIAO_110 DRIFT-IDENTITY registry-hygiene scan.

    Every active adapter that declares ``certificate-anchored: true``
    MUST also declare a ``trust-anchor:`` (subject DN, fingerprint, or
    both). Without an anchor, the runtime issuer-chain validator has
    nothing to compare against, so the substrate's certificate-anchoring
    contract is unenforceable for that adapter.

    Severity policy:
        - active adapter, ``certificate-anchored: true``, no
          ``trust-anchor:`` key → P1 (substrate trust contract; runtime
          issuer-chain cannot be enforced)
        - active adapter, ``certificate-anchored: false`` → skipped
          (declared not anchored)
        - reserved/inactive adapters → skipped
    """
    mod_path = root / MODERNIZATION_REGISTRY
    adapter_path = root / ADAPTER_REGISTRY
    for path in (mod_path, adapter_path):
        if not path.is_file():
            continue
        try:
            doc = _load_yaml(path)
        except yaml.YAMLError:
            continue
        if not doc:
            continue
        adapters = doc.get("adapters") or doc.get("modernization_adapters") or []
        if not isinstance(adapters, list):
            continue
        rel = str(path.relative_to(root))
        for entry in adapters:
            if not isinstance(entry, dict):
                continue
            adapter_id = str(entry.get("id", "")).strip()
            if not adapter_id:
                continue
            status = str(entry.get("status", "")).strip().lower()
            if status != "active":
                continue
            cert_anchored = entry.get("certificate-anchored")
            if cert_anchored is not True:
                continue
            if "trust-anchor" not in entry:
                report.findings.append(
                    DriftFinding(
                        drift_class="DRIFT-IDENTITY",
                        severity="P1",
                        path=f"{rel}#{adapter_id}",
                        detail=(
                            f"active adapter '{adapter_id}' declares "
                            "certificate-anchored: true but has no trust-anchor: "
                            "declaration; issuer-chain validation cannot be enforced"
                        ),
                    )
                )


def _scan_consent_envelope(root: Path, report: SubstrateReport) -> None:
    """UIAO_110 DRIFT-AUTHZ registry-hygiene scan.

    Every active modernization adapter MUST declare a non-empty ``scope:``
    in canon. An adapter with no scope key — or an empty list — cannot be
    validated by the consent-envelope detector at runtime, which is itself
    a DRIFT-AUTHZ violation against the substrate trust contract.

    Severity policy:
        - missing ``scope:`` key on an active adapter → P1 (cannot validate)
        - explicit ``scope: []`` on an active adapter → P2 (validates, but
          no consent envelope means no audited surface)
        - reserved/inactive adapters → skipped
    """
    mod_path = root / MODERNIZATION_REGISTRY
    adapter_path = root / ADAPTER_REGISTRY
    for path in (mod_path, adapter_path):
        if not path.is_file():
            continue
        try:
            doc = _load_yaml(path)
        except yaml.YAMLError:
            continue
        if not doc:
            continue
        adapters = doc.get("adapters") or doc.get("modernization_adapters") or []
        if not isinstance(adapters, list):
            continue
        rel = str(path.relative_to(root))
        for entry in adapters:
            if not isinstance(entry, dict):
                continue
            adapter_id = str(entry.get("id", "")).strip()
            if not adapter_id:
                continue
            status = str(entry.get("status", "")).strip().lower()
            if status not in ("active",):
                continue
            if "scope" not in entry:
                report.findings.append(
                    DriftFinding(
                        drift_class="DRIFT-AUTHZ",
                        severity="P1",
                        path=f"{rel}#{adapter_id}",
                        detail=(
                            f"active adapter '{adapter_id}' has no scope: declaration; "
                            "consent envelope cannot be enforced"
                        ),
                    )
                )
                continue
            raw = entry.get("scope") or []
            if isinstance(raw, list) and len(raw) == 0:
                report.findings.append(
                    DriftFinding(
                        drift_class="DRIFT-AUTHZ",
                        severity="P2",
                        path=f"{rel}#{adapter_id}",
                        detail=(
                            f"active adapter '{adapter_id}' declares an empty scope: list; "
                            "no objects fall under the consent envelope"
                        ),
                    )
                )


def _scan_prose_for_code_refs(
    root: Path,
    scan_dir: Path,
    file_patterns: tuple[str, ...],
    source_label: str,
    report: SubstrateReport,
) -> None:
    """Scan a prose directory for code-path citations that don't resolve.

    Severity P2. A missing code path is a spec/impl drift warning — the
    substrate still loads and serves, but a narrative document (canon or
    derived docs) claims an implementation exists where it does not.

    Parameters
    ----------
    root
        Workspace root.
    scan_dir
        Directory to walk (`src/uiao/canon/` or `docs/`).
    file_patterns
        Glob patterns for files to scan (e.g. `("*.md",)` for canon or
        `("*.md", "*.qmd")` for docs).
    source_label
        Human-readable label for the finding detail ("canon document" or
        "docs document").
    report
        Mutated in place: `code_refs_checked` is incremented per hit and
        DRIFT-PROVENANCE P2 findings are appended for dangling refs.
    """
    if not scan_dir.is_dir():
        return

    # Track unique (file, code_path) pairs so the same dangling reference
    # inside the same file is reported once; distinct files citing the same
    # dangling path each report.
    seen: set[tuple[str, str]] = set()

    files: list[Path] = []
    for pattern in file_patterns:
        files.extend(scan_dir.rglob(pattern))

    for md_file in sorted(set(files)):
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for match in CODE_REF_PATTERN.finditer(text):
            code_rel = match.group(0)
            report.code_refs_checked += 1
            file_rel = md_file.relative_to(root).as_posix()
            key = (file_rel, code_rel)
            if key in seen:
                continue
            seen.add(key)
            if not (root / code_rel).exists():
                report.findings.append(
                    DriftFinding(
                        drift_class="DRIFT-PROVENANCE",
                        severity="P2",
                        path=code_rel,
                        detail=f"{source_label} {file_rel} cites code path {code_rel} which does not exist",
                    )
                )


def _scan_canon_code_refs(root: Path, report: SubstrateReport) -> None:
    """Scan canon `.md` files for references to code paths under
    `src/uiao/` (current) or the retired `impl/` prefix.
    """
    _scan_prose_for_code_refs(
        root=root,
        scan_dir=root / CANON_ROOT,
        file_patterns=("*.md",),
        source_label="canon document",
        report=report,
    )


def _scan_docs_code_refs(root: Path, report: SubstrateReport) -> None:
    """Scan `docs/` `.md` and `.qmd` files for code-path citations.

    Catches narrative drift in derived documentation (guides, narratives,
    Quarto articles) that still cites retired `impl/` or stale
    `src/uiao/` paths. Same DRIFT-PROVENANCE P2 semantics as the canon
    scan; extending coverage lets the substrate-drift gate fire on
    docs-only PRs when they introduce dangling code citations.
    """
    _scan_prose_for_code_refs(
        root=root,
        scan_dir=root / DOCS_ROOT,
        file_patterns=("*.md", "*.qmd"),
        source_label="docs document",
        report=report,
    )
