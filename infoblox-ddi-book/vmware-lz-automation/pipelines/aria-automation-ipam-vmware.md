# Infoblox IPAM Plug-In for VMware Aria Automation — provisioning-time allocation

> Companion to the Terraform module. Where the module stands up the **DDI fabric** (vNIOS
> members, DFW, DNS forwarder, DHCP relay, discovery), the **Aria Automation IPAM plug-in**
> is the day-2 **self-service seam**: it lets Aria (formerly vRealize Automation / vRA)
> request addresses and DNS records from Infoblox *at provisioning time*, and reclaim them on
> teardown. This is the VMware analogue of the "self-service IPAM in provisioning pipelines"
> idea from the hyperscaler chapters — but native to the private cloud's own catalog.

## Where it fits

The module makes Infoblox the **authoritative IPAM/DNS/DHCP** for the private cloud. The
plug-in makes that authority *consumable from the VMware catalog*: a blueprint author asks
for a network/IP, and Infoblox answers — no spreadsheet, no manual handoff, every allocation
recorded, tagged, and conflict-checked centrally (the same `ipam-conflict-check.sh` gate then
protects it).

```
Aria Automation (Cloud Assembly / Service Broker)
   blueprint / cloud template  ──requests──▶  Infoblox IPAM plug-in (external IPAM provider)
        │  deploy                                   │  WAPI / 443
        │                                           ▼
        │                              Infoblox Grid (authoritative IPAM/DNS)
        │  allocate IP + create A/PTR + inject gateway/netmask/DNS into the VM
        ▼
   Tenant VM on an NSX segment  ◀── IP + DNS ready at first boot
        │  delete
        └──reclaim──▶  plug-in releases IP + removes DNS records (IP reclaim on delete)
```

## What the plug-in does

- **Register Infoblox as an external IPAM provider** in Aria Automation: download the
  provider package (from the VMware Marketplace / Infoblox), add the integration point with
  the **Grid address + a scoped admin credential**, and validate the connection.
- **Provisioning-time allocation:** in cloud templates/blueprints, network and machine
  resources request address space and IPs from Infoblox. On deploy, the plug-in **allocates
  the IP, creates the A/PTR (host) record, and injects gateway/netmask/DNS settings into the
  VM** — cutting provisioning time and eliminating manual IP handoffs.
- **Tag-/property-driven allocation:** Infoblox **extensible attributes (EAs)** and
  Infoblox-specific template properties steer which network/range a VM draws from (e.g.
  `environment`, `tenant`, `zone`), so allocation follows metadata rather than hand-picked
  subnets. These are the same EAs CNA discovery stamps (contract §5/§8).
- **IP reclaim on VM delete:** when Aria deprovisions the VM, the plug-in **releases the IP
  and removes the DNS records**, so leases, records, and allocations stay consistent — the
  core DDI promise. CNA discovery independently reaps orphaned objects if a VM is deleted
  outside Aria.

## How it relates to the module

| Module (Terraform) | Aria plug-in (this doc) |
|---|---|
| Deploys vNIOS members, DFW, DNS forwarder, DHCP relay, discovery role | Consumes the running Grid as an external IPAM provider |
| Sets the **authoritative** IPAM/DNS/DHCP fabric | Performs **provisioning-time** allocate/register + reclaim-on-delete |
| CNA reflects vSphere reality *into* IPAM (discovery) | Aria requests allocations *from* IPAM (self-service) |
| `ipam-conflict-check.sh` gates address-space integrity | Every plug-in allocation is conflict-checked by that same gate |

## Prerequisites (version-dependent — confirm before relying on these)

- **Aria Automation / vRA 8.9.1+** (per `../05-vmware.md §8`).
- **Infoblox IPAM plug-in 1.5+**, Grid **WAPI v2.7+**.
- A **scoped Infoblox admin group** for the plug-in credential: cloud-API access and IPAM +
  DNS + DHCP + Grid (+ Tenant when CNA is licensed) rights on the relevant objects (contract
  §5) — **not** a full Grid superuser.
- Network path from the Aria appliances to the Grid on **443/tcp** (the module's DFW opens
  HTTPS/WAPI inbound from `mgmt_source_cidrs`; include the Aria appliance range there).

## Config values you must supply

These are captured as fill-in fields in the runbook's **Appendix A** (the Aria plug-in
worksheet). At a glance:

| Value | Where it comes from |
|---|---|
| Grid Master / WAPI address | module output `grid_master_ip` (or the DDI VIP) |
| Plug-in admin username / password | the scoped Infoblox admin group above (from Vault/CI) |
| WAPI version | your NIOS release (e.g. `v2.12`) |
| Default network view | usually `default` (or a tenant view) |
| EA/property keys for steering | `environment` / `tenant` / `zone` (align with CNA EAs) |

> The plug-in package itself is distributed via the VMware Marketplace and the Infoblox
> download site (the deep VMware/Broadcom TechDocs pages gate/redirect — search their docs
> for "download and deploy an external IPAM provider package" and "Infoblox external IPAM
> integration"). It carries no separate per-VM license beyond the underlying Grid.
