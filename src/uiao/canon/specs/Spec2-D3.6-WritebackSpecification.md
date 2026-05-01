---
deliverable_id: Spec2-D3.6
title: "Writeback Specification"
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
  - Spec2-D1.4
  - Spec2-D3.1
  - Spec2-D3.2
  - Spec2-D3.3
  - Spec2-D3.4
sibling_deliverables:
  - Spec2-D3.7
  - Spec2-D3.8
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D3.6: Writeback Specification

> **Status (v0.1, 2026-05-01):** Initial draft. Two writeback
> directions are addressed: Entra → on-prem AD (via the
> provisioning agent, during coexistence) and Entra → HR system
> (mostly out of scope; UIAO's posture is HR is source-of-truth
> and writeback to HR is deployment-specific). v0.2 verification
> against Microsoft Entra Cloud Sync writeback documentation
> will close attribute-list specifics.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Writeback Specification called
for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 3 → D3.6:

> *Attributes written back from Entra ID to HR system (if
> supported): email address, UPN, phone number. Attributes written
> from Entra ID to on-prem AD: all mapped attributes during
> coexistence.*

### 1.1 Scope

In scope:

- Entra → on-prem AD writeback during coexistence (the canonical,
  high-volume direction).
- The attribute set written back.
- Conflict resolution between Entra-side changes and AD-side
  changes (the legacy AD edit case).
- Direction-flip considerations (when Entra becomes source-of-
  truth, AD becomes a downstream target only — not a source).
- Entra → HR writeback (per-tenant decision; UIAO posture is
  "rare, deployment-specific").
- Sunset path for AD writeback once domain decommission completes.

Out of scope:

- The provisioning agent itself (D3.3).
- Attribute mapping rules (D3.4 §4.4 has the canonical Entra → AD
  mapping table).
- HR-system writeback APIs per HR vendor (Workday / Oracle /
  SuccessFactors APIs vary).
- Conflict-resolution UI (operator-facing surface; out of scope).

## 2. Direction 1: Entra → On-Prem AD (Coexistence)

The primary writeback direction. Required during the AD-decom-
mission coexistence period (UIAO_007).

### 2.1 Trigger

Any change to a writeback-mapped Entra ID attribute (per D3.4
§4.4) on a user record in scope of the provisioning agent's OU
subtree. The agent polls Entra cloud and writes the change to
AD on the next sync cycle.

### 2.2 Attribute set

Per D3.4 §4.4, the writeback set includes (full table in D1.4):

- Identity: `userPrincipalName`, `mail`, `employeeId`,
  `displayName`, `givenName`, `sn`.
- Organizational: `department`, `title`, `manager` (DN-resolved),
  `extensionAttribute1` (OrgPath).
- Lifecycle: `accountEnabled` (mapped to `userAccountControl`
  bits).
- Region: `c` (country, from `usageLocation`).

Out of writeback set:

- `objectId` / `objectGuid` — preserved per side (cloud and AD
  use independent identifiers).
- `proxyAddresses` — managed by Exchange / Entra side; not
  written back during normal operation.
- Group memberships — handled by separate AD group-writeback
  configuration (Cloud Sync supports group writeback when
  enabled; UIAO posture: group writeback enabled when
  there are AD-side legacy applications consuming group
  membership from on-prem).

### 2.3 Volume + cadence

- Initial writeback (post-cutover): all in-scope users → AD in
  the first hours after Cloud Sync agent activation.
- Steady-state: writeback-relevant attribute changes flow
  through the agent within minutes of the cloud-side write.
- Large org changes (re-orgs per D3.5 §5): same throttling rules
  apply on the writeback side.

## 3. Conflict Resolution

The canonical UIAO posture: **Entra is source-of-truth post-
cutover; AD-side edits during coexistence are NOT supported.**

Operationally:

- AD-side writes to in-scope OUs MUST be blocked at the AD
  authentication / ACL layer (revoke service-account write
  access except for the gMSA + a small break-glass set).
- If an AD-side write does occur (operator with elevated
  rights), the next Entra → AD sync OVERWRITES it without
  warning.
- The middleware does not surface AD-side drift as a separate
  finding — the drift engine (ADR-040) does, in its
  AD-vs-Entra reconciliation pass.

This posture is contrasted with Entra Connect Sync's symmetric
synchronization model. UIAO's posture is asymmetric: cloud-first.

### 3.1 The legacy AD edit case

Some legacy applications expect to write user attributes to AD.
For those:

- Assess whether the legacy app can be reconfigured to read from
  Entra ID (preferred — eliminates the writeback).
- If not, designate the specific attributes the legacy app may
  write, exclude them from the cloud → AD writeback set, and
  document the exception in the deployment's
  `substrate-manifest.yaml`.
- The drift engine ignores excluded attributes.

