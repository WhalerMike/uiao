---
title: "11 Glossaryanddefinitions"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Glossary and Definitions

## 1. Title Page

| Field | Value |
|---|---|
| **Version** | 1.0 |
| **Date** | March 2026 |
| **Classification** | CUI/FOUO |
| **Source Planes** | Identity, Network, Addressing, Telemetry, Security, Management |
| **Document Type** | Canon Glossary (02_Appendices) |

---

## 2. Purpose

This document provides the authoritative glossary for the Unified Identity-Addressing-Overlay (UIAO) canon. It defines all core terms, architectural concepts, control-plane vocabulary, compliance terminology, and modernization language used throughout the 12-document corpus. These definitions are frozen and must not be altered without a formal canon revision.

---

## 3. Scope

### Included

- Canonical definitions of all UIAO terms
- Control-plane terminology
- Compliance and governance vocabulary
- Acronyms and abbreviations
- Cross-plane conceptual language

### Excluded

- Vendor-specific product documentation
- Implementation-specific terminology
- Non-canonical slang or shorthand

---

## 4. Control Plane Alignment

This glossary spans all six UIAO control planes:

| Plane | Vocabulary Domain |
|---|---|
| Identity | Identity, assurance, lifecycle, governance |
| Network | Routing, segmentation, overlay, DIA, INR |
| Addressing | IPAM, DNS/DHCP, deterministic addressing |
| Telemetry and Location | Telemetry, location inference, KSI |
| Security and Compliance | Zero Trust, TIC 3.0, FedRAMP |
| Management | CMDB, drift detection, configuration baselines |

---

## 5. Core Concepts

The glossary includes the frozen definitions of the Eight Core Concepts:

### Conversation as the Atomic Unit

A correlated interaction consisting of identity, addressing, certificates, path, QoS, and telemetry.

### Identity as the Root Namespace

Identity governs addressing, certificates, segmentation, and policy.

### Deterministic Addressing

IP addresses derived from identity attributes and policy, not spreadsheets or manual assignment.

### Certificate-Anchored Overlay

mTLS-anchored tunnels and service chains that enforce identity-aware routing.

### Telemetry as Control

Telemetry is a real-time control input for routing, access, segmentation, and compliance.

### Embedded Governance and Automation

Governance executed through automated workflows, not manual tickets.

### Public Service First

Citizen experience, accessibility, and privacy are top-level design constraints.

---

## 6. Glossary (Canonical Definitions)

Below is the authoritative glossary for the UIAO canon.

### A

**AC-4 (Access Control)**
NIST control governing segmentation and identity-aware routing.

**Addressing Control Plane**
The plane responsible for deterministic IPAM, DNS/DHCP, and identity-derived addressing.

**Asset Inventory (CM-8)**
Authoritative list of hardware, software, and virtual assets maintained through CMDB and IPAM.

### B

**Baseline Configuration (CM-2)**
Approved configuration settings enforced through Intune and validated through CMDB.

**Branch Modernization**
TIC 3.0 Branch Use Case implementation using SD-WAN and identity-aware segmentation.

### C

**CA-7 (Continuous Monitoring)**
NIST control requiring real-time telemetry and automated evidence generation.

**Certificate-Anchored Overlay**
mTLS-anchored tunnels that enforce identity-aware routing and segmentation.

**CMDB (Configuration Management Database)**
Authoritative system of record for assets, configurations, and relationships.

**Conditional Access**
Identity-driven access control based on device posture, location, and assurance.

**Conversation**
The atomic unit of UIAO runtime behavior.

**Crosswalk**
A mapping between UIAO concepts and external compliance frameworks.

### D

**Deterministic Addressing**
Identity-derived IP addressing that eliminates manual assignment and spreadsheet drift.

**DIA (Direct Internet Access)**
Cloud-first routing model that bypasses legacy TIC 2.0 bottlenecks.

### E

**E911**
Emergency location services requiring accurate, real-time location inference.

**Entra ID**
Authoritative identity provider for UIAO.

### F

**FedRAMP 20x**
Telemetry-based validation framework for federal cloud services.

**Frozen State**
Legacy architectural constraints that prevent modernization.

### G

**Governance**
Automated enforcement of identity, configuration, and compliance policies.

### H

**HLD (High-Level Design)**
Architecture-level design documents defining system behavior and boundaries.

### I

**Identity Assurance**
Confidence level in the authenticity of an identity, governed by NIST 800-63.

**Identity Control Plane**
The plane responsible for identity lifecycle, authentication, and assurance.

**INR (Intelligent Network Routing)**
Location-aware routing based on telemetry and identity.

**IPAM (IP Address Management)**
Authoritative addressing system for deterministic IP allocation.

### K

**KSI (Key Security Indicator)**
Telemetry-based evidence required for FedRAMP 20x validation.

### L

**LLD (Low-Level Design)**
Implementation-level design documents defining configuration details.

**Location Inference**
Determining user or device location based on IPAM, SD-WAN, and telemetry.

### M

**Management Plane**
The plane responsible for CMDB, drift detection, device compliance, and governance.

**mTLS (Mutual TLS)**
Certificate-based authentication used for overlay tunnels.

### N

**NIST SP 800-53 Rev 5**
Primary federal security control framework.

**NIST SP 800-63**
Identity assurance and authentication framework.

### O

**Overlay**
Identity-anchored, certificate-secured virtual network layer.

### P

**PIM (Privileged Identity Management)**
Governance system for privileged access.

**Public Service First**
Design principle prioritizing citizen experience and accessibility.

### R

**Runtime Model**
UIAO's operational model based on conversation-level evaluation.

### S

**SCuBA**
CISA's M365 hardening and identity governance framework.

**SD-WAN**
Software-defined WAN used for cloud-first routing and segmentation.

**Segmentation**
Identity-aware network separation enforced through SD-WAN.

**ServiceNow**
Authoritative system for CMDB, change control, and drift detection.

### T

**Telemetry**
Real-time signals used for routing, access, segmentation, and compliance.

**TIC 3.0**
Modern federal perimeter and cloud security framework.

### Z

**Zero Trust**
Security model requiring continuous verification of identity, device, and context.

---

## 7. Dependencies and Sequencing

### Upstream Dependencies

- Identity modernization
- IPAM modernization
- SD-WAN overlay deployment

### Downstream Dependencies

- Crosswalk generation
- Leadership reporting
- Governance automation

---

## 8. Governance and Drift Controls

### Source of Authority

- HR — identity lifecycle
- Network architecture — addressing
- PKI — certificate trust
- System owners — configuration baselines

### Drift Detection

- CMDB reconciliation
- Intune compliance
- SD-WAN overlay validation
- IPAM reconciliation

---

## 9. Appendices

### Appendix A: Acronyms

*All acronyms are defined inline within Section 6.*

### Appendix B: Extended Definitions

*See individual canonical documents for extended context on each term.*

### Appendix C: Evidence Sources

*See `data/parameters.yml` and control-library entries for evidence source catalogs.*

---

## 10. Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-03 | UIAO Canon Engine | Initial canonical release |
