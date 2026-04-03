# 11 Glossaryanddefinitions
UIAO Modernization Program
April 3, 2026

- [<span class="toc-section-number">1</span> UIAO Glossary and
  Definitions](#uiao-glossary-and-definitions)
  - [<span class="toc-section-number">1.1</span> 1. Title
    Page](#1-title-page)
  - [<span class="toc-section-number">1.2</span> 2. Purpose](#2-purpose)
  - [<span class="toc-section-number">1.3</span> 3. Scope](#3-scope)
    - [<span class="toc-section-number">1.3.1</span>
      Included](#included)
    - [<span class="toc-section-number">1.3.2</span>
      Excluded](#excluded)
  - [<span class="toc-section-number">1.4</span> 4. Control Plane
    Alignment](#4-control-plane-alignment)
  - [<span class="toc-section-number">1.5</span> 5. Core
    Concepts](#5-core-concepts)
    - [<span class="toc-section-number">1.5.1</span> Conversation as the
      Atomic Unit](#conversation-as-the-atomic-unit)
    - [<span class="toc-section-number">1.5.2</span> Identity as the
      Root Namespace](#identity-as-the-root-namespace)
    - [<span class="toc-section-number">1.5.3</span> Deterministic
      Addressing](#deterministic-addressing)
    - [<span class="toc-section-number">1.5.4</span>
      Certificate-Anchored Overlay](#certificate-anchored-overlay)
    - [<span class="toc-section-number">1.5.5</span> Telemetry as
      Control](#telemetry-as-control)
    - [<span class="toc-section-number">1.5.6</span> Embedded Governance
      and Automation](#embedded-governance-and-automation)
    - [<span class="toc-section-number">1.5.7</span> Public Service
      First](#public-service-first)
  - [<span class="toc-section-number">1.6</span> 6. Glossary (Canonical
    Definitions)](#6-glossary-canonical-definitions)
    - [<span class="toc-section-number">1.6.1</span> A](#a)
    - [<span class="toc-section-number">1.6.2</span> B](#b)
    - [<span class="toc-section-number">1.6.3</span> C](#c)
    - [<span class="toc-section-number">1.6.4</span> D](#d)
    - [<span class="toc-section-number">1.6.5</span> E](#e)
    - [<span class="toc-section-number">1.6.6</span> F](#f)
    - [<span class="toc-section-number">1.6.7</span> G](#g)
    - [<span class="toc-section-number">1.6.8</span> H](#h)
    - [<span class="toc-section-number">1.6.9</span> I](#i)
    - [<span class="toc-section-number">1.6.10</span> K](#k)
    - [<span class="toc-section-number">1.6.11</span> L](#l)
    - [<span class="toc-section-number">1.6.12</span> M](#m)
    - [<span class="toc-section-number">1.6.13</span> N](#n)
    - [<span class="toc-section-number">1.6.14</span> O](#o)
    - [<span class="toc-section-number">1.6.15</span> P](#p)
    - [<span class="toc-section-number">1.6.16</span> R](#r)
    - [<span class="toc-section-number">1.6.17</span> S](#s)
    - [<span class="toc-section-number">1.6.18</span> T](#t)
    - [<span class="toc-section-number">1.6.19</span> Z](#z)
  - [<span class="toc-section-number">1.7</span> 7. Dependencies and
    Sequencing](#7-dependencies-and-sequencing)
    - [<span class="toc-section-number">1.7.1</span> Upstream
      Dependencies](#upstream-dependencies)
    - [<span class="toc-section-number">1.7.2</span> Downstream
      Dependencies](#downstream-dependencies)
  - [<span class="toc-section-number">1.8</span> 8. Governance and Drift
    Controls](#8-governance-and-drift-controls)
    - [<span class="toc-section-number">1.8.1</span> Source of
      Authority](#source-of-authority)
    - [<span class="toc-section-number">1.8.2</span> Drift
      Detection](#drift-detection)
  - [<span class="toc-section-number">1.9</span> 9.
    Appendices](#9-appendices)
    - [<span class="toc-section-number">1.9.1</span> Appendix A:
      Acronyms](#appendix-a-acronyms)
    - [<span class="toc-section-number">1.9.2</span> Appendix B:
      Extended Definitions](#appendix-b-extended-definitions)
    - [<span class="toc-section-number">1.9.3</span> Appendix C:
      Evidence Sources](#appendix-c-evidence-sources)
  - [<span class="toc-section-number">1.10</span> 10. Revision
    History](#10-revision-history)

# UIAO Glossary and Definitions

## 1. Title Page

| Field | Value |
|----|----|
| **Version** | 1.0 |
| **Date** | March 2026 |
| **Classification** | CUI/FOUO |
| **Source Planes** | Identity, Network, Addressing, Telemetry, Security, Management |
| **Document Type** | Canon Glossary (02_Appendices) |

------------------------------------------------------------------------

## 2. Purpose

This document provides the authoritative glossary for the Unified
Identity-Addressing-Overlay (UIAO) canon. It defines all core terms,
architectural concepts, control-plane vocabulary, compliance
terminology, and modernization language used throughout the 12-document
corpus. These definitions are frozen and must not be altered without a
formal canon revision.

------------------------------------------------------------------------

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

------------------------------------------------------------------------

## 4. Control Plane Alignment

This glossary spans all six UIAO control planes:

| Plane                   | Vocabulary Domain                              |
|-------------------------|------------------------------------------------|
| Identity                | Identity, assurance, lifecycle, governance     |
| Network                 | Routing, segmentation, overlay, DIA, INR       |
| Addressing              | IPAM, DNS/DHCP, deterministic addressing       |
| Telemetry and Location  | Telemetry, location inference, KSI             |
| Security and Compliance | Zero Trust, TIC 3.0, FedRAMP                   |
| Management              | CMDB, drift detection, configuration baselines |

------------------------------------------------------------------------

## 5. Core Concepts

> **Single Source of Truth (SSOT):** The README.md is the authoritative
> origin for all canonical definitions.

The glossary includes the frozen definitions of the Eight Core Concepts:

### Conversation as the Atomic Unit

A correlated interaction consisting of identity, addressing,
certificates, path, QoS, and telemetry.

### Identity as the Root Namespace

Identity governs addressing, certificates, segmentation, and policy.

### Deterministic Addressing

IP addresses derived from identity attributes and policy, not
spreadsheets or manual assignment.

### Certificate-Anchored Overlay

mTLS-anchored tunnels and service chains that enforce identity-aware
routing.

### Telemetry as Control

Telemetry is a real-time control input for routing, access,
segmentation, and compliance.

### Embedded Governance and Automation

Governance executed through automated workflows, not manual tickets.

### Public Service First

Citizen experience, accessibility, and privacy are top-level design
constraints.

------------------------------------------------------------------------

## 6. Glossary (Canonical Definitions)

Below is the authoritative glossary for the UIAO canon.

### A

**AC-4 (Access Control)** NIST control governing segmentation and
identity-aware routing.

**Addressing Control Plane** The plane responsible for deterministic
IPAM, DNS/DHCP, and identity-derived addressing.

**Asset Inventory (CM-8)** Authoritative list of hardware, software, and
virtual assets maintained through CMDB and IPAM.

### B

**Baseline Configuration (CM-2)** Approved configuration settings
enforced through Intune and validated through CMDB.

**Branch Modernization** TIC 3.0 Branch Use Case implementation using
SD-WAN and identity-aware segmentation.

### C

**CA-7 (Continuous Monitoring)** NIST control requiring real-time
telemetry and automated evidence generation.

**Certificate-Anchored Overlay** mTLS-anchored tunnels that enforce
identity-aware routing and segmentation.

**CMDB (Configuration Management Database)** Authoritative system of
record for assets, configurations, and relationships.

**Conditional Access** Identity-driven access control based on device
posture, location, and assurance.

**Conversation** The atomic unit of UIAO runtime behavior.

**Crosswalk** A mapping between UIAO concepts and external compliance
frameworks.

### D

**Deterministic Addressing** Identity-derived IP addressing that
eliminates manual assignment and spreadsheet drift.

**DIA (Direct Internet Access)** Cloud-first routing model that bypasses
legacy TIC 2.0 bottlenecks.

### E

**E911** Emergency location services requiring accurate, real-time
location inference.

**Entra ID** Authoritative identity provider for UIAO.

### F

**FedRAMP 20x** Telemetry-based validation framework for federal cloud
services.

**Frozen State** Legacy architectural constraints that prevent
modernization.

### G

**Governance** Automated enforcement of identity, configuration, and
compliance policies.

### H

**HLD (High-Level Design)** Architecture-level design documents defining
system behavior and boundaries.

### I

**Identity Assurance** Confidence level in the authenticity of an
identity, governed by NIST 800-63.

**Identity Control Plane** The plane responsible for identity lifecycle,
authentication, and assurance.

**INR (Intelligent Network Routing)** Location-aware routing based on
telemetry and identity.

**IPAM (IP Address Management)** Authoritative addressing system for
deterministic IP allocation.

### K

**KSI (Key Security Indicator)** Telemetry-based evidence required for
FedRAMP 20x validation.

### L

**LLD (Low-Level Design)** Implementation-level design documents
defining configuration details.

**Location Inference** Determining user or device location based on
IPAM, SD-WAN, and telemetry.

### M

**Management Plane** The plane responsible for CMDB, drift detection,
device compliance, and governance.

**mTLS (Mutual TLS)** Certificate-based authentication used for overlay
tunnels.

### N

**NIST SP 800-53 Rev 5** Primary federal security control framework.

**NIST SP 800-63** Identity assurance and authentication framework.

### O

**Overlay** Identity-anchored, certificate-secured virtual network
layer.

### P

**PIM (Privileged Identity Management)** Governance system for
privileged access.

**Public Service First** Design principle prioritizing citizen
experience and accessibility.

### R

**Runtime Model** UIAO’s operational model based on conversation-level
evaluation.

### S

**SCuBA** CISA’s M365 hardening and identity governance framework.

**SD-WAN** Software-defined WAN used for cloud-first routing and
segmentation.

**Segmentation** Identity-aware network separation enforced through
SD-WAN.

**ServiceNow** Authoritative system for CMDB, change control, and drift
detection.

### T

**Telemetry** Real-time signals used for routing, access, segmentation,
and compliance.

**TIC 3.0** Modern federal perimeter and cloud security framework.

### Z

**Zero Trust** Security model requiring continuous verification of
identity, device, and context.

------------------------------------------------------------------------

## 7. Dependencies and Sequencing

### Upstream Dependencies

- Identity modernization
- IPAM modernization
- SD-WAN overlay deployment

### Downstream Dependencies

- Crosswalk generation
- Leadership reporting
- Governance automation

------------------------------------------------------------------------

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

------------------------------------------------------------------------

## 9. Appendices

### Appendix A: Acronyms

*All acronyms are defined inline within Section 6.*

### Appendix B: Extended Definitions

*See individual canonical documents for extended context on each term.*

### Appendix C: Evidence Sources

*See `data/parameters.yml` and control-library entries for evidence
source catalogs.*

------------------------------------------------------------------------

## 10. Revision History

| Version | Date    | Author            | Summary                   |
|---------|---------|-------------------|---------------------------|
| 1.0     | 2026-03 | UIAO Canon Engine | Initial canonical release |
