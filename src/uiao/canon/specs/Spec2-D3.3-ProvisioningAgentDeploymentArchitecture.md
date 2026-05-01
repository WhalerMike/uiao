---
deliverable_id: Spec2-D3.3
title: "Provisioning Agent Deployment Architecture"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 3
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-01
updated: 2026-05-01
canonical_adrs:
  - ADR-003
  - ADR-049
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D3.1
sibling_deliverables:
  - Spec2-D3.2
  - Spec2-D3.6
  - Spec2-D3.8
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D3.3: Provisioning Agent Deployment Architecture

> **Status (v0.1, 2026-05-01):** Initial draft. The HA / sizing /
> network requirements summarized here track Microsoft Entra Cloud
> Sync prerequisites verified at D3.1 v1.0 closure (2026-04-30).
> This document binds those facts to UIAO's deployment posture
> (gMSA naming, OU-scope rules, AD permission model, monitoring
> hooks). v0.2 verification pass will revisit the prerequisites
> page for any 2026-05+ updates.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Provisioning Agent Deployment
specification called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 3 → D3.3:

> *On-prem provisioning agent deployment for AD writeback: HA
> configuration (2+ agents), network requirements, service account
> (gMSA), AD permissions required (Create/Delete/Modify user
> objects in designated OUs), monitoring.*

[D3.1 §3.5](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md)
established the agent's role and verified hardware / network /
gMSA prerequisites against Microsoft Learn. D3.3 is the deployment
runbook + UIAO-specific binding.

### 1.1 Scope

In scope:

- HA topology (active / active / active per Microsoft's recommended
  three-agent posture).
- Per-agent host requirements (Windows Server matrix, hardware
  minimums, network).
- gMSA design (naming, scope, AD permission model).
- OU-scope rules for writeback.
- Agent configuration binding.
- Monitoring hooks (per-agent health into D3.7).
- Decommission path (post-AD-sunset per UIAO_007).

Out of scope:

- Microsoft Graph synchronization-job configuration (that's the
  cloud side; D3.4 Attribute Mapping Engine).
- HR-source adapter behavior (D3.2).
- Tenant-side AD topology (each deployment's existing AD is the
  inheritable context; this spec is about the agent, not the
  forest).
- Cloud Sync vs. Entra Connect Sync feature comparison (out of
  band — UIAO uses Cloud Sync agents per ADR-003 sequencing).

## 2. HA Topology

The canonical UIAO posture: **3 active agents** per Microsoft
Entra Cloud Sync recommendation (verified at D3.1 v1.0).

| Layer | Configuration |
|---|---|
| Number of agents | 3 (active / active / active; round-robin) |
| Failure tolerance | 1 agent down: degraded (2 active); 2 down: critical alert; 3 down: writeback halted |
| Geographic placement | Co-located with the writeback target AD; not across WAN to a remote DC |
| Update cadence | Rolling — one agent at a time; never all three concurrently |
| Failover semantics | Microsoft cloud side handles agent selection; UIAO does not load-balance |

The three-agent posture is the documented Microsoft recommendation
and the UIAO default. Smaller deployments (sub-agency, lab) MAY
run two agents with explicit acknowledgment that single-agent
failure produces degraded service. Single-agent posture is NOT
supported by UIAO.

## 3. Per-Host Requirements

Per the Microsoft Entra Cloud Sync prerequisites verified at
D3.1 v1.0:

| Requirement | Value |
|---|---|
| OS | Windows Server 2016, 2019, or 2022 (2022 recommended). 2025 NOT yet supported per Microsoft (verify at v0.2 cutover). |
| Edition | Standard or Datacenter (Server Core NOT supported) |
| RAM | 4 GB minimum |
| Disk | 30 GB free |
| .NET Framework | 4.7.1 or higher |
| TLS | TLS 1.2 enabled before agent install |
| Tier | Tier 0 / control-plane posture |
| Domain join | Member of the AD writeback target domain |

UIAO MUST NOT run the agent on:

