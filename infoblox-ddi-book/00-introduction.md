# Chapter 0 — Introduction: DDI in the Multi-Cloud Landing Zone

> **Scope note — breadth exception.** This kit is also **Volume VIII** of the
> Federal Application-Aware Networking series. It is **intentionally multi-CSP**
> (Azure, AWS, Google Cloud, OCI, VMware) — the one deliberate breadth exception
> to the series' current **FedRAMP Moderate + Microsoft GCC Moderate** scope, by
> author direction. Federal control closure is operated at the GCC-Moderate
> ServiceNow front door (Chapter 7); the per-cloud chapters are CSP-agnostic
> mechanism build-out. Treat the non-Azure chapters as reference architecture,
> not an in-scope authorization surface, unless your own boundary covers them.

## 0.1 What this volume is

This is an implementation volume. Each chapter takes one target platform — a public
cloud service provider (CSP) or VMware private cloud — and walks an architect or
platform engineer from a blank landing zone to a working, production-grade Infoblox
**DDI** (DNS, DHCP, IP Address Management) and DNS-security layer inside it.

Every platform chapter follows the identical 11-section skeleton defined in
[`_conventions.md`](./_conventions.md): overview → reference architecture → product
options → prerequisites → deployment runbook → cloud discovery adapter → native-DNS
integration → IPAM automation → HA/sizing → security/compliance → validation & Day-2.
Read a chapter end-to-end to deploy one platform; read the same section across
chapters to compare how a single concern (say, DNS forwarding) differs between clouds.

| Ch. | Platform | Native DDI baseline it augments |
|-----|----------|--------------------------------|
| 1 | Microsoft Azure | Azure DNS (public/private zones), Azure DHCP (platform-managed), no native IPAM (Azure IPAM is a sample app) |
| 2 | Amazon Web Services | Route 53 (public/Resolver/private zones), VPC DHCP option sets, VPC IPAM |
| 3 | Google Cloud | Cloud DNS (public/private/peering zones), platform-managed DHCP, no first-class IPAM |
| 4 | Oracle Cloud (OCI) | OCI DNS (private views/resolvers), platform-managed DHCP, no native IPAM |
| 5 | VMware (VCF / vSphere / NSX-T) | NSX-T DHCP/DNS forwarder, no native enterprise IPAM |

## 0.2 What DDI is, and why it belongs in a landing zone

**DDI** bundles the three interdependent network-foundation services:

- **DNS (Domain Name System)** — name-to-address resolution (`app.corp.example` →
  `10.20.4.7`) and reverse. Everything finds everything else by name.
- **DHCP (Dynamic Host Configuration Protocol)** — automatic assignment of addresses
  and network options (gateway, DNS servers, mask) as devices join.
- **IPAM (IP Address Management)** — the authoritative record of subnets, allocations,
  reservations, and ownership. It is the source of truth that keeps DNS and DHCP
  consistent.

They are grouped because they are mutually dependent: DHCP hands out an address, that
address needs a DNS record, and IPAM must know about both to prevent conflicts. Run
them in disconnected tools (spreadsheets, per-cloud native services, manual edits) and
you get **drift** — overlapping CIDRs, stale records, and outages. A **DDI platform**
manages all three from one system on a shared database so an allocation, a lease, and a
record stay consistent automatically.

A **landing zone** is a cloud provider's blueprint for a governed, scalable
environment (Azure Cloud Adoption Framework landing zones, AWS Control Tower /
Landing Zone Accelerator, Google Cloud Foundation, OCI Landing Zone, VMware Cloud
Foundation). Every one of these blueprints has a **network topology & connectivity**
design area — hub-and-spoke or transit-fabric connectivity, hybrid links back to
on-prem, and name resolution across all of it. DDI is precisely that design area's
foundation. Native cloud DNS/DHCP handles a single cloud adequately; the moment you
have **multiple clouds plus on-prem** you need one authoritative IPAM and one
consistent, secure resolution fabric spanning them all. That is the job Infoblox does
*inside* the landing zone.

> **Scope discipline.** Infoblox does **not** deploy the whole landing zone
> (management-group/OU hierarchy, identity, governance policy, compute). Those come
> from the platform's own landing-zone accelerator or a systems integrator. Infoblox
> provides the **DDI + DNS-security layer within** that landing zone. Every chapter
> keeps this framing.

## 0.3 The Infoblox product families you will deploy

Two control-plane models, plus a cloud-integration layer that works with either:

### NIOS + vNIOS (the Grid) — self-managed
The classic Infoblox platform. **NIOS** is the OS; a **Grid** is a clustered set of
appliances with one Grid Master (and Grid Master Candidate) and multiple members, all
sharing one distributed database. **vNIOS** is the virtual-appliance form deployed from
each cloud's marketplace (or an OVA for VMware). You own and operate the control plane.
Best when you already run an on-prem Infoblox Grid and want to **extend** it into cloud,
or when data-plane sovereignty requires the control plane inside your own tenancy.

### Universal DDI (formerly BloxOne DDI) — SaaS-managed
Infoblox operates the control plane as a cloud service (the **Infoblox Portal**, a.k.a.
Cloud Services Portal / CSP). You deploy lightweight on-prem/on-cloud **hosts** that run
DNS/DHCP under central SaaS management. Best for greenfield multi-cloud, where you want
centralized management without operating Grid Masters yourself. (Note: Infoblox's own
term *CSP* means **Cloud Services Portal** — not the cloud service providers this volume's
chapters cover.)

