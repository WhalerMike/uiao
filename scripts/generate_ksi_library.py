#!/usr/bin/env python3
"""Generate KSI YAML files from the control library.

Reads all control YAML files from data/control-library/,
groups enhancements with base controls, and writes one KSI
file per base control to rules/ksi/<category>/.
"""

import hashlib
import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTROL_LIB = REPO_ROOT / "data" / "control-library"
KSI_DIR = REPO_ROOT / "rules" / "ksi"

TIMESTAMP = "2026-04-04T00:00:00Z"
COLLECTOR_ID = "uiao-core-ksi-builder"
VERSION = "1.0.0"

# --- Data source mappings per family ---
FAMILY_DATA_SOURCES = {
    "AC": ["EntraID", "AzureActivityLogs"],
    "AT": ["CustomApi"],
    "AU": ["AzureActivityLogs", "AzureMonitorMetrics"],
    "CA": ["AzurePolicy", "AzureResourceGraph"],
    "CM": ["AzurePolicy", "AzureResourceGraph", "AzureMonitorMetrics"],
    "CP": ["AzureResourceGraph", "CustomApi"],
    "IA": ["EntraID", "AzureActivityLogs"],
    "IR": ["MicrosoftDefenderXDR", "AzureActivityLogs"],
    "MA": ["AzureActivityLogs", "CustomApi"],
    "MP": ["Other"],
    "PE": ["Other"],
    "PL": ["CustomApi"],
    "PS": ["EntraID", "CustomApi"],
    "RA": ["DefenderForEndpoint", "AzureResourceGraph"],
    "SA": ["AzureResourceGraph", "CustomApi"],
    "SC": ["AzureFirewallLogs", "AzureWAFLogs", "AzureMonitorMetrics"],
    "SI": ["DefenderForEndpoint", "MDE", "AzureMonitorMetrics"],
    "SR": ["CustomApi"],
}

# Override/supplement data sources for specific controls
CONTROL_DATA_SOURCES = {
    "AC-2": ["EntraID", "AzureActivityLogs"],
    "AC-3": ["EntraID", "AzurePolicy"],
    "AC-4": ["AzureFirewallLogs", "AzureWAFLogs"],
    "AC-17": ["EntraID", "AzureActivityLogs"],
    "AC-18": ["AzureResourceGraph", "AzureMonitorMetrics"],
    "AC-19": ["DefenderForEndpoint", "EntraID"],
    "AU-2": ["AzureActivityLogs", "AzureMonitorMetrics"],
    "AU-6": ["AzureActivityLogs", "MicrosoftDefenderXDR"],
    "AU-12": ["AzureActivityLogs", "Syslog", "WindowsEventLogs"],
    "CA-7": ["AzurePolicy", "DefenderForEndpoint", "AzureMonitorMetrics"],
    "CA-8": ["DefenderForEndpoint", "AzureResourceGraph"],
    "CM-2": ["AzurePolicy", "AzureResourceGraph"],
    "CM-6": ["AzurePolicy", "AzureResourceGraph"],
    "CM-7": ["AzurePolicy", "DefenderForEndpoint"],
    "CM-8": ["AzureResourceGraph", "AzurePolicy"],
    "IA-2": ["EntraID", "AzureActivityLogs"],
    "IA-5": ["EntraID", "AzureActivityLogs"],
    "IA-8": ["EntraID", "AzureActivityLogs"],
    "IR-4": ["MicrosoftDefenderXDR", "AzureActivityLogs", "DefenderForEndpoint"],
    "IR-6": ["MicrosoftDefenderXDR", "AzureActivityLogs"],
    "RA-5": ["DefenderForEndpoint", "MDE", "AzureResourceGraph"],
    "SC-7": ["AzureFirewallLogs", "AzureWAFLogs", "CiscoSDWAN"],
    "SC-8": ["AzureMonitorMetrics", "AzureFirewallLogs"],
    "SC-12": ["AzureResourceGraph", "CustomApi"],
    "SC-28": ["AzurePolicy", "AzureResourceGraph"],
    "SI-2": ["DefenderForEndpoint", "AzurePolicy"],
    "SI-3": ["DefenderForEndpoint", "MDE"],
    "SI-4": ["MicrosoftDefenderXDR", "DefenderForEndpoint", "AzureMonitorMetrics"],
    "SI-7": ["AzurePolicy", "DefenderForEndpoint"],
}

