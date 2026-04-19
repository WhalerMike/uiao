---
document_id: DM_020
title: "PKI / Certificate Services Adapter Interface"
version: "0.1-draft"
status: DRAFT
owner: "Michael Stratton"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
core_concepts: ["#5 Certificate-anchored overlay"]
priority: CRITICAL
risk: "Silent auth failure weeks post-migration"
---

# PKI / Certificate Services Adapter Interface

**Priority:** CRITICAL | **Risk:** Silent auth failure weeks post-migration

## Registered Implementations

| Adapter | Use Case |
|---|---|
| adcs/ | On-premises ADCS migration source |
| digicert/ | Enterprise CA replacement |
| entrust/ | Enterprise CA replacement |
| entra-cert/ | Entra ID Certificate-Based Authentication (CBA) |

## Required Capabilities

- Full certificate inventory: issued, pending, revoked, expired
- Certificate-to-identity binding (who owns each cert)
- Expiry timeline export — identify certs expiring within 90/180/365 days
- CA hierarchy mapping — root CA, issuing CA, subordinate CA chain
- Template inventory — what certificate templates exist and who uses them
- Smart card / PIV / CAC certificate inventory (federal critical)
- CRL and OCSP endpoint migration path
- Auto-enrollment policy migration (Group Policy → Intune/SCEP)
- Side-by-side operation during CA transition window

## Migration Sequence

1. Inventory all issued certificates and expiry dates
2. Map certificates to identity objects in governance model
3. Establish replacement CA before any AD retirement begins
4. Migrate auto-enrollment to Intune/SCEP/EST
5. Validate certificate chain resolves through new CA
6. Retire ADCS only after all cert renewals confirmed through new CA
