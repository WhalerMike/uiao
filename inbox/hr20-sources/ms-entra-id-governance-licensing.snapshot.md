# Snapshot: Microsoft Entra ID Governance licensing fundamentals

> **Source:** https://learn.microsoft.com/en-us/entra/id-governance/licensing-fundamentals
> **Page updated_at:** 2026-06-26 (ms.date 2026-03-27) · **Snapshot retrieved:** 2026-07-23
> Point-in-time extraction for durable reference. The live page is authoritative.

## Government cloud availability — THE key sentence

> "The Microsoft Entra ID Governance for Government and Microsoft Entra ID Governance Add-on for Microsoft Entra ID P2 for Government products are **available in the US Government community cloud (GCC), GCC-High, and Department of Defense cloud environments**."

This confirms the Governance SKU (which gates Lifecycle Workflows) exists for GCC. Residual check: per-feature availability in a specific cloud is tracked separately ("Microsoft Entra feature availability" page for Azure Government) — verify API-driven provisioning + Lifecycle Workflows feature rows in the actual tenant.

## License tiers relevant to HR-driven provisioning

- **Entra ID P1** (standalone, or in Microsoft 365 E3 / Business Premium; G3 counts as prerequisite).
- **Entra ID P2** (standalone, or in Microsoft 365 E5/G5).
- **Entra ID Governance** — add-on above P1/P2; six product variants differing only in prerequisites, including **Entra ID Governance for Government** (requires a product with `AAD_PREMIUM` or `AAD_PREMIUM_P2` service plan, e.g. M365 G3/G5) and **Governance Add-on for Entra ID P2 for Government** (requires `AAD_PREMIUM_P2`, e.g. M365 G5).
- **Microsoft Entra Suite** includes all Governance capabilities.

## Feature → license matrix (provisioning + LCW rows)

| Feature | P1 | P2 | Governance |
| --- | --- | --- | --- |
| API-driven provisioning | ✅ | ✅ | ✅ |
| HR-driven provisioning | ✅ | ✅ | ✅ |
| Automated provisioning to on-prem apps | ✅ | ✅ | ✅ |
| **Lifecycle Workflows** | — | — | ✅ |
| LCW + Custom Extensions (Logic Apps) | — | — | ✅ |
| Access reviews (P2-era capabilities) | — | ✅ | ✅ |
| Entitlement management (P2-era capabilities) | — | ✅ | ✅ |
| PIM | — | ✅ | ✅ |

Bottom line for the kit: **API-driven inbound provisioning works at P1; automated joiner/mover/leaver (Lifecycle Workflows) requires the Governance add-on.** No new IGA features will be added to the P2 SKU.

## API-driven provisioning quotas by license (tenant level)

| Customer license | Limits |
| --- | --- |
| Entra ID P1 or P2 | Daily quota **100K user records/24h** (2,000 /bulkUpload calls × max 50 records). Max **2 apps** per flow (2 to on-prem AD, 2 to Entra ID). |
| Governance alongside P1/P2 | Daily quota **300K user records/24h** (6,000 calls × 50). Max **20 apps** per flow. |

A subscription license is required with enough seats for every identity sourced via /bulkUpload and provisioned to either on-premises AD or Entra ID.

## Lifecycle Workflows entitlements (with Governance license)

- Up to **50 workflows**; on-demand and scheduled execution; up to **100 custom task extensions**.
- License count = member users in scope + administrators configuring (see page for worked examples).

## Other notes

- Users don't need individually assigned Governance licenses, but the tenant needs as many licenses as member users in scope of (or configuring) governance features. Guest governance uses MAU billing via an Azure subscription.
- Prerequisite subscription must remain active in the tenant or governance scenarios may stop functioning.
- PIM requires P2 or Governance; on license expiry eligible assignments are removed, time-bound become permanent.