# Severity by family (default)
FAMILY_SEVERITY = {
    "AC": "high",
    "AT": "moderate",
    "AU": "high",
    "CA": "moderate",
    "CM": "high",
    "CP": "moderate",
    "IA": "critical",
    "IR": "high",
    "MA": "moderate",
    "MP": "moderate",
    "PE": "low",
    "PL": "low",
    "PS": "moderate",
    "RA": "high",
    "SA": "moderate",
    "SC": "critical",
    "SI": "high",
    "SR": "moderate",
}

# Override severity for specific controls
CONTROL_SEVERITY = {
    "AC-1": "low",
    "AC-2": "critical",
    "AC-3": "critical",
    "AC-6": "high",
    "AT-1": "low",
    "AU-1": "low",
    "AU-2": "high",
    "AU-6": "high",
    "CA-1": "low",
    "CM-1": "low",
    "CP-1": "low",
    "IA-1": "low",
    "IA-2": "critical",
    "IA-5": "critical",
    "IR-1": "low",
    "IR-4": "critical",
    "MA-1": "low",
    "MP-1": "low",
    "PE-1": "low",
    "PL-1": "low",
    "PS-1": "low",
    "RA-1": "low",
    "RA-5": "critical",
    "SA-1": "low",
    "SC-1": "low",
    "SC-7": "critical",
    "SI-1": "low",
    "SI-4": "critical",
}

# Freshness windows
FAMILY_FRESHNESS = {
    "AC": "PT24H",
    "AT": "P30D",
    "AU": "PT24H",
    "CA": "P7D",
    "CM": "PT24H",
    "CP": "P30D",
    "IA": "PT24H",
    "IR": "PT1H",
    "MA": "P7D",
    "MP": "P30D",
    "PE": "P30D",
    "PL": "P30D",
    "PS": "P7D",
    "RA": "P7D",
    "SA": "P30D",
    "SC": "PT24H",
    "SI": "PT24H",
    "SR": "P30D",
}

# OSCAL evidence types
FAMILY_OSCAL_TYPE = {
    "AC": "observation",
    "AT": "assessment-result",
    "AU": "observation",
    "CA": "assessment-result",
    "CM": "observation",
    "CP": "assessment-result",
    "IA": "observation",
    "IR": "observation",
    "MA": "assessment-result",
    "MP": "assessment-result",
    "PE": "assessment-result",
    "PL": "implemented-requirement",
    "PS": "assessment-result",
    "RA": "observation",
    "SA": "assessment-result",
    "SC": "observation",
    "SI": "observation",
    "SR": "assessment-result",
}

# Quarto snippet types
FAMILY_QUARTO_TYPE = {
    "AC": "evidence-panel",
    "AT": "table-row",
    "AU": "dashboard-widget",
    "CA": "evidence-panel",
    "CM": "dashboard-widget",
    "CP": "table-row",
    "IA": "evidence-panel",
    "IR": "dashboard-widget",
    "MA": "table-row",
    "MP": "table-row",
    "PE": "table-row",
    "PL": "markdown-fragment",
    "PS": "table-row",
    "RA": "dashboard-widget",
    "SA": "table-row",
    "SC": "evidence-panel",
    "SI": "dashboard-widget",
    "SR": "table-row",
}

# Tags per family (UIAO control plane mapping)
FAMILY_TAGS = {
    "AC": ["access-control", "identity-plane"],
    "AT": ["awareness-training", "management-plane"],
    "AU": ["audit", "telemetry-plane"],
    "CA": ["assessment", "management-plane"],
    "CM": ["configuration", "management-plane"],
    "CP": ["contingency", "management-plane"],
    "IA": ["identification-authentication", "identity-plane"],
    "IR": ["incident-response", "telemetry-plane"],
    "MA": ["maintenance", "management-plane"],
    "MP": ["media-protection", "management-plane"],
    "PE": ["physical-security", "management-plane"],
    "PL": ["planning", "management-plane"],
    "PS": ["personnel-security", "identity-plane"],
    "RA": ["risk-assessment", "security-plane"],
    "SA": ["acquisition", "management-plane"],
    "SC": ["system-communications", "network-plane"],
    "SI": ["system-integrity", "security-plane"],
    "SR": ["supply-chain", "management-plane"],
}


