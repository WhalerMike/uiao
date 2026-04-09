---
title: "UIAO Vendor Stack Analysis"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  docx: default
  pdf: default
  html: default
  gfm: default
---

# UIAO Vendor Technology Stack and Compliance Registry

**Classification:** CUI/FOUO  
**Version:** 1.0  
**Generated:** Auto-compiled from `data/vendor-stack.yml`  

---

## 1. Purpose

This document provides a comprehensive registry of the core technology vendors that comprise the UIAO architecture. It serves three critical functions within the Documentation-as-Code pipeline: it tracks each vendor's FedRAMP authorization status, maps vendor capabilities to NIST 800-53 Rev 5 controls, and monitors compliance with active CISA directives including Binding Operational Directives and Emergency Directives.

Unlike traditional vendor documentation maintained in static Word files or spreadsheets, this registry is machine-generated from structured YAML data stored in the repository. When a vendor releases a critical patch, updates its FedRAMP certification, or when CISA issues a new directive, a single update to `data/vendor-stack.yml` automatically regenerates this document, the FedRAMP Crosswalk, and all downstream compliance artifacts.

---

## 2. How This Document Works

The vendor stack document is produced through the UIAO Document Compiler pipeline, which operates as follows:

1. **Data Layer:** The structured vendor data resides in `data/vendor-stack.yml`. Each vendor entry includes its product name, UIAO pillar mapping, FedRAMP certification class, required software versions, applicable NIST controls, KSI category mapping, and any active CISA directive compliance notes.

2. **Template Layer:** This Jinja2 template (`templates/vendor_stack_v1.0.md.j2`) defines the narrative structure and formatting. It uses Jinja2 loops and conditionals to iterate over the vendor entries and render them into readable Markdown.

3. **Generation Engine:** The `scripts/generate_docs.py` Python script loads the canon YAML and all `data/*.yml` files, merges them into a unified context dictionary, and passes that context to each Jinja2 template. The template engine replaces variable placeholders with actual data values.

4. **CI/CD Pipeline:** On every push to the `main` branch, a GitHub Actions workflow (`.github/workflows/docs.yml`) triggers the generation script. The output is written to both `docs/` and `site/` directories, then committed back to the repository automatically.

5. **Website Delivery:** The GitHub Pages site at `https://whalermike.github.io/uiao-core/` reads the generated Markdown from the `site/` directory and renders it through the USWDS-styled Document Compiler interface, where it can be viewed inline or downloaded in Markdown, Word, PDF, or HTML formats.

---

## 3. Core Vendor Registry

The UIAO architecture integrates five primary technology vendors, each mapped to a specific architectural pillar. Under FedRAMP 20x (2026 Consolidated Rules), all vendors are classified using the new Class-based system, where Class C corresponds to the legacy Moderate baseline.

| Provider | Product | UIAO Pillar | FedRAMP Class | Status |
| :--- | :--- | :--- | :--- | :--- |
| Infoblox | BloxOne Threat Defense | Addressing (A) | Class C | Authorized |
| Cisco | Catalyst SD-WAN | Overlay (O) | Class C | Authorized |
| Microsoft | Entra ID + Informed Network Routing (INR) | Identity (U) | Class C | Authorized |
| Microsoft | Intune Endpoint Management | Identity (U) - Device Compliance | Class C | Authorized |
| Microsoft | Defender for Endpoint (MDE) | Overlay (O) - Endpoint Detection | Class C | Authorized |
| Microsoft | Sentinel SIEM/SOAR | Governance (G) - Security Operations | Class C | Authorized |
| Palo Alto Networks | Next-Generation Firewall (NGFW) | Overlay (O) - Security Inspection | Class C | Authorized |
| CyberArk | Privileged Access Management | Identity (U) - Privileged Access | Class C | Authorized |
| ServiceNow | IT Service Management (ITSM) + GRC | Governance (G) | Class C | Authorized |
| Splunk | Splunk Enterprise (GovCloud) | Governance (G) - Log Analytics | Class C | Authorized |



### 3.1. Infoblox — BloxOne Threat Defense

**UIAO Pillar:** Addressing (A)  
**Role:** Deterministic IPAM and DNS Security  
**FedRAMP Certification:** Class C (FR1908234567)  
**Authorization Status:** Authorized  
**Required Version:** NIOS 9.0.8 / BloxOne 2026.1  

**NIST 800-53 Controls:**

- CM-8: System Component Inventory

- SC-20: Secure Name/Address Resolution


**KSI Category:** `KSI-PIY`  
**Evidence Method:** BloxOne DDI API - Identity-to-IP Binding Logs