This is a temporary accommodation — the canonical post-decom-
mission state is no AD writes from any source.

## 4. Direction 2: Entra → HR System (Optional)

Some HR systems support attribute write-back from identity
systems (e.g., updating the HR record's `emailAddress` field
when a user's UPN changes). UIAO's posture:

- This is **deployment-specific, not canonical**.
- When tenants choose to enable Entra → HR writeback, the
  middleware MUST emit a dedicated provenance event
  (`provisioning.user.hr-writeback`) with the HR system
  identifier and the attribute(s) written.
- The HR-side write goes through a per-source HR adapter (the
  same adapter that handles HR → middleware ingestion, in its
  outbound direction).
- The default UIAO posture is **HR writeback DISABLED** — HR is
  source-of-truth; cloud should not write back unless agency
  policy explicitly authorizes it.

Reasons UIAO disables by default:

- HR systems are typically the records-of-authority for legal
  / privacy purposes; writeback can violate authority-of-record
  rules.
- HR vendors charge per record-level write API; cost can grow.
- Federation / system-of-record audit requirements may forbid
  bidirectional writes.

When enabled (deployment-specific), the mappings live in the
deployment's `substrate-manifest.yaml`:

```yaml
hr_writeback:
  enabled: false           # default
  source: "entra-id"
  target: "<hr-source-id>" # e.g., "primary"
  attributes:
    - entra: "userPrincipalName"
      hr:    "workEmail"
    - entra: "mail"
      hr:    "workEmail"   # often redundant
    - entra: "businessPhones[0]"
      hr:    "workPhone"
```

## 5. Sunset Path (Post-AD-Decommission)

Once the deployment's AD decommission completes per UIAO_007
sequencing, AD writeback is no longer needed. The path:

1. Verify zero AD-side identity dependencies (per UIAO_007
   exit criteria).
2. Disable cloud → AD writeback in the synchronization job
   configuration (Microsoft Entra portal or Graph API).
3. Continue AD writeback observability for 30 days to confirm
   no missing attributes surface as application failures.
4. Decommission the provisioning agent per D3.3 §9.
5. Remove the writeback section from `substrate-manifest.yaml`
   (the Entra → AD mappings, the agent block, and the gMSA
   block).

After sunset, the only remaining writeback direction is the
optional Entra → HR (if enabled).

## 6. Failure Modes

Writeback-specific failures (delegated to D2.6):

| Failure | `failure_reason` |
|---|---|
| Provisioning agent offline (no AD writeback possible) | `agent-offline` (alert; not record-specific) |
| AD-side write rejected (permissions / schema) | `ad-write-rejected` |
| Conflict — AD-side modification overwritten | logged as `ad-write-overrode-local-edit` (informational) |
| HR writeback API rate-limited | per HR vendor; routes to standard retry/quarantine |
| HR writeback API authentication failure | `hr-auth-failure` (when Entra → HR enabled) |
| Attribute mapping missing in writeback config | `entra-mapping-missing` (per D3.4) |

## 7. Provenance Emission

Each writeback direction emits its own provenance event family:

| Event | Direction | Trigger |
|---|---|---|
| `provisioning.user.ad-writeback` | Entra → AD | Per record writeback success/failure |
| `provisioning.user.ad-writeback.skipped` | Entra → AD | Record passed scope filter but excluded from writeback per attribute-exclusion list |
| `provisioning.user.hr-writeback` | Entra → HR | Per record (only when feature enabled) |

All events conform to the D3.1 §8.2 provenance shape, with the
direction encoded in the event_type and an additional
`writeback_target` field in the source block:

```yaml
source:
  hr_system: <id>
  writeback_target: "active-directory" or "<hr-source-id>"
```

## 8. References

### 8.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-049](../adr/adr-049-microsoft-adapter-coverage-expansion.md)

### 8.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) — coexistence + decommission sequencing.
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 3 → D3.6.

### 8.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) — owns the SCIM emit; HR-writeback adapter direction.
- [Spec2-D3.3](./Spec2-D3.3-ProvisioningAgentDeploymentArchitecture.md) — the agent that performs AD writeback.
- [Spec2-D3.4](./Spec2-D3.4-AttributeMappingEngineConfiguration.md) §4.4 — Entra → AD attribute table.
- [Spec2-D3.7](./Spec2-D3.7-MonitoringAlertingConfiguration.md) — writeback health alerts.
- [Spec2-D3.8](./Spec2-D3.8-DataFlowSecurityAssessment.md) — writeback security posture.
- Spec2-D1.4 — HR → AD attribute mapping matrix (forthcoming).

### 8.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Learn — Microsoft Entra Cloud Sync attribute writeback.
- Microsoft Learn — Group writeback in Cloud Sync.

### 8.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, AU-2 (writeback observability), CM-3 (configuration change control).