FAMILY_CATEGORY = {
    "AC": "iam",
    "IA": "iam",
    "PS": "planning-personnel",
    "SC": "boundary-protection",
    "AU": "monitoring-logging",
    "SI": "monitoring-logging",
    "CM": "configuration-management",
    "IR": "incident-response",
    "MA": "planning-personnel",
    "MP": "planning-personnel",
    "PE": "planning-personnel",
    "PL": "planning-personnel",
    "AT": "other",
    "CA": "other",
    "CP": "other",
    "RA": "other",
    "SA": "other",
    "SR": "other",
}

def parse_control_id(filename: str) -> tuple[str, str, str | None]:
    """Parse filename into (family, base_number, enhancement_number|None)."""
    name = filename.replace(".yml", "")
    m = re.match(r"^([A-Z]{2})-(\d+)(?:\((\d+)\))?$", name)
    if not m:
        return ("", "", None)
    return (m.group(1), m.group(2), m.group(3))


def make_ksi_id(family: str, number: str) -> str:
    """Create KSI ID like KSI-AC-02."""
    return f"KSI-{family}-{number.zfill(2)}"


def make_control_ref(family: str, number: str, enh: str | None) -> str:
    """Create NIST control reference like AC-2 or AC-2(3)."""
    base = f"{family}-{number}"
    if enh:
        base += f"({enh})"
    return base