### Cloud discovery & automation (Universal Cloud / Cloud Network Automation)
The integration layer that connects either control plane to each CSP's control plane.
Using a per-platform credential (Azure service principal, AWS IAM role, GCP service
account, OCI API key), it **discovers** VNets/VPCs/VCNs, subnets, and cloud DNS zones,
and **synchronizes** them into Infoblox IPAM — so IPAM reflects cloud reality instead of
drifting from it. This is what turns Infoblox from "DNS servers in the cloud" into
"authoritative IPAM for the cloud."

| Concern | NIOS / vNIOS Grid | Universal DDI (SaaS) |
|---|---|---|
| Control plane | You operate Grid Master(s) | Infoblox operates (Portal/CSP) |
| Deployment unit | vNIOS appliance (Marketplace/OVA) | Managed host / service |
| Best for | Extending existing on-prem Grid; sovereign control plane | Greenfield multi-cloud; low-ops |
| Cloud discovery | Cloud Network Automation | Universal Cloud discovery |
| Air-gapped / gov cloud | Fully self-contained | Requires outbound 443 to Portal |

Each chapter states which model(s) apply on that platform and defaults to the one most
enterprises pick there.

## 0.4 A shared reference architecture (the pattern every chapter specializes)

![Shared hub-and-spoke DDI reference architecture: an on-prem Grid Master/GMC (or Universal DDI) drives anycast vNIOS DNS/DHCP members in the cloud hub, workload spokes forward DNS to them, members conditionally forward to native cloud DNS, and the discovery adapter syncs cloud VNets/VPCs into the authoritative Infoblox IPAM](figs/intro-01-shared-reference-architecture.png)

```
                    ┌──────────────────────────────────────────┐
   On-prem DC ──────┤  Grid Master / GMC  or  Universal DDI     │
   (existing Grid)  │  control plane (mgmt subnet, hub)         │
                    └───────────────┬──────────────────────────┘
                                    │ Grid comms / SaaS sync
        ┌───────────────────────────┼───────────────────────────┐
        │ Hub VNet/VPC (connectivity landing zone)               │
        │   • vNIOS members (DNS/DHCP anycast)                   │
        │   • Conditional forwarding ↔ native cloud DNS         │
        └───────┬───────────────────────────────┬───────────────┘
                │ peering / transit             │
        ┌───────┴────────┐             ┌────────┴────────┐
        │ Spoke: workload │            │ Spoke: workload │
        │  VNet/VPC       │            │  VNet/VPC       │
        └─────────────────┘            └─────────────────┘
```

The recurring pattern: **Infoblox DNS/DHCP members live in the hub (connectivity)
landing zone**; workload spokes forward DNS to them; the members conditionally forward
to each cloud's native private DNS for cloud-service names; the discovery adapter keeps
IPAM synchronized with the cloud's real VNets/VPCs; and everything ties back to a single
authoritative control plane (on-prem Grid Master or Universal DDI SaaS) so IPAM is
consistent across every cloud and on-prem. Each platform chapter fills in the concrete
resource names, ports, IAM objects, and click/CLI/IaC steps.

## 0.5 The governed front door (ServiceNow)

Deploying the fabric is half the story; **operating** it in a governed enterprise is the
other half. Every platform chapter's provisioning process — allocate a subnet, register a
record, reclaim on delete — can be driven directly by an engineer *or* fronted by a
**ServiceNow** self-service catalog so the same actions are **requested, approved, and
audited**. The Infoblox calls and the validation checks are identical; ServiceNow adds the
approval / separation-of-duties gate, the change record, and the closed-loop CMDB sync that
keeps the ITSM system reflecting reality instead of guessing it.

![ServiceNow closed-loop for DDI: a catalog request is approved in Flow Designer, the CPG Terraform Connector plans and applies the platform module, Infoblox allocates and registers via WAPI/Universal DDI, a MID Server gate runs the validation checks, the Service Graph Connector syncs the result into the CMDB, and the request closes with a full audit trail while a failed gate returns to approval](figs/sn-01-closed-loop.png)

This is **assembly of certified products** — ServiceNow's CPG Terraform Connector and the
Service Graph Connector for Infoblox — not custom glue. It appears here, in the framing
chapter, because it is part of the **target operating model**, not an afterthought:
[Chapter 7](./07-servicenow-orchestration.md) develops it in full, **each platform chapter's
section 8 shows the platform-specific loop** over that platform's Terraform module and
validation scripts, and [`servicenow-app/`](./servicenow-app/README.md) is an importable
starting point (Script Includes, REST Message, Flow blueprint, MID gate). The boundary
discipline the rest of the volume applies holds here too — the MID Server that runs
Terraform and the validation gate stays **inside the ATO boundary**, and the Universal DDI
SaaS path is the explicit, `acknowledge_saas_boundary`-gated exception.

## 0.6 How to read this volume

- **Deploying one platform now?** Jump straight to its chapter and work the runbook.
- **Designing the multi-cloud target state?** Read section 1 (overview) and 2
  (reference architecture) of every chapter, then the cross-platform operations
  appendix, before touching a single deployment.
- **Standardizing?** The identical skeleton means you can lift the section-5 runbooks
  into your own IaC/pipeline and the section-4 prerequisites into your landing-zone
  guardrails.

---

*Sources for this chapter:*
- [Infoblox — Universal DDI](https://www.infoblox.com/products/universal-ddi/)
- [Infoblox — NIOS DDI](https://www.infoblox.com/products/nios/)
- [Microsoft — What is an Azure landing zone? (CAF)](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/)
- [AWS — Landing Zone Accelerator / Control Tower](https://aws.amazon.com/solutions/implementations/landing-zone-accelerator-on-aws/)
- [Google Cloud — Landing zone design](https://cloud.google.com/architecture/landing-zones)
- [Oracle — OCI Core Landing Zone](https://docs.oracle.com/en-us/iaas/Content/cloud-adoption-framework/oci-core-landing-zone.htm)