**Documentation:** [Infoblox Technical Docs](https://docs.infoblox.com/space/BloxOneThreatDefense)



### 3.2. Cisco — Catalyst SD-WAN

**UIAO Pillar:** Overlay (O)  
**Role:** Encrypted mTLS Service Chain and Fabric Transport  
**FedRAMP Certification:** Class C (FR2104567890)  
**Authorization Status:** Authorized  
**Minimum IOS-XE:** 17.12.1a  

**NIST 800-53 Controls:**

- AC-4: Information Flow Enforcement

- SC-8: Transmission Confidentiality

- SC-23: Session Authenticity


**KSI Category:** `KSI-SVC`  
**Evidence Method:** Catalyst SD-WAN mTLS Configuration and IPFIX Flow Logs


> **CISA Directive Compliance:** ED 26-03 — CVE-2026-20127  
> **Status:** Patched (2026-02-28)



**Hardening Guide:** [Vendor Hardening Documentation](https://sec.cloudapps.cisco.com/security/center/resources/Cisco-Catalyst-SD-WAN-HardeningGuide)  

**Documentation:** [Cisco Technical Docs](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/routing/v17-9/routing-book.html)



### 3.3. Microsoft — Entra ID + Informed Network Routing (INR)

**UIAO Pillar:** Identity (U)  
**Role:** Identity Provider and Network Telemetry Attribution  
**FedRAMP Certification:** Class C (FR1612345678)  
**Authorization Status:** Authorized  

**NIST 800-53 Controls:**

- IA-2: Identification and Authentication

- IA-5: Authenticator Management

- CA-7: Continuous Monitoring


**KSI Category:** `KSI-IAM`  
**Evidence Method:** Entra ID Conditional Access Logs and INR Telemetry Feed



**Supported Authentication Methods:**

- Phishing-Resistant MFA (FIDO2)

- PIV/CAC Smart Card

- Certificate-Based Authentication (CBA)


**Documentation:** [Microsoft Technical Docs](https://learn.microsoft.com/en-us/entra/identity/)



### 3.4. Microsoft — Intune Endpoint Management

**UIAO Pillar:** Identity (U) - Device Compliance  
**Role:** Endpoint Management, Device Compliance Enforcement, and Configuration Baseline Deployment  
**FedRAMP Certification:** Class C (FR1612345678)  
**Authorization Status:** Authorized  

**NIST 800-53 Controls:**

- CM-2: Baseline Configuration

- CM-6: Configuration Settings

- CM-8: System Component Inventory

- IA-3: Device Identification and Authentication

- SC-7: Boundary Protection (Device Compliance Gates)

- SI-2: Flaw Remediation


**KSI Category:** `KSI-IAM`  
**Evidence Method:** Intune Compliance Policy Audit Logs and Device Configuration Profiles



**Documentation:** [Microsoft Technical Docs](https://learn.microsoft.com/en-us/mem/intune/)



### 3.5. Microsoft — Defender for Endpoint (MDE)

**UIAO Pillar:** Overlay (O) - Endpoint Detection  
**Role:** Endpoint Detection and Response, Threat Intelligence, and Automated Investigation  
**FedRAMP Certification:** Class C (FR1612345678)  
**Authorization Status:** Authorized  

**NIST 800-53 Controls:**

- SI-3: Malicious Code Protection

- SI-4: System Monitoring

- IR-4: Incident Handling

- IR-5: Incident Monitoring

- RA-5: Vulnerability Monitoring and Scanning

- SC-7: Boundary Protection (Host-Based)


**KSI Category:** `KSI-SVC`  
**Evidence Method:** MDE Advanced Hunting Logs and Automated Investigation Audit Trail



**Documentation:** [Microsoft Technical Docs](https://learn.microsoft.com/en-us/defender-endpoint/)



### 3.6. Microsoft — Sentinel SIEM/SOAR

**UIAO Pillar:** Governance (G) - Security Operations  
**Role:** Cloud-Native SIEM, Security Orchestration, Automated Response, and Continuous Monitoring  
**FedRAMP Certification:** Class C (FR1612345678)  
**Authorization Status:** Authorized  

**NIST 800-53 Controls:**

- AU-6: Audit Record Review, Analysis, and Reporting

- AU-12: Audit Record Generation

- SI-4: System Monitoring

- IR-4: Incident Handling

- IR-5: Incident Monitoring

- IR-6: Incident Reporting

- CA-7: Continuous Monitoring


**KSI Category:** `KSI-GOV`  
**Evidence Method:** Sentinel Analytics Rules, Incident Logs, and Playbook Execution Audit Trail



**Documentation:** [Microsoft Technical Docs](https://learn.microsoft.com/en-us/azure/sentinel/)



### 3.7. Palo Alto Networks — Next-Generation Firewall (NGFW)

**UIAO Pillar:** Overlay (O) - Security Inspection  
**Role:** Deep Packet Inspection within SD-WAN Service Chain  
**FedRAMP Certification:** Class C (FR1905678901)  
**Authorization Status:** Authorized  

**NIST 800-53 Controls:**

- SC-7: Boundary Protection

- SI-4: System Monitoring


**KSI Category:** `KSI-SVC`  
**Evidence Method:** NGFW Threat Prevention Logs via Panorama API





### 3.8. CyberArk — Privileged Access Management

**UIAO Pillar:** Identity (U) - Privileged Access  
**Role:** Privileged Identity Lifecycle and Session Recording  
**FedRAMP Certification:** Class C  
**Authorization Status:** Authorized  

**NIST 800-53 Controls:**

- AC-6: Least Privilege

- AU-10: Non-Repudiation


**KSI Category:** `KSI-IAM`  
**Evidence Method:** CyberArk Session Audit Logs





### 3.9. ServiceNow — IT Service Management (ITSM) + GRC

**UIAO Pillar:** Governance (G)  
**Role:** IT Service Management, Incident Response, and Continuous Authorization Support  
**FedRAMP Certification:** Class C (FR1710155498)  
**Authorization Status:** Authorized  

**NIST 800-53 Controls:**

- IR-4: Incident Handling

- IR-5: Incident Monitoring

- IR-6: Incident Reporting

- SI-4: System Monitoring

- CA-7: Continuous Monitoring

- SA-9: External System Services


**KSI Category:** `KSI-GOV`  
**Evidence Method:** ServiceNow CMDB + Incident/Change Audit Trail


> **CISA Directive Compliance:**  —   
> **Status:**  ()



**Documentation:** [ServiceNow Technical Docs](https://docs.servicenow.com/bundle/xanadu-it-service-management/page/product/incident-management/concept/c_IncidentManagement.html)



### 3.10. Splunk — Splunk Enterprise (GovCloud)

**UIAO Pillar:** Governance (G) - Log Analytics  
**Role:** Operational Log Aggregation, Search Analytics, and Compliance Reporting  
**FedRAMP Certification:** Class C (FR2009876543)  
**Authorization Status:** Authorized  

**NIST 800-53 Controls:**

- AU-2: Audit Events

- AU-3: Content of Audit Records

- AU-6: Audit Record Review, Analysis, and Reporting

- AU-7: Audit Record Reduction and Report Generation

- AU-12: Audit Record Generation

- SI-4: System Monitoring


**KSI Category:** `KSI-GOV`  
**Evidence Method:** Splunk Search Processing Language (SPL) Queries and Scheduled Report Audit Logs


> **CISA Directive Compliance:**  —   
> **Status:**  ()



**Documentation:** [Splunk Technical Docs](https://docs.splunk.com/Documentation/SplunkCloud)




---

## 4. External Security Baselines

The UIAO architecture integrates with CISA's Secure Cloud Business Applications (SCuBA) project to provide automated compliance validation and continuous reporting as required by BOD 25-01.


### ScubaGear

- **Description:** CISA Secure Cloud Business Applications - Microsoft 365
- **Repository:** [ScubaGear](https://github.com/cisagov/ScubaGear)
- **Current Version:** TBD - auto-synced via scripts/sync-scuba.py
- **Mandate:** BOD 25-01
- **Reporting:** Continuous to CISA


### ScubaGoggles

- **Description:** CISA Secure Cloud Business Applications - Google Workspace
- **Repository:** [ScubaGoggles](https://github.com/cisagov/ScubaGoggles)
- **Current Version:** TBD - auto-synced via scripts/sync-scuba.py
- **Mandate:** BOD 25-01




---

## 5. Active CISA Directives

The following Binding Operational Directives (BODs) and Emergency Directives (EDs) are actively tracked in this repository. Compliance status is updated in `data/vendor-stack.yml` and reflected automatically in all generated documents.

| Directive | Name | Status | Affected Vendor |
| :--- | :--- | :--- | :--- |
| BOD 25-01 | Implementing Secure Practices for Cloud Services | Active | All Federal |
| ED 26-03 | Mitigate Vulnerabilities in Cisco SD-WAN Systems | Remediated | Cisco |



### BOD 25-01: Implementing Secure Practices for Cloud Services

**Status:** Active  
**Required Tools:** ScubaGear, ScubaGoggles  
**Reporting Frequency:** Continuous  



### ED 26-03: Mitigate Vulnerabilities in Cisco SD-WAN Systems

**Status:** Remediated  
**Patch Deadline:** 2026-03-15  
**UIAO Response:** Patched 2026-02-28 - Logged in compliance_notes  




---

## 6. Maintaining This Document

This document is automatically regenerated whenever changes are pushed to the `main` branch. To update vendor information:

1. Edit `data/vendor-stack.yml` with the new vendor version, directive status, or certification update.
2. Commit and push to `main`.
3. The GitHub Actions workflow will regenerate all documents, including this one.
4. The updated document will appear on the UIAO-Core website within minutes.

This approach ensures that the vendor compliance registry is never stale, always version-controlled, and permanently auditable through Git history.