def generate_hash(content: str) -> str:
    """Generate SHA-256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def build_expected_patterns(title: str, family: str, narrative: str) -> list[str]:
    """Generate meaningful expected patterns based on control content."""
    patterns = []

    # Family-specific pattern templates
    family_patterns = {
        "AC": [
            f"All {title.lower()} policies must be enforced and validated",
            "Access decisions must be logged and auditable within the telemetry plane",
        ],
        "AT": [
            f"All personnel must complete {title.lower()} within required timeframes",
            "Training completion records must be current and verifiable",
        ],
        "AU": [
            f"{title} must be continuously operational across all system components",
            "Audit data must be collected, stored, and available for review within freshness window",
        ],
        "CA": [
            f"{title} must be performed according to the defined schedule",
            "Assessment results must be documented and tracked to resolution",
        ],
        "CM": [
            f"{title} must reflect current approved state of all system components",
            "Configuration drift must be detected and reported within 24 hours",
        ],
        "CP": [
            f"{title} must be tested and validated according to schedule",
            "Recovery objectives must be achievable based on current infrastructure state",
        ],
        "IA": [
            f"{title} must enforce phishing-resistant MFA for all privileged access",
            "All authentication events must be bound to UIAO identity namespace",
        ],
        "IR": [
            f"{title} must be operational and tested",
            "Incident detection to response initiation must meet defined SLA thresholds",
        ],
        "MA": [
            f"{title} must be performed only by authorized personnel with proper access",
            "All maintenance activities must be logged in the telemetry plane",
        ],
        "MP": [
            f"{title} must be enforced for all media containing CUI",
            "Media handling events must be tracked and auditable",
        ],
        "PE": [
            f"{title} must be enforced at all facility access points",
            "Physical access events must be logged and reviewable",
        ],
        "PL": [
            f"{title} must be current and approved by authorizing official",
            "Planning artifacts must be updated within defined review cycles",
        ],
        "PS": [
            f"{title} must be completed before system access is granted",
            "Personnel status changes must trigger automated access review",
        ],
        "RA": [
            f"{title} must identify and prioritize all known vulnerabilities",
            "Risk findings must be tracked to remediation or acceptance",
        ],
        "SA": [
            f"{title} must include security requirements in all acquisitions",
            "Vendor compliance evidence must be collected and validated",
        ],
        "SC": [
            f"{title} must be enforced across all system communication paths",
            "Network security posture must be continuously monitored and validated",
        ],
        "SI": [
            f"{title} must detect and report anomalies within defined thresholds",
            "System integrity checks must pass validation within freshness window",
        ],
        "SR": [
            f"{title} must be validated for all critical supply chain components",
            "Supply chain risk indicators must be monitored and current",
        ],
    }

    patterns = family_patterns.get(family, [
        f"{title} must be validated and current",
        "Evidence must be collected within the defined freshness window",
    ])

    return patterns


def load_controls() -> dict[str, dict]:
    """Load all controls, grouped by base control ID."""
    groups: dict[str, dict] = {}

    for f in sorted(CONTROL_LIB.glob("*.yml")):
        if f.name in ("control_library_report.md", "dir.txt", "uiao-control-matrix.yaml"):
            continue

        family, number, enh = parse_control_id(f.name)
        if not family:
            continue

        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        base_key = f"{family}-{number}"
        ctrl_ref = make_control_ref(family, number, enh)

        if base_key not in groups:
            groups[base_key] = {
                "family": family,
                "number": number,
                "title": data.get("title", f"{family}-{number}"),
                "narrative": data.get("narrative", ""),
                "controls": [],
                "implemented_by": data.get("implemented-by", []),
                "status": data.get("status", "planned"),
            }

        groups[base_key]["controls"].append(ctrl_ref)

        # If this is the base control, update title/narrative
        if enh is None:
            groups[base_key]["title"] = data.get("title", groups[base_key]["title"])
            groups[base_key]["narrative"] = data.get("narrative", groups[base_key]["narrative"])
            groups[base_key]["implemented_by"] = data.get("implemented-by", groups[base_key]["implemented_by"])
            groups[base_key]["status"] = data.get("status", groups[base_key]["status"])

    return groups


def generate_ksi(base_key: str, group: dict) -> dict:
    """Generate a KSI definition dict for a control group."""
    family = group["family"]
    number = group["number"]
    ksi_id = make_ksi_id(family, number)
    title = group["title"]
    narrative = group["narrative"]

    # Sort controls naturally
    controls = sorted(set(group["controls"]))

    data_sources = CONTROL_DATA_SOURCES.get(base_key, FAMILY_DATA_SOURCES.get(family, ["Other"]))
    severity = CONTROL_SEVERITY.get(base_key, FAMILY_SEVERITY.get(family, "moderate"))
    freshness = FAMILY_FRESHNESS.get(family, "P7D")
    oscal_type = FAMILY_OSCAL_TYPE.get(family, "observation")
    quarto_type = FAMILY_QUARTO_TYPE.get(family, "table-row")
    tags = FAMILY_TAGS.get(family, []) + [f"fedramp-moderate"]

    expected_patterns = build_expected_patterns(title, family, narrative)

    filename = f"ksi-{family.lower()}-{number.zfill(2)}.yaml"
    validation_ref = f"ksi/{filename}"

    # Build the KSI dict
    ksi = {
        "ksi_id": ksi_id,
        "title": title,
        "description": f"Measures and validates compliance with {base_key} ({title}) and its enhancements. "
                       f"Monitors {', '.join(data_sources)} for evidence of control implementation and effectiveness.",
        "severity": severity,
        "family": family,
        "controls": controls,
        "data_sources": data_sources,
        "validation_logic_ref": validation_ref,
        "freshness_window": freshness,
        "expected_patterns": expected_patterns,
        "evidence_output": {
            "oscal_evidence_type": oscal_type,
            "quarto_snippet_type": quarto_type,
        },
        "provenance": {
            "source": "generated-from-template",
            "timestamp": TIMESTAMP,
            "collector_id": COLLECTOR_ID,
            "hash": "placeholder",  # Will be replaced
        },
        "version": VERSION,
        "tags": tags,
        "enabled": True,
    }

    # Generate hash from content (excluding the hash field itself)
    hash_content = yaml.dump(ksi, default_flow_style=False, sort_keys=True)
    ksi["provenance"]["hash"] = generate_hash(hash_content)

    return ksi


def write_ksi_file(ksi: dict, family: str, number: str) -> str:
    """Write a KSI YAML file and return the filename."""
    filename = f"ksi-{family.lower()}-{number.zfill(2)}.yaml"
    category = FAMILY_CATEGORY.get(family, "other")
    subdir = KSI_DIR / category
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / filename

    # Custom YAML dumper to get nice formatting
    content = yaml.dump(
        ksi,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )

    filepath.write_text(content, encoding="utf-8")
    return filename


def main() -> None:
    KSI_DIR.mkdir(parents=True, exist_ok=True)

    groups = load_controls()
    print(f"Found {len(groups)} base controls to generate KSIs for")

    generated = []
    for base_key in sorted(groups.keys(), key=lambda k: (k.split("-")[0], int(k.split("-")[1]))):
        group = groups[base_key]
        ksi = generate_ksi(base_key, group)
        filename = write_ksi_file(ksi, group["family"], group["number"])
        generated.append(filename)
        print(f"  Generated {filename} ({ksi['ksi_id']}) — {len(group['controls'])} controls")

    print(f"\nDone: {len(generated)} KSI files written to {KSI_DIR}")


if __name__ == "__main__":
    main()
