"""uiao.oscal.orgtree_evidence — OrgTree bundle → OSCAL Assessment-Results evidence.

Plane: OrgTree bundle dict → OSCAL assessment-results JSON file.

Controls covered
----------------
CM-8  System Component Inventory — all users, groups, computers, servers emitted
      as inventory-items in the Result's local-definitions.

IA-3  Device Identification & Authentication — computers + servers with object
      SID and DNS name emitted as inventory-item props.

IA-2  User Identification & Authentication — user accounts with derived auth
      method (password / smartcard / fido2) emitted as inventory-item props.

AC-2  Account Management — disabled and stale (>90 days without logon) accounts
      surfaced as OSCAL Findings referencing companion Observations.

AC-6  Least Privilege — privileged group membership (Domain Admins, Enterprise
      Admins, Schema Admins, Account Operators, Backup Operators, Server
      Operators, Print Operators) emitted as Findings with member counts and
      inventory-item props.

Public API
----------
    emit_orgtree_evidence(bundle: dict, out_dir: Path | str) -> Path

The function is deterministic: identical input always produces identical output.
It writes a single ``orgtree-evidence.json`` file and returns its path.

Bundle schema (synthetic / WS-A5 mock)
---------------------------------------
The ``bundle`` dict is the output of the WS-A5 bundle builder (mocked in tests).
Expected top-level keys (all optional — the emitter degrades gracefully):

    bundle["users"]      list[dict]   — AD user objects
    bundle["groups"]     list[dict]   — AD group objects
    bundle["computers"]  list[dict]   — AD workstation/client objects
    bundle["servers"]    list[dict]   — AD server objects
    bundle["run_id"]     str          — stable run identifier
    bundle["tenant"]     str          — tenant name

User dict keys used:
    samAccountName, distinguishedName, objectSid, userAccountControl,
    userPrincipalName, displayName, lastLogonTimestamp (epoch seconds or None),
    enabled (bool), extensionAttribute1..15, mail

Group dict keys used:
    samAccountName, distinguishedName, objectSid, description, members (list[str])
    primaryGroupToken (int, optional — RID)

Computer/Server dict keys used:
    name, distinguishedName, objectSid, dNSHostName, operatingSystem,
    lastLogonTimestamp (epoch seconds or None), enabled (bool)
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
# Constants — privileged group RIDs and canonical names
# ---------------------------------------------------------------------------

_UIAO_NS = "https://uiao.gov/ns/orgtree-evidence"

#: Well-known RIDs for privileged groups; used when primaryGroupToken is set.
_PRIVILEGED_RIDS: frozenset[int] = frozenset(
    [
        512,  # Domain Admins
        519,  # Enterprise Admins
        518,  # Schema Admins
        544,  # BUILTIN\Administrators (Phase 1.5 fix #2 — was missing)
        548,  # Account Operators
        551,  # Backup Operators
        549,  # Server Operators
        550,  # Print Operators
    ]
)

#: Canonical name fragments (lower-cased) for privileged group detection by name.
_PRIVILEGED_NAME_FRAGMENTS: tuple[str, ...] = (
    "domain admins",
    "enterprise admins",
    "schema admins",
    "account operators",
    "backup operators",
    "server operators",
    "print operators",
)

#: Controls emitted by this module (used in reviewed-controls list).
_CONTROLS: list[str] = ["cm-8", "ia-3", "ia-2", "ac-2", "ac-6"]

#: Stale-account threshold in days.
_STALE_DAYS: int = 90

# ---------------------------------------------------------------------------
# Deterministic UUID helpers
# ---------------------------------------------------------------------------

_UUID_NS = _uuid_mod.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
_UIAO_NS_URL = _UIAO_NS  # alias for clarity


def _det_uuid(kind: str, key: str) -> str:
    """Return a stable UUIDv5 from *kind* + *key*."""
    return str(_uuid_mod.uuid5(_UUID_NS, f"{_UIAO_NS}{kind}:{key}"))


def _stable_hash(data: Any) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Auth-method derivation from userAccountControl
# ---------------------------------------------------------------------------

# userAccountControl bit flags
_UAC_PASSWD_NOTREQD = 0x0020
_UAC_SMARTCARD_REQUIRED = 0x0040000


def _derive_auth_method(user: dict[str, Any]) -> str:
    """Derive authentication method from AD attributes.

    Priority:
    1. extensionAttribute* hints (fido2 / smartcard / password keywords).
    2. userAccountControl SMARTCARD_REQUIRED bit.
    3. Default: "password".
    """
    for k in (
        "extensionAttribute1",
        "extensionAttribute2",
        "extensionAttribute3",
        "extensionAttribute4",
        "extensionAttribute5",
    ):
        val = str(user.get(k, "") or "").lower()
        if "fido2" in val or "fido" in val:
            return "fido2"
        if "smartcard" in val or "smart card" in val or "piv" in val or "cac" in val:
            return "smartcard"
        if "password" in val:
            return "password"

    uac = int(user.get("userAccountControl", 0) or 0)
    if uac & _UAC_SMARTCARD_REQUIRED:
        return "smartcard"
    return "password"


# ---------------------------------------------------------------------------
# Stale / disabled detection
# ---------------------------------------------------------------------------


def _is_disabled(obj: dict[str, Any]) -> bool:
    """Return True if the object is disabled (users, computers, servers)."""
    enabled = obj.get("enabled")
    if enabled is not None:
        return not bool(enabled)
    uac = int(obj.get("userAccountControl", 0) or 0)
    return bool(uac & 0x0002)  # ADS_UF_ACCOUNTDISABLE


def _days_since_logon(obj: dict[str, Any], now_ts: float) -> int | None:
    """Return integer days since last logon, or None if unknown."""
    ts = obj.get("lastLogonTimestamp")
    if ts is None:
        return None
    try:
        return int((now_ts - float(ts)) / 86400)
    except (TypeError, ValueError):
        return None


def _is_stale(obj: dict[str, Any], now_ts: float) -> bool:
    days = _days_since_logon(obj, now_ts)
    if days is None:
        return False
    return days > _STALE_DAYS


# ---------------------------------------------------------------------------
# Privileged-group detection
# ---------------------------------------------------------------------------


def _is_privileged_group(group: dict[str, Any]) -> bool:
    rid = group.get("primaryGroupToken")
    if rid is not None:
        try:
            if int(rid) in _PRIVILEGED_RIDS:
                return True
        except (TypeError, ValueError):
            pass
    name = str(group.get("samAccountName", "") or group.get("name", "") or "").lower()
    return any(frag in name for frag in _PRIVILEGED_NAME_FRAGMENTS)


# ---------------------------------------------------------------------------
# Property builder helper
# ---------------------------------------------------------------------------


def _prop(name: str, value: str, ns: str = _UIAO_NS) -> _c.Property:
    # OSCAL Property.value must be non-empty and match ^\S(.*\S)?$
    safe_value = value.strip() if value else "(none)"
    if not safe_value:
        safe_value = "(none)"
    return _c.Property(name=name, value=safe_value, ns=ns)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CM-8: inventory-item builders
# ---------------------------------------------------------------------------


def _user_inventory_item(user: dict[str, Any]) -> _c.InventoryItem:
    """Build a CM-8 InventoryItem for an AD user."""
    sam = str(user.get("samAccountName", "") or "")
    dn = str(user.get("distinguishedName", "") or "")
    key = sam or dn or _stable_hash(user)
    uid = _det_uuid("cm8-user", key)

    props: list[_c.Property] = [
        _prop("asset-type", "user"),
        _prop("sam-account-name", sam),
        _prop("distinguished-name", dn),
        _prop("control", "cm-8"),
    ]
    sid = str(user.get("objectSid", "") or "")
    if sid:
        props.append(_prop("object-sid", sid))
    mail = str(user.get("mail", "") or "")
    if mail:
        props.append(_prop("email", mail))
    display = str(user.get("displayName", "") or "")
    if display:
        props.append(_prop("display-name", display))

    # IA-2: auth method
    auth = _derive_auth_method(user)
    props.append(_prop("auth-method", auth))
    props.append(_prop("control", "ia-2"))

    disabled = _is_disabled(user)
    props.append(_prop("account-enabled", str(not disabled).lower()))

    desc = f"AD user: {sam}" if sam else "AD user"
    return _c.InventoryItem(uuid=uid, description=desc, props=props)


def _group_inventory_item(group: dict[str, Any]) -> _c.InventoryItem:
    """Build a CM-8 InventoryItem for an AD group."""
    sam = str(group.get("samAccountName", "") or "")
    dn = str(group.get("distinguishedName", "") or "")
    key = sam or dn or _stable_hash(group)
    uid = _det_uuid("cm8-group", key)

    props: list[_c.Property] = [
        _prop("asset-type", "group"),
        _prop("sam-account-name", sam),
        _prop("distinguished-name", dn),
        _prop("control", "cm-8"),
    ]
    sid = str(group.get("objectSid", "") or "")
    if sid:
        props.append(_prop("object-sid", sid))
    member_count = len(group.get("members", []) or [])
    props.append(_prop("member-count", str(member_count)))

    if _is_privileged_group(group):
        props.append(_prop("privileged-group", "true"))
        props.append(_prop("control", "ac-6"))

    desc = str(group.get("description", "") or f"AD group: {sam}")
    return _c.InventoryItem(uuid=uid, description=desc, props=props)


def _computer_inventory_item(computer: dict[str, Any], *, is_server: bool = False) -> _c.InventoryItem:
    """Build a CM-8 / IA-3 InventoryItem for an AD computer or server."""
    name = str(computer.get("name", "") or "")
    dn = str(computer.get("distinguishedName", "") or "")
    key = name or dn or _stable_hash(computer)
    asset_type = "server" if is_server else "computer"
    uid = _det_uuid(f"cm8-{asset_type}", key)

    props: list[_c.Property] = [
        _prop("asset-type", asset_type),
        _prop("hostname", name),
        _prop("distinguished-name", dn),
        _prop("control", "cm-8"),
    ]
    sid = str(computer.get("objectSid", "") or "")
    if sid:
        props.append(_prop("object-sid", sid))
        props.append(_prop("control", "ia-3"))  # IA-3: device identification via SID

    dns = str(computer.get("dNSHostName", "") or "")
    if dns:
        props.append(_prop("dns-name", dns))
        props.append(_prop("control", "ia-3"))  # IA-3: device identification via DNS

    os_name = str(computer.get("operatingSystem", "") or "")
    if os_name:
        props.append(_prop("operating-system", os_name))

    disabled = _is_disabled(computer)
    props.append(_prop("account-enabled", str(not disabled).lower()))

    desc = f"AD {asset_type}: {name}" if name else f"AD {asset_type}"
    return _c.InventoryItem(uuid=uid, description=desc, props=props)


# ---------------------------------------------------------------------------
# AC-2: findings for disabled / stale accounts
# ---------------------------------------------------------------------------


def _ac2_observation(
    obj: dict[str, Any],
    reason: str,
    obj_type: str,
    now_ts: float,
) -> _c.Observation:
    sam = str(obj.get("samAccountName", obj.get("name", "")) or "")
    key = f"ac2-{reason}-{sam}"
    uid = _det_uuid("ac2-obs", key)
    days = _days_since_logon(obj, now_ts)
    days_str = f"{days}d" if days is not None else "unknown"
    desc = f"AC-2 finding: {obj_type} account '{sam}' is {reason}. Last logon: {days_str} ago."
    return _c.Observation(
        uuid=uid,
        title=f"AC-2 {reason.title()} Account: {sam}",
        description=desc,
        methods=["AUTOMATED"],
        types=[_c.ObservationTypeValidValues.finding.value],
        collected=datetime.fromtimestamp(now_ts, tz=timezone.utc),
        props=[
            _prop("control", "ac-2"),
            _prop("account-name", sam),
            _prop("finding-type", reason),
            _prop("object-type", obj_type),
        ],
    )


def _ac2_finding(obs: _c.Observation, control_key: str) -> _c.Finding:
    fid = _det_uuid("ac2-finding", obs.uuid)
    return _c.Finding(
        uuid=fid,
        title=obs.title,
        description=obs.description,
        target=_c.FindingTarget(
            type=_c.FindingTargetTypeValidValues.statement_id.value,  # type: ignore[arg-type]
            target_id="ac-2_smt",
            remarks=obs.description,
        ),
        related_observations=[_c.RelatedObservation(observation_uuid=obs.uuid)],
        props=[_prop("control", "ac-2")],
    )


# ---------------------------------------------------------------------------
# AC-6: findings for privileged group membership
# ---------------------------------------------------------------------------


def _ac6_observation(group: dict[str, Any]) -> _c.Observation:
    sam = str(group.get("samAccountName", "") or "")
    key = f"ac6-priv-{sam}"
    uid = _det_uuid("ac6-obs", key)
    members = group.get("members", []) or []
    member_count = len(members)
    desc = (
        f"AC-6 privileged group '{sam}' has {member_count} member(s). Review membership for least-privilege compliance."
    )
    return _c.Observation(
        uuid=uid,
        title=f"AC-6 Privileged Group: {sam}",
        description=desc,
        methods=["AUTOMATED"],
        types=[_c.ObservationTypeValidValues.finding.value],
        collected=datetime.now(timezone.utc),
        props=[
            _prop("control", "ac-6"),
            _prop("group-name", sam),
            _prop("member-count", str(member_count)),
        ],
    )


def _ac6_finding(obs: _c.Observation) -> _c.Finding:
    fid = _det_uuid("ac6-finding", obs.uuid)
    return _c.Finding(
        uuid=fid,
        title=obs.title,
        description=obs.description,
        target=_c.FindingTarget(
            type=_c.FindingTargetTypeValidValues.statement_id.value,  # type: ignore[arg-type]
            target_id="ac-6_smt",
            remarks=obs.description,
        ),
        related_observations=[_c.RelatedObservation(observation_uuid=obs.uuid)],
        props=[_prop("control", "ac-6")],
    )


# ---------------------------------------------------------------------------
# Top-level assembly
# ---------------------------------------------------------------------------


def _build_assessment_results(bundle: dict[str, Any]) -> _ar.AssessmentResults:
    now_dt = datetime.now(timezone.utc)
    now_ts = now_dt.timestamp()

    run_id = str(bundle.get("run_id", "unknown"))
    tenant = str(bundle.get("tenant", "unknown"))

    users: list[dict[str, Any]] = list(bundle.get("users", []) or [])
    groups: list[dict[str, Any]] = list(bundle.get("groups", []) or [])
    computers: list[dict[str, Any]] = list(bundle.get("computers", []) or [])
    servers: list[dict[str, Any]] = list(bundle.get("servers", []) or [])

    # --- CM-8 / IA-2 / IA-3 inventory items --------------------------------
    inventory_items: list[_c.InventoryItem] = []
    for u in users:
        inventory_items.append(_user_inventory_item(u))
    for g in groups:
        inventory_items.append(_group_inventory_item(g))
    for c in computers:
        inventory_items.append(_computer_inventory_item(c, is_server=False))
    for s in servers:
        inventory_items.append(_computer_inventory_item(s, is_server=True))

    # --- AC-2 observations + findings (disabled / stale accounts) -----------
    ac2_observations: list[_c.Observation] = []
    ac2_findings: list[_c.Finding] = []

    for obj_list, obj_type in ((users, "user"), (computers, "computer"), (servers, "server")):
        for obj in obj_list:
            if _is_disabled(obj):
                obs = _ac2_observation(obj, "disabled", obj_type, now_ts)
                ac2_observations.append(obs)
                ac2_findings.append(_ac2_finding(obs, "ac-2"))
            elif _is_stale(obj, now_ts):
                obs = _ac2_observation(obj, "stale", obj_type, now_ts)
                ac2_observations.append(obs)
                ac2_findings.append(_ac2_finding(obs, "ac-2"))

    # --- AC-6 observations + findings (privileged groups) -------------------
    ac6_observations: list[_c.Observation] = []
    ac6_findings: list[_c.Finding] = []

    for g in groups:
        if _is_privileged_group(g):
            obs = _ac6_observation(g)
            ac6_observations.append(obs)
            ac6_findings.append(_ac6_finding(obs))

    all_observations = ac2_observations + ac6_observations
    all_findings = ac2_findings + ac6_findings

    # --- Build OSCAL structure ----------------------------------------------
    reviewed_controls = _c.ReviewedControls(
        description="OrgTree evidence covers CM-8, IA-3, IA-2, AC-2, AC-6",
        control_selections=[
            _c.ControlSelection(
                include_all=_c.IncludeAll(),
                description=f"Controls assessed: {', '.join(_CONTROLS).upper()}",
            )
        ],
    )

    local_defs = _ar.LocalDefinitions1(
        inventory_items=inventory_items if inventory_items else None,
    )

    result = _ar.Result(
        uuid=_det_uuid("result", run_id),
        title=f"OrgTree Evidence — {tenant}",
        description=(
            f"OSCAL assessment result generated from OrgTree bundle run_id={run_id}. "
            f"Covers CM-8 (inventory), IA-3 (device id), IA-2 (user auth), "
            f"AC-2 (account management), AC-6 (least privilege)."
        ),
        start=now_dt,
        reviewed_controls=reviewed_controls,
        local_definitions=local_defs,
        observations=all_observations if all_observations else None,
        findings=all_findings if all_findings else None,
        props=[
            _prop("run-id", run_id),
            _prop("tenant", tenant),
            _prop("generator", "uiao.oscal.orgtree_evidence"),
            _prop("user-count", str(len(users))),
            _prop("group-count", str(len(groups))),
            _prop("computer-count", str(len(computers))),
            _prop("server-count", str(len(servers))),
        ],
    )

    metadata = _c.Metadata(
        title=f"OrgTree Evidence — {tenant}",
        last_modified=now_dt,
        version="0.1.0",
        oscal_version="1.0.4",
        remarks=(
            f"Generated by uiao.oscal.orgtree_evidence from bundle run_id={run_id}. "
            f"Controls: {', '.join(c.upper() for c in _CONTROLS)}."
        ),
    )

    return _ar.AssessmentResults(
        uuid=_det_uuid("assessment-results", run_id),
        metadata=metadata,
        import_ap=_ar.ImportAp(href="#"),
        results=[result],
    )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_orgtree_evidence(
    bundle: dict[str, Any],
    out_dir: Path | str,
) -> Path:
    """Emit OSCAL assessment-results evidence from an OrgTree bundle.

    Parameters
    ----------
    bundle:
        OrgTree bundle dict (synthetic WS-A5 output or real bundle).
        Expected keys: users, groups, computers, servers, run_id, tenant.
    out_dir:
        Directory where ``orgtree-evidence.json`` will be written.
        Created automatically if it does not exist.

    Returns
    -------
    Path
        Absolute path to the written ``orgtree-evidence.json`` file.
    """
    ar_obj = _build_assessment_results(bundle)
    out_path = Path(out_dir) / "orgtree-evidence.json"
    # Use trestle's .json() for correct enum serialization, then round-trip
    # through json.loads so we get a plain dict before pretty-printing.
    ar_json_str = ar_obj.json(exclude_none=True, by_alias=True)
    payload: dict[str, Any] = {"assessment-results": json.loads(ar_json_str)}
    _write_json(out_path, payload)
    return out_path.resolve()
