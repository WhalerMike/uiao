# ServiceNow Orchestration — GCP DDI Automation Package

> **Scope.** This is the **GCP-specific wiring** for the volume-level pattern in
> [`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md).
> That chapter defines the certified pieces (CPG Terraform Connector, Service
> Graph Connector for Infoblox, IntegrationHub REST, MID Server, Flow Designer)
> and the closed loop; this file maps them onto **this package's** artifacts:
> the [`../terraform`](../terraform) module, the [`../validation`](../validation)
> scripts, and the [`_module-contract.md`](../_module-contract.md) variables.
>
> **Starter skeleton — labeled as such.** Names below are the module's real
> variables (see [`../terraform/variables.tf`](../terraform/variables.tf)); the
> ServiceNow objects (catalog UI, flow, connections) are illustrative structure,
> not an exported update set.

The three companion artifacts in this folder:

| File | Role |
|---|---|
| [`ServiceNow-Orchestration.md`](./ServiceNow-Orchestration.md) (this file) | Catalog→tfvars mapping, the Flow Designer flow, CMDB mapping, GCC-Moderate notes. |
| [`integrationhub-actions.md`](./integrationhub-actions.md) | The Infoblox WAPI / Universal DDI REST bodies (allocate-next-IP, A/PTR, delete). |
| [`midserver-validate.sh`](./midserver-validate.sh) | MID Server wrapper that runs the three [`../validation`](../validation) gates and emits one JSON result. |

---

## 1. Catalog item → tfvars mapping

The **CPG Terraform Connector** ingests [`../terraform`](../terraform) as a
catalog item. Each catalog form field maps to exactly one module input variable;
the connector renders them into the `terraform.tfvars` for the `plan`/`apply`.
Variable names, types, and defaults are **verbatim** from
[`../terraform/variables.tf`](../terraform/variables.tf) /
[`_module-contract.md`](../_module-contract.md) §3.

### 1.1 Core placement & model

| Catalog field | tfvars variable | Type | Default | Notes |
|---|---|---|---|---|
| Resource name prefix | `name_prefix` | string | `ddi` | 2–11 chars, `^[a-z][a-z0-9-]{1,10}$`. |
| GCP region | `region` | string | — (required) | Commercial cloud region; members land in its zones. *(Azure `location`)* |
| Environment | `environment` | string | `prod` | `dev` \| `test` \| `prod`; feeds labels + sizing. |
| Control-plane model | `deployment_model` | string | `grid` | `grid` (in-boundary) \| `universal_ddi` (SaaS). |
| Acknowledge SaaS boundary | `acknowledge_saas_boundary` | bool | `false` | Must be `true` to allow `universal_ddi` (hard-fails otherwise). **SoD-gated field.** |
| Compliance profile | `compliance_profile` | string | `gcc-moderate` | Drives labels + control mapping. |
| Member count | `member_count` | number | `2` | vNIOS/NIOS-X hosts; 1–8, ≥2 for HA. |
| Zone letters | `zones` | list(string) | `["a","b"]` | Single letters within `region` (e.g. `a`,`b`). |
| Machine type | `machine_type` | string | — (required) | N1-family, model/version dependent — not hard-coded. *(Azure `vnios_vm_sku`)* |
| vNIOS image | `vnios_image` | object `{project,family?,name?}` | — (required) | Exactly one of `family`/`name`. Discover via `gcloud compute images list`. |

### 1.2 Host project / Shared VPC

| Catalog field | tfvars variable | Type | Default | Notes |
|---|---|---|---|---|
| Shared VPC host project | `host_project_id` | string | — (required) | Stage-1 output; subnet/firewall/members/SA land here. *(Azure `hub_resource_group_name`)* |
| Host VPC network | `shared_vpc_network` | string | — (required) | Name or self-link of the host VPC. *(Azure `hub_vnet_id`)* |
| DDI subnet CIDR | `ddi_subnet_cidr` | string | — (required) | Dedicated subnet created in the host VPC, e.g. `10.10.4.0/27`. *(Azure `ddi_subnet_address_prefix`)* |
| Spoke networks | `spoke_networks` | list(string) | `[]` | Service-project VPC self-links to point at the DDI resolver. *(Azure `spoke_vnet_ids`)* |
| Extra labels | `labels` | map(string) | `{}` | Merged with module-managed labels (lowercase). *(Azure `tags`)* |

### 1.3 VPC firewall source ranges (contract §4 — never `0.0.0.0/0`)

| Catalog field | tfvars variable | Type | Default | Notes |
|---|---|---|---|---|
| Management source ranges | `mgmt_source_ranges` | list(string) | — (required) | 443/tcp (+22 if SSH). Non-empty, must not contain `0.0.0.0/0`. |
| DNS client ranges | `dns_client_ranges` | list(string) | — (required) | 53 tcp+udp ingress (also DHCP ingress). Non-empty, no `0.0.0.0/0`. |
| Grid peer ranges | `grid_peer_ranges` | list(string) | `[]` | 1194/udp + 2114/tcp; `deployment_model=grid` only. |
| Monitoring source ranges | `monitoring_source_ranges` | list(string) | `[]` | 161/udp SNMP when `enable_snmp=true`; no `0.0.0.0/0`. |
| Enable SSH | `enable_ssh` | bool | `false` | 22/tcp from `mgmt_source_ranges`; prefer IAP TCP forwarding. |
| Enable DHCP | `enable_dhcp` | bool | `false` | 67–68/udp; GCP DHCP is platform-managed. |
| Enable SNMP | `enable_snmp` | bool | `false` | 161/udp ingress. |

### 1.4 DNS integration (contract §8)

| Catalog field | tfvars variable | Type | Default | Notes |
|---|---|---|---|---|
| Inbound forwarding | `inbound_forwarding_enabled` | bool | `true` | Cloud DNS inbound server policy on the host VPC. |
| Cloud DNS inbound IP | `cloud_dns_inbound_ip` | string | `null` | Inbound forwarder IP the members conditionally forward to. |
| Infoblox forward domains | `infoblox_forward_domains` | list(string) | `["googleapis.com","run.app"]` | Domains members forward to the Cloud DNS inbound IP. |
| Enterprise forward domains | `enterprise_forward_domains` | list(string) | `[]` | Cloud DNS forwarding zones → member IPs; trailing dot required. |
| Anycast VIP | `ddi_anycast_vip` | string | `null` | Service VIP; falls back to `dns_server_ips` if null. |
| Spoke DNS peering | `enable_spoke_dns_peering` | bool | `false` | Peering zones for `spoke_networks`. |

### 1.5 Secret Manager secret names (contract §1 — secrets stay in Secret Manager)

| Catalog field | tfvars variable | Type | Default | Notes |
|---|---|---|---|---|
| Secret project | `secret_project_id` | string | — (required) | Project holding the secrets (often = `host_project_id`). *(Azure `key_vault_id`)* |
| Admin password secret | `admin_password_secret_id` | string | `ddi-vnios-admin-password` | vNIOS default admin password. |
| Temp license secret | `temp_license_secret_id` | string | `ddi-vnios-temp-license` | vNIOS temp license string(s). |
| Grid shared-secret | `grid_shared_secret_id` | string | `ddi-grid-shared-secret` | Grid join shared secret (`grid`). |
| SaaS join-token secret | `saas_join_token_secret_id` | string | `ddi-uddi-join-token` | Portal (CSP) join token (`universal_ddi`). |

### 1.6 Discovery service-account discovery vars (contract §5)

| Catalog field | tfvars variable | Type | Default | Notes |
|---|---|---|---|---|
| Discovery identity type | `discovery_identity_type` | string | `service_account` | `service_account` (module creates `ddi-disco`) \| `existing_service_account`. |
| Existing SA email | `existing_service_account_email` | string | `null` | Required when `discovery_identity_type=existing_service_account`. |
| Discovered project IDs | `discovered_project_ids` | list(string) | `[]` | Gets `roles/compute.networkViewer` + `roles/dns.reader`. |
| DNS-admin project IDs | `dns_admin_project_ids` | list(string) | `[]` | `roles/dns.admin` **only if** `enable_record_write=true`. |
| Enable record write | `enable_record_write` | bool | `false` | Opt-in Cloud DNS record write. |

### 1.7 Grid / Universal DDI join parameters

| Catalog field | tfvars variable | Type | Default | Notes |
|---|---|---|---|---|
| Grid name | `grid_name` | string | `Infoblox` | Grid the members join (`grid`). |
| Grid Master VIP | `grid_master_vip` | string | `null` | GM the members join over 1194/2114 (`grid`). |
| Portal URL | `infoblox_portal_url` | string | `https://csp.infoblox.com` | NIOS-X enrollment (`universal_ddi`); outbound 443. |

---

## 2. Flow Designer flow

The flow implements the volume chapter's closed loop for **this** module:
**intake → approval/SoD → CPG Terraform apply of [`../terraform`](../terraform)
→ IntegrationHub IPAM → MID Server gate → Service Graph Connector CMDB → close.**
After approval it is hands-off; the approval and validation gates are kept on
purpose (that governance is the reason to front the pipeline with ITSM).

![GCP DDI ServiceNow closed loop: a Service Catalog request maps catalog inputs to the module tfvars, Flow Designer runs an approval and separation-of-duties gate, the CPG Terraform Connector plans and applies ../terraform on an in-boundary MID Server, IntegrationHub REST allocates the next available IP and creates A/PTR via the Infoblox WAPI / Universal DDI API, the MID Server runs midserver-validate.sh over the three validation gates, and on success the Service Graph Connector reconciles Infoblox subnets/IPs into the CMDB and the change closes — a failed gate returns to approval with the reason in work-notes](../figs/gcp-sn-01-catalog-flow.png)

1. **Intake.** Requester submits the **Service Catalog** item. Form fields map to
   the module inputs per §1; the connector renders `terraform.tfvars`. Required
   fields with no default (`region`, `host_project_id`, `shared_vpc_network`,
   `ddi_subnet_cidr`, `machine_type`, `vnios_image`, `secret_project_id`,
   `mgmt_source_ranges`, `dns_client_ranges`) block submission if empty.
2. **Approval + SoD gate.** Flow Designer runs the approval. **Separation of
   duties:** the requester cannot approve; selecting `deployment_model =
   universal_ddi` (hence `acknowledge_saas_boundary = true`) routes to an
   additional security/authorization approver, because that path leaves the ATO
   boundary. A rejected request closes with the reason recorded. *(AC-5/AC-6.)*
3. **CPG Terraform apply.** The **CPG Terraform Connector** runs a **speculative
   `plan`** against [`../terraform`](../terraform) on the in-boundary **MID
   Server**, posts the plan for approval, then `apply`. Secrets are pulled from
   **Secret Manager** via the MID Server credential store — never rendered into
   the flow. Outputs (`ddi_anycast_vip`, `dns_server_ips`, `ddi_subnet_id`,
   `discovery_service_account_email`) are captured into flow variables.
4. **IntegrationHub IPAM.** IntegrationHub **REST** steps call the Infoblox
   **WAPI / Universal DDI API** to allocate the next-available IP and create the
   A/PTR records (bodies in [`integrationhub-actions.md`](./integrationhub-actions.md)),
   tagging each object with the request number and GCP project/region as
   extensible attributes.
5. **MID Server validation gate.** The MID Server runs
   [`midserver-validate.sh`](./midserver-validate.sh), which executes the three
   [`../validation`](../validation) scripts (`dns-validation.sh`,
   `discovery-sync-check.sh`, `ipam-conflict-check.sh`), captures each exit code,
   and emits **one JSON result**. **Non-zero exit fails the change**, posts the
   failing check's reason to work-notes, and returns the request to approval
   (the loop-back edge in the figure). *(CM-6.)*
6. **Service Graph Connector CMDB reconcile.** On success the **Service Graph
   Connector for Infoblox** imports the affected Infoblox networks/IPs/EAs into
   the CMDB (§3), reconciling IPAM as the source of truth against the CIs.
7. **Close.** The change closes with the full audit trail — approvals, plan,
   apply, validation JSON, and CMDB deltas. *(AU-2/AU-6/AU-12, CM-3/CM-5.)*

**Day-2 / retirement** is a sibling flow: a retirement catalog item runs
`terraform destroy`, then the IntegrationHub **delete** actions
([`integrationhub-actions.md`](./integrationhub-actions.md) Action 3) reclaim the
DNS/IP objects, and a scheduled MID Server run of `discovery-sync-check.sh`
raises an **Incident** when a sync goes stale.

---

## 3. IntegrationHub REST summary

Full method/path/JSON bodies live in
[`integrationhub-actions.md`](./integrationhub-actions.md). Host placeholders are
written **without** an `https://` scheme (`<grid-master>` / `$GRID_MASTER`,
`<csp-host>`); the IntegrationHub connection record supplies scheme, port, and
TLS. Summary:

| Flow step | Action | Flavor | Method | Path |
|---|---|---|---|---|
| 4 | Next-available IP + host | NIOS/WAPI | `POST` | `<grid-master>/wapi/v2.12/record:host` |
| 4 | Next-available IP | Universal DDI | `POST` | `<csp-host>/api/ddi/v1/ipam/address?_next_available=1` |
| 4 | Create A | NIOS/WAPI | `POST` | `<grid-master>/wapi/v2.12/record:a` |
| 4 | Create PTR | NIOS/WAPI | `POST` | `<grid-master>/wapi/v2.12/record:ptr` |
| Day-2 | Find record `_ref` | NIOS/WAPI | `GET` | `<grid-master>/wapi/v2.12/record:a?name=<hostname-fqdn>` |
| Day-2 | Delete record | NIOS/WAPI | `DELETE` | `<grid-master>/wapi/v2.12/<record-ref>` |

---

## 4. Service Graph Connector CMDB mapping

The **Service Graph Connector for Infoblox** keeps IPAM as the source of truth
and reflects it into the CMDB. What the GCP module produces maps to CIs as:

| Infoblox / GCP object | CMDB class | Key fields / reconciliation |
|---|---|---|
| Infoblox `network` (incl. the `ddi_subnet_cidr` and discovered GCP subnets) | `cmdb_ci_ip_network` | CIDR, network view; reconciled against the module's `ddi_subnet_id`. |
| Infoblox subnet / range | `cmdb_ci_ip_network_subnet` | Subnet CIDR, gateway; child of `cmdb_ip_network`. |
| Allocated IP / A record (from step 4) | `cmdb_ci_ip_address` | Address, FQDN, MAC (if any); linked to the requesting CI. |
| vNIOS / NIOS-X member instances (`name_prefix-member-<zone>`) | `cmdb_ci_vm_instance` (GCP VM) | Instance name/zone/machine type; related to the IP CI. |
| Extensible attributes (`gcp_project`, `gcp_region`, `sn_request`, `cmdb_ci`) | CI attributes / relationships | EAs written in step 4 correlate the IP CI back to the catalog request and GCP project. |
| Discovery SA (`discovery_service_account_email`) | (context) | Not a CI; identity behind the IPAM→CMDB sync per contract §5. |

Import is scheduled (Service Graph data source + IntegrationHub ETL), so the CMDB
reflects IPAM reality rather than guessing it — the reconcile in flow step 6
matches these CIs against the change's outputs. *(CM-8 accurate inventory.)*

---

## 5. GCC-Moderate notes

This orchestration **strengthens** the compliance story (see the volume chapter
§7.4 and [`_module-contract.md`](../_module-contract.md) §1):

- **MID Server in-boundary.** Use a **FedRAMP-authorized ServiceNow (GovCloud)
  instance** and keep the **MID Server inside the ATO boundary**. Every execution
  and credential path — the Terraform `plan`/`apply`, the WAPI REST callouts, and
  the [`midserver-validate.sh`](./midserver-validate.sh) gate — runs on that
  in-boundary MID Server, so nothing sensitive transits the SaaS control plane.
- **Secrets in Secret Manager.** The module never inlines credentials: the WAPI
  service credential, `admin_password_secret_id`, `temp_license_secret_id`,
  `grid_shared_secret_id`, and `saas_join_token_secret_id` all resolve from
  **Secret Manager** (`secret_project_id`) through the MID Server credential
  store. IntegrationHub and Flow Designer reference credential aliases, not
  values.
- **Assured Workloads note.** Data-residency / personnel controls on GCP are
  delivered via **Assured Workloads** folders, which are a **Stage-1** foundation
  concern — this package targets commercial projects and does not itself
  provision Assured Workloads. If the landing zone places the host project under
  an Assured Workloads folder, this module and its ServiceNow front door inherit
  that posture unchanged.
- **Universal DDI SaaS caveat.** `deployment_model = grid` (WAPI-to-Grid) keeps
  DDI calls **in-boundary** and is the default. `deployment_model =
  universal_ddi` uses the Infoblox **Portal (CSP)** control plane **outside** the
  boundary; it is hard-gated by `acknowledge_saas_boundary = true` (default
  `false` hard-fails the plan) and, in the flow, routes to the extra
  security/authorization approver in step 2. The Universal DDI variants of the
  IntegrationHub actions and the discovery-sync check should only run on that
  acknowledged path.

**Control-family mapping** (evidence in ServiceNow, truth in Infoblox): catalog
approval + SoD → **AC-5/AC-6**; change record + immutable audit trail →
**AU-2/AU-6/AU-12** and **CM-3/CM-5**; validation gates → **CM-6**; reclaim-on-
delete + CMDB reconcile → **CM-8**.

---

## Sources

- Volume chapter: [`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md)
- Module contract: [`../_module-contract.md`](../_module-contract.md)
- Module variables: [`../terraform/variables.tf`](../terraform/variables.tf)
- Validation scripts: [`../validation`](../validation)
- Companion artifacts: [`integrationhub-actions.md`](./integrationhub-actions.md), [`midserver-validate.sh`](./midserver-validate.sh)
