---
deliverable_id: Spec2-D3.8
title: "Data Flow Security Assessment"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 3
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-01
updated: 2026-05-01
canonical_adrs:
  - ADR-003
  - ADR-004
  - ADR-049
  - ADR-050
canonical_docs:
  - UIAO_007
  - UIAO_136
upstream_deliverables:
  - Spec2-D3.1
  - Spec2-D3.2
  - Spec2-D3.3
sibling_deliverables:
  - Spec2-D2.3
  - Spec2-D3.6
  - Spec2-D3.7
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D3.8: Data Flow Security Assessment

> **Status (v0.1, 2026-05-01):** Initial draft. v0.2 verification
> against current TLS-1.3 / Microsoft Graph TLS posture, current
> Microsoft Graph permission catalog (least-privileged for the
> middleware service principal), and the FedRAMP Moderate
> control catalog.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Data Flow Security Assessment
called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 3 → D3.8:

> *Security review: data in transit (TLS 1.2+), data at rest (HR
> PII handling), least-privilege API permissions
> (User.ReadWrite.All scope), conditional access for provisioning
> service principal, audit logging.*

D3.8 is the security posture statement for the entire Spec 2 data
flow. It cites NIST 800-53 Rev 5 controls per surface and is the
artifact that an auditor reviews to confirm the substrate is
deployable into a FedRAMP Moderate boundary.

### 1.1 Scope

In scope:

- Data in transit (transport security per leg).
- Data at rest (HR PII storage; provenance store; quarantine
  store; logs).
- Microsoft Graph permissions (least-privileged scope set).
- Service-principal credential model (managed identity / WIF /
  certificate fallback).
- Conditional Access for the middleware's service principal.
- Audit logging completeness.
- Boundary controls (FedRAMP Moderate alignment).
- Threat-model summary (key risks + mitigations).

Out of scope:

- Per-deployment penetration testing results (separate artifact
  per agency).
- Code-level static analysis (the middleware repo's CI pipeline
  enforces this; not a substrate-level concern).
- HR-source-side security (HR vendor's own SOC 2 / FedRAMP
  attestation is the authoritative source).
- Cryptographic algorithm validation (FIPS 140-3 inheritance from
  Azure Government / Microsoft Graph).

## 2. Data in Transit

Every leg of the data flow:

| Leg | Protocol | Cipher floor | Notes |
|---|---|---|---|
| HR system → middleware | HTTPS / TLS 1.2+ | TLS 1.2+ enforced; TLS 1.3 preferred | HR vendor TLS posture per vendor SOC 2 |
| Middleware ↔ Microsoft Graph | HTTPS / TLS 1.2+ | TLS 1.2+ enforced by Microsoft | Microsoft mandates TLS 1.2+ for all Graph endpoints |
| Microsoft Graph → Entra ID | (internal Microsoft) | inherited | Microsoft attestation |
| Entra ID → Provisioning Agent | HTTPS / TLS 1.2+ | TLS 1.2+ enforced | Per D3.3 §3 (TLS 1.2 on host before agent install) |
| Provisioning Agent → On-Prem AD | LDAP/389 + GC/3268 | LDAPS preferred when supported; Kerberos for auth | Tenant-side AD configuration may force LDAPS |
| Middleware → Provenance store | HTTPS / TLS 1.2+ | TLS 1.2+ | Azure Cosmos / Postgres-over-TLS / etc. |
| Middleware → Monitoring backend | HTTPS / TLS 1.2+ | TLS 1.2+ | Application Insights / Log Analytics |

UIAO MUST NOT use TLS 1.0 or 1.1 on any leg. TLS 1.3 is preferred
where the platform supports it.

Certificate validation: the middleware MUST validate the
Microsoft Graph endpoint certificate chain to a known
trusted-root anchor (typically the platform's certificate
store). Pinning is OPTIONAL and tenant-policy-driven.

## 3. Data at Rest

| Data class | Store | Encryption | Retention |
|---|---|---|---|
| HR PII (canonical record snapshot in quarantine) | Quarantine store (Cosmos/Table/Postgres) | Platform-default at-rest encryption (AES-256) | Per agency policy; default 7 years for federal civilian |
| HR PII (canonical payload in provenance store) | Provenance store (Cosmos/Postgres) | Platform-default at-rest encryption | Per agency policy; default 7 years |
| HR PII in operational logs | Log Analytics / Application Insights | Platform-default | Per §3 of D3.7; default 1–3 years operational |
| Service-principal credentials | Managed identity → no stored credential; certificate fallback → Key Vault | HSM-backed when available | Per certificate validity |
| Substrate manifest | Deployment repo + Key Vault for secrets | Repo encrypted in transit + at rest | Per repo policy |

