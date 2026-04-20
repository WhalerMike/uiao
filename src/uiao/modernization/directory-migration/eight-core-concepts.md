---
document_id: DM_001
title: "UIAO Eight Core Concepts"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
---

# UIAO Eight Core Concepts

These concepts are universal — not federal-specific. They form the architectural
foundation for all UIAO governance, including directory migration.

| # | Core Concept | Definition |
|---|---|---|
| 1 | **SSOT** | Every claim has one authoritative origin. All other representations are pointers, not copies. |
| 2 | **Conversation as atomic unit** | Every interaction binds identity, certificates, addressing, path, QoS, and telemetry. |
| 3 | **Identity as root namespace** | Every IP, certificate, subnet, policy, and telemetry event derives from identity. |
| 4 | **Deterministic addressing** | Addressing is identity-derived and policy-driven. |
| 5 | **Certificate-anchored overlay** | mTLS anchors tunnels, services, and trust relationships. |
| 6 | **Telemetry as control** | Telemetry is a real-time control input, not passive reporting. |
| 7 | **Embedded governance** | Governance is executed through orchestrated workflows, not manual tickets. |
| 8 | **User experience first** | The migration is invisible to end users if governance was done right. |

## Alignment to Directory Migration

Each adapter interface in this canon references the Core Concepts it implements:

- **IPAM Adapter** → Concepts #1 (SSOT) and #4 (Deterministic Addressing)
- **PKI Adapter** → Concept #5 (Certificate-anchored overlay)
- **RADIUS Adapter** → Concepts #3 (Identity as root namespace) and #5
- **LDAP Proxy Adapter** → Concept #3 (Identity as root namespace)
- **Sync Engine Adapter** → Concept #1 (SSOT) — retirement means SSOT moves to Entra
- **Device Management Adapter** → Concept #7 (Embedded governance)
- **NTP Adapter** → Concept #5 (Certificate-anchored overlay — Kerberos dependency)
- **DFS Adapter** → Concept #8 (User experience first — UNC paths must not break)
