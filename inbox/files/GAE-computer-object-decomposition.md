---
id: UIAO_GAE
title: "Appendix GAE — Decomposition of the AD Computer Object"
category: Model
status: canonical
canon_refs:
  - ADR-031
  - Appendix_C_Attribute_Mapping_Table
  - Appendix_F_Migration_Runbook
  - Appendix_D_Delegation_Matrix
diagrams:
  - DIAG-GAE-001
  - DIAG-GAE-002
date: 2026-04-20
---

# Appendix GAE — Decomposition of the AD Computer Object

## GAE.0 Purpose

Defines how the AD computer object is decomposed across three cloud-native
planes during migration to Entra ID, Azure Arc, and managed workload
identities. This decomposition is the architectural basis for all
computer-object disposition decisions in the UIAO migration runbook.

The AD computer object does not survive the transition as a unified
construct. It is disassembled. This appendix specifies exactly what
each function becomes and where it lives.

---

## GAE.1 Legacy Semantics of the AD Computer Object

| Label | Function | Notes |
|---|---|---|
| GAE.1.1 | **Security principal** — SID, Kerberos TGT, NTLM, SPN binding | Machine is first-class identity in AD |
| GAE.1.2 | **Policy anchor** — OU placement → GPO inheritance, ACL delegation | Organizational hierarchy expressed via container model |
| GAE.1.3 | **Workload binding** — SPN registration, constrained delegation, GMSAs | Server workloads tied to machine identity |
| GAE.1.4 | **Management anchor** — inventory, discovery, config management tooling | Single object serves all management planes |

These four functions are satisfied by four different cloud-native constructs.
None of them is a "computer object."

---

## GAE.2 Cloud-Era Decomposition

### GAE.2.1 — Identity Plane: Entra Device

**Target construct:** Entra ID Device object (Azure AD Joined / Registered / Hybrid)

**What it does:**
- Issues device-bound Primary Refresh Token (PRT)
- Satisfies Conditional Access device compliance requirement
- Anchors Intune MDM/MAM enrollment
- Provides device identity for Entra RBAC scoping

**What it does NOT do:**
- Is not a security principal (no SID, no Kerberos)
- Cannot hold SPNs, ACLs, or delegation rules
- Cannot be placed in an OU
- Is not used for server workloads

**OrgPath integration:**
OrgPath is written to `extensionAttribute1` on the Entra device object
via AD write-back + Entra Connect sync. Dynamic device groups derive
from OrgPath exactly as user groups do (Appendix B). Intune profiles
target these groups (Appendix GAE.3).

**Applies to:** Desktops, laptops, hybrid-joined workstations.
**Does NOT apply to:** Servers, DCs, ADCS, ADFS, NPS, RADIUS hosts.

---

### GAE.2.2 — Workload Plane: Service Principal / Managed Identity / Workload Identity

**Target constructs:**
- **App Registration** — for applications that authenticate to APIs
- **Service Principal** — the runtime identity of an app registration
- **Managed Identity** — system-assigned or user-assigned identity for Azure resources
- **Workload Identity** — federated identity for non-Azure workloads (Kubernetes, CI/CD)

**What it replaces:**
- SPNs registered on computer accounts
- Kerberos constrained delegation (KCD)
- GMSAs (Group Managed Service Accounts)
- Machine-to-machine authentication via computer accounts
- Service accounts tied to computer objects

**What it requires:**
- Applications must support OAuth2/OIDC (or a wrapper must be built)
- Legacy Kerberos-only applications cannot migrate to this plane
  without re-architecture — they become blockers to AD retirement

**Migration gate:** Every SPN in the AD environment must be catalogued
and either (a) mapped to a Managed Identity / Service Principal or (b)
documented as an AD retirement blocker requiring remediation before
forest decommission.

---

### GAE.2.3 — Management Plane

**For client devices (desktops/laptops):** Microsoft Intune

- Configuration profiles → replaces GPO Computer Configuration
- Compliance policies → replaces GPO-enforced compliance baselines
- App deployment → replaces GPO Software Installation / SCCM
- Security baselines → replaces GPO Security Templates
- **OrgPath-scoped dynamic groups** are the targeting mechanism

**For servers:** Azure Arc-enabled Server

