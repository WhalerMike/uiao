# ServiceNow Orchestration — AWS DDI Package

> **What this is.** The AWS-specific wiring that puts a governed, self-service
> **ServiceNow** front door on this package's Terraform module and validation
> scripts. It is the AWS instance of the volume-level pattern in
> [`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md) —
> read that chapter first for the three-systems loop, the certified pieces (CPG
> Terraform Connector, Service Graph Connector for Infoblox, IntegrationHub REST,
> MID Server), and the GCC-Moderate control-family mapping. This file maps those
> pieces onto the **exact variables, scripts, and CMDB objects** of
> `aws-lz-automation/`.
>
> **Starter skeleton — labeled as such**, consistent with the rest of this
> package ([`../_module-contract.md`](../_module-contract.md) §9). It encodes the
> right structure and mappings; it is not a certified ServiceNow application.

## Companion files in this folder

| File | What it is |
|---|---|
| `ServiceNow-Orchestration.md` (this file) | AWS catalog→tfvars mapping, Flow Designer flow, CMDB mapping, GCC-Moderate notes. |
| [`integrationhub-actions.md`](./integrationhub-actions.md) | The Infoblox WAPI / Universal DDI REST bodies (allocate-next-IP, create A/PTR, delete-on-reclaim). |
| [`midserver-validate.sh`](./midserver-validate.sh) | MID Server wrapper that runs the three [`../validation/`](../validation/) scripts and emits one JSON gate result. |

---

## 1. Catalog item → `tfvars` mapping

The **CPG Terraform Connector** ingests [`../terraform`](../terraform/) as a catalog
item; each catalog input variable below writes the correspondingly-named Terraform
variable in the generated `*.tfvars`. Names are the **exact** module inputs from
[`../terraform/variables.tf`](../terraform/variables.tf) — do not rename them in the
catalog, or the Connector's variable binding breaks.

| Catalog field (label) | Terraform variable (`tfvars`) | Type | Notes / default |
|---|---|---|---|
| Resource name prefix | `name_prefix` | string | `ddi`; drives `ddi-sg`, `ddi-vnios-use1a`, `ddi-disco-role`. |
| AWS region | `region` | string | Commercial partition only; catalog choice list must **exclude `us-gov-*`** (module hard-fails on it). |
| Environment | `environment` | string | `dev` / `test` / `prod` choice list. |
| Control-plane model | `deployment_model` | string | `grid` (default) / `universal_ddi`. Selecting `universal_ddi` reveals the acknowledgement field below. |
| Acknowledge SaaS boundary | `acknowledge_saas_boundary` | bool | Must be `true` to allow `universal_ddi`; ties to the SoD/authorization approval (§2). Default `false`. |
| Compliance profile | `compliance_profile` | string | `gcc-moderate` (default). |
| Network account ID | `network_account_id` | string | Stage-1 output; 12-digit. **Hub-VPC equivalent of Azure's `hub_resource_group`** owner. |
| Hub VPC ID | `hub_vpc_id` | string | Stage-1 output (`vpc-…`). The DDI subnets are created inside this **hub VPC** — the AWS analog of the Azure hub resource group / hub VNet. |
| Transit Gateway ID | `transit_gateway_id` | string | Stage-1 output (`tgw-…`); spokes/on-prem route here (hub-and-spoke equivalent). |
| DDI subnet CIDRs (per AZ) | `ddi_subnet_cidrs` | list(string) | One CIDR per AZ; the AWS analog of Azure's `ddi_subnet_address_prefix`. Must fit the hub VPC CIDR. |
| Member count | `member_count` | number | `2` default; ≥2 for HA. |
| Availability Zones | `availability_zones` | list(string) | Length must equal `ddi_subnet_cidrs`. |
| vNIOS instance type | `vnios_instance_type` | string | No default — region/NIOS-version-dependent (M7i/R7i for 9.0.5+). |
| vNIOS AMI ID | `vnios_ami_id` | string | `ami-…`; **never invented** — from `aws ec2 describe-images`. |
| Secrets store | `secrets_store_type` | string | `secrets_manager` (default) / `ssm_parameter_store`. |
| Discovery identity type | `discovery_identity_type` | string | `iam_role` (cross-account, preferred) / `instance_profile`. |
| Spoke VPC IDs | `spoke_vpc_ids` | list(string) | Optional; DHCP option-set write targets. |
| Extra tags | `tags` | map(string) | Merged with module-managed tags. |

**Security-group source CIDR fields** (contract §4 forbids `0.0.0.0/0`; the catalog
UI must validate this before submit):

| Catalog field | Terraform variable | Notes |
|---|---|---|
| Management source CIDRs | `mgmt_source_cidrs` | 443/tcp (and 22 if SSH). Non-empty, no `0.0.0.0/0`. |
| DNS client CIDRs | `dns_client_cidrs` | 53 tcp+udp from spokes/on-prem. Non-empty, no `0.0.0.0/0`. |
| Grid peer CIDRs | `grid_peer_cidrs` | 1194/udp + 2114/tcp; required when `deployment_model=grid`. |
| Monitoring source CIDRs | `monitoring_source_cidrs` | 161/udp when `enable_snmp`. |
| Enable SSH / SNMP / DHCP | `enable_ssh` · `enable_snmp` · `enable_dhcp` | Booleans, all off by default. |

**Secret-name fields** — these are **names/paths, not secret values**. The actual
secrets live in **AWS Secrets Manager** (or SSM Parameter Store per
`secrets_store_type`); the MID Server resolves them at run time. Never put a secret
value in a catalog field.

| Catalog field | Terraform variable | Default name/path |
|---|---|---|
| Admin password secret | `admin_password_secret_name` | `ddi/vnios-admin-password` |
| Temp license secret | `temp_license_secret_name` | `ddi/vnios-temp-license` |
| Grid shared secret | `grid_shared_secret_name` | `ddi/grid-shared-secret` (grid) |
| Portal join-token secret | `saas_join_token_secret_name` | `ddi/uddi-join-token` (universal_ddi) |

**Cross-account discovery fields** (contract §5 — the AWS→Infoblox IPAM sync identity):

| Catalog field | Terraform variable | Notes |
|---|---|---|
| Discovered account IDs | `discovered_account_ids` | AWS accounts to discover; role is replicated into each. |
| Discovery integration account | `discovery_integration_account_id` | Account trusted to `sts:AssumeRole` the discovery role (`iam_role` mode). |
| Discovery ExternalId | `discovery_external_id` | `sensitive` — treat as a secret; confused-deputy protection. |
| Enable Route 53 record read | `enable_record_read` | Opt-in Route 53 zone sync. |
| Existing instance-profile role ARN | `existing_instance_profile_role_arn` | `instance_profile` mode only. |

**Grid / DNS-integration fields** (`deployment_model=grid` and DNS wiring):
`grid_name`, `grid_master_vip`, `r53_resolver_inbound_ip`,
`aws_service_forward_domains`, `ddi_anycast_vip`, `enable_spoke_dns_write`,
`enable_source_dest_check`, `ssh_key_name`, `infoblox_portal_url` — surface these as
**advanced/optional** catalog fields with the module defaults pre-filled.

---

## 2. Flow Designer flow

![ServiceNow closed loop for the AWS DDI module: a Service Catalog subnet request passes a Flow Designer approval and separation-of-duties gate, the CPG Terraform Connector plans and applies ../terraform on an in-boundary MID Server, IntegrationHub REST calls allocate the next-available IP and create A/PTR records in Infoblox, the MID Server validation gate runs the three ../validation scripts, and on pass the Service Graph Connector syncs the networks into the CMDB and the change closes — a failed validation gate returns to approval](../figs/aws-sn-01-catalog-flow.png)

The numbered flow (matches the figure left-to-right; the FAIL branch is the closed
loop back to approval):

1. **Intake.** Requester submits the Service Catalog item; fields map to `tfvars`
   per §1. A Record Producer creates the request (`REQ`/`RITM`) and captures the
   requested `region`, `ddi_subnet_cidrs`, `deployment_model`, and SG source CIDRs.
2. **Approval + SoD gate.** Flow Designer approval. The requester cannot self-approve
   (separation of duties → AC-5/AC-6). If `deployment_model = universal_ddi`, require
   the **additional SaaS-boundary/authorization approval** that backs
   `acknowledge_saas_boundary = true` before the flow may continue.
3. **CPG Terraform apply.** The **CPG Terraform Connector** runs a **speculative plan**
   of [`../terraform`](../terraform/) on the in-boundary **MID Server**, posts the plan
   summary to work-notes, and — after the plan is approved — runs `apply`. This creates
   the DDI subnets, vNIOS/NIOS-X members, security groups, and discovery role.
4. **IntegrationHub IPAM calls.** IntegrationHub REST steps call Infoblox to
   **allocate the next-available IP** and **create the A + PTR** records for the
   requested host(s) — WAPI (grid) or CSP (universal_ddi). Bodies are in
   [`integrationhub-actions.md`](./integrationhub-actions.md). The returned `_ref`/`id`
   handles are stored on the request for Day-2 reclaim.
5. **MID Server validation gate.** The MID Server runs
   [`midserver-validate.sh`](./midserver-validate.sh), which executes the three
   [`../validation/`](../validation/) scripts (`dns-validation.sh`,
   `discovery-sync-check.sh`, `ipam-conflict-check.sh`) and returns one JSON result.
   **`overall != "pass"` fails the change**, posts the failing check(s) to work-notes,
   and **routes back to step 2** (the dashed FAIL edge in the figure) — nothing is
   recorded as good until the gates pass.
6. **Service Graph Connector CMDB sync.** On pass, the **Service Graph Connector for
   Infoblox** reconciles the new/updated networks and addresses into the CMDB (§4), so
   ServiceNow reflects IPAM reality rather than the request's intent.
7. **Close.** The change closes with the full audit trail — plan, approvals,
   validation JSON, and CMDB deltas attached (AU-2/AU-6/AU-12, CM-3/CM-5).

A **retirement** catalog item runs the mirror: `terraform destroy` +
delete-on-reclaim REST (allocate's inverse) + a CMDB retire.

---

## 3. IntegrationHub REST summary

The active IPAM/DNS calls are defined in full (method / path / JSON) in
[`integrationhub-actions.md`](./integrationhub-actions.md). In brief:

| Flow step | Action | NIOS / WAPI object | Universal DDI (CSP) |
|---|---|---|---|
| Allocate | next-available IP | `record:a` with `func:nextavailableip:$NETWORK` / `network` `next_available_ip` | `ipam/address` `next_available_id` |
| Register | create A + PTR | `record:a`, `record:ptr` | `dns/record` type `A`, `PTR` |
| Reclaim | delete on retire | `DELETE <ref>` (A, PTR, fixedaddress) | `DELETE dns/record/$ID`, `ipam/address/$ID` |

Credentials (WAPI basic-auth / CSP token) are resolved from **AWS Secrets Manager**
by the MID Server via the IntegrationHub connection alias — never stored in the flow.

---

## 4. Service Graph Connector — CMDB mapping

The **Service Graph Connector for Infoblox** imports IPAM into the CMDB so IPAM stays
the source of truth. The AWS-relevant classes:

| Infoblox object | CMDB class | Key fields (from this module) |
|---|---|---|
| Network container / supernet | `cmdb_ci_ip_network` | `subnet` (CIDR), `network_view`, description, extensible attributes. |
| `network` (a `ddi_subnet_cidrs` entry / discovered VPC subnet) | `cmdb_ci_ip_network_subnet` | `subnet` (CIDR), `netmask`, `network_view`, parent `cmdb_ci_ip_network`. |
| Allocated address (A/PTR host) | `cmdb_ci_ip_address` | `ip_address`, `fqdn`, related to its `cmdb_ci_ip_network_subnet`. |

Map the module's identifying data onto these CIs:

- `ddi_subnet_cidrs` entries and cloud-discovered VPC/subnet CIDRs → the `subnet`
  field on `cmdb_ci_ip_network_subnet`; the parent VPC/supernet → `cmdb_ip_network`.
- Infoblox **extensible attributes** written during allocation (`Source=ServiceNow`,
  `aws_account_id`, `aws_region` — see [`integrationhub-actions.md`](./integrationhub-actions.md))
  → CMDB attributes / correlation IDs, so a CI reconciles back to the AWS account,
  region, and originating `REQ`.
- Reconciliation runs on the Service Graph Connector's schedule; the flow's post-apply
  sync (step 6) triggers it on demand so the change closes against fresh CMDB data.

---

## 5. GCC-Moderate notes

Consistent with [`../_module-contract.md`](../_module-contract.md) §1 and the volume
chapter [`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md) §7.4:

