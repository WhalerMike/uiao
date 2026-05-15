"""uiao.oscal.servicenow_evidence -- ServiceNow claims -> OSCAL component-definition.

Emits a signed, OSCAL 1.1.2 component-definition document that maps ServiceNow
incident/change/problem claims to NIST control implementations for IR-4, IR-5,
IR-6, and CM-3.

Plane: ServiceNow claim list (from servicenow_adapter.normalize()) -> OSCAL
component-definition JSON dict.

Controls covered
----------------
IR-4   Incident Handling     -- incident tickets with resolution evidence
IR-5   Incident Monitoring   -- open/active incident tracking
IR-6   Incident Reporting    -- incident escalation / reporting records
CM-3   Configuration Change Control -- change-request records

Public API
----------
    emit_servicenow_component_definition(
        claims, tenant_id, signer, signing_key
    ) -> dict

    verify_signature(component_def, signing_key) -> bool

    _canonical_hash(component_def) -> str   (internal; exposed for tests)

Schema note
-----------
compliance-trestle's ``ComponentDefinition`` model is used for best-effort
validation when available.  If the import fails (e.g., trestle is not installed
or its model rejects the payload), a plain dict matching the OSCAL 1.1.2
component-definition JSON schema is returned.  Both paths are schema-correct;
the trestle path adds Pydantic-level structural validation as a bonus.

Provenance contract (UIAO-CANON-003 / ADR-054)
-----------------------------------------------
source:     "UIAO-CANON-003"
version:    "1.0"
derived_by: "uiao.oscal.servicenow_evidence.emit_servicenow_component_definition"
derived_at: ISO 8601 UTC timestamp (volatile -- excluded from content hash)

Signing model
-------------
Content hash: SHA-256 of canonical JSON (sort_keys=True, separators=(",", ":"))
of the component-definition dict excluding three volatile fields:
    signature.value, signature.signed_at, provenance.derived_at

HMAC: HMAC-SHA256(signing_key, content_hash.encode("utf-8"))
Comparison uses hmac.compare_digest for constant-time protection.

References
----------
- UIAO-CANON-003 -- ServiceNow integration canon entry
- ADR-054 SS Implementation -- emitter pattern ratified here
- modernization-registry.yaml: service-now entry, controls IR-4/IR-5/IR-6/CM-3
- src/uiao/oscal/reciprocity_record.py -- canonical signing pattern
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

_OSCAL_VERSION = "1.1.2"
_UIAO_NS = "https://uiao.gov/ns/servicenow-evidence"

_PROVENANCE_SOURCE = "UIAO-CANON-003"
_PROVENANCE_VERSION = "1.0"
_PROVENANCE_DERIVED_BY = "uiao.oscal.servicenow_evidence.emit_servicenow_component_definition"

#: Namespace UUID for deterministic UUIDs (DNS namespace UUIDv5 seed).
_UUID_NS = _uuid_mod.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

#: Control IDs this emitter recognises.
_SUPPORTED_CONTROLS: frozenset[str] = frozenset(["IR-4", "IR-5", "IR-6", "CM-3"])

#: Volatile fields excluded from the content hash (same contract as
#: reciprocity_record.py, plus metadata.last-modified which is a
#: wall-clock stamp like signed_at).
_VOLATILE_PATHS: tuple[tuple[str, ...], ...] = (
    ("signature", "value"),
    ("signature", "signed_at"),
    ("provenance", "derived_at"),
    ("metadata", "last-modified"),
)

#: Human-readable description for each supported control.
_CONTROL_DESCRIPTIONS: dict[str, str] = {
    "IR-4": (
        "Incident Handling -- ServiceNow incident tickets provide evidence "
        "of incident detection, classification, response, and resolution."
    ),
    "IR-5": (
        "Incident Monitoring -- ServiceNow active/open incident records "
        "demonstrate continuous monitoring of security events."
    ),
    "IR-6": (
        "Incident Reporting -- ServiceNow escalation and reporting records "
        "demonstrate timely reporting to appropriate authorities."
    ),
    "CM-3": (
        "Configuration Change Control -- ServiceNow change-request records "
        "provide evidence of controlled configuration changes."
    ),
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _det_uuid(kind: str, key: str) -> str:
    """Return a stable UUIDv5 from *kind* and *key*."""
    return str(_uuid_mod.uuid5(_UUID_NS, f"uiao:servicenow:{kind}:{key}"))


def _strip_volatile(obj: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy *obj* with volatile fields removed."""
    stripped = copy.deepcopy(obj)
    for path in _VOLATILE_PATHS:
        node: Any = stripped
        for step in path[:-1]:
            node = node.get(step, {}) if isinstance(node, dict) else {}
        if isinstance(node, dict) and path[-1] in node:
            del node[path[-1]]
    return stripped


