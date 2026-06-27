---
id: UIAO-FIG-030
slug: windows-server-deployment
title: "Windows Server Deployment — IIS → Python"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#5A5A5A", "#FFFFFF"]
---

## Description
House-style replacement for the IIS deployment ASCII diagram: Internet/Intranet → HTTPS :443 → IIS 10 (UIAO-API site, Windows Auth Kerberos/Negotiate, TLS termination with enterprise CA) → HttpPlatformHandler → loopback → Python 3.13 / Uvicorn (uiao.api.app:app, bound 127.0.0.1) → downstream LDAPS :636 to the AD domain controller and HTTPS (MSAL) to Microsoft Entra ID Graph/ARM endpoints.

## Prompt
A 16:9 blueprint schematic (ADR-093), white background, vertical stack: Internet/Intranet → teal HTTPS :443 arrow → ice IIS box (Windows Auth, TLS termination, HttpPlatformHandler) → teal loopback arrow → navy Python/Uvicorn box → two downstream teal arrows (LDAPS :636 to a navy Active Directory box; HTTPS MSAL to an ice Microsoft Entra ID box). Literal SVG text; no logos, no photos.
