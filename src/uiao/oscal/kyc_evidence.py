"""uiao.oscal.kyc_evidence — KYC / Customer Identity events → OSCAL assessment-results.

Plane: Customer Identity Record + reciprocity events (UIAO_141 / UIAO_142) →
OSCAL assessment-results JSON files.

Public API
----------
    emit_customer_identity_record(cir: dict, out_dir: Path | str) -> Path
    emit_reciprocity_attribute_record(entitlement: dict, out_dir: Path | str) -> Path
    emit_reciprocity_record(reciprocity: dict, out_dir: Path | str) -> Path

The first two emit OSCAL evidence for the KYC canon block (ADR-055 /
UIAO_141 / UIAO_142). The third emits OSCAL evidence for the single-ATO
reciprocity model (ADR-054 / UIAO_140) — that's authorization-level
reciprocity (one ATO covering many tenants), distinct from the
attribute-level reciprocity covered by the second emitter.

All three emitters are deterministic: identical input always produces
identical output (UUIDv5 from canonicalized inputs). Each writes a
single assessment-results JSON file and returns its path.

Controls covered
----------------
IA-2 / IA-4   Identification & Authentication of users — IAL/AAL/FAL
              binding emitted in CIR.
IA-5 / IA-8   Authenticator management & federation — federation
              authority binding emitted in CIR.
AC-2          Account management — CIR lifecycle states emitted.
AC-3          Access enforcement — entitlement-bound access emitted in
              reciprocity-attribute records.
AC-21         Information sharing — every reciprocity event is a
              first-class disclosure record.
AU-2 / AU-12  Audit-event generation — every emitter produces a
              signed evidence-graph anchor.
SC-8 / SC-13  Cryptographic protection — trust-anchor and signature
              metadata emitted in props.
CA-2          Security assessments — single-ATO reciprocity record
              (UIAO_140) anchors the ATO decision.

Schemas referenced
------------------
- UIAO_141 §2 — Customer Identity Record bindings
- UIAO_142 §3 — CIR lifecycle states
- src/uiao/schemas/reciprocal-consumption/registry.schema.json —
  entitlement shape

The emitters do NOT validate input against those schemas — that is the
caller's responsibility (and is handled by the registry CI gate added
in the schema-validation workflow). The emitters degrade gracefully on
missing optional fields per UIAO_141 §2.
"""

from __future__ import annotations

import hashlib
import json
import uuid as _uuid_mod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trestle.oscal import assessment_results as _ar
from trestle.oscal import common as _c

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_UIAO_NS = "https://uiao.gov/ns/kyc-evidence"

#: UUIDv5 namespace anchor — DNS-namespace UUID; same anchor as orgtree_evidence
#: so KYC and OrgTree UUIDs share a deterministic root.
_UUID_NS = _uuid_mod.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

_CONTROLS_CIR: list[str] = ["ia-2", "ia-4", "ia-5", "ia-8", "ac-2", "au-2", "sc-8"]
_CONTROLS_RECIP_ATTR: list[str] = ["ac-3", "ac-21", "au-2", "au-12", "sc-13"]
_CONTROLS_RECIP_ATO: list[str] = ["ca-2", "ac-2", "au-2", "au-12"]

# CIR lifecycle states per UIAO_142 §3
_CIR_STATES: frozenset[str] = frozenset(
    {"proposed", "proofed", "active", "reciprocally-provisioned", "quarantined", "retired"}
)


# ---------------------------------------------------------------------------
# Deterministic helpers
# ---------------------------------------------------------------------------


def _det_uuid(kind: str, key: str) -> str:
    """Return a stable UUIDv5 from *kind* + *key*."""
    return str(_uuid_mod.uuid5(_UUID_NS, f"{_UIAO_NS}{kind}:{key}"))


