---
title: "UIAO Leadership Briefing"
subtitle: "Modernization Status & Strategic Direction"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  pptx:
    slide-level: 2
  pdf: default
  html: default
---

# Executive Briefing: The Modernization Atlas

**The Problem:** Current agency onboarding/offboarding (JML) is manual, error-prone, and takes >24 hours to revoke access. Asset inventory relies on manual data entry with no automated validation against the network source of truth.

**The Solution:** An automated orchestration layer that synchronizes the Identity, Management, and Network planes using existing agency tools (Entra ID, ServiceNow, InfoBlox, CyberArk).

## Key Outcomes

1. **<120s Revocation:** Instant network isolation for "Leaver" events via automated Palo Alto/SD-WAN quarantine
2. **100% CMDB Accuracy:** Automated synchronization between InfoBlox (the wire) and ServiceNow (the business)
3. **Continuous Monitoring:** Real-time visibility into device compliance drift via Sentinel KQL intelligence
4. **Zero-Day Productivity:** New hires provisioned and productive on Day 1 through HR-driven automation
5. **Privileged Access Visibility:** CyberArk vault accounts mapped to CMDB assets with full audit trail

## 12-Month Roadmap

| Phase | Timeline | Deliverable |
| :--- | :--- | :--- |
| **Phase 1: Identity** | Q1 2026 | HR-driven Entra ID lifecycle; Phishing-resistant MFA rollout |
| **Phase 2: Governance** | Q2 2026 | InfoBlox-ServiceNow CMDB sync; CyberArk vault integration |
| **Phase 3: Visibility** | Q3 2026 | Sentinel KQL alert fabric; Compliance dashboards for ConMon |
| **Phase 4: Enforcement** | Q4 2026 | Palo Alto/SD-WAN automated quarantine; JIT access enforcement |

## Investment Strategy

This leverages existing investments in Entra ID, ServiceNow, and InfoBlox. The orchestration logic runs on GitHub Actions with no additional infrastructure cost. Migration to Entra ID P2 for advanced Identity Protection is the primary licensing consideration.

## Requested Action

Approval to move from the GitHub-hosted sandbox to the **Agency GCC-Moderate** environment for Pilot Phase testing.
