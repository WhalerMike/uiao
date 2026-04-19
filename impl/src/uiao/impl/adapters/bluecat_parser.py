"""
bluecat_parser.py — Real BlueCat Address Manager (BAM) JSON parsing.

Internal module consumed by BlueCatAdapter. Handles:
- BAM HostRecord JSON → flat record list (A-record equivalent)
- BAM AliasRecord JSON → flat record list (CNAME equivalent)
- BAM DHCP4Range JSON → flat range list
- BAM IP4Address JSON → flat address list
- Entity-set comparison for three-way drift detection

BAM APIs return "entity" objects with a pipe-delimited `properties`
string (e.g. `"absoluteName=host.example.gov|addresses=10.0.1.5|"`).
Parsers here expand that into a plain dict so downstream code can treat
BAM output like any other JSON.
"""

from __future__ import annotations

from typing import Any, Iterable, List


def _results(payload: Any) -> Iterable[dict]:
    """Normalize BAM response envelopes.

    BAM's REST v1 typically returns either a bare list or an object with
    a `result` key. Accept both; anything else yields empty.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, list):
            return result
    return []


def _entity_properties(entity: dict) -> dict:
    """Expand BAM's pipe-delimited `properties` string into a dict.

    Example input:
        {"properties": "absoluteName=web01|addresses=10.0.1.5|"}
    Example output:
        {"absoluteName": "web01", "addresses": "10.0.1.5"}

    If `properties` is already a dict (some wrappers pre-parse it),
    return a shallow copy. Malformed chunks are silently skipped.
    """
    raw = entity.get("properties")
    if isinstance(raw, dict):
        return dict(raw)
    if not isinstance(raw, str):
        return {}
    out: dict[str, str] = {}
    for chunk in raw.split("|"):
        if not chunk:
            continue
        if "=" not in chunk:
            continue
        k, _, v = chunk.partition("=")
        out[k.strip()] = v.strip()
    return out


def parse_host_records(payload: Any) -> List[dict]:
    """Parse BAM HostRecord entries (A-record equivalent)."""
    records: List[dict] = []
    for entry in _results(payload):
        props = _entity_properties(entry)
        records.append({
            "type": "host-record",
            "id": entry.get("id"),
            "name": props.get("absoluteName") or entry.get("name", ""),
            "ipv4addr": props.get("addresses", ""),
            "view": props.get("view", ""),
            "zone": props.get("parentZoneName", ""),
            "ttl": props.get("ttl"),
            "comment": props.get("comments", ""),
        })
    return records


def parse_alias_records(payload: Any) -> List[dict]:
    """Parse BAM AliasRecord entries (CNAME equivalent)."""
    records: List[dict] = []
    for entry in _results(payload):
        props = _entity_properties(entry)
        records.append({
            "type": "alias-record",
            "id": entry.get("id"),
            "name": props.get("absoluteName") or entry.get("name", ""),
            "canonical": props.get("linkedRecordName", ""),
            "view": props.get("view", ""),
            "zone": props.get("parentZoneName", ""),
            "ttl": props.get("ttl"),
            "comment": props.get("comments", ""),
        })
    return records


def parse_dhcp_ranges(payload: Any) -> List[dict]:
    """Parse BAM DHCP4Range entries."""
    ranges: List[dict] = []
    for entry in _results(payload):
        props = _entity_properties(entry)
        ranges.append({
            "type": "dhcp-range",
            "id": entry.get("id"),
            "start": props.get("start", ""),
            "end": props.get("end", ""),
            "network": props.get("network", ""),
            "view": props.get("configuration", ""),
            "comment": props.get("comments", ""),
        })
    return ranges


def parse_ip_addresses(payload: Any) -> List[dict]:
    """Parse BAM IP4Address entries (static, DHCP_RESERVED, DHCP_FREE)."""
    addresses: List[dict] = []
    for entry in _results(payload):
        props = _entity_properties(entry)
        addresses.append({
            "type": "ip-address",
            "id": entry.get("id"),
            "ipv4addr": props.get("address", ""),
            "mac": props.get("macAddress", ""),
            "name": entry.get("name", "") or props.get("name", ""),
            "state": props.get("state", ""),
            "view": props.get("configuration", ""),
            "comment": props.get("comments", ""),
        })
    return addresses


def _record_key(record: dict) -> str:
    """Stable identity key for a parsed BAM record.

    BAM object `id` is the canonical key when present. Falls back to
    `<type>:<view>:<ident>` so comparisons work on hand-crafted baselines
    that lack numeric IDs.
    """
    ident = record.get("id")
    if ident is not None and ident != "":
        return f"bam:{ident}"
    rtype = record.get("type", "unknown")
    view = record.get("view", "default")
    fallback = (
        record.get("name")
        or record.get("ipv4addr")
        or record.get("start", "")
    )
    return f"{rtype}:{view}:{fallback}"


def diff_record_sets(
    baseline: List[dict],
    live: List[dict],
) -> dict:
    """Compare a baseline record set against live BAM output.

    Returns dict with added/removed/modified/consistent keys + summary
    counts. Shape matches `infoblox_parser.diff_record_sets` so both
    IPAM adapters can share downstream drift-handling code.
    """
    baseline_map = {_record_key(r): r for r in baseline}
    live_map = {_record_key(r): r for r in live}

    baseline_keys = set(baseline_map.keys())
    live_keys = set(live_map.keys())

    added = sorted(live_keys - baseline_keys)
    removed = sorted(baseline_keys - live_keys)

    modified: List[str] = []
    consistent: List[str] = []
    for key in sorted(baseline_keys & live_keys):
        if baseline_map[key] != live_map[key]:
            modified.append(key)
        else:
            consistent.append(key)

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "consistent": consistent,
        "summary": {
            "total": len(baseline_keys | live_keys),
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "consistent_count": len(consistent),
            "drift_count": len(added) + len(removed) + len(modified),
        },
    }
