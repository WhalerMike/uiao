"""Link-registry evidence rendering (UIAO_145 / ADR-132 Phase 2).

Renders the external-interconnection inventory from the canonical link
registry (``uiao.canon/link-registry.yaml``) as control evidence — the
substrate-side replacement for the retired SharePoint-pointer pattern on
CA-3 (Information Exchange) and its sibling controls (CA-9, SA-9, AC-20).

The registry is read via ``importlib.resources`` (canon is package data;
never a hardcoded filesystem path). Output is deterministic: links are
sorted by id, and no wall-clock values are stamped — callers that need a
generation timestamp add it at the edge.
"""

from __future__ import annotations

from importlib import resources
from typing import Any

import yaml

# Controls the link registry evidences (UIAO_145 §2). A link declares the
# subset that applies via its `controls:` field; this list is the render
# surface offered by `uiao evidence links`.
LINK_EVIDENCE_CONTROLS: tuple[str, ...] = ("CA-3", "CA-9", "SA-9", "AC-20")


def load_link_registry() -> dict[str, Any]:
    """Load the canonical link registry from package data.

    Returns the parsed YAML document. Raises ``FileNotFoundError`` if the
    registry is absent from the installed canon (a packaging error — the
    registry ships with the wheel) and ``yaml.YAMLError`` on a corrupt
    document; callers surface both as hard failures rather than treating
    a missing inventory as an empty one.
    """
    resource = resources.files("uiao.canon").joinpath("link-registry.yaml")
    if not resource.is_file():
        raise FileNotFoundError("uiao.canon/link-registry.yaml is not present in the installed package")
    with resource.open("r", encoding="utf-8") as fh:
        try:
            data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise ValueError(f"link-registry.yaml is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("link-registry.yaml did not parse to a mapping")
    return data


def _link_row(link: dict[str, Any]) -> dict[str, Any]:
    counterparty = link.get("counterparty") or {}
    agreement = link.get("agreement") or {}
    return {
        "id": link.get("id"),
        "name": link.get("name"),
        "counterparty": counterparty.get("name"),
        "counterparty-class": counterparty.get("class"),
        "direction": link.get("direction"),
        "ssot-stance": link.get("ssot-stance"),
        "status": link.get("status"),
        "agreement-type": agreement.get("type"),
        "agreement-location": agreement.get("artifact-location"),
        "provenance-anchored": agreement.get("provenance-anchored"),
        "review-cadence": agreement.get("review-cadence"),
        "next-review": agreement.get("next-review"),
        "regime-overlays": list(link.get("regime-overlays") or []),
        "authorized-by": list(link.get("authorized-by") or []),
    }


def link_evidence_inventory(
    controls: tuple[str, ...] | list[str] | None = None,
    *,
    registry: dict[str, Any] | None = None,
    include_inactive: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Build the per-control interconnection inventory.

    Args:
        controls: Controls to render; defaults to ``LINK_EVIDENCE_CONTROLS``.
            An unknown control (one the render surface doesn't offer)
            raises ``ValueError`` — a typo'd control id must not silently
            render an empty (and thus false) "no interconnections" table.
        registry: Pre-loaded registry document (tests); defaults to the
            packaged canon registry.
        include_inactive: When True, ``proposed``/``retired`` links are
            included with their status shown. Default False: evidence
            renders only what is operationally live.

    Returns:
        Mapping of control id -> list of link rows (sorted by link id).
        A control with no bound links maps to an empty list, which is a
        truthful statement ("no registered interconnection evidences this
        control") — the link-gap scanner is the surface that judges
        whether that emptiness is a gap.
    """
    wanted = tuple(controls) if controls else LINK_EVIDENCE_CONTROLS
    unknown = [c for c in wanted if c not in LINK_EVIDENCE_CONTROLS]
    if unknown:
        raise ValueError(
            f"not a link-evidence control: {', '.join(unknown)} (render surface is {', '.join(LINK_EVIDENCE_CONTROLS)})"
        )

    doc = registry if registry is not None else load_link_registry()
    links = doc.get("links") or []

    inventory: dict[str, list[dict[str, Any]]] = {c: [] for c in wanted}
    for link in sorted(
        (entry for entry in links if isinstance(entry, dict)), key=lambda entry: str(entry.get("id", ""))
    ):
        status = str(link.get("status", "")).strip().lower()
        if status != "active" and not include_inactive:
            continue
        for control in link.get("controls") or []:
            control_id = str(control).strip()
            if control_id in inventory:
                inventory[control_id].append(_link_row(link))
    return inventory


def render_markdown(inventory: dict[str, list[dict[str, Any]]]) -> str:
    """Render the inventory as a deterministic markdown evidence appendix."""
    lines: list[str] = ["# External Interconnection Inventory (link registry, UIAO_145)", ""]
    for control in sorted(inventory):
        rows = inventory[control]
        lines.append(f"## {control}")
        lines.append("")
        if not rows:
            lines.append("_No registered interconnection evidences this control._")
            lines.append("")
            continue
        lines.append("| Link | Counterparty | Class | Direction | SSOT stance | Agreement | Anchored | Authorized by |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for row in rows:
            agreement = f"{row['agreement-type'] or '—'} @ {row['agreement-location'] or '—'}"
            anchored = "yes" if row["provenance-anchored"] else "no"
            authorized = "<br>".join(row["authorized-by"]) or "—"
            lines.append(
                f"| `{row['id']}` | {row['counterparty']} | {row['counterparty-class']} "
                f"| {row['direction']} | {row['ssot-stance']} | {agreement} | {anchored} | {authorized} |"
            )
        lines.append("")
    return "\n".join(lines)