- DCs (control-plane separation).
- ADFS / PKI servers (control-plane separation).
- Server Core (unsupported by Microsoft).
- Servers running other UIAO components.

## 4. gMSA Design

### 4.1 Naming

The canonical gMSA name pattern, per Microsoft documentation
verified at D3.1 v1.0:

```
<DOMAIN>\provAgentgMSA$
```

For UIAO deployments with multiple writeback domains:

```
<DOMAIN1>\provAgentgMSA$
<DOMAIN2>\provAgentgMSA$
```

(One gMSA per writeback target domain; the agents themselves can
serve multiple gMSAs.)

### 4.2 Permissions on AD

Per the Microsoft prerequisites (verified at D3.1 v1.0):

| Permission | Scope |
|---|---|
| Read | Descendant Computer / Contact / User / InetOrgPerson |
| Full Control | Descendant Group |
| Create / Delete | User objects (within the target OU subtree) |

UIAO MUST scope the Create/Delete-user permission to a **target
OU subtree**, NOT the domain root. The target subtree is the OU
where provisioned-from-Entra users land — typically a dedicated
`OU=Cloud-Provisioned` (or per-agency-naming-equivalent).

### 4.3 Why gMSA over named service account

- No password to rotate (managed by AD).
- Constrained to specific computers (the three agent hosts).
- Auditable in the AD security log distinct from human accounts.
- Aligns with NIST SP 800-53 IA-5 password management controls.

### 4.4 gMSA installation

Per the Microsoft installer flow (referenced at D3.1 v1.0; not
re-verified here):

1. Pre-create the gMSA in AD (PowerShell: `New-ADServiceAccount`).
2. Grant the agent host computer the right to retrieve the gMSA
   password (`PrincipalsAllowedToRetrieveManagedPassword`).
3. The agent installer is run with the gMSA selected as the
   service identity.

## 5. OU Scope for Writeback

The middleware (D3.2) emits an OU-placement hint via `dn` in
the SCIM payload. The provisioning agent honors that hint and
creates / modifies users in the specified OU.

UIAO MUST configure:

- **Default writeback OU** — `OU=Cloud-Provisioned, DC=…`. New
  hires writeback here.
- **Worker-type sub-OUs** — `OU=Employees`, `OU=Contractors`,
  `OU=Interns`, etc. Per D2.1 §8.
- **Location sub-OUs** — second-level placement.
- **Department sub-OUs** — third-level placement.

Outside the writeback subtree, the agent MUST NOT have
Create/Delete permission. This is the canonical containment rule.

## 6. Network Requirements

Per the Microsoft prerequisites:

| Direction | Port | Protocol | Target | Notes |
|---|---|---|---|---|
| Outbound | 443 | TCP/HTTPS | Microsoft Entra (cloud) | Primary; mandatory |
| Outbound | 80 | TCP/HTTP | CRL endpoints | Certificate validation |
| Outbound | 8080 | TCP/HTTP | Microsoft cloud | Optional status reporting |
| Inbound from agents | n/a | n/a | n/a | Agents are outbound-only |
| Outbound to AD | 389 | TCP | LDAP to DCs | AD writeback |
| Outbound to AD | 3268 | TCP | Global Catalog | AD lookups |
| Outbound to AD | 88 | TCP | Kerberos | gMSA auth |
| Outbound to AD | 445 | TCP | SMB | gMSA password retrieval |

UIAO MUST NOT expose inbound ports on the agent hosts. The agent
is a pure outbound-pull architecture.

### 6.1 Egress allow-list

Per UIAO security posture (D3.8), agent hosts in segmented
networks MUST allow-list:

- `*.microsoftonline.com` (auth)
- `*.windowsazure.com` (legacy paths still in use)
- `*.azure.com` (Graph)
- `*.msappproxy.net` (cloud sync agent communications)
- The CRL distribution points for the certificates used.

The exact allow-list is published by Microsoft and MUST be
reviewed at each agent install. Agents in air-gapped or
heavily-restricted networks require explicit egress engineering.

