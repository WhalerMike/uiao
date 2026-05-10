"""FedRAMP CR26 Catalog conformance adapter.

ADR-061 D3 slot: read-only reconciler between the vendored CR26 snapshot
at ``src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/<sha>/``
and ``src/uiao/ksi/rules/*.yaml``. The adapter never writes to the
target; ``ssot-mutation`` is ``never``. Snapshot is identified by the
upstream commit SHA per ADR-061 D2.

Two drift classes are emitted (UIAO_133 §2):

* ``DRIFT-SCHEMA`` — catalog shape diverges in a way that breaks the
  emitter contract (missing the ``KSI`` group, missing one of the ten
  expected KSI themes, malformed group/control structure).
* ``DRIFT-PROVENANCE`` — a CR26 control ID or KSI theme cited by uiao
  no longer resolves in the snapshot.

Status is ``proposed`` while the adapter stabilizes; once governance
review accepts ADR-061 and the substrate begins citing CR26 control
IDs in ``fedramp:ksi-mapping-source`` props, status advances to
``active``.

Canon references:
    - ADR-061 (catalog vendoring policy)
    - UIAO_133 §2 (KSI emission + drift classes)
    - ADR-047 (FedRAMP 20x integration)
    - src/uiao/canon/adapter-registry.yaml — id: fedramp-cr26-catalog
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

__all__ = [
    "ADAPTER_ID",
    "STATUS",
    "DEFAULT_SNAPSHOT_SHA",
    "EXPECTED_KSI_THEMES",
    "Cr26SnapshotNotFound",
    "Cr26CatalogMalformed",
    "Finding",
    "Cr26CatalogAdapter",
    "default_snapshot_dir",
    "load_catalog",
    "enumerate_ksi_themes",
    "enumerate_ksi_controls",
    "reconcile",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ADAPTER_ID: str = "fedramp-cr26-catalog"
STATUS: str = "proposed"

DEFAULT_SNAPSHOT_SHA: str = "c31eb04c082d6d578a26a00de9a482707ab7a00c"

EXPECTED_KSI_THEMES: tuple[str, ...] = (
    "KSI-CMT",
    "KSI-CNA",
    "KSI-CED",
    "KSI-IAM",
    "KSI-INR",
    "KSI-MLA",
    "KSI-PIY",
    "KSI-RPL",
    "KSI-SVC",
    "KSI-SCR",
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class Cr26SnapshotNotFound(FileNotFoundError):
    """Snapshot directory does not exist or is missing the catalog JSON."""


class Cr26CatalogMalformed(ValueError):
    """Catalog JSON is present but missing required top-level structure."""


# ---------------------------------------------------------------------------
# Finding dataclass — local to the adapter; reconciliation produces a list
# of these. Callers serialize via ``Finding.to_dict()`` for JSON output.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    drift_class: str
    severity: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Snapshot resolution + catalog loading
# ---------------------------------------------------------------------------


def default_snapshot_dir(sha: str = DEFAULT_SNAPSHOT_SHA) -> Path:
    """Return the on-disk path of the pinned snapshot bundled as package data.

    Uses ``importlib.resources`` so the adapter works whether the
    package is installed editably or as a wheel (AGENTS.md I4).
    """
    canon_root = resources.files("uiao.canon")
    candidate = canon_root.joinpath("compliance", "reference", "fedramp-cr26", "snapshot", sha)
    return Path(str(candidate))


def load_catalog(snapshot_dir: Path) -> dict[str, Any]:
    """Load the CR26 catalog JSON from a snapshot directory.

    Raises :class:`Cr26SnapshotNotFound` if the directory or catalog
    file is missing, :class:`Cr26CatalogMalformed` if the JSON parses
    but lacks the expected top-level ``catalog`` key.
    """
    catalog_path = snapshot_dir / "catalog" / "json" / "FedRAMP_CR26_catalog.json"
    if not catalog_path.is_file():
        raise Cr26SnapshotNotFound(
            f"CR26 catalog JSON not found at {catalog_path}. "
            "Snapshot may be missing or pinned to a SHA without a vendored "
            "snapshot directory; see ADR-061 D2."
        )
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Cr26CatalogMalformed(f"CR26 catalog JSON at {catalog_path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or "catalog" not in data:
        raise Cr26CatalogMalformed(f"CR26 catalog at {catalog_path} is missing top-level 'catalog' key.")
    return data


# ---------------------------------------------------------------------------
# Catalog enumerators
# ---------------------------------------------------------------------------


def _ksi_group(catalog: dict[str, Any]) -> dict[str, Any] | None:
    for group in catalog.get("catalog", {}).get("groups", []) or []:
        if group.get("id") == "KSI":
            return group
    return None


def enumerate_ksi_themes(catalog: dict[str, Any]) -> list[str]:
    """Return the list of KSI theme IDs (e.g. ``KSI-IAM``) in catalog order."""
    ksi = _ksi_group(catalog)
    if ksi is None:
        return []
    return [g["id"] for g in ksi.get("groups", []) or [] if "id" in g]


def enumerate_ksi_controls(
    catalog: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    """Return ``{theme_id: [{"id": control_id, "title": ...}, ...]}``.

    The mapping preserves catalog order. Themes with zero controls
    map to an empty list.
    """
    ksi = _ksi_group(catalog)
    if ksi is None:
        return {}
    out: dict[str, list[dict[str, str]]] = {}
    for theme in ksi.get("groups", []) or []:
        theme_id = theme.get("id")
        if not theme_id:
            continue
        controls: list[dict[str, str]] = []
        for ctl in theme.get("controls", []) or []:
            ctl_id = ctl.get("id")
            if not ctl_id:
                continue
            controls.append({"id": ctl_id, "title": ctl.get("title", "")})
        out[theme_id] = controls
    return out


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


def _ksi_rule_files(ksi_rules_dir: Path) -> list[Path]:
    return sorted(p for p in ksi_rules_dir.glob("KSI-*.yaml") if p.is_file())


def reconcile(
    snapshot_dir: Path | None = None,
    ksi_rules_dir: Path | None = None,
    expected_themes: tuple[str, ...] = EXPECTED_KSI_THEMES,
) -> list[Finding]:
    """Compare a CR26 snapshot against the local KSI rule corpus.

    Returns a list of :class:`Finding` objects. Empty list means no
    drift was detected. The adapter never raises on drift — drift is
    the *return value*. Snapshot loading errors still raise.
    """
    snapshot_dir = snapshot_dir or default_snapshot_dir()
    if ksi_rules_dir is None:
        ksi_rules_dir = Path(str(resources.files("uiao.ksi").joinpath("rules")))

    findings: list[Finding] = []
    catalog = load_catalog(snapshot_dir)

    # --- DRIFT-SCHEMA: catalog must expose a KSI top-level group. ---
    if _ksi_group(catalog) is None:
        findings.append(
            Finding(
                drift_class="DRIFT-SCHEMA",
                severity="P1",
                summary="CR26 catalog missing top-level 'KSI' group.",
                details={
                    "snapshot_dir": str(snapshot_dir),
                    "found_top_level_groups": [g.get("id") for g in catalog.get("catalog", {}).get("groups", []) or []],
                },
            )
        )
        # No point checking themes if the KSI group itself is absent.
        return findings

    present_themes = set(enumerate_ksi_themes(catalog))

    # --- DRIFT-PROVENANCE: expected themes must resolve. ---
    for theme in expected_themes:
        if theme not in present_themes:
            findings.append(
                Finding(
                    drift_class="DRIFT-PROVENANCE",
                    severity="P2",
                    summary=f"Expected KSI theme {theme} not present in CR26 snapshot.",
                    details={
                        "snapshot_dir": str(snapshot_dir),
                        "expected_theme": theme,
                        "present_themes": sorted(present_themes),
                    },
                )
            )

    # --- DRIFT-SCHEMA: every theme should have at least one control. ---
    for theme_id, controls in enumerate_ksi_controls(catalog).items():
        if not controls:
            findings.append(
                Finding(
                    drift_class="DRIFT-SCHEMA",
                    severity="P3",
                    summary=f"KSI theme {theme_id} has zero controls.",
                    details={
                        "snapshot_dir": str(snapshot_dir),
                        "theme": theme_id,
                    },
                )
            )

    # --- DRIFT-PROVENANCE: local KSI rules dir must be readable. ---
    # The current local KSI corpus (KSI-NNN numbered) is a different
    # vocabulary from CR26 theme-prefixed IDs — the mapping itself is
    # tracked in a UIAO_NNN companion doc, not this adapter. We only
    # check rule-file readability here so a misconfigured rules dir
    # surfaces as a finding rather than a silent skip.
    if not ksi_rules_dir.is_dir():
        findings.append(
            Finding(
                drift_class="DRIFT-PROVENANCE",
                severity="P2",
                summary=f"KSI rules directory not found at {ksi_rules_dir}.",
                details={"ksi_rules_dir": str(ksi_rules_dir)},
            )
        )
    elif not _ksi_rule_files(ksi_rules_dir):
        findings.append(
            Finding(
                drift_class="DRIFT-PROVENANCE",
                severity="P3",
                summary=f"KSI rules directory {ksi_rules_dir} contains no KSI-*.yaml files.",
                details={"ksi_rules_dir": str(ksi_rules_dir)},
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Adapter class — thin OO wrapper so callers that prefer instantiation
# get a stable surface. Function API above is the load-bearing form.
# ---------------------------------------------------------------------------


class Cr26CatalogAdapter:
    """Read-only reconciler for the vendored FedRAMP CR26 OSCAL snapshot."""

    ADAPTER_ID: str = ADAPTER_ID
    STATUS: str = STATUS

    def __init__(
        self,
        snapshot_dir: Path | None = None,
        ksi_rules_dir: Path | None = None,
    ) -> None:
        self.snapshot_dir = snapshot_dir or default_snapshot_dir()
        self.ksi_rules_dir = ksi_rules_dir

    def load_catalog(self) -> dict[str, Any]:
        return load_catalog(self.snapshot_dir)

    def reconcile(self) -> list[Finding]:
        return reconcile(self.snapshot_dir, self.ksi_rules_dir)
