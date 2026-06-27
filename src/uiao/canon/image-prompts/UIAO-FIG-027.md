---
id: UIAO-FIG-027
slug: git-server-interfaces
title: "UIAO-GIT01 — Network Interfaces"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#5A5A5A", "#FFFFFF"]
---

## Description
House-style replacement for the git-server interfaces ASCII diagram: the platform git server (UIAO-GIT01, WS2025) with every inbound/outbound flow and its caller — Operators (443 HTTPS via IIS to Gitea, 2222 SSH, 5986 WinRM), Forest (636 LDAPS), Tenant (Graph), Arc plane, Backup (blob), ConMon (Log Analytics), GitHub (api.github pull-mirror) — plus storage (D:\GitRepos, D:\Gitea) and OrgPath/AU governance tags.

## Prompt
A 16:9 blueprint schematic (ADR-093), white background. A central ice server box listing each interface in monospace; left-side caller labels (Operators, Forest, Tenant, Arc plane, Backup, ConMon, GitHub) with teal arrows into the box. A navy storage footer box and a teal-tint governance footer box (OrgPath + AU). Literal SVG text; no logos, no photos.
