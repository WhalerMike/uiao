# Shared Module Contract — AWS LZ + Infoblox DDI

> **Purpose.** This file is the single source of truth that keeps the Terraform module,
> the pipelines, and the written guide **consistent** — identical variable names, ports,
> IAM scopes, resource-naming, and architectural decisions. Every artifact in
> `aws-lz-automation/` MUST conform to this contract. If a value is
> version/region-dependent, the artifact says so rather than hard-coding a guess.
>
> This is the **Terraform-only** AWS analog of the Azure ALZ package
> (`../azure-alz-automation/`). It mirrors that package's structure and boundary rule,
> adapted to AWS primitives (Security Groups, cross-account IAM roles, EC2/AMI, Route 53
> Resolver, VPC IPAM). There is **no Bicep/CloudFormation module** here — a short
> CodePipeline note documents the native-CI equivalent, but the IaC is Terraform.

## 1. Boundary & compliance profile (fixed for this deliverable)

- **Cloud boundary:** Commercial AWS, **`.com` endpoints** (`ec2.amazonaws.com`,
  `sts.amazonaws.com`, `route53.amazonaws.com`, `secretsmanager.<region>.amazonaws.com`,
  `s3.amazonaws.com`). **Not** AWS GovCloud (`amazonaws-us-gov.com` / the `us-gov-*`
  partition). This matches a **GCC-Moderate** operating posture running on the commercial
  partition. (vNIOS, multi-account vDiscovery from NIOS 9.0.4+, and Route 53 integration
  from NIOS 8.6.3+ all run in GovCloud too — see §9 — but that partition is out of scope
  here.)
- **Compliance profile:** `gcc-moderate` (FedRAMP Moderate-equivalent controls). Artifacts
  carry a `compliance_profile` variable defaulting to `"gcc-moderate"`.
- **Control-plane boundary rule (critical):**
  - `deployment_model = "grid"` → the vNIOS Grid control plane runs **inside the account /
    ATO boundary**. Boundary-clean; the default for GCC-Moderate.
  - `deployment_model = "universal_ddi"` → the Infoblox Portal (SaaS) control plane is
    **outside** the ATO boundary and requires outbound `443` to the Portal. Artifacts MUST
    emit a boundary/authorization caveat and gate this path behind an explicit
    `acknowledge_saas_boundary = true` variable (default `false`, which hard-fails the plan
    with a message pointing to the authorization review).

## 2. Layering model (how it sits on the Landing Zone Accelerator / Control Tower)

Three stages; this module is **Stage 2**. It never creates the organization, accounts,
guardrails, or the hub VPC — those are Stage 1 (AWS Control Tower + Landing Zone
Accelerator on AWS).

```
Stage 1  Control Tower / Landing Zone Accelerator on AWS (CloudFormation/CDK)
         → outputs: network_account_id, hub_vpc_id, hub_vpc_cidr, transit_gateway_id,
           ddi_route_table_id (optional), r53_resolver_inbound_ip (optional),
           dns_query_log_group_arn (optional)
                     │  (remote state / SSM parameters / exported outputs consumed as inputs)
                     ▼
Stage 2  THIS MODULE — Infoblox DDI extension in the Network-account hub VPC
                     │  outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                     ▼            discovery_identity_id, ddi_subnet_ids
Stage 3  Validation (pipeline gates: resolve a record, confirm discovery sync, conflict check)
```

## 3. Canonical input variables (mirrors the Azure package where names map)

| Variable | Type | Default | Notes |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | Prefix for all resource names. |
| `region` | string | — | AWS region (commercial partition). |
| `environment` | string | `"prod"` | `dev`/`test`/`prod`; feeds tags + sizing. |
| `deployment_model` | string | `"grid"` | `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` to allow `universal_ddi` (see §1). |
| `compliance_profile` | string | `"gcc-moderate"` | Drives tags + control mapping. |
| `network_account_id` | string | — | From Stage 1 output — the Network/connectivity account. |
| `hub_vpc_id` | string | — | From Stage 1 output — the shared-services (hub) VPC. |
| `transit_gateway_id` | string | — | From Stage 1 — spokes attach here; DDI subnets route to it. |
| `ddi_subnet_cidrs` | list(string) | — | One dedicated DDI subnet CIDR per AZ (created by this module in the hub VPC). |
| `member_count` | number | `2` | vNIOS members / NIOS-X hosts; ≥2 for HA. |
| `availability_zones` | list(string) | — | Spread members across zones (e.g. `["us-east-1a","us-east-1b"]`). |
| `vnios_instance_type` | string | — | EC2 instance type; region/NIOS-version-dependent — do not hard-code (M7i/R7i for NIOS 9.0.5+). |
| `vnios_ami_id` | string | — | vNIOS Marketplace AMI ID — **supply your own** (`aws ec2 describe-images`); never invented. |
| `secrets_store_type` | string | `"secrets_manager"` | `secrets_manager` \| `ssm_parameter_store` (where module secrets live). |
| `discovery_identity_type` | string | `"iam_role"` | `iam_role` (cross-account, preferred) \| `instance_profile`. |
| `spoke_vpc_ids` | list(string) | `[]` | Spokes whose `dns_servers` (DHCP option set) should point at the DDI VIP (optional). |
| `tags` | map(string) | `{}` | Merged with module-managed tags. |

