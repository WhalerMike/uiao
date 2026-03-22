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

Auto-generated machine-readable compliance artifacts:
- [Component Definition](https://github.com/WhalerMike/uiao-core/blob/main/exports/oscal/uiao-component-definition.json)
- [POA&M Template](https://github.com/WhalerMike/uiao-core/blob/main/exports/oscal/uiao-poam-template.json)
- [SSP Skeleton](https://github.com/WhalerMike/uiao-core/blob/main/exports/oscal/uiao-ssp-skeleton.json)

### SSP Inventory

The SSP `system-inventory` section is auto-generated from [`data/inventory-items.yml`](https://github.com/WhalerMike/uiao-core/blob/main/data/inventory-items.yml).
Each inventory item links back to a component in the Component Definition via its `component-id` prop.

| Inventory ID | Description | Component Link | Vendor |
|---|---|---|---|
| `inv-entra-id` | Microsoft Entra ID - Identity Provider | `component-identity` | Microsoft |
| `inv-sentinel` | Microsoft Sentinel - SIEM Platform | `component-telemetry` | Microsoft |
| `inv-cisco-sdwan` | Cisco SD-WAN - Network Segmentation | `component-network` | Cisco |
| `inv-infoblox-ddi` | InfoBlox DDI - DNS/DHCP/IPAM | `component-addressing` | InfoBlox |