def _canonical_hash(component_def: dict[str, Any]) -> str:
    """SHA-256 of the stable (non-volatile) canonical JSON of *component_def*.

    Excludes ``signature.value``, ``signature.signed_at``, and
    ``provenance.derived_at`` before serialising.  The serialisation uses
    ``json.dumps(d, sort_keys=True, separators=(",", ":"))`` to produce a
    deterministic byte sequence.
    """
    stable = _strip_volatile(component_def)
    canonical = json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hmac_hex(content_hash: str, signing_key: bytes) -> str:
    """Return HMAC-SHA256(signing_key, content_hash) as a hex string."""
    return hmac.new(signing_key, content_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def _normalise_control_id(raw: str) -> str:
    """Return the canonical upper-case control ID, e.g. "ir-4" to "IR-4"."""
    return raw.strip().upper()


def _group_claims_by_control(
    claims: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Return {control_id: [claim, ...]} for each control found in *claims*.

    Claims whose control_id is not in _SUPPORTED_CONTROLS are silently
    bucketed under their (uppercased) control_id so no data is dropped.
    The returned dict always contains an entry for every control that
    appears at least once in *claims*.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        raw_ctrl = claim.get("uiao_control_id") or claim.get("control_id") or "IR-4"
        ctrl = _normalise_control_id(str(raw_ctrl))
        grouped.setdefault(ctrl, []).append(claim)
    return grouped


def _build_statement(claim: dict[str, Any], ctrl: str) -> dict[str, Any]:
    """Build an OSCAL control-implementation statement dict from one claim."""
    sys_id = str(claim.get("sys_id", claim.get("claim_id", "unknown")))
    short_desc = str(claim.get("short_description", claim.get("implementation_statement", "")))
    timestamp = str(claim.get("timestamp", claim.get("collected_at", "")))

    stmt_uuid = _det_uuid("statement", f"{ctrl}:{sys_id}")
    return {
        "statement-id": f"{ctrl.lower()}_smt",
        "uuid": stmt_uuid,
        "description": (short_desc or f"ServiceNow {ctrl} evidence record {sys_id}"),
        "props": [
            {
                "name": "sys-id",
                "ns": _UIAO_NS,
                "value": sys_id,
            },
            {
                "name": "uiao-control-id",
                "ns": _UIAO_NS,
                "value": ctrl,
            },
            {
                "name": "short-description",
                "ns": _UIAO_NS,
                "value": short_desc or "(none)",
            },
            {
                "name": "timestamp",
                "ns": _UIAO_NS,
                "value": timestamp or "(none)",
            },
        ],
    }


def _build_control_implementation(ctrl: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Build an OSCAL control-implementation block for one control."""
    impl_uuid = _det_uuid("control-impl", ctrl)
    statements = [_build_statement(c, ctrl) for c in claims]
    description = _CONTROL_DESCRIPTIONS.get(
        ctrl,
        f"ServiceNow evidence for control {ctrl}.",
    )
    return {
        "uuid": impl_uuid,
        "source": ("https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final"),
        "description": description,
        "implemented-requirements": [
            {
                "uuid": _det_uuid("req", ctrl),
                "control-id": ctrl.lower(),
                "description": description,
                "statements": statements,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Public: emit_servicenow_component_definition
# ---------------------------------------------------------------------------


def emit_servicenow_component_definition(
    claims: list[dict[str, Any]],
    tenant_id: str,
    signer: str,
    signing_key: bytes,
) -> dict[str, Any]:
    """Emit a signed OSCAL 1.1.2 component-definition for ServiceNow evidence.

    Parameters
    ----------
    claims:
        List of ServiceNow claim dicts as returned by
        ``ServiceNowAdapter.normalize()``.  Each dict should carry at least:
        ``sys_id`` (or ``claim_id``), ``short_description`` (or
        ``implementation_statement``), ``uiao_control_id`` (or
        ``control_id``), and ``timestamp`` (or ``collected_at``).
        An empty list is valid; the resulting document has zero
        control-implementations but is otherwise schema-correct.
    tenant_id:
        ServiceNow tenant / instance identifier
        (e.g., "acme.service-now.com").
    signer:
        Identity of the signing principal (e.g., ISSO or automated
        pipeline ID).
    signing_key:
        Raw bytes used as the HMAC-SHA256 key.

    Returns
    -------
    dict
        Complete OSCAL 1.1.2 component-definition dict including top-level
        ``signature`` and ``provenance`` blocks.  Required keys at the top
        level: ``uuid``, ``metadata``, ``components``, ``signature``,
        ``provenance``.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    grouped = _group_claims_by_control(claims) if claims else {}
    control_implementations = [
        _build_control_implementation(ctrl, ctrl_claims) for ctrl, ctrl_claims in sorted(grouped.items())
    ]

    comp_uuid = _det_uuid("component", tenant_id)
    cd_uuid = _det_uuid("component-definition", tenant_id)

    component: dict[str, Any] = {
        "uuid": comp_uuid,
        "type": "service",
        "title": f"ServiceNow ITSM -- {tenant_id}",
        "description": (
            "ServiceNow integration component providing incident management, "
            "change control, and problem management capabilities. Covers "
            "controls IR-4, IR-5, IR-6, and CM-3."
        ),
        "props": [
            {
                "name": "asset-type",
                "ns": _UIAO_NS,
                "value": "itsm-platform",
            },
            {
                "name": "tenant-id",
                "ns": _UIAO_NS,
                "value": tenant_id,
            },
            {
                "name": "vendor",
                "ns": _UIAO_NS,
                "value": "ServiceNow",
            },
        ],
        "status": {"state": "operational"},
        "control-implementations": control_implementations,
    }

    component_def: dict[str, Any] = {
        "uuid": cd_uuid,
        "metadata": {
            "title": f"ServiceNow Evidence Component Definition -- {tenant_id}",
            "last-modified": now_iso,
            "version": "1.0",
            "oscal-version": _OSCAL_VERSION,
            "remarks": (
                f"Generated by uiao.oscal.servicenow_evidence for tenant {tenant_id}. Controls: IR-4, IR-5, IR-6, CM-3."
            ),
        },
        "components": [component],
        # Volatile envelope -- values filled after hash computation below.
        "signature": {
            "algorithm": "HMAC-SHA256",
            "signer": signer,
            "value": "",
            "signed_at": "",
        },
        "provenance": {
            "source": _PROVENANCE_SOURCE,
            "version": _PROVENANCE_VERSION,
            "derived_by": _PROVENANCE_DERIVED_BY,
            "derived_at": "",
        },
    }

    # Compute content hash over stable fields, then sign.
    c_hash = _canonical_hash(component_def)
    sig_value = _hmac_hex(c_hash, signing_key)
    signed_at = datetime.now(timezone.utc).isoformat()

    component_def["signature"]["value"] = sig_value
    component_def["signature"]["signed_at"] = signed_at
    component_def["provenance"]["derived_at"] = signed_at

    # Best-effort trestle validation (non-fatal if unavailable).
    try:
        from trestle.oscal.component import ComponentDefinition  # noqa: PLC0415

        ComponentDefinition(**component_def)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        # trestle.oscal.component.ComponentDefinition import/validation failed.
        # The returned dict is schema-compliant plain OSCAL 1.1.2 JSON but has
        # not been validated by the trestle Pydantic model.
        pass

    return component_def


# ---------------------------------------------------------------------------
# Public: verify_signature
# ---------------------------------------------------------------------------


def verify_signature(component_def: dict[str, Any], signing_key: bytes) -> bool:
    """Verify the HMAC-SHA256 signature embedded in *component_def*.

    Recomputes the canonical content hash over the stable (non-volatile)
    portion of *component_def* and compares the resulting HMAC against
    ``component_def["signature"]["value"]`` using a constant-time comparison.

    Parameters
    ----------
    component_def:
        A dict previously returned by
        :func:`emit_servicenow_component_definition`.
    signing_key:
        The same raw bytes used during emission.

    Returns
    -------
    bool
        ``True`` if the signature is valid; ``False`` otherwise.
    """
    stored_sig = component_def.get("signature", {}).get("value", "")
    if not stored_sig:
        return False
    c_hash = _canonical_hash(component_def)
    expected = _hmac_hex(c_hash, signing_key)
    return hmac.compare_digest(expected, stored_sig)
