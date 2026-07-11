# Pipelines — LZ → DDI → Validate (Stage 2 + Stage 3)

> **Starter skeleton.** A valid, internally consistent CI definition plus an OCI
> Resource Manager note that encode the right stages, contract variables, and
> guardrails — but you must pin action versions, wire your own compartments /
> backend / Vault, and supply region-dependent inputs (shape, imported image OCID)
> before production use.

Two ways to run the **same Terraform module**:

| File | Runner | OCI auth |
|---|---|---|
| `github-actions-oci-ddi.yml` | GitHub Actions | **OCI API-key config assembled from GitHub secrets** (OCI's OIDC-to-GitHub is limited — see the honest note below) |
| `resource-manager-oci-ddi.md` | OCI Resource Manager (managed Terraform) | **Resource principal, injected automatically — no key in CI** |

Both run **commercial OCI (the OC1 realm, `*.oraclecloud.com`)** — **not** OCI
Government (OC2/OC3) or National-Security realms.

## Auth — candid on OCI vs. Azure

The Azure package uses **OIDC federated credentials** (`azure/login`) so no client
secret is stored. **OCI's OIDC federation to GitHub Actions is limited**, so
`github-actions-oci-ddi.yml` assembles an **OCI API-key config from GitHub secrets**
(`OCI_CLI_USER/TENANCY/FINGERPRINT/KEY_CONTENT/REGION`) — an honest compromise,
commented as such in the workflow. The **cleaner native option is OCI Resource
Manager**, which runs the stack *inside* OCI under a resource principal and needs no
key in CI — the preferred path for a FedRAMP-Moderate posture. See
[`resource-manager-oci-ddi.md`](./resource-manager-oci-ddi.md).

## How this layers on Stage 1

Stage 1 is the **OCI CIS Landing Zone** (compartments, IAM, logging, the hub VCN +
DRG) — typically its **own** stack/pipeline owned by the platform team. These
pipelines are **Stage 2 + Stage 3** and never build the landing zone. The first
stage (`lz`) is a **read-only handoff**: it consumes Stage 1's outputs and passes
them as inputs to the DDI module (contract §2):

```
Stage 1 CIS Landing Zone (separate stack/pipeline)
   └── outputs: hub_vcn_ocid, network_compartment_ocid, drg_ocid,
                vault_ocid, hub_resolver_ocid
                        │  (remote state / stack outputs read by the lz stage)
                        ▼
Stage 2 ddi         terraform init/plan/apply of ../terraform
   └── outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                discovery_identity_id, ddi_subnet_id
                        │
                        ▼
Stage 3 validate    validation/*.sh — any non-zero exit fails the run
```

## Variable / secret wiring

Non-secret config is plain variables; **secrets come from OCI Vault** and are never
committed. Ports, IAM scopes, and variable names follow `_module-contract.md`.

| Purpose | GitHub Actions |
|---|---|
| OCI identity | secrets `OCI_CLI_USER/TENANCY/FINGERPRINT/KEY_CONTENT/REGION` |
| TF remote-state backend | secrets `TF_BACKEND_ACCESS_KEY/SECRET_KEY`; vars `STATE_BUCKET/STATE_NAMESPACE` |
| Stage 1 state location | vars `LZ_STATE_BUCKET` / `LZ_STATE_KEY` |
| Vault | var `VAULT_OCID`; secret OCIDs via vars |
| Infoblox WAPI creds | OCI Vault secret OCIDs `IB_USER_SECRET_OCID` / `IB_PASS_SECRET_OCID` |
| Infoblox CSP token (universal_ddi) | OCI Vault secret OCID |
| DNS test inputs | vars `TEST_FQDN` / `EXPECTED_IP` / `OCI_FQDN` |

## Boundary gate (contract §1)

The pipeline carries `DEPLOYMENT_MODEL` (`grid` default) and
`ACKNOWLEDGE_SAAS_BOUNDARY` (`false` default). Before any init/apply, a gate step
**hard-fails** if `deployment_model = universal_ddi` and
`acknowledge_saas_boundary != true`, because that path routes the control plane to
the Infoblox Portal SaaS **outside the ATO boundary**. The Terraform module enforces
the same rule; the pipeline fails fast so the SaaS path is never even planned without
an authorization review.

## Promotion flow (dev sandbox → prod)

1. **PR** → plan-only. PRs never apply; `validate` is skipped (nothing deployed).
2. **dev sandbox** → `workflow_dispatch` with `apply=true`, `environment=dev`. Apply
   + full validation against a sandbox landing zone.
3. **test** → same, `environment=test`. Environment protection / approval gates entry.
4. **prod** → `environment=prod`; **required reviewers** provide the human gate. Keep
   prod behind explicit approval.

Each environment uses a distinct state key (`ddi-<env>.tfstate`) so promotions are
isolated.

## Runner tooling

The `validate` stage installs `dnsutils` (`dig`), `jq`, and `curl`. Runners need
network reachability to the DDI anycast VIP, the Grid Master WAPI, and (for
`universal_ddi`) `csp.infoblox.com`.
