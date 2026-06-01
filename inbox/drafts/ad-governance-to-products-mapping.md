# Mapping — AD-Era Governance Functions → Actual Modern Products (OrgPath-Bound)

> **Date:** 2026-06-01
> **Status:** draft — spec for fleshing out the Governance narrative's infrastructure surface
> **Origin:** Mike's direction to "flush out AD DNS and DHCP with InfoBlox, and flush
> out the additional missing AD Governance with actual products."
> **Decisions locked this pass:**
> 1. **InfoBlox = permanent product pillar** for DNS + DHCP + IPAM in hybrid GCC-Moderate
>    (Azure has no scope-based DHCP service and weak authoritative hybrid IPAM). NOT a
>    retire-me transitional supplement. This reframes [`Book_14`](../../docs/customer-documents/orgpath-narrative/Book_14.qmd)
>    (currently "exit criteria — when Azure native takes full ownership").
> 2. **Complete product mapping first** (this doc), then deepen into Book content.
> **Invariant (non-negotiable through-line):** every product below must carry **OrgPath in
> a native field** — InfoBlox Extensible Attributes, certificate subject/SAN or CA metadata,
> Entra AU/dynamic-group scoping, etc. No product earns a place in the narrative unless its
> governance derives from the OrgPath SSOT. (Reinforces the five keystone primitives / six
> cross-stream invariants of the AD→EntraID modernization track.)

## 1. The gap, stated precisely

The OrgPath/Governance narrative covers the **Microsoft-native projections** of OrgPath
well — Intune (Book_05), Defender (Book_06), Purview (Book_07), Azure Policy / Guest Config
(Book_09), SecOps (Book_11). It under-serves the **AD-era infrastructure substrate**: the
functions are often *discussed* but the *actual replacement product* is rarely named, and
several functions (DHCP-as-permanent, RADIUS/NPS, NTP, PAM, identity-lifecycle governance)
are barely present.

Empirical coverage scan of `docs/customer-documents/orgpath-narrative/*.qmd` (2026-06-01):
PKI discussed in 29 files but Keyfactor / Venafi / Intune Cloud PKI named in **0**;
RADIUS in 5 files but NPS in **0**; SailPoint in **0** (despite canon carve-out ADR-059);
CyberArk, NTP/time-service in **0**.

## 2. The mapping

| # | AD-era function | Lead modern product | Alternates | OrgPath binding field | Permanent / Transitional | Proposed narrative home |
|---|---|---|---|---|---|---|
| 1 | **DNS** (AD-integrated) | Azure DNS / Private DNS + Private Resolver | **InfoBlox NIOS/BloxOne** (hybrid authoritative) | DNS zone tags; InfoBlox Extensible Attributes | Azure native = permanent; InfoBlox = permanent where hybrid | InfoBlox DDI Book + Book_12 DNS |
| 2 | **DHCP** | **InfoBlox** (NIOS/BloxOne) | Azure has *no* scope-based DHCP — none native | EA on DHCP ranges / fixed addresses | **Permanent** | InfoBlox DDI Book |
| 3 | **IPAM** | **InfoBlox IPAM** | Azure Network Manager IPAM (immature for hybrid) | EA on networks/containers | **Permanent** | InfoBlox DDI Book |
| 4 | **Group Policy (GPO)** | **Intune** config/compliance | **Azure Policy Guest Config / DSC** | Dynamic group + AU scoping from OrgPath | Permanent | Covered (Book_05, Book_09) |
| 5 | **PKI / ADCS** | **Intune Cloud PKI** (device certs) | **Keyfactor**, **Venafi**, AKV-backed issuance | Cert subject/SAN (OU→OrgPath); Keyfactor/Venafi metadata | Permanent | Extend Book_12 Certificate Services |
| 6 | **RADIUS / 802.1X / NPS** | **Cloud RADIUS** (SecureW2 / Cloud RADIUS) | Entra certificate-based auth; Intune-issued certs | Cert / group attribute → access policy | Permanent | New "network access" chapter |
| 7 | **NTP / authoritative time** | Azure host time / chrony hierarchy | — | Time-source governance by tier | Permanent | Book_12 (small addition) |
| 8 | **Privileged access / admin tiering** | **Entra PIM** | **CyberArk** (vaulting, session isolation) | PIM-eligible AU scoping from OrgPath | Permanent | Book_11 SecOps extension / new |
| 9 | **Identity lifecycle governance** | **Entra ID Governance** (access packages, lifecycle workflows) | **SailPoint NERM** (non-employee / identity warehouse — canon carve-out **ADR-059**) | Access-package scoping by OrgPath; NERM identity → OrgPath map | Permanent | New "Identity Governance" Book (ties to KYC/HRIT) |
| 10 | **Legacy LDAP / Kerberos app auth** | **Entra Domain Services** (managed domain, lift-and-shift) | App modernization to OIDC/SAML | AU / group from OrgPath | Transitional (prefer app modernization) | Extend Book_08 App Identity |
| 11 | **File / Print / SYSVOL** | Azure Files / SharePoint / Azure Files Sync; **Universal Print** | DFS for transition | Share/print permissions by OrgPath group | Mixed | Book_12 |

