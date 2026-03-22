# Modernization Atlas: Project uiao-core

Welcome to the authoritative guide for the agency's infrastructure transformation. The **uiao-core** initiative replaces legacy, fragmented silos with a unified, programmable architecture.

## Mission-to-Tech Alignment
Our modernization strategy is built to deliver three primary outcomes: **Agility**, **Security**, and **Compliance**.

![Mission Mapping](./images/mission_tech_mapping.png)

### Core Strategic Pillars

* **Identity Plane:** Moving to a Zero-Trust identity model via Azure AD and Cisco ISE.
* **Addressing Plane:** Automating the lifecycle of every IP and DNS record via Infoblox.
* **Overlay Plane:** Implementing a programmable fabric that abstracts the physical network.
* **Telemetry Plane:** Creating a closed-loop feedback system using Splunk and Azure Monitor.

---

> **Executive Summary:** This Atlas is a "Living Document." It is generated directly from our codebase, ensuring that the documentation is always synchronized with the authoritative technical standards.

## OSCAL Exports (FedRAMP 20x Ready)

Auto-generated machine-readable compliance artifacts. Use the **Download** buttons to retrieve each JSON file directly, or expand the preview panels to inspect key metadata inline.

---

### SSP Skeleton

[⬇ Download SSP Skeleton JSON](https://raw.githubusercontent.com/WhalerMike/uiao-core/main/exports/oscal/uiao-ssp-skeleton.json){ .md-button }

??? example "JSON Preview — SSP Skeleton"

    ```json
    {
      "system-security-plan": {
        "uuid": "bca56052-5f31-4e02-904b-89aa87261f1f",
        "metadata": {
          "title": "UIAO Unified Identity-Addressing-Overlay Architecture - System Security Plan (FedRAMP Moderate Skeleton)",
          "last-modified": "2026-03-22T19:19:12.593713Z",
          "version": "1.0-skeleton",
          "oscal-version": "1.0.0",
          "props": [
            { "name": "impact-level", "value": "moderate", "ns": "https://fedramp.gov/ns/oscal" },
            { "name": "compliance-strategy", "value": "OSCAL-based Telemetry Validation" }
          ]
        },
        "import-profile": {
          "href": "https://github.com/GSA/fedramp-automation/raw/main/dist/content/rev5/baselines/json/FedRAMP_rev5_MODERATE-baseline_profile.json"
        },
        "..."
      }
    }
    ```

    > Full file: [uiao-ssp-skeleton.json](https://raw.githubusercontent.com/WhalerMike/uiao-core/main/exports/oscal/uiao-ssp-skeleton.json)

---

### Component Definition

[⬇ Download Component Definition JSON](https://raw.githubusercontent.com/WhalerMike/uiao-core/main/exports/oscal/uiao-component-definition.json){ .md-button }

??? example "JSON Preview — Component Definition"

    ```json
    {
      "component-definition": {
        "uuid": "4fd8ae60-ce43-4079-93be-ee53425a91db",
        "metadata": {
          "title": "UIAO Unified Identity-Addressing-Overlay Architecture",
          "last-modified": "2026-03-22T18:59:48.718579Z",
          "version": "1.0",
          "oscal-version": "1.0.0",
          "props": [
            { "name": "fedramp-impact", "value": "Moderate", "ns": "https://fedramp.gov/ns/oscal" },
            { "name": "compliance-strategy", "value": "OSCAL-based Telemetry Validation" },
            { "name": "ksi-dashboard", "value": "Operational" }
          ]
        },
        "components": [ "... 5 components defined ..." ],
        "..."
      }
    }
    ```

    > Full file: [uiao-component-definition.json](https://raw.githubusercontent.com/WhalerMike/uiao-core/main/exports/oscal/uiao-component-definition.json)

---

### POA&M Template

[⬇ Download POA&M Template JSON](https://raw.githubusercontent.com/WhalerMike/uiao-core/main/exports/oscal/uiao-poam-template.json){ .md-button }

??? example "JSON Preview — POA&amp;M Template"

    ```json
    {
      "plan-of-action-and-milestones": {
        "uuid": "39a67b22-78ed-41d2-80a1-6a72e11eaaa7",
        "metadata": {
          "title": "UIAO Modernization POA&M - Auto-Detected Gaps (FedRAMP Moderate)",
          "last-modified": "2026-03-22T19:19:12.316140Z",
          "version": "1.0",
          "oscal-version": "1.0.0",
          "props": [
            { "name": "impact-level", "value": "moderate", "ns": "https://fedramp.gov/ns/oscal" },
            { "name": "generated-from", "value": "UIAO Canon Gap Detection" }
          ]
        },
        "import-ssp": { "href": "../oscal/uiao-ssp-skeleton.json" },
        "poam-items": [ "... 7 items ..." ],
        "..."
      }
    }
    ```

    > Full file: [uiao-poam-template.json](https://raw.githubusercontent.com/WhalerMike/uiao-core/main/exports/oscal/uiao-poam-template.json)

### SSP Inventory

The SSP `system-inventory` section is auto-generated from [`data/inventory-items.yml`](https://github.com/WhalerMike/uiao-core/blob/main/data/inventory-items.yml).
Each inventory item links back to a component in the Component Definition via its `component-id` prop.

| Inventory ID | Description | Component Link | Vendor |
|---|---|---|---|
| `inv-entra-id` | Microsoft Entra ID - Identity Provider | `component-identity` | Microsoft |
| `inv-sentinel` | Microsoft Sentinel - SIEM Platform | `component-telemetry` | Microsoft |
| `inv-cisco-sdwan` | Cisco SD-WAN - Network Segmentation | `component-network` | Cisco |
| `inv-infoblox-ddi` | InfoBlox DDI - DNS/DHCP/IPAM | `component-addressing` | InfoBlox |
---

## Continuous Monitoring

Real-time telemetry from **Microsoft Sentinel** (SIEM) is integrated with POA&M status tracking. When a monitoring signal fires, the corresponding POA&M finding is automatically enriched with the signal source, type, and timestamp so that compliance documentation stays synchronized with operational security posture.

### Active Monitoring Sources

| Source | Type | Controls Covered |
|---|---|---|
| Microsoft Sentinel | SIEM | AC-2, AC-6, IA-2, SC-7 |

### Telemetry Signal → POA&M Mapping

| Signal | Control | Trigger | Description |
|---|---|---|---|
| `identity_anomaly` | AC-2 | open | Anomalous identity behavior detected |
| `mfa_bypass_attempt` | IA-2 | open | MFA bypass or fallback detected |
| `network_segmentation_alert` | SC-7 | open | Unexpected cross-segment traffic detected |
| `privileged_access_escalation` | AC-6 | open | Unauthorized privilege escalation detected |

When a signal's `poam_status_trigger` is `open`, the relevant POA&M item receives:

- **`monitoring-source`** prop — name of the originating SIEM (e.g., *Microsoft Sentinel*)
- **`signal-type`** prop — machine-readable signal identifier (e.g., `identity_anomaly`)
- **`last-signal-date`** prop — ISO 8601 timestamp of the most recent enrichment run
- **`continuous-monitoring`** remark — human-readable note linking the telemetry to the finding

Enrichment is performed automatically by `scripts/generate_poam.py` (via `monitoring_enabled=True`) and can also be run standalone with `scripts/update_poam_from_monitoring.py`. Use the `--dry-run` flag to preview changes without modifying any artifacts.