## 4. Ports (Security-Group rules the module creates on the DDI members)

| Service | Port | Proto | Direction | When |
|---|---|---|---|---|
| DNS | 53 | tcp+udp | ingress from spokes/on-prem | always |
| DHCP | 67–68 | udp | ingress | only if module serves DHCP (AWS VPC DHCP is option-set based; off by default) |
| Grid VPN | 1194 | udp | in/out to Grid members/GM | `deployment_model=grid` |
| Grid comms | 2114 | tcp | in/out | `deployment_model=grid` |
| NTP | 123 | udp | egress | always |
| HTTPS mgmt | 443 | tcp | ingress (mgmt CIDR) | always |
| Portal sync | 443 | tcp | **egress to Infoblox Portal** | `deployment_model=universal_ddi` only |
| SNMP | 161 | udp | ingress (monitoring CIDR) | optional |
| SSH | 22 | tcp | ingress (mgmt CIDR) | optional (`enable_ssh`, prefer SSM Session Manager) |

Security Groups are **default-deny ingress** by AWS design; this module **also manages the
full egress set** (replacing AWS's default allow-all egress) so egress is default-deny too.
Scope mgmt/monitoring/client sources to explicit CIDR variables, **never `0.0.0.0/0`**
(hard-rejected in `variables.tf`).

## 5. Least-privilege discovery identity (AWS → Infoblox IPAM sync)

The discovery credential is a **cross-account IAM role** assumed by the Infoblox
integration account, with an **`ExternalId`** condition (confused-deputy protection).
Grant a **custom** least-privilege policy — never the broad AWS-managed
`AmazonVPCReadOnlyAccess` / `AmazonRoute53ReadOnlyAccess` / `AmazonS3ReadOnlyAccess`.

| Capability | Representative least-privilege actions | When |
|---|---|---|
| VPC / subnet / instance discovery | `ec2:DescribeVpcs`, `ec2:DescribeSubnets`, `ec2:DescribeInstances`, `ec2:DescribeNetworkInterfaces`, `ec2:DescribeAvailabilityZones`, `ec2:DescribeRegions` | always |
| Tags (tag-driven allocation) | `ec2:DescribeTags` | always |
| Route 53 DNS sync | `route53:ListHostedZones`, `route53:ListResourceRecordSets`, `route53:GetHostedZone` | only if Infoblox syncs Route 53 zones (`enable_record_read`) |
| Cross-account trust | trust policy: `sts:AssumeRole` from the integration account principal, `Condition` on `sts:ExternalId` | always |

No `Owner`-equivalent, no `*:*`, **zero data-plane access** (no `s3:GetObject`). The role is
created in the account this module runs in; **replicate it to each discovered account**
(CloudFormation StackSets or a per-account apply) with the same trust + ExternalId. Record
write-back (Route 53) is opt-in.

## 6. Resource-naming convention

`${name_prefix}-<role>-<zone/index>` e.g. `ddi-vnios-use1a`, `ddi-sg`, `ddi-subnet-use1a`,
`ddi-disco-role`. All resources tagged: `workload=infoblox-ddi`, `layer=connectivity-ddi`,
`compliance_profile=<value>`, `deployment_model=<value>`, `managed_by=terraform`,
`environment=<value>`.

## 7. Canonical outputs (mirror the Azure package)

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_identity_id` (the IAM role ARN), `ddi_subnet_ids` (list).

## 8. DNS integration contract

- Infoblox members are authoritative for enterprise zones and **conditionally forward**
  AWS-service names (`amazonaws.com`, `<region>.compute.internal`, Route 53
  private-hosted-zone domains) to the **Route 53 Resolver inbound endpoint** (Stage-1/existing).
- Spoke `dns_servers` (the VPC **DHCP option set** `domain-name-servers`) set to
  `ddi_anycast_vip` (or `dns_server_ips`) — module writes this only when `spoke_vpc_ids`
  provided and the write is enabled (`enable_spoke_dns_write`).
- Reverse the direction with a Route 53 Resolver **outbound** endpoint + forwarding **rules**
  (shared across accounts via AWS RAM) targeting the DDI member IPs (documented in the guide;
  not all deployments automate it).
- **VPC IPAM coexistence:** Infoblox discovers VPC CIDRs (visibility model) or, via the 2025
  Amazon VPC IPAM ↔ Infoblox integration + BYOIP, becomes the **management authority for a
  VPC IPAM private scope** (authoritative model). Private scopes only.

## 9. Style for code artifacts

- Terraform: pin `hashicorp/aws` and `infobloxopen/infoblox` providers in `versions.tf`;
  every variable documented; skeleton is **illustrative-but-coherent** (labeled as a starter,
  not a certified production module). Guard the SaaS path per §1.
- Never invent AMI IDs, instance types, or Marketplace product codes — parameterize and point
  to `aws ec2 describe-images` / the AWS Marketplace listing.
- Secrets live in **AWS Secrets Manager** or **SSM Parameter Store** (`secrets_store_type`);
  never in state as plaintext, never committed.