UIAO MUST NOT store HR PII in:

- Source-control repositories (other than test data clearly
  marked synthetic).
- Local developer workstations beyond the tenancy environment.
- Backup copies outside the tenant's compliance boundary.

PII handling per §3.1 of D3.2's logging contract: logs reference
`external_id` and `upn` only; full PII appears only in the
canonical-payload audit store with separate access controls.

## 4. Microsoft Graph Permissions (Least-Privileged)

The middleware's service principal MUST hold ONLY the
permissions necessary to perform its operations. The canonical
permission set:

| Permission | Used by | Justification |
|---|---|---|
| `SynchronizationData-User.Upload` | bulkUpload (D3.1 §4.2) | Required to call POST /bulkUpload |
| `ProvisioningLog.Read.All` | Provisioning log read (D3.1 §4.2) | Required to read Microsoft-side provisioning logs (per D3.7 §7) |
| `User.RevokeSessions.All` | revokeSignInSessions (D2.3 step 2) | Least-privileged for the leaver session-revoke step (per D2.3 v0.2 verification) |

The middleware MUST NOT hold:

- `User.ReadWrite.All` — too broad; bulkUpload is more restricted.
  (This is a UIAO posture refinement vs. some Microsoft tutorials
  that grant the broader permission.)
- `Directory.ReadWrite.All` — far too broad.
- `RoleManagement.ReadWrite.Directory` — outside middleware scope.

ISVs supplying tenant-deployed middleware can use
`SynchronizationData-User.Upload.OwnedBy` (verified at D3.1 v0.2)
to scope the upload to the ISV's own provisioning app, but
in-tenant deployments use the tenant-default permission name.

Additional permissions (per-feature, granted only when the
feature is enabled):

| Permission | Feature |
|---|---|
| Group.ReadWrite.All (limited) | Leaver group-removal (D2.3 step 4) — narrowed via app-only scope and per-group attestation |
| (HR-specific) | HR writeback when enabled (D3.6 §4) — vendor-specific |

## 5. Service-Principal Credential Model

Per ADR-004 (Workload Identity Federation as Default):

1. **Preferred**: Federated credential / managed identity. No
   stored secret; the credential is a trust relationship between
   Azure AD and the runtime platform (Azure Functions managed
   identity; Kubernetes WIF; etc.).
2. **Acceptable**: Certificate-based authentication. Certificate
   stored in Key Vault; access scoped via Key Vault RBAC.
3. **Discouraged**: Client-secret authentication. Acceptable only
   when (1) and (2) are infeasible (e.g., legacy platform
   constraints); requires explicit ADR documenting the deviation.

Rotation:

- Managed identity / WIF: no rotation needed (Microsoft manages).
- Certificate: rotated per agency policy (typically 1 year max).
- Client secret: rotated quarterly.

The middleware MUST surface `secret-rotation-due` warnings via
D3.7 alerts at 30 / 14 / 3 days before expiry.

## 6. Conditional Access for the Middleware Service Principal

The middleware's service principal MUST be in scope of a
Conditional Access policy that:

- Restricts authentication to the middleware's runtime IPs
  (named-location bound) when the middleware runs from a fixed
  host set.
- Requires risk-level = "low" (sign-in risk) — the service
  principal should never trigger anomalous-sign-in detections.
- Audits all sign-ins to the dedicated provisioning app.

For service principals not associated with a fixed runtime IP
(e.g., consumption-plan Azure Functions), the named-location
restriction is replaced with a **device-attribute-bound**
restriction (the runtime carries managed-identity attributes
that can be CA-targeted).

## 7. Audit Logging Completeness

The audit logging story spans:

