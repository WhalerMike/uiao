# Pipelines — Inventory → DDI → Validate (Stage 2 + Stage 3)

> **Starter skeleton.** A valid, internally consistent CI definition that encodes the right
> stages, contract variables, and guardrails — but you must pin action versions, wire your
> own vCenter/NSX coordinates / backend / Vault, and supply model-dependent inputs (OVA,
> appliance model) before production use.

| File | Platform | Auth |
|---|---|---|
| `github-actions-vmware-ddi.yml` | GitHub Actions | vCenter/NSX/Infoblox **username + password** from GitHub secrets (ideally fronted by HashiCorp Vault). **No cloud OIDC** — see below. |
| `aria-automation-ipam-vmware.md` | (doc) | How the Infoblox IPAM plug-in for VMware Aria Automation does provisioning-time allocation. |

## The honest auth difference (no cloud OIDC)

The hyperscaler packages authenticate CI to the cloud with **OIDC / workload-identity
federation** — the runner trades a short-lived OIDC token for a cloud access token, and no
long-lived secret is stored. **VMware has no such token service.** The `vsphere`, `nsxt`,
and `infoblox` providers authenticate with **username + password**, so those passwords must
be provided as secrets. Handle them well:

- Use **least-privilege service accounts** (a deploy account for TF; a separate **read-only**
  account for CNA discovery, contract §5).
- Front the secrets with **HashiCorp Vault** (the `hashicorp/vault-action` GitHub Action, or
  a self-hosted runner with a Vault agent) so GitHub only ever holds a short-lived token.
- Run on a **self-hosted runner inside the management network** (`runs-on: [self-hosted,
  mgmt-network]`) so credentials and the vCenter/NSX/Grid endpoints never traverse the
  public internet — important for a sovereign / air-gapped VCF.
- **Rotate on the enterprise schedule** and audit their use.

## How this layers on Stage 1

Stage 1 is the **VCF SDDC** (vCenter, NSX-T, SDDC Manager) — built and owned by the platform
team. This pipeline is **Stage 2 + Stage 3** and never builds the SDDC. The first stage
(`inventory`) is a **read-only handoff**: it publishes the SDDC facts Stage 2 consumes as
inputs (contract §2):

```
Stage 1 VCF SDDC (built elsewhere)
   └── facts: vsphere_datacenter, compute_cluster, datastore,
              management_portgroup, tier1 gateway paths
                        │  (read by the inventory stage)
                        ▼
Stage 2 ddi         terraform init/plan/apply of ../terraform
   └── outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                discovery_identity_id, ddi_member_vm_ids
                        │
                        ▼
Stage 3 validate    validation/*.sh — any non-zero exit fails the run
```

## State

Remote state lives on a **shared on-prem backend** — there is no cloud object store here.
Pick one your SDDC already runs (S3-compatible like **MinIO**, an **HTTP** backend,
**Consul**, or **Terraform Enterprise**), add the matching `backend` block in `../terraform`,
and pass its coordinates via `-backend-config` (as the workflow shows). Use state locking.

## Variable / secret wiring

Non-secret config is plain **variables**; **secrets** come from GitHub secrets / Vault and
are never committed. Ports, discovery scopes, and variable names follow `_module-contract.md`.

| Purpose | GitHub Actions |
|---|---|
| vCenter/NSX endpoints + users | vars `VSPHERE_SERVER` / `VSPHERE_USER` / `NSX_MANAGER` / `NSX_USER` |
| vCenter/NSX passwords | secrets `VSPHERE_PASSWORD` / `NSX_PASSWORD` (from Vault) |
| vNIOS admin pw + grid shared secret | secrets `VNIOS_ADMIN_PASSWORD` / `GRID_SHARED_SECRET` |
| Portal join token (universal_ddi) | secret `SAAS_JOIN_TOKEN` |
| Infoblox WAPI creds (validation) | secrets `INFOBLOX_USERNAME` / `INFOBLOX_PASSWORD` |
| TF remote-state backend | vars `TFSTATE_BUCKET` / `TFSTATE_ENDPOINT` |
| SDDC inventory | vars `VSPHERE_DATACENTER` / `COMPUTE_CLUSTER` / `DATASTORE` / `MGMT_PG` |
| DNS test inputs | vars `TEST_FQDN` / `EXPECTED_IP` / `AD_FQDN` |

## Boundary gate (contract §1)

The pipeline carries `DEPLOYMENT_MODEL` (`grid` default) and `ACKNOWLEDGE_SAAS_BOUNDARY`
(`false` default). Before any init/apply, a gate step **hard-fails** if
`deployment_model = universal_ddi` and `acknowledge_saas_boundary != true`, because that path
routes the control plane to the Infoblox Portal SaaS **outside the SDDC boundary** (frequently
disallowed on a sovereign VCF). The Terraform module enforces the same rule; the pipeline
fails fast so the SaaS path is never even planned without an authorization review.

## Promotion flow (dev sandbox → prod)

1. **PR** → plan-only. PRs never apply; the `validate` stage is skipped. Review the plan.
2. **dev sandbox** → `workflow_dispatch` with `apply=true`, `environment=dev`. Apply + full
   validation against a sandbox vSphere cluster.
3. **test** → same, `environment=test`. Environment protection / approval checks gate entry.
4. **prod** → `environment=prod`; **required reviewers** (GitHub Environments) gate entry.

Each environment uses a distinct state key (`vmware-ddi-<env>.tfstate`) so promotions are
isolated.

## Runner tooling

The `validate` stage needs `dig` (dnsutils), `jq`, and `curl`, and — because it runs on a
self-hosted mgmt-network runner — network reachability to the DDI VIP, the Grid Master WAPI,
and (for `universal_ddi`) `csp.infoblox.com`.
