# Chapter 5 — VMware (VCF / vSphere / NSX-T)

## 1. Overview — where DDI fits in the VMware landing zone

VMware Cloud Foundation (VCF) is the private-cloud landing zone this book anchors to.
A VCF instance is organized into a **management domain** (vCenter, NSX Manager, SDDC
Manager, and the platform's own infrastructure VMs) and one or more **workload
domains** (tenant vSphere clusters), stitched together by an **NSX** overlay of
Tier-0 and Tier-1 gateways. Unlike the hyperscalers, VMware does not hand you a
managed DNS zone service or a managed DHCP fabric. What NSX ships is deliberately
thin: a **DNS forwarder** (a stub that forwards queries to an upstream resolver, not
an authoritative server) that can run on a Tier-0 or Tier-1 gateway, and a **DHCP
service** that can act either as a small local server per segment or as a **DHCP
relay** to an external server. There is **no native enterprise IPAM** at all — NSX
tracks segment subnets, but there is no authoritative, auditable source of truth for
address space across domains, clusters, and the on-prem estate.

That gap is exactly where Infoblox slots in. On VMware, **DHCP is genuinely
Infoblox's job.** This is the sharpest difference from the CSP chapters: on Azure,
AWS, GCP, and OCI the platform owns DHCP and you cannot replace it, so Infoblox
provides DNS + IPAM and consumes the platform's leases. On VMware you own the data
path end to end, so Infoblox vNIOS members can be the *authoritative DHCP servers* for
tenant segments (via NSX DHCP relay) and the *authoritative DNS servers* that the NSX
DNS forwarder points at — while a single Grid database keeps IPAM consistent.

Because most enterprises adopting VMware already run an on-prem Infoblox Grid, the
VMware chapter is the **private-cloud/on-prem anchor** of this book. The Grid Master
(and often the whole control plane) frequently lives right here in the VCF management
domain. The CSP chapters then *extend* this Grid into each public cloud rather than
standing up a parallel one. Keep the scope discipline from Chapter 0: Infoblox
provides the **DDI + DNS-security layer inside** the VCF landing zone — it does not
deploy the SDDC, NSX, or the domain topology itself.

## 2. Reference architecture

Place the Infoblox control plane and the primary DNS/DHCP members in the **VCF
management (or a dedicated edge/services) domain**, on a management port group reachable
by every workload domain across the NSX fabric. Workload segments never talk to the
Grid Master directly; they use their local NSX gateway's DNS forwarder and DHCP relay,
which point at the Infoblox members.

```
                 VCF Management / Edge Domain (vSphere cluster)
   ┌───────────────────────────────────────────────────────────────┐
   │  vNIOS Grid Master (GM)  ──  vNIOS GM Candidate (GMC)          │
   │        │  Grid comms (VPN 1194/udp + 2114/tcp)                │
   │  vNIOS DNS/DHCP member A ── HA pair ── member B  (VRRP)        │
   │        │ MGMT port group (dvPortGroup / VMXNET3)              │
   └────────┼───────────────────────────────┬──────────────────────┘
            │ conditional fwd                │ Grid comms / SaaS sync
     ┌──────┴────────┐                ┌──────┴───────────────┐
     │ On-prem AD DNS │                │ Existing on-prem Grid │
     │ corp.example   │                │  or Universal DDI     │
     └───────────────┘                └───────────────────────┘
            ▲ NSX overlay (Geneve)             ▲ vCenter/NSX API discovery
   ┌────────┼─────────────────────────────────┼──────────────────┐
   │  NSX Tier-0 GW ── Tier-1 GW (per workload domain / tenant)   │
   │     DNS forwarder ─► vNIOS members (53/tcp+udp)              │
   │     DHCP relay ─────► vNIOS members (67-68/udp)              │
   │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐         │
   │  │ Segment/    │   │ Segment/    │   │ Segment/    │  …      │
   │  │ tenant VMs  │   │ tenant VMs  │   │ tenant VMs  │         │
   │  └─────────────┘   └─────────────┘   └─────────────┘         │
   └─────────────────────────────────────────────────────────────┘
```

**Resolution/lease flow.** A tenant VM boots on an NSX segment → DHCP `DISCOVER`
hits the Tier-1 DHCP relay → relayed to the vNIOS DHCP member, which allocates from
the IPAM-authoritative range and (optionally) writes the A/PTR record → the VM
resolves names via its assigned DNS server, which is either the vNIOS member directly
or the NSX DNS forwarder that forwards to vNIOS. Names in `corp.example` are
conditionally forwarded to on-prem AD DNS; everything else is answered or recursed by
the Grid.

## 3. Infoblox product options for VMware

| Option | What it is | On VMware |
|---|---|---|
| **vNIOS Grid (NIOS)** | Self-managed Grid of virtual appliances deployed from an **OVA/OVF** onto vSphere | **Default.** Native fit — you already own the hypervisor and data path; extends an existing on-prem Grid directly |
| **Universal DDI (SaaS)** | Infoblox-operated control plane (Infoblox Portal / CSP); lightweight on-prem hosts run DNS/DHCP | Viable for greenfield/low-ops; hosts still run as VMs on vSphere but the Grid Master burden moves to Infoblox. Requires outbound 443 to the Portal |
| **Cloud Network Automation (CNA)** | Discovery/automation adapter that discovers vCenter/NSX objects into IPAM | Add-on license on the Grid; the VMware discovery + tenant model |
| **Infoblox IPAM Plug-In for VMware Aria Automation / vRA** | External IPAM provider package registered in Aria Automation | The automation/provisioning integration for self-service catalogs |

There is **no VMware Marketplace SKU that auto-deploys the Grid** — you deploy vNIOS
from the Infoblox-provided **`.ova`** (downloaded from the Infoblox support/download
portal) using the vSphere Client or `ovftool`. Licensing is by appliance
model/subscription; the Aria Automation plug-in package is distributed via the VMware
Marketplace and the Infoblox download site and carries no separate per-VM license
beyond the underlying Grid. This chapter defaults to the **self-managed vNIOS Grid**,
because the private-cloud anchor almost always hosts the existing Grid Master.

## 4. Prerequisites

| Category | Requirement |
|---|---|
| vSphere / VCF | ESXi hosts in a cluster with DRS + HA; a management (or edge/services) workload domain; datastore (DAS, iSCSI, or FC SAN) with capacity for the chosen models |
| NSX | NSX Manager reachable; Tier-0/Tier-1 gateways for tenant domains; ability to configure DNS forwarder and DHCP relay profiles |
| Networking | A management **distributed port group** (dvPortGroup) on a vDS for Grid members; routed reachability from every tenant Tier-1 to the member VIPs; **VMXNET3** vNICs |
| Discovery creds | **vCenter read-only service account** and an **NSX API user** (least privilege — see §6) |
| Infoblox | vNIOS `.ova` for the target NIOS release; Grid license + (optionally) **Cloud Network Automation** and DNS-security (RPZ/Threat Defense) licenses |
| Aria (optional) | Aria Automation / vRA **8.9.1 or later**; Infoblox IPAM plug-in **1.5+**; Grid WAPI **v2.7+** |
| Time | Reachable **NTP** (123/udp) — Grid comms and TLS depend on time sync |

**Firewall / port-group rules.** On VMware these are enforced by NSX distributed
firewall (DFW) rules and any physical firewalls between domains:

| Service | Port(s) | Direction |
|---|---|---|
| DNS | 53 tcp + udp | Tenant/NSX forwarder → vNIOS members |
| DHCP | 67–68 udp | NSX DHCP relay → vNIOS members |
| Grid comms (VPN) | 1194/udp | Between Grid members / to GM |
| Grid replication/DB | 2114/tcp | Between Grid members / to GM |
| NTP | 123/udp | vNIOS → NTP source |
| HTTPS (mgmt / WAPI) | 443/tcp | Admins, Aria plug-in, CNA discovery → Grid |
| SNMP (monitoring) | 161/udp | NMS → vNIOS |
| Universal DDI sync (SaaS only) | 443/tcp outbound | Host → Infoblox Portal |

## 5. Step-by-step deployment

**(a) Deploy the vNIOS appliance(s) from the OVA.**

1. Download the vNIOS `.ova` for your NIOS release from the Infoblox download portal.
2. In the vSphere Client: **Deploy OVF Template** → select the `.ova` → target the
   **management/edge cluster** and a resource pool.
3. Choose the **appliance model** during OVF property entry — this sets the VM's
   vCPU/RAM (see §9 sizing table). Right-size disk; **thick-provisioned eager-zeroed**
   is recommended for DNS/DHCP database write performance (thin is acceptable for lab).
4. Map the VM's network adapter to the **management dvPortGroup**; confirm the vNIC is
   **VMXNET3** (the OVA default), not E1000.
5. For scripted/repeatable deploys, use **`ovftool`**, passing OVF properties for IP,
   netmask, gateway, and model, e.g.:

   ```
   ovftool --acceptAllEulas --datastore=DS1 \
     --net:"lan1=MGMT-dvPG" \
     --prop:default_admin_password='****' \
     --prop:temp_license=nios,dns,dhcp,cloud \
     --prop:lan1-v4_addr=10.20.10.11 \
     --prop:lan1-v4_netmask=255.255.255.0 \
     --prop:lan1-v4_gw=10.20.10.1 \
     nios.ova "vi://vcenter/DC/host/MgmtCluster"
   ```

6. Power on; the appliance boots NIOS and applies the temporary licenses.

**(b) Initial Grid setup.**
7. If this is the first appliance, promote it to **Grid Master**: set Grid name,
   shared secret, and the GM VIP. If an on-prem Grid already exists, instead **join**
   this member to it (Grid name + shared secret + GM address) — this is the common
   case, since the VMware chapter extends an existing Grid.
8. Deploy a **Grid Master Candidate** on a *different ESXi host* for control-plane HA.
9. Deploy the DNS/DHCP **member pair** and join them to the Grid.

**(c) Networking & firewall.**
10. Create NSX DFW / physical firewall rules per the port table above.
11. Enable NIOS **DNS** and **DHCP** services on the members; assign the DNS/DHCP VIPs.

**(d) HA pairing.**
12. Configure the two DNS/DHCP members as an **HA pair** — NIOS uses **VRRP** between
    the active/passive nodes over a shared VIP, so the NSX forwarder/relay targets one
    stable address. Apply **VM–VM anti-affinity** rules in vSphere DRS so the two nodes
    never run on the same ESXi host.

## 6. Cloud integration adapter (discovery & automation)

Two adapters apply on VMware, and they are complementary:

**Cloud Network Automation (CNA) — discovery.** With the CNA license on the Grid,
Infoblox connects to **vCenter** (and NSX Manager) to discover the virtual estate and
sync it into IPAM: **clusters/hosts, VMs, port groups/segments, and assigned IP
addresses**, mapped to Infoblox **networks and tenants**. This keeps IPAM reflecting
vSphere reality instead of drifting.

The discovery credential must be **least-privilege**:

| Credential | Where | Least-privilege permission |
|---|---|---|
| vCenter service account | vCenter SSO | A **read-only** role scoped to the datacenter/cluster objects — enough to enumerate clusters, VMs, port groups, and IPs. No write |
| NSX API user | NSX Manager | Read access to segments/gateways (and read/write only if NSX is to *create* networks/records via Infoblox) |
| Infoblox admin (for the adapter/plug-in) | Grid | A **custom admin group** with **cloud API access** and **IPAM + DNS + DHCP + Grid** permissions on the relevant network/DNS objects; **Tenant** permissions when CNA is licensed |

**NSX registration — automation.** NSX (in VCF 9.x, "Register Infoblox NIOS DDI with
NSX") can be pointed at the Grid so that NSX consumes Infoblox for IPAM/DNS directly.
The Infoblox side needs a **custom permission group granting IPAM, DNS, Grid, DHCP, and
Extensible Attribute** rights, which lets NSX **read network containers, create/delete
networks, allocate/release IPs, manage DNS host records, and stamp extensible
attributes** on those objects. WAPI/HTTPS on **443/tcp** carries these calls.

## 7. DNS integration with native VMware (NSX) DNS

NSX's DNS is a **forwarder**, not an authoritative server — so the integration is
simply "point the forwarder at Infoblox."

1. On the **Tier-0 or Tier-1 gateway**, configure the **DNS forwarder** with the
   vNIOS member VIP as the upstream DNS server. (When the forwarder runs on Tier-1,
   enable **route advertisement** for the DNS service IP on Tier-1 and a matching
   **route re-distribution** rule on Tier-0 so the service IP is reachable.)
2. Tenant VMs use the gateway's DNS forwarder IP as their resolver; the forwarder
   sends all queries to vNIOS.
3. On the Grid, configure **conditional forwarding** for `corp.example` (and reverse
   zones) to the **on-prem AD DNS** servers, so AD-integrated names resolve without
   making Infoblox authoritative for AD zones. Everything else is answered
   authoritatively by the Grid or recursed.
4. For split-horizon, use **DNS Views** on the Grid to present internal answers to the
   private cloud while public zones are served separately.

This makes the Grid the single resolution brain for the private cloud, with NSX acting
only as the last-hop forwarder.

## 8. IPAM discovery & automation

The Grid is the **authoritative IPAM** for the VMware private cloud. Beyond CNA
discovery (§6), the marquee automation is the **Infoblox IPAM Plug-In for VMware Aria
Automation / vRealize Automation**:

- Register Infoblox as an **external IPAM provider** in Aria Automation (download the
  provider package from the VMware Marketplace / Infoblox, add the integration point
  with Grid address + admin creds). Supported with **vRA/Aria 8.9.1+**, plug-in
  **1.5+**, WAPI **v2.7**.
- In cloud templates/blueprints, network and machine resources request address space
  and IPs from Infoblox. On deploy, the plug-in **allocates the IP, creates the
  A/PTR (host) record, and injects gateway/netmask/DNS settings into the VM** — cutting
  provisioning time and eliminating manual IP handoffs.
- **Tag-/property-driven allocation:** Infoblox **extensible attributes (EAs)** and
  Infoblox-specific template properties steer which network/range a VM draws from
  (e.g., environment, tenant, zone), so allocation follows metadata rather than
  hand-picked subnets.
- **IP reclaim on VM delete:** when Aria deprovisions the VM, the plug-in **releases
  the IP and removes the DNS records**, so leases, records, and allocations stay
  consistent automatically — the core DDI promise. CNA discovery independently reaps
  orphaned objects if a VM is deleted outside Aria.

## 9. High availability, sizing & scaling

**Grid roles & HA.** Grid Master + Grid Master Candidate for control-plane HA;
DNS/DHCP members as **VRRP HA pairs** for the data path. Spread nodes with **vSphere
DRS VM–VM anti-affinity** so an ESXi host failure never takes both halves of a pair.
Use vSphere **HA** to restart a failed node, but rely on VRRP for sub-second service
continuity. For large or multi-domain VCF, add **Anycast** DNS on members so tenants
resolve to the nearest healthy node.

**Sizing (representative — confirm against the current Infoblox vNIOS-for-VMware
installation guide for your NIOS release; models and figures are version-dependent):**

| vNIOS model | vCPU | RAM | Disk | Typical role |
|---|---|---|---|---|
| CP-V805 | 2 | 16 GB | 250 GB | Cloud Platform Appliance (WAPI/cloud API) |
| TE-V825 | 2 | 16 GB | 250 GB | DNS/DHCP member, small–mid |
| TE-V1425 | 4 | 32 GB | 250 GB | DNS/DHCP member / Grid Master, higher load |

The virtual disk is resizable up to roughly **2.5 TB** for reporting/large databases;
lab deployments can be trimmed (e.g., 2 vCPU / 2–4 GB) but must not be used in
production. Deploy a **Cloud Platform Appliance (CP-V)** member when CNA/WAPI request
volume is high — it is a member dedicated to processing cloud API requests alongside
DNS/DHCP, and you can run several for scale/redundancy.

## 10. Security & compliance considerations

- **Least-privilege discovery:** vCenter service account is **read-only**; the NSX and
  Grid API users get only the object-scoped rights in §6. No shared admin accounts.
- **RBAC:** NIOS admin groups scoped by role (DNS ops, DHCP ops, IPAM, tenant admins);
  integrate NIOS admin auth with the enterprise IdP where possible.
- **Encryption & hardening:** HTTPS/WAPI on 443 with valid certs; disable unused
  services; keep Grid comms (1194/udp, 2114/tcp) confined to a management segment via
  NSX DFW micro-segmentation.
- **DNS security:** enable **RPZ / Infoblox Threat Defense** feeds on the members so
  the private cloud's resolvers block malicious domains and provide DNS-based
  exfiltration detection — a capability the bare NSX forwarder cannot offer.
- **Audit/logging:** ship NIOS syslog and DNS/DHCP query/lease logs to the SIEM;
  IPAM change history provides an auditable allocation trail.
- **Sovereignty:** because vNIOS runs entirely inside your VCF (self-contained Grid),
  the private-cloud deployment is air-gap-friendly and suits gov/regulated estates.
  If you adopt **Universal DDI** instead, note the required **outbound 443** to the
  Infoblox Portal, which may be disallowed in sovereign zones.

## 11. Validation & Day-2 operations

**Validation checklist.**

1. **Resolve a record:** from a tenant VM, `dig app.corp.example @<NSX-forwarder-IP>`
   and confirm the answer traces back to a vNIOS member.
2. **Conditional forwarding:** resolve an AD-only name and confirm it is answered by
   on-prem AD DNS via the Grid's conditional forwarder.
3. **DHCP:** boot a VM on a segment with NSX **DHCP relay**; confirm it receives an
   address from the Infoblox range and that an A/PTR record appears in IPAM.
4. **Discovery:** confirm CNA shows the expected clusters, VMs, port groups, and IPs,
   mapped to the right tenant/network.
5. **Aria lifecycle:** deploy a catalog item → verify IP + DNS record created and
   injected; delete it → verify **IP and records are reclaimed**.
6. **Failover:** power off the active HA member; confirm VRRP moves the VIP and DNS/DHCP
   continue; confirm DRS anti-affinity kept nodes on separate hosts.

**Day-2 operations.** Patch/upgrade NIOS via the Grid (rolling, GM-coordinated —
snapshot/back up the Grid DB first); monitor member health, DNS query rate, and DHCP
pool utilization via SNMP/Infoblox reporting; periodically reconcile CNA discovery
against vCenter to catch drift; review RPZ hit logs; and rotate the vCenter/NSX/Grid
API credentials on the enterprise schedule.

## Sources

- [Infoblox — vNIOS Deployment on VMware vSphere (deployment guide)](https://www.infoblox.com/resources/deployment-guides/vnios-deployment-on-vmware-vsphere)
- [Infoblox Docs — About Infoblox NIOS Virtual Appliance for VMware](https://docs.infoblox.com/space/NVIG/35786250/About+Infoblox+NIOS+Virtual+Appliance+for+VMware)
- [Infoblox Docs — Installing the NIOS Virtual or Reporting Virtual Appliance](https://docs.infoblox.com/space/NVIG/35483668/Installing+the+NIOS+Virtual+or+Reporting+Virtual+Appliance)
- [Infoblox Docs — vNIOS Appliances (models & sizing)](https://docs.infoblox.com/space/nios85/35479116)
- [Infoblox Docs — Introduction, IPAM Plug-In for VMware (Aria/vRA)](https://docs.infoblox.com/space/ipamvmware8x/52048987/Introduction)
- [Infoblox Docs — Installing Infoblox IPAM Plug-In for VMware (Aria Automation Provider for NIOS DDI)](https://docs.infoblox.com/space/ipamvmware8x/52593807/Installing+Infoblox+IPAM+Plug-In+for+VMware)
- [Infoblox — Cloud Network Automation](https://www.infoblox.com/products/cloud-network-automation/)
- [Infoblox Docs — Cloud Network Automation (NIOS 9.0)](https://docs.infoblox.com/space/nios90/280407487)
- [Infoblox — IPAM Plug-in for VMware vRA 8 (deployment guide PDF)](https://www.infoblox.com/wp-content/uploads/infoblox-deployment-guide-infoblox-ipam-plugin-for-vmware-vra-8.pdf)
- [Broadcom TechDocs — Register Infoblox NIOS DDI with NSX (VCF 9.x)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/advanced-network-management/ip-address-management-ipam/integrate-nsx-with-infoblox.html)
- [Broadcom TechDocs — Download and deploy an external IPAM provider package (Aria Automation)](https://techdocs.broadcom.com/us/en/vmware-cis/aria/aria-automation/8-16/assembler-on-prem-using-and-managing-master-map-8-16/starter-kit-introduction/infoblox-external-ipam-integration-use-case-grouper/download-and-deploy-an-external-provider-ipam-package.html)
- [Broadcom TechDocs — Infoblox-specific properties & extensible attributes for IPAM in Aria Automation](https://techdocs.broadcom.com/us/en/vmware-cis/aria/aria-automation/8-16/assembler-on-prem-using-and-managing-master-map-8-16/starter-kit-introduction/infoblox-external-ipam-integration-use-case-grouper/using-infloblox-specific-properties-for-external-ipam.html)
- [Broadcom TechDocs — Configure DHCP Relay on an NSX Segment](https://techdocs.broadcom.com/us/en/vmware-cis/nsx/vmware-nsx/4-2/administration-guide/nsx-dhcp-policy-ui/configure-nsx-dhcp-service/configure-dhcp-relay-on-an-nsx-segment.html)
- [Broadcom TechDocs — Attach a DHCP Profile to a Tier-0 or Tier-1 Gateway](https://techdocs.broadcom.com/us/en/vmware-cis/nsx/nsxt-dc/3-0/administration-guide/ip-address-management-ipam/attach-an-nsx-dhcp-profile-to-a-tier-0-or-tier-1-gateway.html)
