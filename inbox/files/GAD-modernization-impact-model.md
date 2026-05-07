---
id: UIAO_GAD
title: "Appendix GAD — Modernization Impact Model: Loss of Computer Objects"
category: Model
status: canonical
canon_refs:
  - ADR-031
  - Appendix_GAE
  - Appendix_T_Identity_Risk_Scoring
date: 2026-04-20
---

# Appendix GAD — Modernization Impact Model: Loss of Computer Objects

## GAD.0 Purpose

Defines the impact of decomposing AD computer objects across the
identity, workload, and management planes. Provides risk patterns,
target-state principles, and mitigation paths. Feeds the identity
risk scoring model (Appendix T) with computer-object-specific factors.

---

## GAD.1 Impact Dimensions

### GAD.1.1 — Identity-Plane Impact

**Loss:** Machine as first-class security principal in any directory.

AD computer accounts are Kerberos principals. They hold TGTs,
participate in authentication chains, and are first-class principals
in ACLs, delegation, and trust. When a server is Arc-enrolled, it
gains no equivalent Entra identity. When a workstation is Entra-joined,
the device object is not a security principal.

**Shift:** From *machine identity* to *user + app + device posture*
as the primary authentication axes.

Zero Trust identity is user-centric and app-centric. The device
contributes compliance posture to Conditional Access decisions, not
a Kerberos ticket to a resource. This is architecturally correct
for cloud workloads and requires rethinking for anything designed
around machine-as-principal.

**Risk:** Any system that authenticates machines (not users or apps)
cannot migrate without rearchitecture. These are AD retirement blockers.

---

### GAD.1.2 — Governance-Plane Impact

**Loss:** OU / GPO hierarchy as the single source of truth for policy
scoping, delegation, and organizational structure.

The OU tree was the governance model. Everything derived from it:
who administers what, what policies apply to whom, what group
memberships flow from organizational position. It was hierarchical,
inherited, and expressed in the directory itself.

**Shift:** To OrgPath + dynamic groups + Intune + Entra RBAC.

The OrgPath model (Appendix A–D) rebuilds this governance model
without containers. It is more explicit (every decision is a
canonical artifact), more auditable (every change is a governed PR),
and more portable (OrgPath works across Entra, Arc, and workload
identity planes). But it requires intentional construction — it does
not emerge automatically from directory placement the way GPOs did.

**Risk:** Without OrgPath, governance collapses to manual group
management with no organizational coherence. This is the primary
governance failure mode in unstructured Entra migrations.

---

### GAD.1.3 — Workload-Plane Impact

**Loss:** SPN/Kerberos-centric server-to-server authentication.

Every service that authenticates server-to-server via Kerberos,
NTLM, or LDAP bind is tied to a computer account. The computer
account's identity IS the service's identity. When that computer
account loses its role as a security principal, the service loses
its authentication anchor.

**Shift:** To app registrations, OAuth2/OIDC, managed identities,
and API permissions.

This shift is non-trivial for legacy applications. It requires:
1. Identifying every SPN and mapping it to a service
2. Determining whether the service can use OAuth2/OIDC
3. If yes: registering an app, granting permissions, updating the application
4. If no: documenting as a retirement blocker, planning decommission

**Risk:** This is the highest-density risk in the migration. Broken
Kerberos authentication breaks silently — services that worked fine
during hybrid operation stop working the moment the last DC
servicing those SPNs is decommissioned.

---

### GAD.1.4 — Management-Plane Impact

**Loss:** Single directory anchor for inventory, policy, identity,
and lifecycle management.

In AD, one object served all management functions. Enumerating
`Get-ADComputer -Filter *` gave you the definitive inventory of
everything in the environment.

**Shift:** Split across Intune (client inventory), Arc (server
inventory), and Entra (device identity). No single authoritative
source.

UIAO's survey adapter becomes the inventory reconciliation layer —
it queries all three planes and produces a unified view.

**Risk:** Without explicit inventory reconciliation, computers
exist in some planes but not others, producing compliance gaps
that are invisible to any single administrative console.

---

## GAD.2 Risk Patterns

### Pattern D.2.1 — Orphaned Server Workloads

**Symptom:** Legacy applications bound to machine SPNs cannot be
mapped to app identities. Services that authenticate via LDAP bind
using machine credentials break when the machine account is retired.

**Detection:** SPN inventory in the AD survey adapter
(`sa_adcs_dependent`, `kerberos_delegation` fields). Any service
account or computer account with SPNs is a candidate.

**Severity:** P1 if the SPN binds to an active production service.

**Mitigation path:**
1. Catalogue every SPN: `Get-ADComputer -Filter * -Properties ServicePrincipalName`
2. Map each SPN to its service and owner
3. For each service: assess OAuth2/OIDC readiness
4. Migrateable → create Managed Identity, update application
5. Not migrateable → document as blocker, schedule decommission or wrapper

**Retirement gate:** Zero unresolved SPNs on non-excluded computer objects.

---

### Pattern D.2.2 — Governance Drift After OU Loss