## 3. Proposed authoring plan (homes & sequencing)

Numbering note: the 16-book program is complete; **append** new books rather than insert
(insertion renumbers and churns the bundle/image-manifest/nav). Candidate new books take
17+, or fold into the Governance-narrative restructure if the three-narrative split
(Governance / Modernization / Compliance) proceeds.

1. **New: InfoBlox DDI as a permanent pillar** — DNS + **DHCP** + IPAM governed by OrgPath
   Extensible Attributes, no exit criteria. Reframe Book_14 as "DDI — native vs third-party"
   companion (drop the retire-me arc, or scope it to the *native-only* subset).
2. **Extend Book_12** — name the PKI products (Intune Cloud PKI / Keyfactor / Venafi);
   add NTP and File/Print/Universal Print.
3. **New: Network Access** — RADIUS / 802.1X / NAC replacement.
4. **New: Identity Governance** — Entra ID Governance + SailPoint NERM; connects to the
   KYC and HRIT streams. (Reflects canon ADR-059 in the narrative for the first time.)
5. **Extend Book_11** — PAM: Entra PIM + CyberArk.

## 3a. Correction after reading Book_14 (2026-06-01)

The §2 gap table rated DDI "thin" from a **file-count** scan. Reading
[`Book_14_CPT_02`](../../docs/customer-documents/orgpath-narrative/Book_14_CPT_02.qmd)
shows the InfoBlox integration *mechanics* are already well-covered: NIOS + BloxOne
deployment models, the four Extensible Attribute definitions (OrgPath / OrgNodeId /
OrgTier / MigrationPhase), inheritance, and DHCP **scope** objects carrying OrgPath.
A standalone new InfoBlox book would largely duplicate Book_14.

**Revised InfoBlox plan:** *reframe and extend Book_14* into the permanent DDI pillar
— drop the "exit criteria → retire" arc, and add the genuinely-missing material:
InfoBlox as the **permanent DHCP authority** (Azure has no scope service) and as the
**permanent IPAM authority**. Do NOT author a duplicative Book_17.

**Where new-book effort actually belongs** (no existing overlap): Identity Governance
/ **SailPoint NERM** (also closes the ADR-059 canon-vs-narrative gap), **PKI with named
products**, then RADIUS/NPS, PAM/CyberArk, NTP.

## 4. Open decisions for Mike

- **Book_14 disposition** — reframe to native-vs-third-party, or leave it and put the
  permanent-InfoBlox story in a *new* book that supersedes its framing?
- **New books vs Governance-narrative restructure** — append as Book_17+ now, or hold until
  the Governance / Modernization / Compliance split is decided (these infra surfaces are
  squarely Governance)?
- **Depth bar** — full narrative books (per the completed-program recipe: subagent-draft per
  chapter from a CPT_02 exemplar + deterministic fact-check + white fig-alt diagrams), or a
  lighter single "AD Governance → Products" reference doc first?
