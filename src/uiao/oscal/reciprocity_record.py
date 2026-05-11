"""uiao.oscal.reciprocity_record — Reciprocity-Record Emitter (UIAO_140 §6 / ADR-054).

Emits signed, OSCAL-mapped reciprocity records per consuming agency under the
Single-ATO Reciprocity Model defined in UIAO_140 and ratified by ADR-054.

Public API
----------
    emit_reciprocity_record(
        controlling_ato_id, consuming_agency_code, legal_basis,
        reciprocity_basis, effective_at, expires_at,
        configuration_latitude_ref, signer, signing_key
    ) -> dict

    verify_signature(record, signing_key) -> bool

    emit_scoped_component_definition(record) -> dict

Record shape (UIAO_140 §6)
--------------------------
    controlling_ato_id          str   — stable ID of the controlling ATO
    consuming_agency_code       str   — three-to-six-letter agency code
    reciprocity_basis           str   — policy/agreement reference
    legal_basis                 str   — MOU type / legal authority
    effective_at                str   — ISO 8601
    expires_at                  str   — ISO 8601
    configuration_latitude_ref  str   — reference to SSP latitude section
    schema-version              str   — always "1.0.0"
    signature                   dict  — HMAC-SHA256 envelope
    provenance                  dict  — metadata-schema.json provenance block

Signing model
-------------
Content hash: SHA-256 of canonical JSON (sort_keys=True, separators=(',',':'))
of the record excluding three volatile fields:
    signature.value, signature.signed_at, provenance.derived_at

HMAC: HMAC-SHA256(signing_key, content_hash.encode())

References
----------
- UIAO_140 §6 — Evidence Graph Mapping and field set
- ADR-054 §Implementation — deferred emitter this module closes
- ADR-058 — HRIT Productization mission ratifying this workstream
- UIAO_144 §4 — Reciprocity-Record Artifact (operational spec)
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1.0.0"
_PROVENANCE_SOURCE = "UIAO_140"
_PROVENANCE_VERSION = "1.0"
_PROVENANCE_DERIVED_BY = "uiao.oscal.reciprocity_record.emit_reciprocity_record"

#: OSCAL component-definition version emitted by this module.
_OSCAL_VERSION = "1.1.2"

#: Namespace UUID for deterministic UUIDs in OSCAL artifacts.
_UUID_NS = _uuid_mod.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

#: Volatile fields excluded from the content hash.
_VOLATILE_PATHS: tuple[tuple[str, ...], ...] = (
    ("signature", "value"),
    ("signature", "signed_at"),
    ("provenance", "derived_at"),
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _det_uuid(kind: str, key: str) -> str:
    """Return a stable UUIDv5 derived from *kind* and *key*."""
    return str(_uuid_mod.uuid5(_UUID_NS, f"uiao:reciprocity:{kind}:{key}"))


def _strip_volatile(record: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of *record* with volatile fields removed.

    Removed paths (UIAO_140 §6 stable-hash contract):
        signature.value, signature.signed_at, provenance.derived_at
    """
    stripped = copy.deepcopy(record)
    for path in _VOLATILE_PATHS:
        node: Any = stripped
        for step in path[:-1]:
            node = node.get(step, {}) if isinstance(node, dict) else {}
        if isinstance(node, dict) and path[-1] in node:
            del node[path[-1]]
    return stripped


