---
document_id: DM_070
title: "NTP Adapter Interface"
version: "0.1-draft"
status: DRAFT
owner: "Michael Stratton"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
core_concepts: ["#5 Certificate-anchored overlay"]
priority: MEDIUM
risk: "Kerberos clock skew failures post DC decommission"
---

# NTP Adapter Interface

**Priority:** MEDIUM | **Risk:** Kerberos clock skew failures post DC decommission

## Required Capabilities

- Inventory all devices syncing NTP from domain controllers
- Identify authoritative NTP hierarchy in current environment
- Validate external NTP source availability from all network segments
- GPO / Intune policy for w32tm configuration

## Migration Sequence

1. Identify all NTP clients pointing to DCs (`w32tm /query /status`)
2. Deploy Intune policy redirecting NTP to external sources (`time.windows.com`)
3. Validate clock sync across all segments before DC decommission
