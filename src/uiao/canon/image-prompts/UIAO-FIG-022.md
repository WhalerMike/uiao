---
id: UIAO-FIG-022
slug: client-server-to-hybrid
title: "Client-Server → UIAO Platform → Hybrid-Cloud"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#5A5A5A", "#FFFFFF"]
---

## Description

House-style replacement for the three-column ASCII diagram: the legacy
Client-Server estate (navy — AD Forest, GPO, AD-Integrated DNS, AD DHCP,
Kerberos SPNs, ADCS, domain-joined PCs) is read (read-only) by the
teal-bordered UIAO Platform Server (WS2025 + IIS + Gitea, Kerberos +
Enterprise PKI, PowerShell + Python + API, Analysis → Plan → Deliver), which
writes the ice Hybrid-Cloud target (Entra ID + Intune + Arc, IPAM + DNS +
DHCP, SASE + Zero Trust + MFA, Conditional Access, Certificate-Based Auth).

## Prompt

A 16:9 blueprint schematic (ADR-093), white background, three column boxes
left to right: a navy "CLIENT-SERVER (the source)" list; a teal-bordered ice
"UIAO PLATFORM SERVER (the transformer)" with an inner navy "Analysis → Plan
→ Deliver" bar; an ice "HYBRID-CLOUD (the target)" list. A teal "read only"
arrow from source to platform and a teal "write" arrow from platform to
target. Literal SVG text; no logos, no photos.
