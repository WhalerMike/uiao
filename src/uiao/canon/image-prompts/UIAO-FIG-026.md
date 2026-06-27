---
id: UIAO-FIG-026
slug: hybrid-dns-resolution
title: "Hybrid DNS Resolution"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#5A5A5A", "#FFFFFF"]
---

## Description
House-style replacement for the hybrid-DNS ASCII diagram: on-prem namespace (UIAO-GIT01.corp, fileserver.corp, printer.corp) forwards conditionally to the Azure DNS Private Resolver (inbound/outbound endpoints), which bridges the cloud namespace (privatelink.blob.core.windows.net); the resolver feeds the authoritative Azure Private DNS Zone (uiao.internal), which feeds IPAM (DM_010) as the single source of truth.

## Prompt
A 16:9 blueprint schematic (ADR-093), white background. Left navy on-prem box, center ice "Azure DNS Private Resolver" (inbound/outbound endpoints), right ice cloud-namespace box; a teal conditional-forwarder arrow and a bidirectional cloud arrow. Below center, an ice "Azure Private DNS Zone (uiao.internal, authoritative)" then a navy teal-bordered "IPAM (DM_010) single source of truth". Literal SVG text; no logos, no photos.
