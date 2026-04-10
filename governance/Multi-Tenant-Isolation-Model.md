# UIAO Multi-Tenant Isolation Model

## Isolation Dimensions

- **Data Isolation**
  - Per-tenant namespaces in data lake
  - Per-tenant evidence graphs
  - Tenant-scoped encryption keys
- **Execution Isolation**
  - Per-tenant job queues
  - Per-tenant SCuBA runs
  - No cross-tenant process reuse for privileged actions
- **Access Isolation**
  - Tenant claims in JWT
  - All queries filtered by tenant_id
  - Auditor API is tenant-scoped

## Models

- **Single-Tenant Deployment**
  - One UIAO instance per customer
- **Multi-Tenant Deployment**
  - Shared control plane
  - Strict tenant boundaries in:
    - Storage
    - Identity
    - Logs