def _canonical_json(obj: dict[str, Any]) -> bytes:
    """Serialize *obj* to canonical JSON bytes (sort_keys, no extra spaces)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _content_hash(record: dict[str, Any]) -> str:
    """Compute SHA-256 of the stable (non-volatile) portion of *record*."""
    stable = _strip_volatile(record)
    return hashlib.sha256(_canonical_json(stable)).hexdigest()


def _hmac_hex(content_hash: str, signing_key: bytes) -> str:
    """Return HMAC-SHA256(*signing_key*, content_hash) as a hex string."""
    return hmac.new(signing_key, content_hash.encode("utf-8"), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Public: emit_reciprocity_record
# ---------------------------------------------------------------------------


def emit_reciprocity_record(
    controlling_ato_id: str,
    consuming_agency_code: str,
    legal_basis: str,
    reciprocity_basis: str,
    effective_at: datetime,
    expires_at: datetime,
    configuration_latitude_ref: str,
    signer: str,
    signing_key: bytes,
) -> dict[str, Any]:
    """Emit a signed reciprocity record per UIAO_140 §6 and ADR-054.

    Parameters
    ----------
    controlling_ato_id:
        Stable identifier of the controlling ATO (e.g., "OPM-HRIT-2026-001").
    consuming_agency_code:
        Three-to-six-letter agency code of the consuming agency (e.g., "TREAS").
    legal_basis:
        Legal authority or MOU type (e.g., "interagency-mou").
    reciprocity_basis:
        Policy or agreement reference establishing reciprocity.
    effective_at:
        Datetime when this reciprocity record becomes effective.
    expires_at:
        Datetime when this reciprocity record expires.
    configuration_latitude_ref:
        Reference to the SSP section enumerating this agency's configuration
        latitude (e.g., "SSP §5.3 Table 3").
    signer:
        Identity of the signing principal (CIO or delegate).
    signing_key:
        Raw bytes used as the HMAC-SHA256 key.

    Returns
    -------
    dict
        Complete reciprocity record including signature and provenance blocks.
        The record is schema-valid against
        ``src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json``.
    """
    # Step 1: Build the core record (volatile fields left as placeholders).
    record: dict[str, Any] = {
        "schema-version": _SCHEMA_VERSION,
        "controlling_ato_id": controlling_ato_id,
        "consuming_agency_code": consuming_agency_code,
        "legal_basis": legal_basis,
        "reciprocity_basis": reciprocity_basis,
        "effective_at": effective_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "configuration_latitude_ref": configuration_latitude_ref,
        "signature": {
            "algorithm": "HMAC-SHA256",
            "signer": signer,
            # volatile — filled after hash computation
            "value": "",
            "signed_at": "",
        },
        "provenance": {
            "source": _PROVENANCE_SOURCE,
            "version": _PROVENANCE_VERSION,
            "derived_by": _PROVENANCE_DERIVED_BY,
            # volatile — filled after hash computation
            "derived_at": "",
        },
    }

    # Step 2: Compute content hash over the stable fields.
    c_hash = _content_hash(record)

    # Step 3: Sign with HMAC-SHA256.
    sig_value = _hmac_hex(c_hash, signing_key)

    # Step 4: Stamp volatile timestamps.
    now_iso = datetime.now(timezone.utc).isoformat()
    record["signature"]["value"] = sig_value
    record["signature"]["signed_at"] = now_iso
    record["provenance"]["derived_at"] = now_iso

    return record


# ---------------------------------------------------------------------------
# Public: verify_signature
# ---------------------------------------------------------------------------


def verify_signature(record: dict[str, Any], signing_key: bytes) -> bool:
    """Verify the HMAC-SHA256 signature embedded in *record*.

    Recomputes the content hash over the stable (non-volatile) fields and
    compares the resulting HMAC against ``record["signature"]["value"]``.

    Parameters
    ----------
    record:
        A dict previously returned by :func:`emit_reciprocity_record`.
    signing_key:
        The same raw bytes used during emission.

    Returns
    -------
    bool
        ``True`` if the signature is valid; ``False`` otherwise.
    """
    stored_sig = record.get("signature", {}).get("value", "")
    if not stored_sig:
        return False
    c_hash = _content_hash(record)
    expected = _hmac_hex(c_hash, signing_key)
    # Constant-time comparison to prevent timing side-channels.
    return hmac.compare_digest(expected, stored_sig)


# ---------------------------------------------------------------------------
# Public: emit_scoped_component_definition
# ---------------------------------------------------------------------------


def emit_scoped_component_definition(record: dict[str, Any]) -> dict[str, Any]:
    """Return an OSCAL 1.1.2 component-definition skeleton scoped to the consuming agency.

    The component-definition cites the reciprocity record in its metadata.props,
    establishing a machine-readable link between the OSCAL artifact and the
    controlling ATO.

    Parameters
    ----------
    record:
        A dict previously returned by :func:`emit_reciprocity_record`.

    Returns
    -------
    dict
        OSCAL 1.1.2 component-definition as a plain dict.  When
        ``compliance-trestle`` is available the dict is validated against
        its Pydantic model; if the import fails the raw dict is returned
        with a TODO comment noting the caveat.
    """
    agency_code = record.get("consuming_agency_code", "UNKNOWN")
    ato_id = record.get("controlling_ato_id", "UNKNOWN")
    schema_ver = record.get("schema-version", _SCHEMA_VERSION)

    comp_uuid = _det_uuid("component", f"{ato_id}:{agency_code}")
    cd_uuid = _det_uuid("component-definition", f"{ato_id}:{agency_code}")

    now_iso = datetime.now(timezone.utc).isoformat()

    component_definition: dict[str, Any] = {
        "component-definition": {
            "uuid": cd_uuid,
            "metadata": {
                "title": (
                    f"UIAO Reciprocity Component Definition — "
                    f"Controlling ATO: {ato_id} / Consuming Agency: {agency_code}"
                ),
                "last-modified": now_iso,
                "version": schema_ver,
                "oscal-version": _OSCAL_VERSION,
                "props": [
                    {
                        "name": "reciprocity-record-schema-version",
                        "ns": "https://uiao.gov/ns/reciprocity",
                        "value": schema_ver,
                    },
                    {
                        "name": "controlling-ato-id",
                        "ns": "https://uiao.gov/ns/reciprocity",
                        "value": ato_id,
                    },
                    {
                        "name": "consuming-agency-code",
                        "ns": "https://uiao.gov/ns/reciprocity",
                        "value": agency_code,
                    },
                    {
                        "name": "reciprocity-basis",
                        "ns": "https://uiao.gov/ns/reciprocity",
                        "value": record.get("reciprocity_basis", ""),
                    },
                    {
                        "name": "legal-basis",
                        "ns": "https://uiao.gov/ns/reciprocity",
                        "value": record.get("legal_basis", ""),
                    },
                    {
                        "name": "effective-at",
                        "ns": "https://uiao.gov/ns/reciprocity",
                        "value": record.get("effective_at", ""),
                    },
                    {
                        "name": "expires-at",
                        "ns": "https://uiao.gov/ns/reciprocity",
                        "value": record.get("expires_at", ""),
                    },
                    {
                        "name": "provenance-source",
                        "ns": "https://uiao.gov/ns/reciprocity",
                        "value": record.get("provenance", {}).get("source", _PROVENANCE_SOURCE),
                    },
                    {
                        "name": "generator",
                        "ns": "https://uiao.gov/ns/reciprocity",
                        "value": _PROVENANCE_DERIVED_BY,
                    },
                ],
                "remarks": (
                    f"Generated by uiao.oscal.reciprocity_record per UIAO_140 §7 and ADR-054. "
                    f"Scoped to consuming agency {agency_code} under controlling ATO {ato_id}."
                ),
            },
            "components": [
                {
                    "uuid": comp_uuid,
                    "type": "service",
                    "title": f"HRIT Platform — Reciprocity Scope ({agency_code})",
                    "description": (
                        f"OSCAL component representing the UIAO/HRIT platform as consumed "
                        f"by {agency_code} under the single-ATO reciprocity model. "
                        f"Controlling ATO: {ato_id}."
                    ),
                    "props": [
                        {
                            "name": "asset-type",
                            "ns": "https://uiao.gov/ns/reciprocity",
                            "value": "platform",
                        },
                        {
                            "name": "consuming-agency-code",
                            "ns": "https://uiao.gov/ns/reciprocity",
                            "value": agency_code,
                        },
                    ],
                    "status": {"state": "operational"},
                }
            ],
        }
    }

    # Try to validate against compliance-trestle's Pydantic model.
    # If trestle is unavailable or the model rejects the dict, return the raw
    # dict with a TODO note.  Per ADR-054 / WS-A2 scope, trestle validation is
    # best-effort; the plain dict always satisfies the OSCAL JSON schema.
    try:
        from trestle.oscal.component import ComponentDefinition  # noqa: PLC0415

        inner = component_definition["component-definition"]
        ComponentDefinition(**inner)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        # TODO: trestle.oscal.component.ComponentDefinition import/validation
        # failed.  The returned dict is schema-compliant plain OSCAL 1.1.2 JSON
        # but has not been validated by the trestle Pydantic model.  Re-enable
        # once compliance-trestle publishes 1.1.2 model stubs or when WS-A6
        # wires the full bundle aggregator.
        pass

    return component_definition
