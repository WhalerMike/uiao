---
title: "UIAO Unified Architecture"
version: "1.0"
classification: "CUI/FOUO"
---

# UIAO Unified Architecture

**Version 1.0**

---

## 1. Architectural Overview

UIAO consolidates four infrastructure layers that currently operate as separate programs under
separate ownership: identity (Active Directory and Entra ID), addressing (DNS/DHCP/IPAM), network
routing (TIC-compliant SD-WAN), and telemetry (Splunk correlation feeds). Today these layers are
managed by different teams, procured on different cycles, and monitored against different baselines.
When something breaks at the intersection — and it regularly does — the diagnosis takes days because
no single team owns the full picture.

The program is organized around four control planes, each with a defined vendor, a defined OSCAL
component definition, and a defined set of FedRAMP Moderate controls it satisfies. Identity goes to
Entra ID and CyberArk. Network goes to Cisco SD-WAN with TIC 3.0 policy enforcement. Addressing goes
to Infoblox DDI. Telemetry goes to Splunk with Palo Alto Prisma for inline inspection.

Each plane is independently deployable. The agency does not need to cut over everything at once.
Phase 1 can deliver cloud-first routing and Entra ID consolidation without touching IPAM. That matters
because the legacy PKI dependency in the case management platform cannot be resolved until FY27 at
the earliest, and the program is designed to work around it.


The Unified Identity-Addressing-Overlay (UIAO) architecture integrates four control planes into a single cohesive framework. Each plane governs a distinct operational domain while sharing telemetry, policy signals, and configuration data with the others through well-defined integration points.

---

## 2. Four-Plane Architecture Diagram

The following diagram illustrates the complete UIAO architecture, showing how the Identity, Addressing, Overlay, and Telemetry control planes interconnect through the central Policy Engine.

<img src="assets/images/plantuml/diagram_1.png" alt="diagram_1" />

---

## 3. The Control Planes


### 3.1. Identity Control Plane

The Identity Control Plane is anchored in Entra ID and reinforced by
ICAM governance, Conditional Access, Privileged Identity Management,
and lifecycle automation. Identity becomes the authoritative source
for access, addressing, certificates, and policy.



### 3.2. Network Control Plane

The Network Control Plane uses Cisco SD-WAN to deliver cloud-first
routing, performance-optimized paths for M365, and identity-aware
segmentation. Integration with INR enables location-aware routing and
emergency services readiness.



### 3.3. Addressing Control Plane

The Addressing Control Plane modernizes IPAM through InfoBlox,
replacing spreadsheets with authoritative, identity-derived
addressing. DNS and DHCP are unified across cloud and on-prem
environments, enabling consistent policy enforcement and accurate
telemetry correlation.



### 3.4. Telemetry & Location Control Plane

The Telemetry and Location Control Plane consolidates signals from
M365, SD-WAN, endpoints, DNS, CDM/CLAW, and SIEM platforms. Telemetry
becomes a real-time control input for routing, security, and
compliance, enabling conversation-level visibility across the
enterprise.



### 3.5. Security & Compliance Plane

The Security and Compliance Plane aligns the architecture with TIC
3.0, Zero Trust, FedRAMP 20x Phase 2, NIST 800-63, and ICAM governance.
Security becomes embedded in the architecture rather than bolted on,
with automated enforcement replacing manual review.




---

## 4. Multi-Plane Integration

The UIAO architecture achieves its power through deep integration between control planes. The telemetry plane provides closed-loop feedback to all other planes, enabling real-time policy adjustment and continuous compliance validation.

<img src="assets/images/plantuml/diagram_2.png" alt="diagram_2" />

---

## 5. Core Stack Integration

The following diagram illustrates how the three pillars of the UIAO framework interconnect. Each node is derived from the program data layer.

<img src="assets/images/plantuml/graph_lr.png" alt="graph_lr" />

---

## 6. Legacy vs. Modernized State

The following diagram compares the fragmented legacy state with the unified modernized architecture that UIAO delivers.

<img src="assets/images/plantuml/diagram_4.png" alt="diagram_4" />

---

## 7. Mission-to-Technology Mapping

The following diagram demonstrates how each technical control plane maps to strategic mission outcomes, providing executive visibility into the return on modernization investment.

<img src="assets/images/plantuml/diagram_5.png" alt="diagram_5" />

---

## 8. Eight Core Concepts



### 8.1. Single Source of Truth (SSOT)

The canonical data repository is the authoritative origin for all
architectural definitions. Every document, template, and generated
artifact derives its definitions from this single source of truth,
ensuring consistency and preventing drift across the architecture.



### 8.2. Conversation as the Atomic Unit

Every interaction—identity, certificate, addressing, path, QoS, and
telemetry—is treated as a single, correlated conversation rather than
isolated events.



### 8.3. Identity as the Root Namespace

Identity becomes the root namespace for all resources, ensuring that
every IP address, certificate, subnet, policy, and telemetry event is
derived from or bound to identity.



### 8.4. Deterministic Addressing

Addressing becomes deterministic and policy-driven, replacing ad-hoc
assignment with identity-derived logic that enables accurate
correlation and automated governance.



### 8.5. Certificate-Anchored Overlay

Certificates and mutual TLS anchor tunnels, services, and trust
relationships across the enterprise.



### 8.6. Telemetry as Control

Telemetry becomes an active control input for routing, security, and
compliance decisions rather than a passive reporting mechanism.



### 8.7. Embedded Governance & Automation

Governance is executed through orchestrated workflows that enforce
policy consistently and reduce operational burden.



### 8.8. Public Service First

Citizen experience, accessibility, and privacy remain top-level
design constraints.




---

## 9. Jinja2 Normalization Pipeline

All UIAO configuration data flows through a normalization pipeline that ensures consistency between YAML data sources and Jinja2 templates.

<img src="assets/images/plantuml/diagram_6.png" alt="diagram_6" />

---

## 10. Executive Dashboard Status

The following diagram provides a real-time view of deployment readiness across all UIAO components.

<img src="assets/images/plantuml/diagram_7.png" alt="diagram_7" />

---

*Generated from UIAO data layer — Unified Architecture v1.0*