**Symptom:** Teams lose clarity on organizational placement after
OUs are no longer authoritative. Devices accumulate in default
containers. Policy targeting becomes ad-hoc group management.

**Detection:** `user_unresolvable` and `computer_unresolvable`
counts in survey report. Any device without a valid OrgPath is
experiencing this pattern.

**Severity:** P2 operationally. P1 if policy targeting gaps create
security control failures.

**Mitigation:** OrgPath assignment (Appendix F Phase 2–3) is the
complete remediation. The survey adapter writes OrgPath to
`extensionAttribute1` on computer objects. Entra Connect syncs it.
Dynamic device groups provide immediate policy scope.

**Retirement gate:** OrgPath coverage ≥ 99% of enrolled devices.

---

### Pattern D.2.3 — Fragmented Administrative Rights

**Symptom:** Administrators previously scoped by OU ACLs now have
unclear, inconsistent, or over-broad rights in the cloud environment.
Helpdesk staff who managed specific OUs have lost their scope
boundaries and either can't do their jobs or have tenant-wide access.

**Detection:** Delegation Matrix (Appendix D) comparison against
current Entra role assignments. Any scoped OU role that has not
been translated to a scoped AU role is a fragmentation point.

**Severity:** P2 (operational) to P1 (if over-broad admin rights
are granted as a workaround).

**Mitigation:** Administrative Units with OrgPath-scoped dynamic
membership replace OU delegation. One AU per organizational scope
in the delegation matrix. Scoped `User Administrator` and
`Helpdesk Administrator` roles on each AU replicate the previous
OU ACL model with full audit capability.

**Retirement gate:** All previous OU-scoped delegation entries have
corresponding AU + scoped role assignments.

---

### Pattern D.2.4 — Certificate Chain Collapse (ADCS Dependency)

**Symptom:** Certificates issued by on-premises ADCS expire silently
after AD retirement. Services authenticating via certificate bound to
a machine account or ADCS-issued cert break without warning.

**Detection:** `sa_adcs_dependent` flag in survey adapter service
account inventory. Also: any computer object with a certificate
in `userCertificate` attribute.

**Severity:** P1 — this is the silent-failure pattern that causes
the most severe post-migration incidents.

**Mitigation path:**
1. Enumerate all ADCS certificate templates in use
2. For each template: identify all issued certificates and their subjects
3. Map each certificate to the service it authenticates
4. For cloud services: migrate to Entra-issued or managed certificates
5. For on-premises services: deploy NDES/SCEP or Intune PKCS profiles
6. For Kerberos-only services: this is simultaneously a Track 3 issue

**Retirement gate:** No active certificates with ADCS as issuing CA
on services outside the "stay AD" category.

---

## GAD.3 Target-State Principles

### Principle D.3.1 — Identity Is App-First, Not Machine-First

Servers are hosting platforms, not security principals. The workload
running on the server is the identity — expressed as a Managed Identity
or Service Principal. The server's Arc enrollment is its management
anchor, not its identity anchor.

**Operational implication:** Stop asking "what is this server's
identity?" Start asking "what workloads run on this server, and
what are their identities?"

---

### Principle D.3.2 — Policy Is Path-Driven, Not Container-Driven

OrgPath + dynamic groups is the only source of scoping truth.
No policy assignment should reference a manually-curated static
group, an OU path, or a hardcoded device list. Every policy scope
must be traceable to an OrgPath entry in Appendix A.

**Operational implication:** If you cannot express a policy scope
as an OrgPath pattern, the policy needs to be redesigned, not
the OrgPath model.

---

### Principle D.3.3 — Management Is Plane-Specific

The identity plane (Entra), management plane (Intune/Arc), and
workload plane (Azure/app) are explicitly separated. No object
crosses planes. No management tool manages across planes.

**Operational implication:** Intune admins manage client devices.
Arc admins manage servers. App owners manage workload identities.
UIAO governance overlaps all three planes via OrgPath as the
common organizational encoding — but the management tools and
permissions are plane-specific.

---

## GAD.4 Risk Factor Extensions for Appendix T

The following risk factors are added to the identity risk scoring
model (Appendix T) for computer objects:

| Factor ID | Risk Factor | Weight | Detection |
|---|---|---|---|
| RF-C01 | No OrgPath on device object | 9 | extensionAttribute1 IS NULL |
| RF-C02 | Active SPNs with no MI/SP mapping | 10 | SPN present, no linked app registration |
| RF-C03 | ADCS-dependent certificate | 9 | userCertificate with ADCS issuer |
| RF-C04 | Unconstrained Kerberos delegation | 10 | TrustedForDelegation = true |
| RF-C05 | EOL OS with no decommission plan | 7 | OS version EOL, no disposition decision |
| RF-C06 | Domain-joined server, no Arc enrollment | 6 | Computer in AD, not in Arc inventory |
| RF-C07 | GMSA with no managed identity mapping | 8 | GMSA account, no linked MI |
| RF-C08 | No disposition decision recorded | 5 | Missing from Computer Disposition Map |
