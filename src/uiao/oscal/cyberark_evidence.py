"""uiao.oscal.cyberark_evidence -- CyberArk rotation evidence -> OSCAL component-definition."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Any

_OSCAL_VERSION = "1.1.2"
_UIAO_NS = "https://uiao.gov/ns/cyberark-evidence"

_PROVENANCE_SOURCE = "UIAO-CANON-003"
_PROVENANCE_VERSION = "1.0"
_PROVENANCE_DERIVED_BY = "uiao.oscal.cyberark_evidence.emit_cyberark_component_definition"

_UUID_NS = _uuid_mod.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
_SUPPORTED_CONTROLS: frozenset[str] = frozenset(["IA-5", "IA-5(1)", "AC-2", "AC-6"])

_VOLATILE_PATHS: tuple[tuple[str, ...], ...] = (
    ("signature", "value"),
    ("signature", "signed_at"),
    ("provenance", "derived_at"),
    ("metadata", "last-modified"),
)

_CONTROL_DESCRIPTIONS: dict[str, str] = {
    "IA-5": "Authenticator management evidence for privileged credential lifecycle.",
    "IA-5(1)": "Password-based authenticator management evidence from rotation events.",
    "AC-2": "Privileged account management evidence for account ownership and lifecycle.",
    "AC-6": "Least-privilege evidence tied to privileged credential handling.",
}


def _det_uuid(kind: str, key: str) -> str:
    return str(_uuid_mod.uuid5(_UUID_NS, f"uiao:cyberark:{kind}:{key}"))


def _strip_volatile(obj: dict[str, Any]) -> dict[str, Any]:
    stripped = copy.deepcopy(obj)
    for path in _VOLATILE_PATHS:
        node: Any = stripped
        for step in path[:-1]:
            node = node.get(step, {}) if isinstance(node, dict) else {}
        if isinstance(node, dict) and path[-1] in node:
            del node[path[-1]]
    return stripped


def _canonical_hash(component_def: dict[str, Any]) -> str:
    stable = _strip_volatile(component_def)
    canonical = json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hmac_hex(content_hash: str, signing_key: bytes) -> str:
    return hmac.new(signing_key, content_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def _normalise_control_id(raw: str) -> str:
    cid = raw.strip().upper()
    return cid if cid in _SUPPORTED_CONTROLS else "IA-5"


def _group_rotations_by_control(rotations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rotation in rotations:
        ctrl = _normalise_control_id(str(rotation.get("control_id", "IA-5")))
        grouped.setdefault(ctrl, []).append(rotation)
    return grouped


def _build_statement(rotation: dict[str, Any], ctrl: str) -> dict[str, Any]:
    account_id = str(rotation.get("account_id", "unknown-account"))
    safe_name = str(rotation.get("safe_name", "default"))
    rotation_cause = str(rotation.get("rotation_cause", "unspecified"))
    verification_passed = bool(rotation.get("verification_passed", False))
    rotated_at = str(rotation.get("rotated_at", ""))

    return {
        "statement-id": f"{ctrl.lower()}_smt",
        "uuid": _det_uuid("statement", f"{ctrl}:{account_id}:{safe_name}:{rotation_cause}:{rotated_at}"),
        "description": f"Credential rotation for account {account_id} in safe {safe_name}.",
        "props": [
            {"name": "account-id", "ns": _UIAO_NS, "value": account_id},
            {"name": "safe-name", "ns": _UIAO_NS, "value": safe_name},
            {"name": "rotation-cause", "ns": _UIAO_NS, "value": rotation_cause},
            {"name": "verification-passed", "ns": _UIAO_NS, "value": str(verification_passed).lower()},
            {"name": "rotated-at", "ns": _UIAO_NS, "value": rotated_at or "(none)"},
        ],
    }


def _build_control_implementation(ctrl: str, rotations: list[dict[str, Any]]) -> dict[str, Any]:
    description = _CONTROL_DESCRIPTIONS.get(ctrl, f"CyberArk evidence for control {ctrl}.")
    return {
        "uuid": _det_uuid("control-impl", ctrl),
        "source": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
        "description": description,
        "implemented-requirements": [
            {
                "uuid": _det_uuid("req", ctrl),
                "control-id": ctrl.lower(),
                "description": description,
                "statements": [_build_statement(rotation, ctrl) for rotation in rotations],
            }
        ],
    }


def emit_cyberark_component_definition(
    rotations: list[dict[str, Any]],
    vault_id: str,
    signer: str,
    signing_key: bytes,
    *,
    now_dt: datetime | None = None,
) -> dict[str, Any]:
    """Emit a signed OSCAL component-definition for CyberArk credential rotations."""
    now = now_dt or datetime.now(timezone.utc)
    now_iso = now.isoformat()

    grouped = _group_rotations_by_control(rotations) if rotations else {}
    control_implementations = [
        _build_control_implementation(ctrl, ctrl_rotations) for ctrl, ctrl_rotations in sorted(grouped.items())
    ]

    component: dict[str, Any] = {
        "uuid": _det_uuid("component", vault_id),
        "type": "service",
        "title": f"CyberArk PAM Vault -- {vault_id}",
        "description": (
            "CyberArk privileged access management component providing privileged "
            "credential rotation and post-rotation verification evidence."
        ),
        "props": [
            {"name": "asset-type", "ns": _UIAO_NS, "value": "privileged-access-management"},
            {"name": "vault-id", "ns": _UIAO_NS, "value": vault_id},
            {"name": "vendor", "ns": _UIAO_NS, "value": "CyberArk"},
        ],
        "status": {"state": "operational"},
        "control-implementations": control_implementations,
    }

    component_def: dict[str, Any] = {
        "uuid": _det_uuid("component-definition", vault_id),
        "metadata": {
            "title": f"CyberArk Rotation Evidence Component Definition -- {vault_id}",
            "last-modified": now_iso,
            "version": "1.0",
            "oscal-version": _OSCAL_VERSION,
            "remarks": "Generated by uiao.oscal.cyberark_evidence for IA-5, IA-5(1), AC-2, AC-6.",
        },
        "components": [component],
        "signature": {"algorithm": "HMAC-SHA256", "signer": signer, "value": "", "signed_at": ""},
        "provenance": {
            "source": _PROVENANCE_SOURCE,
            "version": _PROVENANCE_VERSION,
            "derived_by": _PROVENANCE_DERIVED_BY,
            "derived_at": "",
        },
    }

    c_hash = _canonical_hash(component_def)
    sig_value = _hmac_hex(c_hash, signing_key)
    signed_at = now.isoformat()

    component_def["signature"]["value"] = sig_value
    component_def["signature"]["signed_at"] = signed_at
    component_def["provenance"]["derived_at"] = signed_at
    return component_def


def verify_signature(component_def: dict[str, Any], signing_key: bytes) -> bool:
    stored_sig = component_def.get("signature", {}).get("value", "")
    if not stored_sig:
        return False
    expected = _hmac_hex(_canonical_hash(component_def), signing_key)
    return hmac.compare_digest(expected, stored_sig)
