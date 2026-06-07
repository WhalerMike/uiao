# UIAO Azure SaaS deployment

> Deployment surface for running UIAO as a **multi-tenant SaaS on Azure
> Container Apps** (ADR-096). This sits alongside `deploy/windows-server/`
> (the single-tenant IIS surface) — it does not replace it.

## Why Container Apps

The SaaS plane is the "behind-the-scenes" governance runtime: it acquires
**per-tenant Microsoft Graph and Azure Resource Manager tokens** to run
governance passes on each customer's directory. Azure Container Apps is the
best fit because:

- Each app gets a **user-assigned managed identity** — the governance
  principal `uiao.api.auth.entra_token` / `uiao.adapters.graph_transport`
  /`arm_transport` already expect for token acquisition. No secrets on disk.
- **Scale-to-zero + KEDA** for bursty, scheduled governance passes.
- Managed **ingress + TLS** and **revision-based** blue/green.
- Lighter to operate than AKS, more elastic than App Service.

## Architecture

```
            Entra ID (customer tenants, admin-consented)
                         │  inbound JWT (tid claim)
                         ▼
        ┌───────────────────────────────────────────┐
        │  Container App: uiao.saas.asgi:app          │
        │   • TenantResolutionMiddleware (data plane) │
        │   • /control/v1 control plane (onboarding)  │
        │   • managed identity → Graph / ARM tokens   │
        └───────────────────────────────────────────┘
             │              │                │
       PostgreSQL       Key Vault        Blob Storage
   (tenant registry)  (per-tenant     (evidence bundles)
                        secrets)
```

## Components (Bicep)

`bicep/main.bicep` orchestrates these modules (under `bicep/modules/`):

| Module | Resource | Role |
|---|---|---|
| `monitoring.bicep` | Log Analytics + App Insights | Telemetry sink |
| `identity.bicep` | User-assigned managed identity | Governance principal |
| `registry.bicep` | Azure Container Registry (+AcrPull) | Image store |
| `keyvault.bicep` | Key Vault (RBAC, +Secrets User) | Per-tenant secrets |
| `postgres.bicep` | PostgreSQL Flexible Server | Tenant registry + state |
| `storage.bicep` | Storage account + `evidence` container | Evidence bundles |
| `containerapp-env.bicep` | Container Apps managed environment | Runtime env |
| `containerapp.bicep` | The SaaS Container App | Data + control plane |

## Configuration

The container reads `UIAO_SAAS_*` env vars (see
`src/uiao/saas/settings.py`), plus the Azure SDK's `AZURE_CLIENT_ID` for
managed-identity selection. The Bicep wires these from module outputs and
secrets; the relevant ones:

| Variable | Source |
|---|---|
| `UIAO_SAAS_DATABASE_URL` | Container Apps secret (DSN with password) |
| `UIAO_SAAS_APP_CLIENT_ID` | Multi-tenant app registration |
| `UIAO_SAAS_PUBLISHER_TENANT_ID` | Home tenant |
| `UIAO_SAAS_API_AUDIENCE` | API app ID URI (e.g. `api://uiao`) |
| `UIAO_SAAS_KEY_VAULT_URI` | Key Vault module output |
| `UIAO_SAAS_STORAGE_ACCOUNT_URL` | Storage module output |
| `UIAO_SAAS_STAMP_EXECUTION_ENABLED` | `true` to execute per-tenant stamps (default off = dry-run) |
| `AZURE_CLIENT_ID` | Managed identity client id (Graph/ARM tokens) |

## Deploy

The CI workflow `.github/workflows/azure-saas-deploy.yml` is **manual-
dispatch only** (segregated until launch). To deploy by hand:

```bash
# 1. Stamp infrastructure (creates ACR, Postgres, Key Vault, etc.)
az deployment group create -g <rg> \
  -f deploy/azure/bicep/main.bicep \
  -p deploy/azure/bicep/main.bicepparam \
  -p pgAdminPassword="$PG_PWD"

# 2. Build & push the image
az acr build --registry <acr> --image uiao-saas:latest \
  --file deploy/azure/Dockerfile .

# 3. Re-deploy pointing at the pushed image
az deployment group create -g <rg> \
  -f deploy/azure/bicep/main.bicep \
  -p deploy/azure/bicep/main.bicepparam \
  -p containerImage="<acr>.azurecr.io/uiao-saas:latest" \
  -p pgAdminPassword="$PG_PWD"
```

## Multi-tenant onboarding

1. A customer admin visits the admin-consent URL (returned by
   `POST /control/v1/tenants`) and grants the UIAO multi-tenant app the
   Graph / ARM application permissions.
2. The control plane records the tenant (`pending → active`) and stamps the
   per-tenant resources (DB schema, Blob container, Key Vault scope). With
   `UIAO_SAAS_STAMP_EXECUTION_ENABLED=true` the `AzureStampExecutor`
   (`uiao.saas.azure_stamp`, constructed via `build_stamp_executor()` in
   `uiao.saas.azure_provisioners`) executes the stamp against Azure; by
   default the `NoOpStampExecutor` plans it without executing.
3. Inbound requests carrying that tenant's token are resolved by
   `TenantResolutionMiddleware` and bound to a per-request tenant context.

## Local development

```bash
pip install -e ".[saas]"
export UIAO_SAAS_INSECURE_ALLOW_UNSIGNED_TOKENS=true   # dev ONLY
export UIAO_SAAS_API_AUDIENCE=api://uiao
export UIAO_SAAS_PUBLISHER_TENANT_ID=<your-tenant-guid>
uvicorn uiao.saas.asgi:app --reload
```

Without `UIAO_SAAS_DATABASE_URL` the runtime uses the in-memory tenant
registry (not durable). See `tests/test_saas_app.py` for the full
onboarding → lifecycle flow exercised against the in-memory store.

## Sovereign clouds

`UIAO_SAAS_CLOUD` selects `commercial` (also GCC-Moderate per ADR-033),
`gcc-high`, or `dod`. This drives the Entra login authority, the issuer
template inbound tokens are validated against, and the Graph/ARM audiences
the managed identity requests — consistent with the adapter cloud-resolution
convention in `AGENTS.md`.