- **MID Server stays in-boundary.** Terraform runs, IntegrationHub REST callouts, and
  the [`midserver-validate.sh`](./midserver-validate.sh) gate all execute on a MID
  Server **inside the account / ATO boundary** — the execution and credential path
  never leaves the boundary. Use a **FedRAMP-authorized ServiceNow (GovCloud) instance**.
- **Secrets in AWS Secrets Manager / SSM.** All credentials (vNIOS admin password,
  temp license, Grid shared secret, WAPI creds, CSP token) live in **AWS Secrets
  Manager** or **SSM Parameter Store** (`secrets_store_type`) and are resolved by the
  MID Server at run time. Never place a secret value in a catalog field, in `tfvars`,
  or in Terraform state.
- **AWS GovCloud is out of scope here.** This package targets the **commercial AWS
  partition (`.com` endpoints)** running a GCC-Moderate posture — the `region` variable
  hard-fails on `us-gov-*`. (vNIOS, multi-account vDiscovery from NIOS 9.0.4+, and
  Route 53 integration do run in AWS GovCloud, but that partition is not automated by
  this deliverable.)
- **Universal DDI SaaS caveat still holds.** The `grid` model keeps every DDI call
  in-boundary (MID Server → Grid Master over WAPI). The `universal_ddi` model reaches
  the Infoblox Portal (CSP) **outside** the boundary and is gated by
  `acknowledge_saas_boundary = true`, which the flow ties to the extra SaaS
  authorization approval in step 2.
- **Control-family evidence:** approval + SoD → **AC-5/AC-6**; change record + audit
  trail → **AU-2/AU-6/AU-12**, **CM-3/CM-5**; validation gates → **CM-6**;
  reclaim-on-delete → **CM-8**.
