# SSA Add-On — Pre-Filled Product Inventory (Vol 0 Book 01 §3)

**SSA edition only. Not published.** This is the section Vol 0 Book 01 always said
would be "removed in the Federal-agnostic edition" — this file is where it went.

It is a real inventory of one agency's deployed tools with verified FedRAMP status.
That is exactly what a generic instrument must NOT carry: the federal edition ships
the empty discovery tables (§4) so a reader fills in their own estate, and a
pre-filled block would answer the questionnaire before they start.

Paste this section back into Book 01 after §2 when rendering the SSA edition.

# Known {{< meta agency.short >}} Inventory — Pre-Filled (SSA edition only) {#known-ssa}

*This section is {{< meta agency.short >}}-specific and is removed in the Federal-agnostic edition.*
Confirmed or stated tools, with verified FedRAMP status (2026-07-08) and
dispositions under §2.

| Product | Category | FedRAMP status (verified) | Disposition | Maps to |
|---|---|---|---|---|
| **SailPoint Identity Security Cloud** | Identity governance (IGA) | **Class C (Moderate)** — AWS GovCloud (CSO FR2001938710A) | ✅ In scope | Identity coordinator; PAM / HRIT / identity books |
| **ServiceNow Government Cloud** | ITSM / CMDB / workflow coordinator | **Class D (High)** (DoD IL-4) | ⚠️ Flag — High covers Moderate; confirm boundary treatment. **CMDB must reconcile to IPAM/DDI (CM-8), not replace it** | Evidence Fabric book (coordination home); Program Mgmt book |
| **Splunk Cloud Platform** | SIEM | **Class C (Moderate)** (2019) *and* Class D (High). **Splunk SOAR = Moderate** | ✅ In scope — use the **Moderate** offering | Evidence Fabric / SIEM book |
| **Riverbed** (Aternity, NPM+, SteelHead) | Network performance / observability / WAN-opt | Riverbed Platform for Gov (Aternity/NPM+) = **Class D (High) only**; **SteelHead = on-prem gear** | ⚠️⚠️ Double flag — cloud DEX is High-only (above Moderate target); SteelHead is gear (NIAP/STIG path) | Transport/telecom books (SI-4/CA-7 telemetry); Network Enforcement Substrate (SteelHead) |
| **Confluence** (Atlassian) | Documentation / knowledge | **Class C (Moderate)** — **only via Atlassian Government Cloud** (Mar 2025). Commercial Confluence is **not** authorized | ⚠️ Flag — confirm you are on **Atlassian Government Cloud**, not commercial | Program Mgmt / governance book; evidence documentation |
| **InfoBlox DDI** | Naming & addressing (DDI/IPAM) | **Class C (Moderate)** (CSO FR2017257053) | ✅ In scope — the authoritative asset-identity join key | Landing Zone book; plane 2 |
| **Microsoft 365 GCC / Entra / Intune / Sentinel / Purview / Defender** | CSP + identity + endpoint + SIEM + data | **GCC Moderate** | ✅ In scope | Landing Zone, identity, patch, SIEM, data books |
| **Cisco Catalyst SD-WAN** | SD-WAN | Cloud-hosted SD-WAN Manager carries a FedRAMP authorization (verify level/CSO on Marketplace); on-prem WAN Edge = gear (NIAP/STIG/FIPS) | ✅ / ↪️ **Chosen** — selected for Microsoft 365 **Informed Network Routing (INR)**; see Network Modernization book Appendix A | Network Mod / Telecom / Network Enforcement · plane 1 |
| **Cisco ThousandEyes for Government** | Network / path observability | **Class C (Moderate)** — ATO 2026-03-05 (CSO FR2523656707), FIPS-validated | ✅ In scope — the Moderate-compliant observability option (contrast Riverbed) | Transport telemetry (SI-4/CA-7) · Evidence Fabric · plane 6 |
| **Palo Alto Prisma** (agency-preferred) | Cloud security / SASE / CNAPP | **Prisma Access (SASE) = Class C (Moderate)** ✅; **Prisma Cloud (CNAPP) = Class D (High)-only** ⚠️ | Prisma Access ✅; Prisma Cloud ⚠️ (High) | SASE → Network Enforcement / Telecom; CNAPP → Cloud-Native Posture |

**Immediate reads from the {{< meta agency.short >}} block:**

- **Observability** has a clean option and a flagged one: **Cisco ThousandEyes
  for Government** is Class C (Moderate) ✅, while **Riverbed** is High-only cloud
  + on-prem gear ⚠️. Prefer ThousandEyes where the Moderate rule binds.
- **SD-WAN** is settled: **Cisco Catalyst SD-WAN**, chosen for Microsoft 365 INR
  (Network Modernization book Appendix A).
- **Palo Alto (Prisma)** is agency-preferred but splits on level: **Prisma
  Access (SASE) is Moderate ✅**; **Prisma Cloud (CNAPP) is High-only ⚠️** — so
  the Cloud-Native Posture book must weigh Prisma Cloud (High) against a
  Moderate-authorized CNAPP (e.g., Microsoft Defender for Cloud in GCC Moderate;
  Wiz and Prisma Cloud are both at High).
- **ServiceNow** (best coordination hub) is High — usable for a Moderate
  boundary, documented as such, CMDB reconciled to IPAM/DDI. **Splunk** and
  **Sentinel** both give you a Moderate SIEM today.
