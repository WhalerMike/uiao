# Terraform — Infoblox DDI on an AWS Landing Zone (Stage 2)

Starter Terraform module that adds an **Infoblox DDI + DNS-security layer** to
the **shared-services (hub) VPC** of an AWS Landing Zone. It is **Stage 2**: it
consumes the network outputs of **AWS Control Tower / the Landing Zone Accelerator
on AWS (Stage 1)** and never creates the organization, accounts, guardrails, or
the hub VPC/Transit Gateway.

> **Read [`../_module-contract.md`](../_module-contract.md) first.** It is the
> single source of truth for variable names, ports, IAM scopes, naming, outputs,
> and the GCC-Moderate boundary rule. This module conforms to it exactly.

## Boundary & compliance posture

Built for a **GCC-Moderate operating posture on the COMMERCIAL AWS partition
(`.com` endpoints)** — **not** AWS GovCloud (`us-gov-*` / `amazonaws-us-gov.com`).
The `aws` provider is left on its default `aws` partition; `variables.tf` rejects
a `us-gov-*` region.

| `deployment_model` | Control plane | GCC-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** the account/ATO boundary | Boundary-clean. Recommended. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443) | **Hard-fails** unless `acknowledge_saas_boundary = true` (points at the FedRAMP/authorization review). |

The hard-fail lives in `main.tf` as a `precondition` on `terraform_data.boundary_guard`.

## What it creates

- Dedicated **DDI subnets** (one per AZ) in the Stage-1 hub VPC, plus a route table
  sending spoke/on-prem CIDRs to the **Transit Gateway**.
- A **Security Group** on the members, exactly per contract §4 (default-deny
  ingress *and* egress; sources scoped to CIDR variables, never `0.0.0.0/0`).
- **`deployment_model = "grid"`** → one `aws_instance` vNIOS member per
  `member_count`, spread across `availability_zones`, each with **two ENIs**
  (ENI0=MGMT, ENI1=LAN1), from the Marketplace **AMI** (`vnios_ami_id`), first-boot
  config via user-data (temp license + admin password + grid-join, from Secrets
  Manager/SSM).
- **`deployment_model = "universal_ddi"`** → lightweight NIOS-X host instances + a
  `null_resource`/local-exec **Portal-enrollment handoff** (the API seam).
- A least-privilege **cross-account IAM discovery role** (ExternalId-gated trust) or
  an instance profile, with a custom read-only policy (contract §5).
- Infoblox **conditional forwarders** for AWS-service names → Route 53 Resolver
  inbound endpoint, and (opt-in) spoke **DHCP option sets** pointing at the DDI VIP
  (contract §8).

## Files

| File | Purpose |
|---|---|
| `versions.tf` | Provider pins (`hashicorp/aws`, `infobloxopen/infoblox`, `null`) + provider blocks. |
| `variables.tf` | Every contract §3 input + supporting inputs, with validation. |
| `main.tf` | Locals, tags (§6), DDI subnets + route table, boundary hard-fail, secret reads. |
| `securitygroups.tf` | Security Group + rules (§4), default-deny in/out, conditional by `deployment_model`. |
| `grid.tf` | vNIOS Grid path (`deployment_model=grid`), multi-ENI members. |
| `universal_ddi.tf` | Universal DDI (SaaS) path + Portal enrollment handoff. |
| `discovery.tf` | Cross-account IAM discovery role + least-priv policy (§5) + vDiscovery placeholder. |
| `dns.tf` | Conditional forwarders + spoke DHCP option sets (§8). |
| `outputs.tf` | Canonical outputs (§7). |
| `examples/hub-integration/` | Realistic call wired to Control Tower / LZA remote state. |

## Inputs (canonical — contract §3)

| Name | Type | Default | Notes |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | Prefix for all resource names. |
| `region` | string | — | AWS region (commercial partition; no `us-gov-*`). |
| `environment` | string | `"prod"` | `dev`/`test`/`prod`. |
| `deployment_model` | string | `"grid"` | `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` for `universal_ddi`. |
| `compliance_profile` | string | `"gcc-moderate"` | Tags + control mapping. |
| `network_account_id` | string | — | Stage-1 output; Network account ID. |
| `hub_vpc_id` | string | — | Stage-1 output; DDI subnets created here. |
| `transit_gateway_id` | string | — | Stage-1 output; DDI subnets route to it. |
| `ddi_subnet_cidrs` | list(string) | — | One DDI subnet CIDR per AZ. |
| `member_count` | number | `2` | vNIOS/NIOS-X hosts; ≥2 for HA. |
| `availability_zones` | list(string) | — | Spread members across zones. |
| `vnios_instance_type` | string | — | Instance type; region/model-dependent — do not hard-code. |
| `vnios_ami_id` | string | — | Marketplace AMI ID — supply your own (`aws ec2 describe-images`). |
| `secrets_store_type` | string | `"secrets_manager"` | `secrets_manager` \| `ssm_parameter_store`. |
| `discovery_identity_type` | string | `"iam_role"` | `iam_role` \| `instance_profile`. |
| `spoke_vpc_ids` | list(string) | `[]` | Spokes whose DHCP option set points at the DDI VIP. |
| `tags` | map(string) | `{}` | Merged under module-managed tags. |

