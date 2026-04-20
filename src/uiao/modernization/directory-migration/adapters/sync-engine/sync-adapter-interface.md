---
document_id: DM_050
title: "Sync Engine Adapter Interface"
version: "0.1-draft"
status: DRAFT
owner: "Michael Stratton"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
core_concepts: ["#1 SSOT"]
priority: HIGH
risk: "Permanent AD dependency if sync engine lifecycle is unmanaged"
---

# Sync Engine Adapter Interface

**Priority:** HIGH | **Risk:** Permanent AD dependency if sync engine lifecycle is unmanaged

## Registered Implementations

| Adapter | Use Case |
|---|---|
| entra-connect/ | Microsoft Entra Connect v2 |
| entra-cloud-sync/ | Microsoft Entra Cloud Sync (lightweight agent) |

## Required Capabilities

- Sync scope inventory: what objects and attributes are being synchronized
- Attribute flow rules: what transformations are applied
- Filtering rules: what is excluded from sync
- Service account inventory for sync engine
- Sync error inventory: objects failing to sync and why
- Password hash sync / pass-through auth / federation status
- Staged rollout configuration
- Sync engine retirement readiness assessment

## Retirement Readiness Criteria

The sync engine may be retired only when ALL of the following are true:

- [ ] All user objects fully provisioned in Entra ID from authoritative HR source
- [ ] All group memberships migrated to dynamic groups or Entra-managed groups
- [ ] All applications migrated away from on-prem AD authentication
- [ ] All device objects managed by Intune with no AD dependency
- [ ] All service accounts migrated to Entra service principals
- [ ] All LDAP-dependent applications confirmed operational against Entra
- [ ] ADCS replaced by cloud or standalone PKI
- [ ] DNS migrated to standalone IPAM (InfoBlox / BlueCat)
- [ ] RADIUS migrated to Entra-backed RADIUS solution
