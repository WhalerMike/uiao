# ServiceNow Orchestration — OCI Landing Zone Infoblox DDI

> **This is the OCI-specific wiring.** For the cross-platform pattern, the certified
> products, the three-systems loop, and the control-family mapping, read the volume
> chapter first: [`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md).
> This file maps that pattern onto **this package's** actual Terraform variables
> ([`../terraform/variables.tf`](../terraform/variables.tf)), validation scripts
> ([`../validation`](../validation)), and the shared contract
> ([`../_module-contract.md`](../_module-contract.md)).

ServiceNow puts a **governed, self-service front door** on the OCI DDI package: a requester
fills a catalog form, it is approved with a separation-of-duties gate, and the
**CPG Terraform Connector** applies [`../terraform`](../terraform), IntegrationHub makes the
Infoblox IPAM/DNS calls, a **MID Server** runs the validation gate inside the OCI ATO
boundary, and the **Service Graph Connector** reconciles the result into the CMDB before the
change closes. This is **assembly of certified products** (CPG Terraform Connector, Service
Graph Connector for Infoblox, IntegrationHub), not custom glue.

![ServiceNow closed loop for OCI DDI: a catalog request is approved with a separation-of-duties gate in Flow Designer, the CPG Terraform Connector applies the OCI module, IntegrationHub allocates IP and writes A/PTR over Infoblox WAPI, the MID Server runs the validation scripts inside the OCI ATO boundary, the Service Graph Connector reconciles the result into the CMDB, and the request closes with a full audit trail — a failed gate returns to approval](../figs/oci-sn-01-catalog-flow.png)

## Candor up front — OCI discovery is API/SDK-driven

Consistent with the rest of this package (`../_module-contract.md` §0/§5 and `../04-oci.md`):
OCI has **no native, event-driven Infoblox cloud-discovery connector** the way AWS/Azure/GCP
do. The ServiceNow front door does **not** magic that away. What ServiceNow orchestrates is
the *provisioning and governance* loop; the OCI→IPAM **discovery sync** underneath remains a
scheduled OCI-SDK job or the Infoblox Terraform provider running in the same apply. The MID
Server validation gate simply **reads the freshness of whatever that job records**
(`discovery-sync-check.sh`) — it does not replace the connector OCI never shipped.

---

## 1. Catalog item → `tfvars` mapping

The CPG Terraform Connector ingests [`../terraform`](../terraform) as a catalog item;
each catalog form field maps to one Terraform input variable, which the connector renders
into the `tfvars` for the `plan`/`apply`. Variable names below are **exact** — from
[`../terraform/variables.tf`](../terraform/variables.tf) and `../_module-contract.md` §3.

| Catalog form field | Terraform variable | Type | Default | Notes |
|---|---|---|---|---|
| Name prefix | `name_prefix` | string | `"ddi"` | 2–11 chars, lowercase/hyphen. |
| OCI region | `region` | string | — | OC1 commercial, e.g. `us-ashburn-1`. Required. |
| Environment | `environment` | string | `"prod"` | `dev`/`test`/`prod` — drives approval routing + sizing. |
| Deployment model | `deployment_model` | string | `"grid"` | `grid` (in-boundary) \| `universal_ddi` (SaaS). Drives the SoD gate. |
| Acknowledge SaaS boundary | `acknowledge_saas_boundary` | bool | `false` | Must be `true` for `universal_ddi`; else the plan hard-fails (see §5, GCC notes). |
| Compliance profile | `compliance_profile` | string | `"fedramp-moderate"` | Tags + control mapping. |
| Network compartment OCID | `network_compartment_ocid` | string | — | Hub-VCN compartment (Stage-1 output). |
| Tenancy OCID | `tenancy_ocid` | string | — | Root; where discovery IAM dynamic group/policy live. |
| Hub VCN OCID | `hub_vcn_ocid` | string | — | DDI subnet is created inside it (Stage-1 output). |
| DRG OCID | `drg_ocid` | string | `null` | Hub-spoke + on-prem reachability reference. |
| **DDI subnet CIDR** | `ddi_subnet_cidr` | string | — | The `ddi_subnet_address_prefix` analogue — the subnet this module creates. IntegrationHub allocates from it. |
| Member count | `member_count` | number | `2` | vNIOS/NIOS-X hosts; ≥2 for HA. |
| Availability domains | `availability_domains` | list(string) | — | Many OCI regions are single-AD (see §5). |
| Fault domains | `fault_domains` | list(string) | `["FAULT-DOMAIN-1","FAULT-DOMAIN-2"]` | Always spread within an AD. |
| vNIOS shape | `vnios_shape` | string | — | Flexible shape, model/region-dependent — not hard-coded. |
| vNIOS OCPUs / memory | `vnios_ocpus` / `vnios_memory_gbs` | number | `4` / `32` | Match the vNIOS model spec. |
| vNIOS image OCID | `vnios_image_ocid` | string | `null` | Imported **custom image** (no Marketplace). Supply your own. |
| Security model | `security_model` | string | `"nsg"` | `nsg` (per-VNIC) \| `security_list` (subnet-wide). |
| Mgmt source CIDRs | `mgmt_source_cidrs` | list(string) | — | 443/22 ingress. **Never `0.0.0.0/0`** (validated). |
| DNS client CIDRs | `dns_client_cidrs` | list(string) | — | 53 tcp+udp ingress (spokes/on-prem). Never `0.0.0.0/0`. |
| Grid peer CIDRs | `grid_peer_cidrs` | list(string) | `[]` | 1194/udp + 2114/tcp; required for `grid`. |
| Monitoring source CIDRs | `monitoring_source_cidrs` | list(string) | `[]` | 161/udp when `enable_snmp`. Never `0.0.0.0/0`. |
| Enable SSH / DHCP / SNMP | `enable_ssh` / `enable_dhcp` / `enable_snmp` | bool | `false` | Optional services (contract §4). |
| **Vault OCID** | `vault_ocid` | string | — | OCI Vault holding module secrets. |
| Admin password secret | `admin_password_secret_ocid` | string | — | Vault secret OCID (read via `oci_secrets_secretbundle`). |
| Temp license secret | `temp_license_secret_ocid` | string | — | Vault secret OCID. |
| Grid shared secret | `grid_shared_secret_ocid` | string | `null` | Vault OCID; `grid` only. |
| SaaS join token secret | `saas_join_token_secret_ocid` | string | `null` | Vault OCID; `universal_ddi` only. |
| **Discovery identity type** | `discovery_identity_type` | string | `"instance_principal"` | `instance_principal` (dynamic group) \| `api_key_user`. |
| Discovery dynamic-group rule | `discovery_dynamic_group_matching_rule` | string | `null` | Instance-principal matching rule (contract §5). |
| Discovery user OCID | `discovery_user_ocid` | string | `null` | Pre-created IAM user for `api_key_user`. |
| Discovered compartments | `discovered_compartment_ocids` | list(string) | `[]` | Read scope for discovery; defaults to `[network_compartment_ocid]`. |
| Enable record write | `enable_record_write` | bool | `false` | Opt-in `manage dns-*` (else read-only discovery). |
| Manage resolver endpoints | `manage_resolver_endpoints` | bool | `true` | Create the VCN resolver LISTENING/FORWARDING endpoints. |
| Spoke VCN OCIDs | `spoke_vcn_ocids` | list(string) | `[]` | Spokes whose forwarding points at the DDI VIP. |
| Enable spoke DNS write | `enable_spoke_dns_write` | bool | `false` | Write spoke→hub forwarding rules. |
| DDI anycast VIP | `ddi_anycast_vip` | string | `null` | Service DNS address; falls back to member IPs. |
| Grid name / Grid Master VIP | `grid_name` / `grid_master_vip` | string | `"Infoblox"` / `null` | `grid` join parameters. |
| Infoblox Portal URL | `infoblox_portal_url` | string | `"csp.infoblox.com"` | `universal_ddi` enrollment host (no scheme). |
| Freeform / defined tags | `freeform_tags` / `defined_tags` | map(string) | `{}` | Merged with module-managed tags. |

Fields with **no default** (`region`, `network_compartment_ocid`, `tenancy_ocid`,
`hub_vcn_ocid`, `ddi_subnet_cidr`, `vault_ocid`, the three no-default source-CIDR lists,
`vnios_shape`, the required secret OCIDs) are **mandatory** on the catalog form; the connector
speculative `plan` fails fast if any are missing, before approval.

---

## 2. Flow Designer flow

The flow is built once and reused for every request. Numbered, end to end:

1. **Intake.** The requester submits the **Service Catalog** item; form fields populate the
   `tfvars` per §1. Client-side validation mirrors the module's own `validation {}` blocks
   (e.g. `mgmt_source_cidrs` may not be `0.0.0.0/0`; `name_prefix` regex).
2. **Speculative plan.** The CPG Terraform Connector runs `terraform plan` against
   [`../terraform`](../terraform) on the **MID Server** and attaches the plan output to the
   request for the approver to review (plan-before-approve).
3. **Approval + SoD gate.** Flow Designer routes for approval. **Separation of duties:** the
   requester cannot approve; `deployment_model = universal_ddi` **and** `environment = prod`
   escalate to a security/authorization approver because that path leaves the ATO boundary
   (maps to **AC-5/AC-6**). A rejected request closes with the reason in work-notes.
4. **Terraform apply.** On approval the connector runs `terraform apply` of the reviewed plan
   on the MID Server. Secrets (`admin_password_secret_ocid`, etc.) are read from **OCI Vault**
   at apply time — never rendered into the catalog record. This creates the DDI subnet, NSG/SL,
   vNIOS members, IAM discovery identity, and resolver endpoints.
5. **IntegrationHub IPAM/DNS.** IntegrationHub REST steps call Infoblox to **allocate the
   next-available IP** from `ddi_subnet_cidr` and **create the A/PTR** records (bodies in
   [`integrationhub-actions.md`](./integrationhub-actions.md)). The allocated IP + FQDN are
   captured back into the flow.
6. **MID Server validation gate.** The flow invokes
   [`midserver-validate.sh`](./midserver-validate.sh) on the MID Server, which runs the three
   `../validation` scripts (DNS resolves, discovery sync fresh, no IPAM conflict) and returns
   one JSON result. **Non-zero fails the change** — the flow posts the failing check + reason
   to work-notes and **routes back to approval** (step 3) rather than closing dirty.
7. **Service Graph Connector → CMDB.** On a passing gate, the **Service Graph Connector for
   Infoblox** reconciles the new subnet/IP/records into the CMDB (§4) so ServiceNow reflects
   IPAM reality rather than guessing it.
8. **Close.** The change record closes with the full audit trail — plan, approver, apply
   output, validation JSON, and CMDB reconcile (maps to **AU-2/AU-6/AU-12**, **CM-3/CM-5**).

**Day-2 retirement** is a sibling flow: a retirement catalog item runs `terraform destroy`,
IntegrationHub deletes the A/PTR and releases the IP ([`integrationhub-actions.md`](./integrationhub-actions.md)
§4), and the CMDB CI is retired (**CM-8** accurate inventory). A scheduled MID Server run of
`discovery-sync-check.sh` opens an **Incident** when a sync goes stale.

---

## 3. IntegrationHub REST summary

Full method/path/JSON bodies are in [`integrationhub-actions.md`](./integrationhub-actions.md).
At a glance (NIOS/WAPI, `grid` default — base `<grid-master>/wapi/v2.12`, no scheme):

| Action | Method | Path (relative to base) | Purpose |
|---|---|---|---|
| Next-available IP | `POST` | `/record:host` with `next_available_ip` func on `network` | Reserve + name an IP from `ddi_subnet_cidr`. |
| Create A | `POST` | `/record:a` | Forward record. |
| Create PTR | `POST` | `/record:ptr` | Reverse record (delegated OCI reverse zones, contract §8). |
| Look up ref | `GET` | `/record:a?name=…` | Resolve `_ref` before delete. |
| Delete A / PTR / host | `DELETE` | `/record:{a,ptr,host}/<_ref>` | Reclaim on retirement. |

The **Universal DDI / Portal** variant (`csp.infoblox.com/api/ddi/v1`, `Authorization: Token`)
is documented alongside and is **outside the ATO boundary** — see §5.

---

## 4. Service Graph Connector → CMDB mapping

The **Service Graph Connector for Infoblox** imports Infoblox IPAM/DNS into the CMDB, keeping
IPAM the source of truth (chapter §7.2). What this OCI package produces maps as:

| Infoblox / OCI object | CMDB class | Key fields populated |
|---|---|---|
| DDI subnet (`ddi_subnet_cidr`) / IPAM `network` | `cmdb_ci_ip_network` | `subnet` (CIDR), `netmask`, network view, `name` (`${name_prefix}-subnet`). |
| Allocated address (step 5) / IPAM `ipv4address` | `cmdb_ci_ip_address` | `ip_address`, owning network, MAC/host if present. |
| A record (`record:a`) | `cmdb_ci_dns_name` (or `cmdb_ci_endpoint`) | `name` (FQDN), `ip_address`, `dns_view`. |
| vNIOS members / OCI instances | `cmdb_ci_server` / `cmdb_ci_vm_instance` | member name (`${name_prefix}-vnios-ad1-fd1`), management IP, region/AD/FD. |
| Extensible attribute `ServiceNow Request` | Relationship / correlation | Reconciles the CI back to the originating `change_request` / `sc_req_item`. |
| OCI VCNs/subnets from the discovery sync | `cmdb_ci_ip_network` | Discovered CIDRs + defined tags → EAs (the API/SDK-driven sync, §candor above). |

**Reconciliation, not blind insert:** the connector uses IRE with Infoblox as the
authoritative source; the `ServiceNow Request` extensible attribute (written by IntegrationHub
in step 5) correlates each imported CI to the change that created it, closing the loop from
request → resource → CMDB record.

---

## 5. GCC-Moderate boundary & governance notes

This package targets a **FedRAMP Moderate-equivalent posture on commercial OCI (OC1 realm,
`*.oraclecloud.com`)** — `../_module-contract.md` §1. The ServiceNow layer strengthens that
story rather than complicating it:

- **FedRAMP-authorized ServiceNow instance + MID Server in-boundary.** Run on a ServiceNow
  **GovCloud (FedRAMP)** instance and keep the **MID Server inside the OCI ATO boundary** so
  the execution and credential path — `terraform apply`, IntegrationHub WAPI callouts, and the
  `../validation` gate via [`midserver-validate.sh`](./midserver-validate.sh) — never leaves
  the boundary. This is the same boundary discipline the rest of the package applies.
- **Secrets stay in OCI Vault.** No credential is stored in the catalog record or the flow.
  The connector reads `admin_password_secret_ocid`, `temp_license_secret_ocid`,
  `grid_shared_secret_ocid` / `saas_join_token_secret_ocid`, and the WAPI/CSP creds from the
  **OCI Vault** referenced by `vault_ocid` (contract §9), surfaced to the MID Server only at
  run time.
- **Universal DDI SaaS caveat still holds.** `deployment_model = grid` keeps the entire vNIOS
  Grid control plane **inside** the tenancy (boundary-clean, the default). `universal_ddi`
  puts the Infoblox Portal (CSP) control plane **outside** the boundary and requires outbound
  443 — so the module **hard-fails the plan unless `acknowledge_saas_boundary = true`**, and
  the flow escalates that path to a security approver (step 3). The IntegrationHub Portal
  bodies and `discovery-sync-check.sh`'s `universal_ddi` variant are the only out-of-boundary
  calls, and only when explicitly acknowledged.
- **OCI Government / National-Security realms.** This deliverable is scoped to **OC1
  (commercial)**. In **OC2 (US Gov)**, **OC3 (US DoD)**, or National-Security / EU Sovereign /
  air-gapped realms, default to **Grid** — the Portal (SaaS) is typically unreachable there,
  so `universal_ddi` should not be offered on the catalog form, and vNIOS custom-image
  availability must be confirmed in the specific realm first (contract §1).
- **Control-family mapping.** Catalog approval + SoD gate → **AC-5/AC-6**; change record and
  immutable audit trail → **AU-2/AU-6/AU-12** and **CM-3/CM-5**; the validation gate →
  **CM-6** configuration enforcement; reclaim-on-delete → **CM-8** accurate inventory.
  ServiceNow supplies the *evidence*; Infoblox supplies the *truth*.

---

## Files in this folder

| File | What it is |
|---|---|
| `ServiceNow-Orchestration.md` | This file — OCI-specific wiring of the chapter-7 pattern. |
| [`integrationhub-actions.md`](./integrationhub-actions.md) | Infoblox WAPI / Universal DDI REST bodies (next-available-IP, A/PTR, delete). |
| [`midserver-validate.sh`](./midserver-validate.sh) | MID Server wrapper: runs `../validation/*.sh`, emits one JSON result, non-zero on failure. |
| [`../figs/oci-sn-01-catalog-flow.mmd`](../figs/oci-sn-01-catalog-flow.mmd) | Source for the closed-loop figure above (rendered to PNG by `render-figs.sh`). |

*Starter skeleton — illustrative, not a certified production configuration. Confirm WAPI/CSP
object and field versions against your Grid Master (`<grid-master>/wapidoc/`) and the current
CSP API docs before relying on them.*
