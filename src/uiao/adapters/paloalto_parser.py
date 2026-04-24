"""
paloalto_parser.py — Real PAN-OS XML configuration parsing.

Internal module consumed by PaloAltoAdapter. Handles:
- PAN-OS security rule XML → flat rule list
- PAN-OS NAT rule XML → flat rule list
- Rule comparison for drift detection
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List


def _members(element: ET.Element | None) -> List[str]:
    """Extract member text values from a PAN-OS list element."""
    if element is None:
        return []
    return [m.text or "" for m in element.findall("member")]


def parse_security_rules_xml(xml_content: str) -> List[dict]:
    """Parse PAN-OS security rules from XML API response.

    Args:
        xml_content: Raw XML string from /api/?type=config&action=show&xpath=...

    Returns:
        List of rule dicts with normalized fields.
    """
    root = ET.fromstring(xml_content)
    rules: List[dict] = []

    for entry in root.findall(".//rules/entry"):
        name = entry.get("name", "unknown")
        action_el = entry.find("action")
        action = action_el.text if action_el is not None else "unknown"

        rules.append(
            {
                "type": "security-rule",
                "name": name,
                "from_zone": _members(entry.find("from")),
                "to_zone": _members(entry.find("to")),
                "source": _members(entry.find("source")),
                "destination": _members(entry.find("destination")),
                "application": _members(entry.find("application")),
                "service": _members(entry.find("service")),
                "action": action,
                "log_start": (entry.findtext("log-start", "no") == "yes"),
                "log_end": (entry.findtext("log-end", "no") == "yes"),
                "tags": _members(entry.find("tag")),
            }
        )

    return rules


def parse_nat_rules_xml(xml_content: str) -> List[dict]:
    """Parse PAN-OS NAT rules from XML API response.

    Args:
        xml_content: Raw XML string.

    Returns:
        List of NAT rule dicts.
    """
    root = ET.fromstring(xml_content)
    rules: List[dict] = []

    for entry in root.findall(".//rules/entry"):
        name = entry.get("name", "unknown")

        dst_trans = entry.find("destination-translation")
        translated_addr = ""
        translated_port = ""
        if dst_trans is not None:
            translated_addr = dst_trans.findtext("translated-address", "")
            translated_port = dst_trans.findtext("translated-port", "")

        rules.append(
            {
                "type": "nat-rule",
                "name": name,
                "from_zone": _members(entry.find("from")),
                "to_zone": _members(entry.find("to")),
                "source": _members(entry.find("source")),
                "destination": _members(entry.find("destination")),
                "service": entry.findtext("service", ""),
                "translated_address": translated_addr,
                "translated_port": translated_port,
                "tags": _members(entry.find("tag")),
            }
        )

    return rules


def compare_rulesets(
    current: List[dict],
    baseline: List[dict],
) -> dict:
    """Compare current firewall rules against a baseline.

    Args:
        current: List of current rule dicts.
        baseline: List of expected baseline rule dicts.

    Returns:
        Dict with added/removed/changed/consistent rule lists + summary.
    """
    current_map = {r["name"]: r for r in current}
    baseline_map = {r["name"]: r for r in baseline}

    current_names = set(current_map.keys())
    baseline_names = set(baseline_map.keys())

    added = sorted(current_names - baseline_names)
    removed = sorted(baseline_names - current_names)

    changed: List[str] = []
    consistent: List[str] = []
    for name in sorted(current_names & baseline_names):
        if current_map[name] != baseline_map[name]:
            changed.append(name)
        else:
            consistent.append(name)

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "consistent": consistent,
        "summary": {
            "total": len(current_names | baseline_names),
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
            "consistent_count": len(consistent),
        },
    }
