# Pipelines — ALZ → DDI → Validate (Stage 2 + Stage 3)

> **Starter skeleton.** Valid, internally consistent CI definitions that encode
> the right stages, contract variables, and guardrails — but you must pin action
> / task versions, wire your own subscriptions / backend / Key Vault, and supply
> region-dependent inputs (VM SKU, Marketplace image) before production use.

Two equivalent pipelines:

| File | Platform | Azure auth |
|---|---|---|
| `github-actions-alz-ddi.yml` | GitHub Actions | `azure/login@v2` **OIDC federated credential** (no stored secret) |
| `azure-pipelines-alz-ddi.yml` | Azure DevOps | ARM service connection using **workload-identity federation** (no stored secret) |

Both run **commercial Azure `.com`** (`login.microsoftonline.com` /
`management.azure.com`) — **not** Government `.us`.

## How this layers on Stage 1

Stage 1 is the **Microsoft ALZ Accelerator** (management groups, identity,
governance, the Connectivity hub) — typically its **own** pipeline owned by the
platform team. These pipelines are **Stage 2 + Stage 3** and never build the
landing zone. The first stage (`alz` / `ALZ`) is a **read-only handoff**: it
consumes Stage 1's remote-state outputs and passes them as inputs to the DDI
module (contract §2):

```
Stage 1 ALZ Accelerator (separate pipeline)
   └── outputs: hub_vnet_id, hub_resource_group_name,
                connectivity_subscription_id, log_analytics_workspace_id
                        │  (remote state read by the alz/ALZ stage)
                        ▼
Stage 2 ddi/DDI     terraform init/plan/apply of ../terraform (or ../bicep)
   └── outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                discovery_identity_id, ddi_subnet_id
                        │
                        ▼
Stage 3 validate/Validate   validation/*.sh — any non-zero exit fails the run
```

Choose **one** IaC path per environment — Terraform (`../terraform`) **or**
Bicep (`../bicep`). The DDI stage runs Terraform and logs the equivalent Bicep
`az deployment` command as a parallel note; do not run both against one state.

## OIDC / workload-identity setup (no stored secrets)

### GitHub Actions
1. Create an Azure **app registration** (or user-assigned managed identity) and
   add a **federated credential** for the repo/branch/environment
   (subject e.g. `repo:<org>/<repo>:environment:prod`, audience
   `api://AzureADTokenExchange`).
2. Grant it least-privilege RBAC on the target scope (deploy the DDI subnet /
   resources; read Stage 1 state storage). Follow contract §5 for the
   *discovery* identity — that is a separate, even-less-privileged identity.
3. Store `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` as
   **secrets** (they are identifiers, not credentials — the actual token is
   fetched via OIDC). The job sets `permissions: id-token: write`.

### Azure DevOps
1. Create an **Azure Resource Manager service connection** using
   **"Workload Identity federation (automatic)"** — ADO provisions the
   federated credential for you. Name it to match `azureServiceConnection`
   (`sc-alz-ddi-wif`).
2. Bind ADO **Environments** (`dev`/`test`/`prod`) with approval checks.
3. Grant the connection's identity the same least-privilege RBAC as above.

## Variable / secret wiring

Non-secret config is plain variables; **secrets come from Azure Key Vault** and
are never committed. Ports, IAM scopes, and variable names follow
`_module-contract.md`.

| Purpose | GitHub Actions | Azure DevOps |
|---|---|---|
| Azure identity IDs | secrets `AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID` | ARM service connection |
| TF remote-state backend | vars `TFSTATE_RG/SA/CONTAINER` | vars `TFSTATE_RG/SA/CONTAINER` |
| Stage 1 state location | vars `ALZ_STATE_*` | vars `ALZ_STATE_*` |
| Key Vault | vars `KEY_VAULT_NAME` / `KEY_VAULT_ID` | vars + `AzureKeyVault@2` |
| Infoblox WAPI creds | Key Vault `infoblox-wapi-username/password` | variable group `alz-ddi-secrets` (KV-linked) |
| Infoblox CSP token (universal_ddi) | Key Vault `infoblox-csp-token` | KV `infoblox-csp-token` |
| DNS test inputs | vars `TEST_FQDN` / `EXPECTED_IP` / `PRIVATELINK_FQDN` | pipeline vars |

## Boundary gate (contract §1)

Both pipelines carry a `deployment_model` (`grid` default) and
`acknowledge_saas_boundary` (`false` default). Before any init/apply, a gate
step **hard-fails** if `deployment_model = universal_ddi` and
`acknowledge_saas_boundary != true`, because that path routes the control plane
to the Infoblox Portal SaaS **outside the ATO boundary**. The Terraform module
enforces the same rule; the pipeline fails fast so the SaaS path is never even
planned without an authorization review.

## Promotion flow (dev sandbox → prod)

1. **PR** → plan-only. PRs never apply; the `validate` stage is skipped (nothing
   deployed). Review the plan.
2. **dev sandbox** → `workflow_dispatch` (GitHub) / run with `apply=true`
   (ADO), `environment=dev`. Apply + full validation against a sandbox ALZ.
3. **test** → same, `environment=test`. Environment protection / approval
   checks gate entry.
4. **prod** → `environment=prod`; **required reviewers** (GitHub Environments)
   / **approval checks** (ADO Environments) provide the human gate. Merge to
   `main` can auto-apply to the configured default environment; keep prod behind
   explicit approval.

Each environment uses a distinct state key (`ddi-<env>.tfstate`) so promotions
are isolated.

## Runner tooling

The `validate` stage installs `dnsutils` (`dig`), `jq`, and `curl`. Runners
need network reachability to the DDI anycast VIP, the Grid Master WAPI, and (for
`universal_ddi`) `csp.infoblox.com`.
