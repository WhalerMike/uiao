# Federal AAN — Governance & Ownership Model (Adoption Artifact)
**Internal CSI Team Working Document — Draft for SSA ratification**

**Date Code:** 2026-07-07 15:05 ET

---

## Purpose and Status

The AAN series deliberately describes **functions, not organizations**
(series doctrine theme D): the books name no owners, because the
architectural facts are true regardless of how any agency's org chart divides
them. Book 16 supplies the governance *templates* — the ISPP, the program
leadership RACI, the SCRM charter. What the series does not (and cannot)
supply is the **binding**: which SSA component owns which plane, who decides
what, and what happens when an enforcement phase would break a field office.

This document is that binding — the adoption artifact the SSA review
correctly identified as missing ("without governance clarity, any roadmap
cannot be adopted"). It is a **draft proposal**: every assignment below is a
recommendation keyed to the component roles already named across the series,
pending ratification by the CIO Office and OIS. Roles are organizational
positions, never named individuals.

> **The two-layer rule.** The series' doctrine layer stays organization-free
> so it survives reorganizations. This adoption layer binds doctrine to the
> current org chart — and because Part 4 made the org chart *data*, a
> reorganization updates this document by re-derivation, not rewrite.

---

## 1. Track Ownership Matrix

R = Responsible (executes) · A = Accountable (owns outcome, one per row) ·
C = Consulted · I = Informed

| Track (series part) | A | R | C | I |
|---|---|---|---|---|
| DDI / IPAM / DNS / PKI substrate (Part 1) | CIO Infrastructure | Network & DNS Team | OIS (DNSSEC key custody); Cloud Infra Teams | SOC; Help Desk |
| NAC / 802.1X device identity (Part 2) | OIS | Network Infrastructure Team | PKI Team; Endpoint Engineering (Intune) | SOC; Facilities (port inventory) |
| Certificates & tokens (Part 3) | OIS | PKI Team | Identity Engineering; Network & DNS Team | Application owners |
| HRIT identity & org SSOT (Part 4) | CIO Office (data ownership: HR) | Identity Engineering | HR / OPM integration office; OIS | All downstream app owners |
| Network & identity modernization (Part 5) | CIO Infrastructure | CSI Team | OIS; Network Infrastructure; Identity Engineering | Regional IT leads |
| Telecom modernization / TIC 3.0 (Part 6) | CIO Infrastructure | Network Infrastructure Team | OIS (TIC posture); carrier/contract office | Field office leads |
| SQL Server auth modernization (Parts 7–8) | Application portfolio owner | Database Engineering | Identity Engineering; OIS | Application owners |
| Database consolidation (Part 9) | Application portfolio owner | Database Engineering | Network Infrastructure (physics/QoS) | Regional data stewards |
| Privileged access management (Part 10) | OIS | Identity Engineering | SOC; all Tier-0 platform teams | Audit liaison |
| Vulnerability management / BOD 26-04 (Part 11) | OIS | SOC / Vulnerability Mgmt Team | Platform teams (remediation); CSI Team | AO; CIO Office |
| Data protection / Purview (Part 12) | Data governance office | Endpoint & Collaboration Engineering | OIS; Records Officer | Business units |
| SIEM / XDR / detection (Part 13) | OIS | SOC | All evidence-producing platform teams | AO |
| Business continuity (Part 14) | CIO Office | CSI Team + platform teams | OIS; Facilities | All components |
| SCRM / SBOM / VDR (Part 15) | OIS | CSI Team (pipeline); Acquisition (vendor side) | Legal; contract office | AO |
| PM governance (Part 16) | SAISO/CISO | Security PMO | CIO Office | All track owners |
| PII processing & transparency (Part 17) | Senior Agency Official for Privacy | Privacy Office | Data governance; OIS | Business units |
| Training & awareness (Part 18) | SAISO/CISO | Security Training Office | HR (LMS); SOC (IR drills) | All staff |
| Authorization package & ConMon (Part 19) | **Authorizing Official** | CSI Team (evidence); ISSO | OIS; 3PAO (when engaged) | CIO Office |

**One-per-row accountability is the point.** The review found the agency
"repeatedly asking who owns Zero Trust, SCuBA, and compliance." Zero Trust
is not a row because it is not a track — it is the doctrine every row
implements. SCuBA ownership = the Part 11/13 rows' A (OIS) with the CSI Team
R for the ScubaDrift pipeline. Compliance ownership = the Part 19 row: the
AO is accountable; everyone else produces evidence.

---

## 2. Decision-Rights Register

Standing decisions the series has explicitly deferred to governance, each
with exactly one decision owner:

| # | Decision | Owner (decides) | Consulted | Type |
|---|---|---|---|---|
| D1 | DDI deployment path — Path A (BloxOne SaaS, inherited ATO) vs. Path B (agency-operated NIOS Grid) | CIO Office | OIS; Network & DNS Team | One-time, then binding |
| D2 | Grid Admin accountability model (full-authority DDI role: MFA + PAW + holder) | OIS | CIO Infrastructure | One-time + annual review |
| D3 | RADIUS platform — NPS HA vs. ISE vs. ClearPass | CIO Infrastructure | OIS; Network Infrastructure | One-time, then binding |
| D4 | NAC hostname-to-certificate binding design (Books 01/02/03 compound guarantee) | OIS | PKI; Network & DNS; Identity Engineering | One-time validation |
| D5 | SD-WAN Manager hosting — self-hosted GovCloud vs. vendor SaaS (boundary consequences) | AO (boundary) + CIO Infrastructure (platform) | OIS | One-time, then binding |
| D6 | TIC 3.0 Use Case E posture — branch stack composition; Optimize-only proxy exemption | OIS | Network Infrastructure; CIO Office | One-time + re-validated per TIC catalog update |
| D7 | Attribute authority map sign-off (Part 4 Phase 1 gate) | CIO Office + HR data owner jointly | OIS; Identity Engineering | One-time + per-attribute change control |
| D8 | Leaver-automation go-live date + separation-to-revocation target | OIS | HR; Identity Engineering | One-time gate |
| D9 | Gated-actuation approvals (Advanced maturity: human approves each corrective action) | Per-plane R from §1 | OIS standing guidance | Standing, per action |
| D10 | MAB exceptions (device classes exempt from 802.1X) | OIS | Network Infrastructure; asset owner | Standing, per exception, expiring |
| D11 | Governed-exception acceptance in ScubaDrift dispositions (with expiry) | OIS | SOC; CSI Team | Standing, per exception, expiring |
| D12 | Boundary-variance escalation (gap register shows non-compensable gap) | AO | OIS; CIO Office | Standing trigger, rare |
| D13 | FedRAMP 20x package submission (Phase 7) | AO | CIO Office; OIS; CSI Team | One-time |
| D14 | Vendor substitution within a mechanism class (per the alternatives matrix) | CIO Office | OIS; track A/R; acquisition | Per procurement |

---

## 3. Enforcement Go / No-Go Criteria — Field Offices and Telework

The review flagged the absence of "no-go criteria." The series' phased
rollouts (Books 02, 03, 04, 05) all share the same shape — monitor before
enforce — and these are the gates that stop an enforcement phase from
breaking mission delivery:

**No enforcement phase proceeds at a site while any of the following holds:**

1. **Baseline incomplete** — the monitor-mode report (NAC Phase 1, cert
   estate discovery, provisioning shadow mode) still shows unexplained
   entries for that site's population.
2. **Exception backlog open** — devices/apps at the site require MAB or
   legacy-auth exceptions that are identified but not yet registered with
   expiry dates.
3. **No same-day rollback** — the site cannot be returned to pre-enforcement
   state within one business day (port config revert, CA report-only
   fallback, provisioning pause).
4. **Help Desk unbriefed** — the site-facing support tier has not received
   the enforcement-phase playbook (quarantine captive portal, remediation
   VLAN self-heal, token re-auth guidance).
5. **Telework parity untested** — for identity/token phases: the remote
   worker path (VPN-less ZTNA or CA-gated access) has not been validated for
   that population; a control that only works on-premises is a regression
   for a hybrid workforce.
6. **Peak-period freeze** — no enforcement cutover inside an agency
   filing/benefit peak window as published by the CIO Office.

**Go requires:** baseline explained + exceptions registered with expiry +
rollback rehearsed + support briefed + telework path validated + freeze
window clear — recorded as a dated gate decision by the track's Accountable
owner (§1) with OIS concurrence.

---

## 4. Review Cadence

This document rides the Book 19 ConMon cadence: §1 ownership reviewed
annually (or on reorganization — a data change per Part 4); §2 standing
decisions (D9–D12) reviewed quarterly with the POA&M; §3 gate decisions
recorded per enforcement phase and retained as authorization evidence.

---

*Internal CSI Team working artifact — draft pending CIO Office / OIS
ratification. Component names reflect the roles used throughout the AAN
series; the CIO Office maps them to current organizational designations at
ratification.*