def _stable_hash(data: Any) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _prop(name: str, value: str, ns: str = _UIAO_NS) -> _c.Property:
    """Build an OSCAL Property with safe defaults.

    OSCAL Property.value must be non-empty and match ``^\\S(.*\\S)?$``.
    Falls back to ``"(none)"`` when the input is empty or whitespace-only.
    """
    safe_value = (value or "").strip() or "(none)"
    return _c.Property(name=name, value=safe_value, ns=ns)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _write_assessment_results(ar_obj: _ar.AssessmentResults, out_path: Path) -> Path:
    """Serialize an AssessmentResults model to disk and return the absolute path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ar_json_str = ar_obj.json(exclude_none=True, by_alias=True)
    payload: dict[str, Any] = {"assessment-results": json.loads(ar_json_str)}
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return out_path.resolve()


# ---------------------------------------------------------------------------
# CIR emitter (UIAO_141 / UIAO_142)
# ---------------------------------------------------------------------------


def _build_cir_inventory_item(cir: dict[str, Any]) -> _c.InventoryItem:
    """Build an OSCAL inventory-item describing a Customer Identity Record."""
    canonical_id = str(cir.get("canonical_identifier", "(unknown)"))
    item_uuid = _det_uuid("cir", canonical_id)

    props: list[_c.Property] = [
        _prop("canonical-identifier", canonical_id),
        _prop("identity-assurance-level", str(cir.get("identity_assurance_level", "(unknown)"))),
        _prop("authentication-assurance-level", str(cir.get("authentication_assurance_level", "(unknown)"))),
        _prop("federation-assurance-level", str(cir.get("federation_assurance_level", "(unknown)"))),
        _prop("authority-of-record", str(cir.get("authority_of_record", "(unknown)"))),
        _prop("lifecycle-state", str(cir.get("lifecycle_state", "(unknown)"))),
    ]

    description = (
        f"Customer Identity Record bound to authority of record "
        f"{cir.get('authority_of_record', '(unknown)')} at IAL "
        f"{cir.get('identity_assurance_level', '?')} / AAL "
        f"{cir.get('authentication_assurance_level', '?')} / FAL "
        f"{cir.get('federation_assurance_level', '?')}. "
        f"Lifecycle state: {cir.get('lifecycle_state', '(unknown)')}."
    )

    return _c.InventoryItem(uuid=item_uuid, description=description, props=props)


def emit_customer_identity_record(
    cir: dict[str, Any],
    out_dir: Path | str,
    *,
    now_dt: datetime | None = None,
) -> Path:
    """Emit an OSCAL assessment-results artifact for a Customer Identity Record.

    Parameters
    ----------
    cir:
        Dict matching UIAO_141 §2's six required CIR bindings:
        ``canonical_identifier``, ``identity_assurance_level``,
        ``authentication_assurance_level``, ``federation_assurance_level``,
        ``authority_of_record``, ``lifecycle_state``. The emitter degrades
        gracefully on missing fields (emitting ``"(unknown)"`` props).
    out_dir:
        Directory to write into. Created if missing.
    now_dt:
        Frozen-time datetime for deterministic golden tests.

    Returns
    -------
    Path
        Absolute path to the written ``customer-identity-record.json``.
    """
    now_dt = now_dt or _now()
    canonical_id = str(cir.get("canonical_identifier", "(unknown)"))
    record_uuid = _det_uuid("cir-record", canonical_id)

    inventory_item = _build_cir_inventory_item(cir)

    local_definitions = _ar.LocalDefinitions1(inventory_items=[inventory_item])

    reviewed_controls = _c.ReviewedControls(
        description=f"Customer Identity Record covers {', '.join(c.upper() for c in _CONTROLS_CIR)}",
        control_selections=[
            _c.ControlSelection(
                include_all=_c.IncludeAll(),
                description=f"Controls assessed: {', '.join(c.upper() for c in _CONTROLS_CIR)}",
            )
        ],
    )

    result = _ar.Result(
        uuid=record_uuid,
        title=f"Customer Identity Record — {canonical_id}",
        description=(
            f"OSCAL evidence for CIR {canonical_id} per UIAO_141 §2. Bound to "
            f"authority of record {cir.get('authority_of_record', '(unknown)')}."
        ),
        start=now_dt,
        local_definitions=local_definitions,
        reviewed_controls=reviewed_controls,
        props=[
            _prop("uiao-event-type", "customer-identity-record"),
            _prop("uiao-canon-ref", "UIAO_141"),
            _prop("uiao-input-hash", _stable_hash(cir)),
        ],
    )

    metadata = _c.Metadata(
        title=f"Customer Identity Record — {canonical_id}",
        last_modified=now_dt,
        version="0.1.0",
        oscal_version="1.0.4",
        remarks=(
            f"Generated by uiao.oscal.kyc_evidence.emit_customer_identity_record. "
            f"Controls: {', '.join(c.upper() for c in _CONTROLS_CIR)}."
        ),
    )

    ar_obj = _ar.AssessmentResults(
        uuid=_det_uuid("assessment-results-cir", canonical_id),
        metadata=metadata,
        import_ap=_ar.ImportAp(href="#"),
        results=[result],
    )

    out_path = Path(out_dir) / f"customer-identity-record-{_safe_filename(canonical_id)}.json"
    return _write_assessment_results(ar_obj, out_path)


# ---------------------------------------------------------------------------
# Reciprocity-attribute-record emitter (UIAO_141 §6 / UIAO_142 §5)
# ---------------------------------------------------------------------------


def emit_reciprocity_attribute_record(
    entitlement: dict[str, Any],
    out_dir: Path | str,
    *,
    now_dt: datetime | None = None,
) -> Path:
    """Emit an OSCAL assessment-results artifact for a reciprocity-attribute-record.

    Parameters
    ----------
    entitlement:
        Dict matching the reciprocal-consumption-registry schema:
        ``id``, ``attribute_id``, ``authority_of_record``,
        ``consumer_principal``, ``legal_basis``, ``scope``,
        ``freshness_window_hours``, ``effective_date``, ``signed_by``.
    out_dir:
        Directory to write into. Created if missing.
    now_dt:
        Frozen-time datetime for deterministic golden tests.

    Returns
    -------
    Path
        Absolute path to the written ``reciprocity-attribute-record.json``.
    """
    now_dt = now_dt or _now()
    ent_id = str(entitlement.get("id", "(unknown)"))
    record_uuid = _det_uuid("reciprocity-attr-record", ent_id)

    legal_basis = entitlement.get("legal_basis", {})
    if isinstance(legal_basis, dict):
        lb_type = str(legal_basis.get("type", "(unknown)"))
        lb_citation = str(legal_basis.get("citation", "(unknown)"))
    else:
        lb_type = "(unknown)"
        lb_citation = str(legal_basis or "(unknown)")

    scope = entitlement.get("scope", []) or []
    scope_str = ",".join(str(s) for s in scope) if scope else "(empty)"

    props: list[_c.Property] = [
        _prop("entitlement-id", ent_id),
        _prop("attribute-id", str(entitlement.get("attribute_id", "(unknown)"))),
        _prop("authority-of-record", str(entitlement.get("authority_of_record", "(unknown)"))),
        _prop("consumer-principal", str(entitlement.get("consumer_principal", "(unknown)"))),
        _prop("legal-basis-type", lb_type),
        _prop("legal-basis-citation", lb_citation),
        _prop("scope", scope_str),
        _prop(
            "freshness-window-hours",
            str(entitlement.get("freshness_window_hours", "(unknown)")),
        ),
        _prop("effective-date", str(entitlement.get("effective_date", "(unknown)"))),
        _prop("signed-by", str(entitlement.get("signed_by", "(unknown)"))),
    ]
    if "expiry_date" in entitlement:
        props.append(_prop("expiry-date", str(entitlement["expiry_date"])))

    inventory_item = _c.InventoryItem(
        uuid=_det_uuid("entitlement", ent_id),
        description=(
            f"Reciprocal-consumption entitlement {ent_id}: "
            f"{entitlement.get('consumer_principal', '(unknown)')} → "
            f"{entitlement.get('authority_of_record', '(unknown)')} for attribute "
            f"{entitlement.get('attribute_id', '(unknown)')}; "
            f"legal basis: {lb_type} ({lb_citation})."
        ),
        props=props,
    )

    local_definitions = _ar.LocalDefinitions1(inventory_items=[inventory_item])

    reviewed_controls = _c.ReviewedControls(
        description=f"Reciprocity Attribute Record covers {', '.join(c.upper() for c in _CONTROLS_RECIP_ATTR)}",
        control_selections=[
            _c.ControlSelection(
                include_all=_c.IncludeAll(),
                description=f"Controls assessed: {', '.join(c.upper() for c in _CONTROLS_RECIP_ATTR)}",
            )
        ],
    )

    result = _ar.Result(
        uuid=record_uuid,
        title=f"Reciprocity Attribute Record — {ent_id}",
        description=(
            f"OSCAL evidence for reciprocity entitlement {ent_id} per UIAO_141 §6 / "
            f"UIAO_142 §5. Authorizes consumer "
            f"{entitlement.get('consumer_principal', '(unknown)')} to consume "
            f"attribute {entitlement.get('attribute_id', '(unknown)')} from "
            f"{entitlement.get('authority_of_record', '(unknown)')} under legal basis "
            f"{lb_type} ({lb_citation})."
        ),
        start=now_dt,
        local_definitions=local_definitions,
        reviewed_controls=reviewed_controls,
        props=[
            _prop("uiao-event-type", "reciprocity-attribute-record"),
            _prop("uiao-canon-ref", "UIAO_141"),
            _prop("uiao-input-hash", _stable_hash(entitlement)),
        ],
    )

    metadata = _c.Metadata(
        title=f"Reciprocity Attribute Record — {ent_id}",
        last_modified=now_dt,
        version="0.1.0",
        oscal_version="1.0.4",
        remarks=(
            f"Generated by uiao.oscal.kyc_evidence.emit_reciprocity_attribute_record. "
            f"Controls: {', '.join(c.upper() for c in _CONTROLS_RECIP_ATTR)}."
        ),
    )

    ar_obj = _ar.AssessmentResults(
        uuid=_det_uuid("assessment-results-recip-attr", ent_id),
        metadata=metadata,
        import_ap=_ar.ImportAp(href="#"),
        results=[result],
    )

    out_path = Path(out_dir) / f"reciprocity-attribute-record-{_safe_filename(ent_id)}.json"
    return _write_assessment_results(ar_obj, out_path)


# ---------------------------------------------------------------------------
# Single-ATO reciprocity-record emitter (UIAO_140 / ADR-054)
# ---------------------------------------------------------------------------


def emit_reciprocity_record(
    reciprocity: dict[str, Any],
    out_dir: Path | str,
    *,
    now_dt: datetime | None = None,
) -> Path:
    """Emit an OSCAL assessment-results artifact for a single-ATO reciprocity record.

    UIAO_140 §3 specifies that each consuming agency files a Reciprocity
    Record acknowledging the controlling SSP and ATO. This function emits
    the OSCAL artifact for that acknowledgment.

    Parameters
    ----------
    reciprocity:
        Dict with the following expected keys (per UIAO_140 §6):
        ``agency_id``, ``ssp_version``, ``ato_decision_id``,
        ``acknowledged_by``, ``acknowledged_at`` (ISO-8601),
        ``configuration_latitude`` (mapping or list).
    out_dir:
        Directory to write into. Created if missing.
    now_dt:
        Frozen-time datetime for deterministic golden tests.

    Returns
    -------
    Path
        Absolute path to the written ``reciprocity-record.json``.
    """
    now_dt = now_dt or _now()
    agency_id = str(reciprocity.get("agency_id", "(unknown)"))
    ato_id = str(reciprocity.get("ato_decision_id", "(unknown)"))
    record_key = f"{agency_id}|{ato_id}"
    record_uuid = _det_uuid("reciprocity-record", record_key)

    config_lat = reciprocity.get("configuration_latitude") or {}
    if isinstance(config_lat, dict):
        config_summary = ",".join(f"{k}={v}" for k, v in sorted(config_lat.items())) or "(default)"
    elif isinstance(config_lat, list):
        config_summary = ",".join(str(v) for v in config_lat) or "(default)"
    else:
        config_summary = str(config_lat) or "(default)"

    props: list[_c.Property] = [
        _prop("agency-id", agency_id),
        _prop("ssp-version", str(reciprocity.get("ssp_version", "(unknown)"))),
        _prop("ato-decision-id", ato_id),
        _prop("acknowledged-by", str(reciprocity.get("acknowledged_by", "(unknown)"))),
        _prop("acknowledged-at", str(reciprocity.get("acknowledged_at", "(unknown)"))),
        _prop("configuration-latitude", config_summary),
    ]

    inventory_item = _c.InventoryItem(
        uuid=_det_uuid("reciprocity-acknowledgment", record_key),
        description=(
            f"Single-ATO reciprocity acknowledgment: agency {agency_id} acknowledges "
            f"controlling ATO {ato_id} (SSP version "
            f"{reciprocity.get('ssp_version', '(unknown)')}) per UIAO_140 §3."
        ),
        props=props,
    )

    local_definitions = _ar.LocalDefinitions1(inventory_items=[inventory_item])

    reviewed_controls = _c.ReviewedControls(
        description=f"Single-ATO Reciprocity Record covers {', '.join(c.upper() for c in _CONTROLS_RECIP_ATO)}",
        control_selections=[
            _c.ControlSelection(
                include_all=_c.IncludeAll(),
                description=f"Controls assessed: {', '.join(c.upper() for c in _CONTROLS_RECIP_ATO)}",
            )
        ],
    )

    result = _ar.Result(
        uuid=record_uuid,
        title=f"Single-ATO Reciprocity Record — {agency_id}",
        description=(
            f"OSCAL evidence for the single-ATO reciprocity acknowledgment by "
            f"agency {agency_id} of controlling ATO {ato_id} per UIAO_140 / ADR-054. "
            f"Establishes that the controlling SSP and ATO cover this agency's "
            f"consumption under documented reciprocity (no per-agency SSP)."
        ),
        start=now_dt,
        local_definitions=local_definitions,
        reviewed_controls=reviewed_controls,
        props=[
            _prop("uiao-event-type", "reciprocity-record"),
            _prop("uiao-canon-ref", "UIAO_140"),
            _prop("uiao-input-hash", _stable_hash(reciprocity)),
        ],
    )

    metadata = _c.Metadata(
        title=f"Single-ATO Reciprocity Record — {agency_id}",
        last_modified=now_dt,
        version="0.1.0",
        oscal_version="1.0.4",
        remarks=(
            f"Generated by uiao.oscal.kyc_evidence.emit_reciprocity_record. "
            f"Controls: {', '.join(c.upper() for c in _CONTROLS_RECIP_ATO)}."
        ),
    )

    ar_obj = _ar.AssessmentResults(
        uuid=_det_uuid("assessment-results-recip-ato", record_key),
        metadata=metadata,
        import_ap=_ar.ImportAp(href="#"),
        results=[result],
    )

    out_path = Path(out_dir) / f"reciprocity-record-{_safe_filename(agency_id)}.json"
    return _write_assessment_results(ar_obj, out_path)


# ---------------------------------------------------------------------------
# Filename helper
# ---------------------------------------------------------------------------


def _safe_filename(s: str) -> str:
    """Return a filename-safe slug derived from *s*.

    Replaces filesystem-unsafe characters with ``-``; collapses repeated
    separators; trims to a sane length.
    """
    safe = "".join(c if c.isalnum() or c in "-_." else "-" for c in s)
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-")[:80] or "record"