### Supporting inputs (not in §3, required by the implementation)

See `variables.tf` for full descriptions/defaults: `mgmt_source_cidrs`,
`monitoring_source_cidrs`, `dns_client_cidrs`, `grid_peer_cidrs`, `enable_ssh`,
`enable_dhcp` (default **off**), `enable_snmp`, `enable_source_dest_check`,
`r53_resolver_inbound_ip`, `aws_service_forward_domains`, `ddi_anycast_vip`,
`enable_spoke_dns_write`, `discovered_account_ids`,
`discovery_integration_account_id`, `discovery_external_id`, `enable_record_read`,
`existing_instance_profile_role_arn`, the `*_secret_name` set, `grid_name`,
`grid_master_vip`, `infoblox_portal_url`, `ssh_key_name`.

## Outputs (contract §7)

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_identity_id` (IAM role ARN), `ddi_subnet_ids` (list).

## Example invocation

See [`examples/hub-integration/main.tf`](./examples/hub-integration/main.tf) for
the full version. Minimal shape:

```hcl
module "infoblox_ddi" {
  source = "../.." # or your module registry path

  region             = "us-east-1"
  deployment_model   = "grid"        # boundary-clean default
  network_account_id = data.terraform_remote_state.lza.outputs.network_account_id
  hub_vpc_id         = data.terraform_remote_state.lza.outputs.hub_vpc_id
  transit_gateway_id = data.terraform_remote_state.lza.outputs.transit_gateway_id
  ddi_subnet_cidrs   = ["10.10.4.0/27", "10.10.4.32/27"]
  availability_zones = ["us-east-1a", "us-east-1b"]

  vnios_instance_type = "m7i.xlarge"     # confirm per NIOS version/region
  vnios_ami_id        = "ami-0123456789abcdef0" # discover with `aws ec2 describe-images`

  mgmt_source_cidrs = ["10.10.0.0/24"]
  dns_client_cidrs  = ["10.20.0.0/16"]
  grid_peer_cidrs   = ["10.10.4.0/26", "192.168.100.0/24"]
  grid_master_vip   = "192.168.100.10"

  discovery_integration_account_id = "111122223333"
  discovery_external_id            = "supply-a-strong-external-id"
  discovered_account_ids           = ["444455556666"]
}
```

## Stage-1 → Stage-2 wiring

```
Stage 1  Control Tower / LZA  ── outputs ──▶  Stage 2 (this module) ── outputs ──▶ Stage 3 (validation)
   hub_vpc_id                    hub_vpc_id             ddi_anycast_vip
   network_account_id       ──▶  network_account_id    dns_server_ips
   transit_gateway_id            transit_gateway_id     grid_master_ip
   (existing Route 53 Resolver   r53_resolver_inbound_ip discovery_identity_id
    inbound endpoint IP)                                 ddi_subnet_ids
```

Consume Stage-1 outputs via `terraform_remote_state` (shown in the example), SSM
parameters, or plain variables/tfvars. Feed `dns_server_ips` / `ddi_anycast_vip`
into Stage-3 validation (resolve a record, confirm discovery sync, conflict check).

## Before you deploy

- **Verify provider versions** in `versions.tf` against the registry.
- **Subscribe to the Infoblox NIOS Marketplace listing** and **discover the AMI**
  (`aws ec2 describe-images`); never invent an AMI ID or instance type.
- **Pre-create the secrets** named by the `*_secret_name` variables in Secrets
  Manager or SSM Parameter Store (per `secrets_store_type`).
- **Scope every CIDR** — the module refuses `0.0.0.0/0` on management/client sources.
- For `universal_ddi`, complete the authorization review and set
  `acknowledge_saas_boundary = true`.

---

> ## ⚠️ Starter skeleton — not a certified production module
>
> This is a **coherent starter skeleton**, explicitly labeled as such. It encodes
> the right structure, variables, resources, and guardrails, but it is **not a
> certified production module**. Several resources are **illustrative** and marked
> in-code where real IDs, a `restapi`/CSP provider, an `import`, or a control-plane
> API handoff is required (notably: Infoblox conditional forwarders, vDiscovery
> jobs, and Universal DDI Portal enrollment). Pin your own provider/module
> versions, supply your Marketplace AMI and instance type, and **test in a sandbox
> account first**.