| Source | Surface | Audited |
|---|---|---|
| UIAO middleware | Provenance store (D3.1 §8) | Every provisioning event |
| UIAO middleware | Quarantine store (D2.6 §3) | Every quarantine + state transition |
| UIAO middleware | Operational logs (D3.7 §3) | Every component operation |
| Microsoft Entra | Provisioning logs (Azure Monitor) | Every Microsoft-side provisioning operation |
| Microsoft Entra | Sign-in logs (Azure Monitor) | All service-principal sign-ins |
| Microsoft Entra | Audit logs (Azure Monitor) | All directory-changing operations |
| On-prem AD | Domain controller security log | All AD writeback operations |

Every UIAO-side event has a 1:1 correspondence with a Microsoft-
side log entry (when one applies); the cross-reference key is
the Microsoft Graph `request_id` captured in the provenance
record (D3.1 §8.2). This is what makes the substrate
auditable end-to-end.

## 8. Boundary Controls (FedRAMP Moderate)

UIAO Spec 2 substrate is built to deploy inside a FedRAMP
Moderate boundary. Specific control mappings:

| Control family | Controls implemented |
|---|---|
| AC (Access Control) | AC-2, AC-3, AC-4, AC-6, AC-12 — per D2.x + D3.x |
| AU (Audit + Accountability) | AU-2, AU-3, AU-6, AU-9, AU-11, AU-12 — per D3.7 + D3.8 |
| IA (Identification + Authentication) | IA-2 (uniqueness), IA-4 (UPN), IA-5 (gMSA password mgmt) |
| IR (Incident Response) | IR-4 (per D2.6 §5 escalation tiers) |
| CM (Configuration Management) | CM-2, CM-3, CM-8 |
| SC (System + Communications Protection) | SC-7 (boundary), SC-8 (data in transit), SC-12, SC-13, SC-28 (data at rest) |

The full FedRAMP Moderate baseline is inherited via Azure
Government / Microsoft Graph attestations; UIAO attests to
correct configuration of the inherited controls.

## 9. Threat Model Summary

Key risks + mitigations:

| Risk | Mitigation |
|---|---|
| Compromised middleware service principal | Managed-identity / WIF + CA + sign-in risk filter (§5, §6) |
| HR feed compromise (malicious HR record injection) | D2.8 scope filter + D2.6 quarantine + Manual review on workflow-elevation cases |
| Provenance-store tampering | Append-only provenance design; integrity-hash chain (referenced from drift engine) |
| Quarantine queue starvation (DoS) | Per-tenant rate limiting; SLA-based escalation |
| AD writeback compromise (agent host owned) | gMSA-scoped permissions; tier-0 host posture; outbound-only network |
| Latency-based attack (cascade timing leakage) | Cascade timings published; not a meaningful side channel |
| Insider — operator manual OrgPath override abuse | All overrides emit provenance with operator identity + justification (D3.5 §7); 30-day default expiry |
| Stolen Graph access token (in-flight) | Token short TTL (default ≤1h); refresh tokens per session-revoke posture (D2.3) |

## 10. References

### 10.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-004](../adr/adr-004-workload-identity-federation-default.md) — credential model.
- [ADR-049](../adr/adr-049-microsoft-adapter-coverage-expansion.md)
- [ADR-050](../adr/adr-050-reference-middleware-implementation-choices.md)

### 10.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 3 → D3.8.

### 10.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate; §4 auth flow + §8 provenance.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) — middleware whose security posture this assesses.
- [Spec2-D3.3](./Spec2-D3.3-ProvisioningAgentDeploymentArchitecture.md) — agent security posture.
- [Spec2-D2.3](./Spec2-D2.3-LeaverWorkflowSpecification.md) — User.RevokeSessions.All requirement basis.
- [Spec2-D3.6](./Spec2-D3.6-WritebackSpecification.md) — writeback security posture.
- [Spec2-D3.7](./Spec2-D3.7-MonitoringAlertingConfiguration.md) — audit-completeness alerts.

### 10.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Learn — Microsoft Graph permissions reference.
- Microsoft Learn — TLS 1.2+ enforcement for Microsoft Graph.
- Microsoft Learn — Conditional Access for service principals.

### 10.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, AC-3, AC-4, AC-6, AC-12, AU-2, AU-3, AU-6, AU-9, AU-11, AU-12, IA-2, IA-4, IA-5, IR-4, CM-2, CM-3, CM-8, SC-7, SC-8, SC-12, SC-13, SC-28.
- FedRAMP Moderate baseline (inherited via Azure Government + Microsoft Graph attestations).