## 7. Configuration Binding

The agent's UIAO-side configuration lives in
`substrate-manifest.yaml` under a per-deployment block:

```yaml
provisioning_agent:
  ha_count: 3
  hosts:
    - hostname: prov-agent-01.<domain>
      ip: 10.x.y.z
    - hostname: prov-agent-02.<domain>
      ip: 10.x.y.z
    - hostname: prov-agent-03.<domain>
      ip: 10.x.y.z
  gmsa:
    name: "provAgentgMSA$"
    domain: "<DOMAIN>"
  writeback:
    target_domain: "<domain>"
    default_ou: "OU=Cloud-Provisioned,DC=…"
    worker_type_ous:
      "Full-Time Employee": "OU=Employees,OU=Cloud-Provisioned,DC=…"
      "Part-Time Employee": "OU=Employees,OU=Cloud-Provisioned,DC=…"
      "Contractor":         "OU=Contractors,OU=Cloud-Provisioned,DC=…"
      "Intern":             "OU=Interns,OU=Cloud-Provisioned,DC=…"
  decommission_target_date: "2027-Q4"
```

The `decommission_target_date` is the planned AD-sunset date per
UIAO_007 sequencing — a forcing function for the operator to
revisit the agent's relevance over time.

## 8. Monitoring Hooks

Per-agent telemetry that D3.7 consumes:

| Metric | Source |
|---|---|
| Agent online | Cloud Sync portal / Graph API |
| Last successful sync timestamp | Per-agent |
| Agent version | Per-agent |
| AD writeback latency | Per-record write timing |
| AD writeback failure rate | Per-record write outcomes |
| Disk free | Host OS |
| RAM utilization | Host OS |
| Outbound HTTPS reachability | Synthetic probe |

Alerts (defined in D3.7):

- Agent offline > 5 minutes → tier-2 alert.
- 2+ agents offline → tier-3 alert (writeback halted).
- AD writeback failure rate > 5% → tier-2 alert.
- Agent version > 90 days behind latest released → tier-1 alert
  (informational; agency upgrade cadence varies).

## 9. Decommission Path

The provisioning agent is **temporary infrastructure**. Per
UIAO_007 sequencing, AD writeback is required during the
coexistence period only; once domain decommission is complete,
the agents are retired.

Decommission steps:

1. Confirm all on-prem-AD-dependent workflows have migrated to
   Entra ID identity (per UIAO_007 milestones).
2. Disable HR-feed writeback to AD (middleware config flag).
3. Verify zero AD-side identity-creation events from middleware
   for 30 days.
4. Stop and uninstall the agent service on each host.
5. Remove the gMSA's permissions from AD.
6. Delete the gMSA.
7. Update `substrate-manifest.yaml` to remove the
   `provisioning_agent` block.
8. Decommission the host VMs.

This is the 8-step canonical agent retirement runbook. Deviations
require an ADR.

## 10. References

### 10.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-049](../adr/adr-049-microsoft-adapter-coverage-expansion.md)

### 10.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) — domain-decommission sequencing.
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 3 → D3.3.

### 10.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — §3.5; verified-prerequisites source.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) — middleware emits the OU-placement hints honored by the agent.
- [Spec2-D3.6](./Spec2-D3.6-WritebackSpecification.md) — what attributes flow back through the agent.
- [Spec2-D3.7](./Spec2-D3.7-MonitoringAlertingConfiguration.md) — agent-health alerting rules.
- [Spec2-D3.8](./Spec2-D3.8-DataFlowSecurityAssessment.md) — agent security posture.

### 10.4 Microsoft documentation (re-verify in v0.2)

- Microsoft Learn — Microsoft Entra Cloud Sync prerequisites (verified at D3.1 v1.0; check 2025-server-support delta).
- Microsoft Learn — Cloud Sync agent installation.
- Microsoft Learn — gMSA management.

### 10.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, IA-5 (gMSA password management), SC-7 (boundary protection).
