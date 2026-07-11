# Chapter 7 — ServiceNow Orchestration: A Governed Front Door for DDI Automation

The platform chapters and their automation packages give you *runnable* DDI
provisioning — Terraform modules, Infoblox WAPI/Universal DDI calls, and validation
scripts. This chapter puts a **governed, self-service front door** on all of it with
**ServiceNow**, turning "an engineer runs the pipeline" into "a requester fills a catalog
form, it's approved, and the whole thing provisions, validates, and records itself."

Crucially, this is **assembly of certified products**, not custom glue: ServiceNow ships
a Terraform connector and Infoblox ships a certified Service Graph Connector. Your job is
to wire them to the modules and scripts this volume already defines.

## 7.1 Three systems, one loop

- **ServiceNow = system of engagement + governance** — the catalog request, approval and
  separation-of-duties gate, change record, and audit trail.
- **Terraform + the validation scripts = system of action** — the provisioning and the
  pass/fail gates (exactly what each package's `terraform/` and `validation/` provide).
- **Infoblox IPAM = system of record** for IP space and DNS — which syncs *back* into the
  ServiceNow CMDB so ServiceNow reflects reality instead of guessing it.

![ServiceNow closed-loop for DDI: a catalog request is approved in Flow Designer, the CPG Terraform Connector plans and applies the platform module, Infoblox allocates and registers via WAPI/Universal DDI, a MID Server gate runs the validation checks, the Service Graph Connector syncs the result into the CMDB, and the request closes with a full audit trail — a failed gate returns to approval](figs/sn-01-closed-loop.png)

The loop: **Service Catalog item → Flow Designer (approvals/SoD) → Terraform run → Infoblox
allocation → validation gate → CMDB update → close.** After approval it is hands-off; the
approval and validation gates are kept on purpose — that governance is the whole reason to
put ITSM in front.

## 7.2 The certified pieces

![ServiceNow ↔ Terraform ↔ Infoblox integration architecture: ServiceNow catalog, Flow Designer, IntegrationHub and the Service Graph Connector drive a MID Server inside the ATO boundary, which runs the per-platform Terraform module against the cloud and calls Infoblox over WAPI/Universal DDI; Infoblox feeds the CMDB through the Service Graph Connector](figs/sn-02-integration-architecture.png)

| Piece | Role | Product |
|---|---|---|
| **CPG Terraform Connector** | Ingests a Terraform module as a **catalog item**; runs `plan`/`apply` on Terraform OSS/Cloud/Enterprise via a **MID Server**, with a **native approval workflow** (speculative plan → approve → apply). Fronts each package's `terraform/` module. | ServiceNow Store (Cloud Provisioning & Governance) |
| **Service Graph Connector for Infoblox** | Imports Infoblox subnets/IPs/extensible-attributes into the CMDB (`cmdb_ci_ip_network`, `cmdb_ci_ip_network_subnet`), keeping IPAM the source of truth. | ServiceNow Store, built on the Infoblox IPAM module |
| **IntegrationHub REST** | Active IPAM/DNS calls from a flow — allocate-next-available, create A/PTR — straight to the Infoblox **WAPI / Universal DDI API**. | ServiceNow IntegrationHub |
| **MID Server** | Executes Terraform runs, REST callouts, and the **validation scripts**; the secure execution + credential path. Runs **inside the ATO boundary**. | ServiceNow MID Server |
| **Flow Designer / Service Catalog** | Request intake, approvals, SoD, orchestration, work-notes, closure. | ServiceNow platform |

HashiCorp's own **ServiceNow Catalog for Terraform** is the equivalent front-end if you
standardize on Terraform Cloud/Enterprise — same pattern (speculative plan → approval →
apply).

## 7.3 Mapping this volume's artifacts to ServiceNow

| Volume artifact | ServiceNow front-end |
|---|---|
| `terraform/` module (per platform) | CPG Terraform catalog item → approve → apply |
| IPAM allocation (`dns.tf`, WAPI) | IntegrationHub REST → Infoblox WAPI `network` / `record:a` (allocate-next-available) |
| `dns-validation.sh` · `discovery-sync-check.sh` · `ipam-conflict-check.sh` | Run on the **MID Server** as post-apply **flow gates**; non-zero exit fails the change and posts the reason to work-notes |
| Reclaim-on-delete (Day-2) | Retirement catalog item → `terraform destroy` + IPAM reclaim + record delete |
| Discovery-sync staleness | Scheduled MID Server check → auto-create **Incident** when a sync is stale |
| Grid/Portal + cloud state | Service Graph Connector → CMDB CIs, reconciled against IPAM |

Each platform package carries a `servicenow/` folder with the **platform-specific wiring**
(catalog input variables mapped to that module's `tfvars`, the IntegrationHub REST action
payloads for that platform's Infoblox calls, and a MID Server wrapper that runs its three
validation scripts): see `azure-alz-automation/servicenow/`, `aws-lz-automation/servicenow/`,
`gcp-lz-automation/servicenow/`, `oci-lz-automation/servicenow/`, and
`vmware-lz-automation/servicenow/`.

For the **importable starting point** — the actual scoped-app records (Script Includes that
implement the WAPI/Universal DDI calls, a REST Message, the MID validation gate, and a Flow
blueprint) — see [`servicenow-app/`](./servicenow-app/README.md).

## 7.4 GCC-Moderate boundary & governance

This *strengthens* the compliance story rather than complicating it:

- Use a **FedRAMP-authorized ServiceNow (GovCloud) instance**, and keep the **MID Server
  in-boundary** so the execution and credential path never leaves the ATO boundary — the
  same boundary discipline the rest of the volume applies.
- The **Universal DDI SaaS caveat still holds**: WAPI-to-Grid keeps DDI calls in-boundary;
  the Portal (CSP) API path is the out-of-boundary case gated by `acknowledge_saas_boundary`.
- **Control-family mapping:** the catalog approval + SoD gate → **AC-5/AC-6**; the change
  record and immutable audit trail → **AU-2/AU-6/AU-12** and **CM-3/CM-5**; the validation
  gates → **CM-6** configuration enforcement; reclaim-on-delete → **CM-8** accurate
  inventory. ServiceNow gives you the *evidence*, Infoblox gives you the *truth*.

## 7.5 Build sequence

1. Install the **Service Graph Connector for Infoblox** and schedule the IPAM → CMDB import.
2. Install the **CPG Terraform Connector**, register a **MID Server** (in-boundary), and
   ingest each platform's `terraform/` module as a **catalog item**.
3. Build the **Flow Designer** flow: intake → approval/SoD → Terraform apply → IntegrationHub
   IPAM calls → MID Server validation gate → CMDB reconcile → close.
4. Wire the **IntegrationHub REST** actions to the Infoblox WAPI/Universal DDI endpoints
   (per each package's `servicenow/` action definitions).
5. Add the **retirement** catalog item (destroy + reclaim) and the **staleness Incident**
   scheduled job.
6. Pilot in a dev catalog, then promote — exactly the dev→prod flow the platform runbooks use.

---

## Sources

- [Service Graph Connector for Infoblox — ServiceNow Store](https://store.servicenow.com/store/app/eeb927621b246a50a85b16db234bcbf1)
- [Cloud Provisioning & Governance: Terraform Connector — ServiceNow Store](https://store.servicenow.com/store/app/6ff8ef2e1be06a50a85b16db234bcbcb)
- [Integration of Infoblox IPAM with ServiceNow — deployment guide](https://docs.infoblox.com/space/DeploymentGuideIPAMwithServiceNow/1297813131/Introduction)
- [HashiCorp — ServiceNow Catalog for Terraform adds approval workflow](https://www.hashicorp.com/en/blog/servicenow-catalog-for-terraform-adds-approval-workflow-integration)
- Volume cross-reference: [`06-cross-platform-operations.md`](./06-cross-platform-operations.md) §6.5 (automation & IaC)
