# Chapter 3 — Google Cloud

## 1. Overview — where DDI fits in the Google Cloud landing zone

Google Cloud gives you a capable but deliberately narrow native name-resolution
stack. **Cloud DNS** is a managed authoritative service with public zones, private
zones (visible only inside authorized VPC networks), **forwarding zones** (send a
domain's queries to specified name servers), **peering zones** (resolve a domain
using another VPC's Cloud DNS configuration), and **DNS server policies** that turn
inbound and/or outbound forwarding on for a whole VPC. DHCP is entirely
platform-managed: every VM leases its primary IP from the subnet and points at the
metadata resolver `169.254.169.254`, which fronts Cloud DNS. There is no first-class
IPAM — subnet ranges are visible per-VPC, but there is no authoritative, cross-
project, cross-cloud address database.

Those gaps show up the moment a landing zone spans more than one project or reaches
back to on-prem and other clouds. Cloud DNS private zones and peering are per-VPC
constructs; stitching consistent split-horizon resolution and one reverse-DNS
authority across dozens of Shared VPC service projects, plus AWS/Azure/on-prem, is
exactly what native tooling does not do. And there is no single pane that says "this
/16 is allocated, these addresses are in use, this record and this lease belong to
that subnet."

**Infoblox slots into the Google Cloud landing zone as the DDI + DNS-security layer.**
In the Google Cloud landing-zone / Cross-Cloud Network model the recommended home is
the **hub (host) VPC** of a **Shared VPC**: Infoblox DNS/DHCP members live there,
workload service projects consume the shared network and forward DNS to them, the
members conditionally forward to Cloud DNS for `*.googleapis.com` / private-zone names
and to on-prem/other clouds for everything else, and the discovery adapter keeps IPAM
synchronized with the real VPCs and subnets. As always in this volume, Infoblox provides
the DDI layer *within* the landing zone — the project hierarchy, org policy, and
Shared VPC itself come from the Google Cloud foundation blueprint.

## 2. Reference architecture

![GCP reference architecture: anycast vNIOS members in the host-project Shared VPC hub, service-project workloads resolving via 169.254.169.254 to Cloud DNS server policies that forward to the members, conditional-forward of googleapis/private names back to Cloud DNS, and a least-privilege discovery service account syncing VPCs into IPAM](figs/gcp-ch-01-reference-architecture.png)

The control plane is either an on-prem/hub **NIOS Grid Master (+ Grid Master
Candidate)** or the **Universal DDI** SaaS portal. Data-plane **vNIOS members**
providing DNS (and DHCP where you override Google's managed DHCP for specific
subnets) live in the Shared VPC host project. Because a **GCP network interface binds
to exactly one VPC network** (there is no multi-VPC single-NIC vNIC), a member that
must touch two VPCs uses **two NICs on two VPCs**; a member serving one Shared VPC
uses a single NIC. Management (Grid VPN) and DNS data typically ride the same
interface in cloud unless you split them across the two NICs.

```
                    ┌───────────────────────────────────────────────┐
   On-prem DC ──────┤  Grid Master / GMC   OR   Universal DDI portal │
  (existing Grid /  │  control plane (mgmt), Cloud Interconnect/VPN  │
   Interconnect)    └───────────────────────┬───────────────────────┘
                                            │ Grid VPN 1194/udp + 2114/tcp
                                            │  (or 443 SaaS sync)
  ┌─────────────────────────────────────────┴──────────────────────────────┐
  │ Host project — HUB / Shared VPC (connectivity landing zone)             │
  │   • vNIOS member A (zone us-central1-a)   • vNIOS member B (…-b) anycast│
  │   • Inbound DNS server policy  → GCP forwards to Infoblox               │
  │   • Outbound policy / alt name server → VMs resolve via Infoblox        │
  │   • Conditional forward ↔ Cloud DNS private zones & googleapis.com      │
  └──────────┬───────────────────────────────────────────┬─────────────────┘
             │ Shared VPC subnet share / DNS peering      │
  ┌──────────┴──────────┐                      ┌──────────┴──────────┐
  │ Service project 1   │                      │ Service project 2   │
  │  workload subnets   │                      │  workload subnets   │
  │  VMs → 169.254.169.254 → Cloud DNS → Infoblox                   │
  └─────────────────────┘                      └─────────────────────┘
```

Resolution flow: a VM queries `169.254.169.254`; Cloud DNS applies the VPC's server
policy / forwarding / peering zones; internal-corp and reverse names go to the
Infoblox members; Google-service and Cloud-DNS-private names stay in Cloud DNS; the
Infoblox members conditionally forward on-prem and other-cloud domains over
Interconnect/VPN.

## 3. Infoblox product options for Google Cloud

| Option | What it is | Marketplace / licensing |
|---|---|---|
| **vNIOS Grid** | Self-managed NIOS appliances forming a Grid in your projects | **Infoblox vNIOS for Google Cloud** on Google Cloud Marketplace, or a custom image from an Infoblox-supplied disk; BYOL (grid/member licenses) or, historically, PAYG SKUs | 
| **Universal DDI (SaaS)** | Infoblox-operated control plane (Infoblox Portal / CSP); lightweight managed hosts run DNS/DHCP on GCP | **Infoblox Universal DDI for Google's Cloud WAN** listing on Marketplace; subscription | 
| **Cloud Network Automation / vDiscovery** | Discovery+automation adapter that syncs GCP VPCs/subnets/VMs into IPAM; works with either control plane | Feature of NIOS/Universal DDI; no separate VM | 
| **DNS Armor (Google Cloud)** | Google-native protective-DNS service powered by Infoblox threat intel (GA since Jan 2026) | Consumed as a Google Cloud service; complements, not replaces, DDI | 

Default guidance: enterprises **extending an existing on-prem Grid** into GCP pick
**vNIOS**; greenfield multi-cloud teams wanting low-ops centralized management pick
**Universal DDI**. Both can use Cloud Network Automation / vDiscovery for IPAM sync.

## 4. Prerequisites

| Area | Requirement |
|---|---|
| Project/org | Host project for the Shared VPC; service projects onboarded; Org/Project IDs for discovery scope |
| IAM (deploy) | `roles/compute.instanceAdmin.v1`, `roles/compute.networkAdmin`, `roles/iam.serviceAccountUser` for the deployer |
| IAM (discovery SA) | Least-privilege service account — see §6 (`roles/compute.viewer` + `roles/dns.reader`, or a custom role) |
| Machine type | **N1** general-purpose series; size per target vNIOS model (e.g. small lab vs. TE/production models — confirm the vCPU/RAM mapping for your NIOS version in the deployment guide) |
| NICs / VPC | 1 NIC (single Shared VPC) or 2 NICs on 2 VPCs — GCP binds one NIC per VPC |
| Disk | Persistent disk sized to the model (e.g. ~250 GB class for production models; confirm per model/version) |
| Region/zone | Place members in ≥2 **zones** of the region(s) you serve for HA |
| Firewall | VPC firewall rules for the ports in §5 |
| Licensing | vNIOS grid + member (and DNS/DHCP/Security) licenses, or Universal DDI subscription |
| Connectivity | Cloud Interconnect or HA VPN to on-prem for Grid VPN / conditional forwarding |

## 5. Step-by-step deployment

1. **Provision the network.** In the host project create the Shared VPC, the
   management/hub subnet(s) in each target region, and share the relevant subnets to
   the service projects. Reserve static internal IPs for each member.

2. **Deploy the appliance(s).** From Google Cloud Marketplace launch **Infoblox
   vNIOS for Google Cloud** (or create instances from the custom vNIOS image). In
   *Machine configuration* pick **General purpose → N1**, then the machine type that
   matches your NIOS model. Choose **Two network interfaces** only if the member must
   attach to two VPCs (one NIC per VPC); otherwise **Single network interface**.
   Attach the persistent disk sized for the model. Pass initial config (host name,
   temp licenses, LAN1 IP/gateway) via the instance startup/user-data as the guide
   describes.

3. **Firewall rules (VPC firewall).** Apply, scoped by network tag/service account:

   | Purpose | Protocol / Port | Direction |
   |---|---|---|
   | DNS | 53 tcp **and** udp | ingress to members; egress to forwarders |
   | DHCP (if used) | 67–68 udp | on served subnets |
   | Grid VPN (member↔GM sync) | **1194 udp** | between members & Grid Master |
   | Grid comms (GM promotion, mgmt) | **2114 tcp** | between members & Grid Master |
   | NTP | 123 udp | members ↔ time source |
   | HTTPS / GUI / API | 443 tcp | admin to Grid Master; Universal DDI sync outbound 443 |
   | SNMP (optional) | 161 udp | monitoring |

   Note the metadata resolver `169.254.169.254` is the DNS next-hop for VMs before
   Cloud DNS forwards onward — you do not firewall it, but it is the reason
   VPC-level server policies (not per-VM config) drive resolution.

4. **Initial Grid setup (vNIOS).** Bring up the first appliance as **Grid Master**,
   set the Grid name/shared secret, then join member VMs to the Grid over the VPN
   (1194/udp, 2114/tcp). For **Universal DDI**, instead register the managed hosts to
   the Infoblox Portal and let them pull config over outbound 443.

5. **HA pairing.** In cloud, Infoblox HA is normally achieved by placing **two or
   more members in different zones** and using **anycast** or client-side multiple
   resolvers, rather than the classic VRRP HA pair (which needs a shared L2 the GCP
   network model does not provide). Configure the Grid Master Candidate in a separate
   zone/region for control-plane resilience.

## 6. Cloud integration adapter (discovery & automation)

Infoblox **Cloud Network Automation** runs a **GCP vDiscovery** task that enumerates
projects, VPC networks, subnets, and VM instances (with their internal/external IPs,
tags, and labels) and synchronizes them into IPAM so networks and fixed addresses
reflect GCP reality instead of drifting.

The credential object is a **GCP service account** (key or, where supported,
workload-identity binding) granted **least-privilege read** roles:

| Role | Purpose |
|---|---|
| `roles/compute.viewer` (Compute Viewer) | Read VPCs, subnets, instances, addresses |
| `roles/dns.reader` | Read Cloud DNS zones/records for DNS discovery |
| `roles/viewer` (Project Viewer) | Broad read fallback if a custom role is not used |

Prefer a **custom role** scoped to the exact `compute.networks.*`,
`compute.subnetworks.*`, `compute.instances.*`, `compute.addresses.*` (list/get) and
`dns.*.list/get` permissions rather than the broad `roles/viewer`. Scope the service
account at **org or folder level** to discover many projects at once, or per-project
for tighter blast radius. In a Shared VPC, grant it read on the **host project** (for
the shared networks/subnets) *and* on each **service project** you want VM-level
discovery for.

## 7. DNS integration with native Google Cloud DNS

Wire both directions; they are independent VPC-level constructs.

**Inbound (GCP → Infoblox, and letting Infoblox/on-prem query into GCP).** Create an
**inbound DNS server policy** on the Shared VPC. Cloud DNS then allocates **inbound
forwarder IP addresses** from the primary IPv4 ranges of the VPC's subnets; on-prem or
the Infoblox members target those IPs to resolve Cloud DNS private-zone names.

**Outbound (VMs resolve via Infoblox).** Two mechanisms:
- **Outbound server policy with alternative name servers** — point the whole VPC's
  resolution at the Infoblox member IPs. Cloud DNS classifies each alternative name
  server by IP: an RFC 1918 address on an authorized VPC is **Type 1/Type 2** (private
  routing); a non-RFC-1918 target is **Type 3**. For Type 2 private routing to
  members reached over Interconnect/VPN, your network must return-route
  **`35.199.192.0/19`** back through the same VPC.
- **Forwarding zones** — create a Cloud DNS **forwarding zone** for specific domains
  (e.g. `corp.example.`, in-addr reverse zones) whose targets are the Infoblox member
  IPs, leaving `*.googleapis.com` and Cloud DNS private zones resolving natively.

**Split-horizon & scale-out.** Use **peering zones** so service-project VPCs resolve
via the hub VPC's Cloud DNS config: a single outbound forwarding zone lives in the
hub VPC and all spoke VPCs peer to it, so every project's on-prem/corp queries funnel
through the hub to the Infoblox members. On the Infoblox side, create matching
**conditional forwarders** back to Cloud DNS inbound forwarder IPs for GCP-internal
domains, giving true bidirectional resolution.

## 8. IPAM discovery & automation

Onboard by scope: point vDiscovery at the **org, folder, or project** set you want
authoritative. Discovered VPCs/subnets become IPAM networks; VM primary/alias IPs and
reserved addresses become fixed addresses/host records. In a **Shared VPC** the
subnets are defined in the **host project** but consumed by **service projects** — so
discover the host project for the address space and the service projects for the
workloads that occupy it, and IPAM will attribute usage correctly.

Drive allocation from GCP **labels and network tags**: map a label such as
`env=prod` or `app=payments` to an Infoblox network view / extensible attribute so new
subnets land in the right container and records inherit ownership metadata. Re-running
vDiscovery on a schedule reconciles adds/moves/deletes; because DHCP for most GCP
subnets is Google-managed, IPAM tracks those as discovered/leased-by-platform while
Infoblox remains the authoritative record for allocations, reservations, and DNS.

## 9. High availability, sizing & scaling

- **Grid roles:** one Grid Master + a Grid Master Candidate (separate zone/region);
  DNS/DHCP-serving **members** in the data path.
- **Zonal spread:** deploy ≥2 members across zones of a region; add members in other
  regions for locality and blast-radius reduction.
- **Anycast** DNS across members (advertised via the members) is the preferred way to
  present a single resolver VIP without L2-VRRP HA, which the GCP network does not
  support.
- **Sizing:** choose the **N1** machine type matching the target vNIOS model's
  vCPU/RAM; validate the exact model→machine-type→disk mapping in the current
  deployment guide, as it is **NIOS-version dependent**.
- **Scaling:** scale horizontally by adding members/regions and steering clients via
  server policies/peering zones per VPC rather than vertically resizing one member.

## 10. Security & compliance considerations

- **Hardening:** restrict VPC firewall rules to member network tags/service accounts;
  keep the Grid Master off any public IP; use IAM-scoped, least-privilege discovery
  service accounts (§6) and rotate keys or use workload identity.
- **Encryption & RBAC:** Grid traffic is carried over the encrypted Grid VPN (1194);
  use NIOS RBAC / admin groups (or Universal DDI RBAC) and per-project IAM separation.
- **Logging/audit:** ship NIOS syslog and query logging to Cloud Logging; enable
  Cloud Audit Logs on the discovery service account's read activity.
- **DNS security:** layer Infoblox **threat-intel feeds** and **RPZ** on the members
  for protective DNS; for a Google-native option, **DNS Armor** (powered by Infoblox,
  GA Jan 2026) inspects internet-bound VM DNS for malicious activity.
- **Sovereignty / gov:** for regulated workloads use **Assured Workloads** folders to
  pin data residency and personnel controls; confirm the vNIOS image/Marketplace SKU
  and Universal DDI Portal region are eligible for your controlled environment, since
  Universal DDI requires outbound 443 to the Infoblox Portal — an air-gapped or
  strict-sovereignty posture favors the self-contained **vNIOS Grid**.

## 11. Validation & Day-2 operations

**Validation checklist**
1. From a workload VM, `dig app.corp.example` resolves via Infoblox (query appears in
   NIOS logs); `dig storage.googleapis.com` still resolves natively.
2. Reverse lookup of a workload IP returns the expected PTR from Infoblox.
3. From on-prem, resolve a Cloud DNS private-zone name through the **inbound forwarder
   IPs**.
4. vDiscovery run completes; a newly created subnet/VM appears in IPAM within a cycle.
5. **Failover test:** stop the primary member's DNS service (or the VM) and confirm
   the second zone's member/anycast VIP keeps answering; promote the GMC in a drill.

**Day-2 operations**
- Schedule vDiscovery and reconcile IPAM drift; review label→network-view mappings as
  new projects onboard.
- Patch/upgrade NIOS on the Grid Master first, then members (rolling, zone by zone);
  for Universal DDI the Portal manages control-plane updates.
- Monitor member health, query rates, and RPZ/threat-feed hits via Cloud Monitoring
  and Infoblox reporting; alert on discovery-SA auth failures and forwarding-zone
  errors.
- Keep the `35.199.192.0/19` return route and forwarding-zone/peering config under
  change control — they are the usual causes of "GCP can't reach Infoblox" incidents.

## Sources

- [Infoblox — About Infoblox vNIOS for Google Cloud](https://docs.infoblox.com/space/vniosgcp/35786143)
- [Infoblox — Supported Deployment Methods for vNIOS for GCP](https://docs.infoblox.com/space/vniosgcp/35850457/Supported+Deployment+Methods+for+Infoblox+vNIOS+for+GCP)
- [Infoblox — Deploying vNIOS for Google Cloud](https://docs.infoblox.com/space/vniosgcp/35449584/Deploying+vNIOS+for+Google+Cloud)
- [Infoblox — Creating GCP Service Account](https://docs.infoblox.com/space/vniosgcp/35483395/Creating+GCP+Service+Account)
- [Infoblox — Performing GCP vDiscovery](https://docs.infoblox.com/space/vniosgcp/46268552)
- [Infoblox — Creating a Cloud DNS Policy](https://docs.infoblox.com/space/vniosgcp/35419584)
- [Infoblox — Prerequisites for Google Cloud DNS Integration](https://docs.infoblox.com/space/vniosgcp/844562479/Prerequisites+for+Google+Cloud+DNS+Integration)
- [Infoblox — vNIOS for GCP Deployment Guide (PDF)](https://www.infoblox.com/wp-content/uploads/infoblox-deployment-guide-infoblox-vnios-for-google-cloud-platform.pdf)
- [Infoblox — Cloud Network Automation](https://www.infoblox.com/products/cloud-network-automation/)
- [Infoblox — Creating a Custom Role in GCP (Universal DDI)](https://docs.infoblox.com/space/BloxOneDDI/847184633/Creating+a+Custom+Role+in+GCP)
- [Infoblox — Universal DDI for Google's Cloud WAN and DNS Armor](https://www.infoblox.com/partners/google-cloud/)
- [Infoblox & Google Cloud partnership press release](https://www.infoblox.com/news/news-events/press-releases/infoblox-and-google-cloud-announce-partnership-to-deliver-cloud-native-networking-and-security-solutions-reducing-complexity-for-enterprise-customers/)
- [Google Cloud — DNS server policies overview](https://docs.cloud.google.com/dns/docs/server-policies-overview)
- [Google Cloud — Configure DNS server policies](https://docs.cloud.google.com/dns/docs/policies)
- [Google Cloud — DNS zones overview](https://docs.cloud.google.com/dns/docs/zones/zones-overview)
- [Google Cloud — Cloud forwarding, peering and zones](https://cloud.google.com/blog/products/networking/cloud-forwarding-peering-and-zones)
- [Google Cloud — Cloud DNS peering in a Shared VPC environment](https://cloud.google.com/blog/products/networking/how-to-use-cloud-dns-peering-in-a-shared-vpc-environment/)
- [Google Cloud — Landing zone design](https://cloud.google.com/architecture/landing-zones)
