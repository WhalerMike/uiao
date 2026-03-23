"""Update POA&M entries from continuous monitoring signals.

Loads data/monitoring-sources.yml and exports/oscal/uiao-poam-template.json,
then enriches POA&M entries whose related controls match a monitoring signal.
Adds 'monitoring-source', 'signal-type', and 'last-signal-date' props to
affected observations. Use --dry-run to preview changes without writing.
"""
import argparse
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import yaml

warnings.warn(
    "scripts/update_poam_from_monitoring.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)

ROOT = Path(__file__).resolve().parent.parent
MONITORING_SOURCES_PATH = ROOT / "data" / "monitoring-sources.yml"
POAM_PATH = ROOT / "exports" / "oscal" / "uiao-poam-template.json"


def load_monitoring_sources():
    """Load monitoring signal definitions from YAML."""
    with MONITORING_SOURCES_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("monitoring_sources", [])


def load_poam():
    """Load the current OSCAL POA&M JSON."""
    with POAM_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_cm_remark(source_name, signal):
    """Build a standardised continuous-monitoring remark string."""
    return (
        f"continuous-monitoring: telemetry from {source_name} "
        f"({signal.get('signal')}) — "
        f"{signal.get('description', '')}"
    )


def build_signal_index(monitoring_sources):
    """Build a dict mapping control-id -> list of (source_name, signal) pairs."""
    index = {}
    for source in monitoring_sources:
        source_name = source.get("name", "Unknown")
        for signal in source.get("telemetry", []):
            control_id = signal.get("maps_to_control")
            if control_id:
                index.setdefault(control_id, []).append((source_name, signal))
    return index


def enrich_poam_items(poam_items, signal_index, now_iso):
    """Add monitoring props to POA&M items whose controls match a signal.

    Returns a list of human-readable change descriptions (empty when no
    enrichment was performed).
    """
    changes = []
    for item in poam_items:
        # Support both old (related-controls list) and new (remarks-embedded)
        # OSCAL item schemas.
        control_ids = item.get("related-controls", {}).get("control-ids", [])
        if not control_ids:
            remarks = item.get("remarks", "")
            for segment in remarks.split("|"):
                segment = segment.strip()
                if segment.startswith("Controls:"):
                    raw = segment[len("Controls:"):].strip()
                    control_ids = [c.strip() for c in raw.split(",") if c.strip()]
                    break

        for ctrl_id in control_ids:
            if ctrl_id not in signal_index:
                continue
            for source_name, signal in signal_index[ctrl_id]:
                if signal.get("poam_status_trigger") != "open":
                    continue

                props = item.setdefault("props", [])

                # Avoid duplicate props from repeated runs
                existing_names = {p.get("name") for p in props}
                new_props = []

                if "monitoring-source" not in existing_names:
                    new_props.append({
                        "name": "monitoring-source",
                        "value": source_name,
                        "ns": "https://fedramp.gov/ns/oscal"
                    })
                if "signal-type" not in existing_names:
                    new_props.append({
                        "name": "signal-type",
                        "value": signal.get("signal", ""),
                        "ns": "https://fedramp.gov/ns/oscal"
                    })

                # Always update last-signal-date
                props[:] = [
                    p for p in props if p.get("name") != "last-signal-date"
                ]
                new_props.append({
                    "name": "last-signal-date",
                    "value": now_iso,
                    "ns": "https://fedramp.gov/ns/oscal"
                })

                props.extend(new_props)

                # Append continuous-monitoring remark
                existing_remarks = item.get("remarks", "")
                cm_note = build_cm_remark(source_name, signal)
                if cm_note not in existing_remarks:
                    item["remarks"] = (
                        f"{existing_remarks}\n{cm_note}".strip()
                    )

                changes.append(
                    f"  Enriched '{item.get('title')}' "
                    f"(control {ctrl_id}) with signal "
                    f"'{signal.get('signal')}' from {source_name}"
                )

    return changes


def main():
    parser = argparse.ArgumentParser(
        description="Update POA&M entries from continuous monitoring signals."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed changes without writing to disk."
    )
    args = parser.parse_args()

    monitoring_sources = load_monitoring_sources()
    poam_doc = load_poam()
    signal_index = build_signal_index(monitoring_sources)

    poam = poam_doc.get("plan-of-action-and-milestones", {})
    poam_items = poam.get("poam-items", [])

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    changes = enrich_poam_items(poam_items, signal_index, now_iso)

    if not changes:
        print("No POA&M entries matched active monitoring signals.")
        return

    print(f"Monitoring enrichment — {len(changes)} update(s):")
    for change in changes:
        print(change)

    if args.dry_run:
        print("\n[dry-run] No files were modified.")
        return

    # Update last-modified timestamp before writing
    poam.setdefault("metadata", {})["last-modified"] = now_iso

    with POAM_PATH.open("w", encoding="utf-8") as f:
        json.dump(poam_doc, f, indent=2)

    print(f"\nPOA&M updated -> {POAM_PATH}")


if __name__ == "__main__":
    main()
