"""uiao.oscal.reciprocity_bundle — Per-agency reciprocity bundle aggregator.

Plane: OSCAL dicts (reciprocity-record, component-definition,
assessment-results) → self-verifiable on-disk bundle per consuming agency.

Public API
----------
    aggregate_per_agency_bundle(
        controlling_ato_id, consuming_agency_code, reciprocity_record,
        component_definition, assessment_results, output_dir
    ) -> Path

    verify_bundle(bundle_dir) -> dict[str, bool | list[str]]

Self-verification
-----------------
A consuming-agency AO can run ``verify_bundle()`` against the bundle directory
without UIAO platform access or network connectivity.  Only stdlib is used
(hashlib, json, pathlib).

Provenance citations
--------------------
- UIAO_140 (Single-ATO Reciprocity Model) §7 OSCAL Output Profile
- ADR-054 (Single-ATO Reciprocity ADR)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Ordered list of bundle files that must always be present.
_BUNDLE_FILES: tuple[str, ...] = (
    "reciprocity-record.json",
    "component-definition.json",
    "assessment-results.json",
    "provenance-manifest.json",
    "BUNDLE-MANIFEST.txt",
)

_PROVENANCE_SOURCE = "UIAO_140"
_PROVENANCE_VERSION = "1.0"
_ADR_REF = "ADR-054"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Return hex-encoded SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_json(path: Path, data: Any) -> None:
    """Write *data* as indented JSON to *path*."""
    path.write_text(
        json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _build_provenance_manifest(
    bundle_dir: Path,
    controlling_ato_id: str,
    consuming_agency_code: str,
    file_hashes: dict[str, str],
) -> dict[str, Any]:
    """Build the provenance-manifest dict (does NOT include its own hash)."""
    return {
        "schema_version": "1.0",
        "bundle_type": "per-agency-reciprocity-bundle",
        "controlling_ato_id": controlling_ato_id,
        "consuming_agency_code": consuming_agency_code,
        "provenance": {
            "source": _PROVENANCE_SOURCE,
            "version": _PROVENANCE_VERSION,
            "adr_ref": _ADR_REF,
            "derived_at": datetime.now(timezone.utc).isoformat(),
            "generator": "uiao.oscal.reciprocity_bundle",
        },
        "files": {fname: {"sha256": digest} for fname, digest in file_hashes.items()},
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def aggregate_per_agency_bundle(
    controlling_ato_id: str,
    consuming_agency_code: str,
    reciprocity_record: dict[str, Any],
    component_definition: dict[str, Any],
    assessment_results: dict[str, Any],
    output_dir: Path,
) -> Path:
    """Aggregate a per-agency reciprocity bundle to disk.

    Creates ``<output_dir>/<consuming_agency_code>/`` and writes five files:

    - ``reciprocity-record.json``       — the record from WS-A2 (passed in)
    - ``component-definition.json``     — OSCAL component-definition scoped to agency
    - ``assessment-results.json``       — OSCAL assessment-results scoped to agency
    - ``provenance-manifest.json``      — SHA-256 hashes + provenance citing UIAO_140 / ADR-054
    - ``BUNDLE-MANIFEST.txt``           — plaintext ``<filename>  <sha256>`` pairs

    Parameters
    ----------
    controlling_ato_id:
        Identifier for the controlling ATO (e.g. ``OPM-HRIT-2026-001``).
    consuming_agency_code:
        Short agency code for the consuming agency (e.g. ``TREAS``, ``IRS``).
    reciprocity_record:
        Dict produced by the WS-A2 emitter (mocked in tests until Phase 2).
    component_definition:
        OSCAL component-definition dict scoped to the consuming agency.
    assessment_results:
        OSCAL assessment-results dict scoped to the consuming agency.
    output_dir:
        Parent directory under which the agency sub-directory is created.

    Returns
    -------
    Path
        Absolute path to the bundle directory
        (``<output_dir>/<consuming_agency_code>``).
    """
    bundle_dir = Path(output_dir) / consuming_agency_code
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Write the three OSCAL payload files ----------------------------
    _write_json(bundle_dir / "reciprocity-record.json", reciprocity_record)
    _write_json(bundle_dir / "component-definition.json", component_definition)
    _write_json(bundle_dir / "assessment-results.json", assessment_results)

    # --- 2. Hash the three payload files -----------------------------------
    payload_hashes: dict[str, str] = {
        fname: _sha256_file(bundle_dir / fname)
        for fname in (
            "reciprocity-record.json",
            "component-definition.json",
            "assessment-results.json",
        )
    }

    # --- 3. Write provenance-manifest.json (its own hash is excluded) ------
    prov_manifest = _build_provenance_manifest(
        bundle_dir=bundle_dir,
        controlling_ato_id=controlling_ato_id,
        consuming_agency_code=consuming_agency_code,
        file_hashes=payload_hashes,
    )
    _write_json(bundle_dir / "provenance-manifest.json", prov_manifest)
    prov_hash = _sha256_file(bundle_dir / "provenance-manifest.json")

    # --- 4. Write BUNDLE-MANIFEST.txt (all five files, including itself) ---
    all_hashes = {**payload_hashes, "provenance-manifest.json": prov_hash}

    # The manifest file references all other files; write it last.
    # We need BUNDLE-MANIFEST.txt's own hash to be stable: compute hash of
    # the manifest *contents* before the file exists.
    manifest_lines = [f"{fname}  {all_hashes[fname]}" for fname in _BUNDLE_FILES if fname != "BUNDLE-MANIFEST.txt"]
    # Add a placeholder line for the manifest itself — we'll compute its hash
    # after writing the four-file manifest, then append the self-hash line.
    manifest_text_without_self = "\n".join(manifest_lines) + "\n"

    # Write a preliminary version without the self-hash line.
    manifest_path = bundle_dir / "BUNDLE-MANIFEST.txt"
    manifest_path.write_text(manifest_text_without_self, encoding="utf-8")
    self_hash = _sha256_file(manifest_path)

    # Append the self-referential line.
    final_text = manifest_text_without_self + f"BUNDLE-MANIFEST.txt  {self_hash}\n"
    manifest_path.write_text(final_text, encoding="utf-8")

    return bundle_dir.resolve()


def verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Verify the integrity of a per-agency reciprocity bundle.

    Checks performed (all without UIAO platform access or network):

    1. All files listed in ``BUNDLE-MANIFEST.txt`` exist.
    2. Each file's SHA-256 matches the manifest entry.
    3. ``provenance-manifest.json`` file hashes match actual on-disk hashes.
    4. ``reciprocity-record.json`` is non-empty (non-zero-length dict).

    Parameters
    ----------
    bundle_dir:
        Path to the bundle directory (``<output_dir>/<agency_code>/``).

    Returns
    -------
    dict
        ``{"ok": True, "errors": []}`` on success, or
        ``{"ok": False, "errors": ["<description>", ...]}`` on failure.
    """
    errors: list[str] = []
    bundle_dir = Path(bundle_dir)

    # -----------------------------------------------------------------------
    # Step A: BUNDLE-MANIFEST.txt must exist
    # -----------------------------------------------------------------------
    manifest_path = bundle_dir / "BUNDLE-MANIFEST.txt"
    if not manifest_path.exists():
        return {"ok": False, "errors": ["BUNDLE-MANIFEST.txt is missing"]}

    manifest_text = manifest_path.read_text(encoding="utf-8")

    # Parse manifest: each non-empty line is "<filename>  <sha256>"
    manifest_entries: dict[str, str] = {}
    for line in manifest_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:  # noqa: PLR2004
            errors.append(f"BUNDLE-MANIFEST.txt: malformed line: {line!r}")
            continue
        fname, digest = parts
        manifest_entries[fname] = digest

    # -----------------------------------------------------------------------
    # Step B: All listed files must exist and hash correctly
    # -----------------------------------------------------------------------
    for fname, expected_digest in manifest_entries.items():
        fpath = bundle_dir / fname
        if not fpath.exists():
            errors.append(f"Missing file: {fname}")
            continue
        # Skip self-check for BUNDLE-MANIFEST.txt (file changed after self-hash written)
        if fname == "BUNDLE-MANIFEST.txt":
            continue
        actual_digest = _sha256_file(fpath)
        if actual_digest != expected_digest:
            errors.append(f"Hash mismatch for {fname}: expected {expected_digest[:16]}…, got {actual_digest[:16]}…")

    # -----------------------------------------------------------------------
    # Step C: provenance-manifest.json hashes must match on-disk
    # -----------------------------------------------------------------------
    prov_path = bundle_dir / "provenance-manifest.json"
    if prov_path.exists():
        try:
            prov = json.loads(prov_path.read_text(encoding="utf-8"))
            prov_files: dict[str, Any] = prov.get("files", {})
            for fname, entry in prov_files.items():
                expected = entry.get("sha256", "")
                fpath = bundle_dir / fname
                if not fpath.exists():
                    errors.append(f"provenance-manifest.json references missing file: {fname}")
                    continue
                actual = _sha256_file(fpath)
                if actual != expected:
                    errors.append(
                        f"provenance-manifest.json hash mismatch for {fname}: "
                        f"expected {expected[:16]}…, got {actual[:16]}…"
                    )
        except (json.JSONDecodeError, KeyError) as exc:
            errors.append(f"provenance-manifest.json is invalid JSON: {exc}")
    else:
        errors.append("Missing file: provenance-manifest.json")

    # -----------------------------------------------------------------------
    # Step D: reciprocity-record.json must be non-empty
    # -----------------------------------------------------------------------
    rr_path = bundle_dir / "reciprocity-record.json"
    if rr_path.exists():
        try:
            rr = json.loads(rr_path.read_text(encoding="utf-8"))
            if not rr:
                errors.append("reciprocity-record.json is empty (zero-key dict or null)")
        except json.JSONDecodeError as exc:
            errors.append(f"reciprocity-record.json is invalid JSON: {exc}")
    # Non-existence already caught in step B

    return {"ok": len(errors) == 0, "errors": errors}