- Arc machine is an **ARM resource**, not an Entra object
- Lives in Azure portal under Arc → Machines, not Entra ID → Devices
- Does not participate in Conditional Access
- Does not receive Intune policies
- **OrgPath is applied as an ARM resource tag**, not an extension attribute
- Policy targeting uses Azure Policy assignments scoped to resource
  groups or subscriptions
- Monitoring via Azure Monitor (subject to GCC boundary constraints
  — see gap registry GAP-ARC-001)

**Applies to:**
- Intune: all managed client devices
- Arc: member servers, infrastructure servers, application servers
- **Excluded from both:** DCs, ADCS servers, ADFS servers, NPS/RADIUS
  (stay AD-anchored until dependencies resolved)

---

## GAE.3 Synthetic OU Model in UIAO

The OU tree provided three things: organizational hierarchy, policy scoping,
and delegated administration. UIAO rebuilds all three without containers.

### GAE.3.1 — OrgPath as OU Surrogate

OrgPath (`ORG-IT-SEC-SOC`) encodes the logical placement that the OU
distinguished name previously encoded. It is:
- Plane-aware: `extensionAttribute1` for Entra objects, ARM tag for Arc
- HR-authoritative: populated from HR system, not OU path
- Codebook-validated: every value must exist in Appendix A

### GAE.3.2 — Dynamic Groups as Policy Scopes

OrgPath segments materialize into Entra dynamic groups (Appendix B).
These groups serve as the assignable scopes for:
- Intune configuration profiles and compliance policies
- Conditional Access policies
- Entra RBAC role assignments
- License assignments
- Entitlement management access packages

For Arc servers, Azure Policy initiative assignments replace dynamic
groups as the scoping mechanism, using OrgPath ARM tags as the filter.

### GAE.3.3 — Delegation Matrices as ACL Surrogate

OU ACLs are replaced by the Delegation Matrix (Appendix D):
- Entra RBAC roles scoped to Administrative Units
- PIM just-in-time elevation for privileged operations
- Intune scope tags for device admin delegation
- Arc RBAC for server management delegation

All delegation decisions are expressed in canonical matrices, not
ACLs on directory objects. Changes follow Workflow 5 (Appendix E).

---

## GAE.4 Disposition Decision Tree

For each AD computer object in the survey (Appendix F Phase 1):

```
[Computer Object]
        │
        ├─ Is it a DC?
        │       └─ YES → STAY-AD-DC (never migrate)
        │
        ├─ Is it ADCS / ADFS / NPS / RADIUS host?
        │       └─ YES → STAY-AD-DEPENDENCY (migrate Track 3 first)
        │
        ├─ Is it EOL OS (Win Server 2008/2012 not extended)?
        │       └─ YES → DECOMMISSION (no migration path)
        │
        ├─ Is it a client (Windows 10/11, laptop, workstation)?
        │       └─ YES → ENTRA-DEVICE (Track 1)
        │
        ├─ Is it a server with only management workloads?
        │       └─ YES → ARC-SERVER (Track 2)
        │
        └─ Is it a server with SPNs / KCD / GMSA?
                └─ YES → ARC-SERVER + MANAGED-IDENTITY-CANDIDATE (Track 2 + Track 3)
```

The output of this classification is the **Computer Disposition Map**
— the authoritative input to the three-track migration runbook
(Appendix GAF).

---

## GAE.5 What This Means for AD Retirement

AD cannot be retired until:

| Gate | Condition |
|---|---|
| GAE-GATE-1 | All `ENTRA-DEVICE` computers are Intune-enrolled and OrgPath-tagged |
| GAE-GATE-2 | All `ARC-SERVER` computers are Arc-enrolled and OrgPath-tagged |
| GAE-GATE-3 | All `MANAGED-IDENTITY-CANDIDATE` SPNs are migrated or documented as accepted risk |
| GAE-GATE-4 | All `STAY-AD-DEPENDENCY` machines have their dependencies resolved |
| GAE-GATE-5 | Zero `STAY-AD-DC` machines exist (last DCs decommissioned) |

Gates are evaluated by the survey adapter on each run. AD retirement
readiness is expressed as: gates GAE-GATE-1 through GAE-GATE-4
all green, with GATE-5 as the final act.
