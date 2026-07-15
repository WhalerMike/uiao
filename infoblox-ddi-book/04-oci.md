# Chapter 4 — Oracle Cloud Infrastructure

## 1. Overview — where DDI fits in the OCI landing zone

Oracle Cloud Infrastructure (OCI) ships a competent-but-partial native DDI
story. **OCI DNS** provides public zones and, since the private-DNS overhaul, a
proper private layer: every VCN gets a **private view** (a container of private
zones), every subnet auto-creates a private zone inside that view, and each VCN
has a **DNS resolver** you can extend with **listening** and **forwarding
endpoints** plus forwarding rules. **DHCP is platform-managed** — a VCN hands
out addresses, gateway, and the resolver IP (`169.254.169.254`) through DHCP
options you configure per subnet, but you do not run a DHCP server and cannot
express reservations or fine-grained option policy the way an enterprise expects.
And there is **no native IPAM**: OCI tracks CIDRs per VCN/subnet, but nothing
gives you an authoritative, cross-tenancy, cross-cloud, cross-on-prem view of
address space, allocations, and ownership.

Those gaps are exactly what bite at enterprise scale. The moment OCI is one of
several clouds — plus on-prem — you need a single source of truth for IP space,
one consistent forward/reverse DNS namespace, and one place to apply DNS security
(RPZ, threat feeds). OCI's private views resolve *within* and *between* VCNs
well, but they are not a multi-cloud IPAM and they are not a DNS-security control
plane.

Infoblox slots into the **hub VCN** of an OCI landing zone (the connectivity
compartment of the CIS/Core Landing Zone) as the DDI + DNS-security layer. vNIOS
Grid members run as OCI compute instances in the hub, spoke VCNs forward DNS to
them over the **DRG**, and the members conditionally forward OCI-service and
private-zone names back to the OCI resolver while owning the authoritative
enterprise namespace and IPAM. This keeps the scope discipline of Chapter 0:
Infoblox does not build the OCI landing zone (the CIS Landing Zone / OCI Core
Landing Zone accelerator does that) — it provides DDI *within* it.

**Candor up front.** OCI is a later, thinner integration target for Infoblox than
AWS, Azure, or GCP. vNIOS on OCI went GA with **NIOS 8.5.2** (the CP-2205 Cloud
Platform appliance as a Grid member). There is no first-class OCI Marketplace
vNIOS listing and no deep, event-driven cloud-discovery adapter equivalent to the
AWS/Azure/GCP Cloud Network Automation connectors. On OCI you deploy vNIOS by
**custom image import** and you keep IPAM in sync **via the OCI API/SDK and
Terraform/Ansible**, not via a turnkey discovery connector. This chapter says so
plainly and gives the API-driven pattern that works.

## 2. Reference architecture

![OCI reference architecture: HA vNIOS CP-2205 members across availability domains in the hub VCN, spoke VCNs pointing subnet DHCP options at the members over the DRG, conditional-forward of oraclevcn.com names to the hub OCI DNS resolver, and an OCI API key driving SDK/Terraform-based discovery into IPAM](figs/oci-ch-01-reference-architecture.png)

The pattern mirrors Chapter 0: authoritative control plane (on-prem Grid Master or
Universal DDI SaaS) → vNIOS DNS/DHCP members in the **hub VCN** → spokes forward
to them → members conditionally forward to the OCI resolver.

**Control plane vs. data plane.** The Grid Master (on-prem or in a management
compartment) holds the authoritative database; OCI members serve the data plane
(DNS answers, DHCP for on-prem/extranet clients, IPAM API). Management is the
HTTPS/SSH path to members and the Grid VPN tunnel back to the Master; the data
path is UDP/TCP 53 from spokes and on-prem.

**Resolution flow.** A workload in Spoke A queries its VCN resolver IP
(`169.254.169.254`); the subnet's DHCP options and the resolver's forwarding
rules send enterprise/unknown names to the vNIOS members in the hub; vNIOS answers
authoritatively for corporate zones and **conditionally forwards** OCI private
names (e.g. `*.oraclevcn.com` or your private zones) back to the hub VCN's OCI
resolver via its forwarding endpoint.

## 3. Infoblox product options for OCI

| Option | What runs on OCI | Control plane | Marketplace | When to pick |
|---|---|---|---|---|
| **vNIOS Grid member (NIOS)** | vNIOS compute instance (CP-2205 / TE-V) as a Grid member | You operate Grid Master (on-prem or OCI mgmt compartment) | No native listing — **custom image import** | Extending an existing on-prem Grid into OCI; sovereign control plane |
| **Universal DDI (NIOS-X host)** | NIOS-X server instance on OCI | Infoblox SaaS (Infoblox Portal / CSP) | Custom image / OVA-equivalent import | Greenfield multi-cloud, low-ops; outbound 443 to Portal allowed |
| **Cloud discovery / automation** | No appliance — an OCI IAM identity + SDK/Terraform | Either of the above | n/a | Keeping IPAM synced with OCI VCNs/subnets |

**Licensing.** vNIOS on OCI is BYOL — Grid, DNS, DHCP, and (optionally) Cloud
Network Automation / Threat Defense licenses are applied to the member from the
Grid Master; OCI bills only the compute/storage/egress. The **CP-2205 Cloud
Platform** appliance is the model validated for OCI Grid-member use and exposes a
direct DNS/IPAM API on the member so DevOps calls (Terraform/Ansible) need not
traverse the Grid Master. Confirm current model/shape support against the vNIOS
for OCI installation guide, as the supported-appliance matrix is version-specific.

Default recommendation: enterprises with an existing Infoblox estate extend the
**vNIOS Grid** into OCI; pure-greenfield multi-cloud teams use **Universal DDI**.

## 4. Prerequisites

| Category | Requirement |
|---|---|
| Tenancy / compartments | OCI tenancy; a **hub (connectivity)** compartment and a **network/DDI** compartment; CIS/OCI Core Landing Zone recommended |
| IAM | An IAM **user + API signing key** *or* a **dynamic group + instance principal** for automation; a group/policy to launch compute & manage the network (see §6) |
| Image | vNIOS **qcow2/VMDK** image from Infoblox Support, uploaded to an **Object Storage** bucket, imported as a **custom image** (paravirtualized) |
| Compute | A **flexible shape** (e.g. `VM.Standard.E4.Flex` / `VM.Standard3.Flex`) with OCPU + memory matched to the target vNIOS model spec; one instance per member |
| Network | Hub VCN + subnets for MGMT/LAN1 (and HA if used); **DRG v2** for hub-spoke + hybrid; route tables; **Security Lists or NSGs** with the ports in §5 |
| Storage | Boot volume plus the vNIOS data **block volume** per the model's disk requirement |
| Connectivity | **FastConnect** or site-to-site **IPSec VPN** via the DRG for the Grid VPN tunnel back to an on-prem Grid Master |
| Licensing | vNIOS Grid/DNS/DHCP (+CNA/Threat Defense) tokens; for Universal DDI, a join token and outbound 443 to the Infoblox Portal |

## 5. Step-by-step deployment

**a. Import the vNIOS image.**
1. Obtain the vNIOS OCI image from Infoblox Support and upload it to an **Object
   Storage bucket** (`oci os object put ...`).
2. **Custom Images → Import Image**, source the object, image type **QCOW2/VMDK**,
   launch mode **Paravirtualized**. OCI creates a reusable custom image.

**b. Launch the member instance.**
3. **Compute → Create Instance** from the custom image. Pick a **flexible shape**
   and assign OCPU/memory to match the vNIOS model. Place it in the **hub VCN**
   MGMT subnet, in a chosen **availability domain** and **fault domain**.
4. Attach the vNIOS **data block volume**. Add a second **VNIC** if you separate
   MGMT (LAN0) from the service/LAN1 interface; assign each a private IP (and a
   reserved public IP only if the design requires it).
5. Pass initial config via the instance **user-data / cloud-init** (temp admin
   password, license, Grid join parameters) per the vNIOS-for-OCI guide.

**c. Networking & security rules.** Apply on the subnet **Security List** or,
preferably, per-VNIC **NSGs**:

| Port | Proto | Direction | Purpose |
|---|---|---|---|
| 53 | TCP + UDP | Ingress (from spokes/on-prem) | DNS queries/zone transfer |
| 67–68 | UDP | Ingress | DHCP (on-prem/extranet relay clients; OCI VCNs use platform DHCP) |
| 1194 | UDP | Both (to/from Grid Master) | Grid VPN tunnel (DB sync) |
| 2114 | TCP | Both | Grid comms / CRAM authentication & Master promotion |
| 123 | UDP | Egress | NTP time sync |
| 443 | TCP | Ingress (mgmt) / Egress | HTTPS admin & WAPI; Universal DDI outbound to Portal |
| 161 | UDP | Ingress | SNMP monitoring (optional) |
| 22 | TCP | Ingress (mgmt) | SSH admin (restrict to bastion) |

Add route-table rules so spoke VCNs reach the hub member IPs via the **DRG**, and
so the members reach the on-prem Grid Master over FastConnect/IPSec.

**d. Grid setup / HA pairing.**
6. First member: run initial setup, then **join it to the Grid** (Grid Master IP,
   shared secret) — the VPN tunnel forms over 1194/udp + 2114/tcp. For Universal
   DDI instead, apply the join token so the NIOS-X host registers to the Portal.
7. Deploy a **second member** in a different **availability domain / fault
   domain** and pair it. Because OCI has no L2/gratuitous-ARP failover, front the
   pair with **anycast** (advertise a /32 service IP via BGP over the DRG) or an
   **OCI network/flexible Load Balancer** VIP for the DNS service address.

## 6. Cloud integration adapter (discovery & automation)

**Be candid: OCI discovery is thinner than the hyperscalers.** Infoblox does not
ship a deep, event-driven OCI discovery connector equivalent to its AWS/Azure/GCP
Cloud Network Automation adapters. On OCI you achieve IPAM synchronization through
an **API-driven pattern**, not a turnkey connector.

**The credential.** Use one of:
- an **IAM user + API signing key** (RSA key pair; the public key registered on
  the user, the private key held by the sync job/Terraform), or
- an **instance principal** — put the vNIOS/automation instance in a **dynamic
  group** and grant that group policies, so no long-lived key is stored.

**Least-privilege policy (read-only for discovery):**

| Verb / resource | Scope | Purpose |
|---|---|---|
| `inspect vcns` / `read virtual-network-family` | in compartment `network` | Enumerate VCNs, subnets, CIDRs, VNICs |
| `read dns` (`inspect dns-zones`, `read dns-views`) | in compartment `network` | Read private views/zones for reconciliation |
| `read instance-family` | in compartment `network` | Map instances/IPs to records (optional) |
| `use tag-namespaces` (read) | tenancy | Read defined tags that drive allocation |

Example: `Allow group DDI-Discovery to read virtual-network-family in
compartment network` (or `Allow dynamic-group DDI-Automation to ...` for instance
principals). Grant `manage dns-*` only if Infoblox is to *write* OCI zones.

**How it works in practice.** A scheduled job (or Terraform provider + Infoblox
WAPI/Universal DDI API) uses the OCI SDK to list VCNs/subnets in each onboarded
compartment and pushes them into Infoblox IPAM as **networks/network
containers**, tagging each with tenancy/compartment/VCN OCID. Because vNIOS on OCI
exposes a **direct member API**, Terraform (`infoblox` provider) and **Ansible**
modules can allocate the next free IP and create the A/PTR record in the same
pipeline that `terraform apply` provisions the OCI instance — closing the
IPAM-to-cloud-reality gap without a native connector.

## 7. DNS integration with native OCI DNS

OCI private DNS and vNIOS meet at the **hub VCN resolver**, using OCI resolver
endpoints in both directions:

- **OCI → Infoblox (outbound forwarding).** On the hub VCN resolver create a
  **forwarding endpoint** (consumes **2 private IPs** in its subnet — one used,
  one reserved) and add **forwarding rules**: send corporate domains
  (`corp.example`, reverse `10.in-addr.arpa`) and a **catch-all** to the vNIOS
  member IPs. Spoke VCNs then reach enterprise/on-prem names by forwarding to the
  hub via **associated private views** (attach each spoke's private view to the
  hub resolver) or a spoke→hub forwarding rule.

- **Infoblox → OCI (inbound / conditional forwarding).** On the OCI resolver
  create a **listening endpoint** (consumes **1 private IP**) so it answers
  queries arriving from vNIOS. On the Grid, configure **conditional forwarders**
  for OCI-owned names — the VCN's `*.oraclevcn.com` domain and any OCI **private
  zones** — pointing at that listening endpoint IP. This gives split-horizon:
  vNIOS owns the enterprise namespace; OCI owns its private/service zones; each
  forwards the other's names.

This bidirectional wiring lets a spoke workload resolve both `db.corp.example`
(authoritative on vNIOS) and `app.subnet.vcn.oraclevcn.com` (authoritative on OCI)
through one resolution path. Delegate reverse zones for OCI CIDRs to Infoblox so
PTRs live in the authoritative IPAM.

## 8. IPAM discovery & automation

**Onboarding.** Model each OCI **tenancy → compartment → VCN → subnet** hierarchy
in Infoblox using network views and network containers; tag every object with the
VCN/compartment **OCID** so IPAM maps 1:1 to OCI. Import existing CIDRs on first
sync, then let the §6 job reconcile additions/removals on a schedule.

**Tag-driven allocation.** OCI **defined tags** (e.g. `env=prod`, `app=payments`)
carried on subnets become Infoblox **extensible attributes**, so Next-Available-IP
requests can be scoped by tag and records inherit ownership metadata. In pipelines,
Terraform's `infoblox_ip_allocation` + `infoblox_a_record` (or the Universal DDI
API) reserve the address and create DNS *before* the OCI VNIC is attached — so no
pipeline-provisioned address enters OCI that IPAM doesn't already know about;
out-of-band changes (console-attached VNICs, platform DHCP) are caught by the
scheduled reconciliation in §6/Day-2.

**Consistency.** Because OCI VCN DHCP is platform-managed (no vNIOS leases inside
the VCN), keep records authoritative by driving allocation through IPAM at
provision time and reconciling discovered state on a cadence. For on-prem/extranet
segments that vNIOS *does* serve DHCP for, the standard lease→A/PTR fixed-address
flow keeps DHCP, DNS, and IPAM consistent on the shared database.

### Governed self-service provisioning (ServiceNow)

The discovery and allocation machinery above is what an engineer drives directly. In a governed enterprise you put a **ServiceNow front door** on it so a subnet or DNS record is *requested*, *approved*, and *provisioned* through one auditable loop instead of ad-hoc API calls — the **same** Infoblox WAPI/Universal DDI operations and the **same** validation checks, now behind a catalog item and an approval gate.

![OCI ServiceNow closed loop for Infoblox DDI: a Service Catalog request carrying the OCI module tfvars is approved with a separation-of-duties gate, the CPG Terraform Connector plans and applies the oci-lz-automation/terraform module on an in-boundary MID Server, IntegrationHub REST allocates the next available IP and registers the A/PTR records over Infoblox WAPI/Universal DDI, the MID Server runs the three validation checks as a pass/fail gate, the Service Graph Connector reconciles the result into cmdb_ci_ip_network, and the request closes with a full audit trail while a failed gate routes back to approval](oci-lz-automation/figs/oci-sn-01-catalog-flow.png)

**The governed loop for OCI:** Service Catalog request (form fields mapped to this module's `tfvars`) → Flow Designer approval + separation-of-duties gate → the **CPG Terraform Connector** applies the [`oci-lz-automation/terraform`](./oci-lz-automation/terraform/README.md) module on an **in-boundary MID Server** → **IntegrationHub REST** allocates the next-available IP and registers A/PTR over Infoblox WAPI/Universal DDI → the MID Server runs the package's three validation checks (`dns-validation.sh`, `discovery-sync-check.sh`, `ipam-conflict-check.sh`) as a **pass/fail gate** → the **Service Graph Connector for Infoblox** reconciles the result into the CMDB (`cmdb_ci_ip_network`) → the request closes with a full audit trail. A failed gate routes back to approval; nothing is recorded as done until validation passes.

Boundary discipline is unchanged: the MID Server and credential path stay **inside the ATO boundary**, secrets stay in **OCI Vault**, and the Universal DDI SaaS path remains the `acknowledge_saas_boundary`-gated exception. See **[Chapter 7 — ServiceNow Orchestration](./07-servicenow-orchestration.md)** for the certified pieces and control-family mapping, **[`oci-lz-automation/servicenow/`](./oci-lz-automation/servicenow/ServiceNow-Orchestration.md)** for this platform's catalog→`tfvars` wiring and IntegrationHub payloads, and the importable **[`servicenow-app/`](./servicenow-app/README.md)** for the actual scoped-app records.

## 9. High availability, sizing & scaling

- **Grid roles.** Grid Master (+ GMC) authoritative; OCI members are DNS/DHCP/IPAM
  data-plane. Put the GMC in a second region or on-prem for control-plane DR.
- **Placement.** Spread members across **availability domains** (in multi-AD
  regions) and always across **fault domains** within an AD, so a rack/AD failure
  never takes both members. Many OCI regions are single-AD — there, fault domains
  are your only intra-region isolation, so add a **second region** for true DR.
- **Failover.** No L2 in OCI, so the classic vNIOS HA VIP does not float via ARP.
  Use **anycast** (advertise the DNS service /32 via BGP over the DRG v2, equal
  routes to both members) or an **OCI Load Balancer** in front of the members.
- **Scaling.** Members are **flexible shapes** — scale vertically by adding
  OCPU/memory to match the vNIOS model, or horizontally by adding members per
  spoke/region. Deploy **regional CP-2205 members** that sync periodically with a
  central Grid Master so each region resolves locally with consolidated visibility.
- **Sizing.** Match OCPU/memory/disk to the target vNIOS model's published minimum
  (CP-2205 / TE-V); the OCI console lets you set OCPU and memory on the flexible
  shape at launch. Validate against the current vNIOS-for-OCI spec table, which is
  version-dependent.

## 10. Security & compliance considerations

- **Hardening & RBAC.** Restrict member management to a bastion subnet; use
  Infoblox **RBAC** for admin roles and OCI **IAM** least-privilege for the
  automation identity (§6). Prefer **instance principals** over stored API keys.
- **Encryption.** Grid DB sync is carried in the encrypted **Grid VPN tunnel**
  (1194/udp); enable encryption at rest on OCI **block volumes** (Oracle-managed
  or your own key in **OCI Vault/KMS**); terminate admin/WAPI on TLS (443).
- **DNS security.** Layer Infoblox **RPZ** and **Threat Defense** feeds on the
  members so every OCI-originated lookup is policy-filtered; enable DNS **query
  logging** and export to **OCI Logging**/SIEM. Capture Grid audit logs centrally.
- **Sovereignty / gov cloud.** OCI runs **Government (US Gov / DoD)**, **National
  Security**, **EU Sovereign**, and dedicated/air-gapped regions. In these,
  **vNIOS Grid** keeps the entire control plane inside the tenancy — the
  self-managed, air-gap-friendly choice. **Universal DDI needs outbound 443 to the
  Infoblox Portal**, which sovereign/air-gapped regions typically disallow — so in
  those environments default to the self-contained vNIOS Grid. Confirm vNIOS image
  availability in the specific realm before committing.
- **Compliance baseline.** Deploy Infoblox inside the **CIS OCI Foundations
  Benchmark**-aligned Landing Zone so NSGs, logging, and IAM guardrails apply to
  the DDI compartment like any other workload.

## 11. Validation & Day-2 operations

**Validation checklist:**
1. From a spoke workload, `dig db.corp.example` resolves via the hub vNIOS members
   (authoritative), and `dig app.<subnet>.<vcn>.oraclevcn.com` resolves via OCI —
   confirming both forwarding directions.
2. Reverse: `dig -x <oci-ip>` returns the PTR from Infoblox for delegated OCI CIDRs.
3. On the Grid Master, confirm both OCI members show **Running/Online** and the VPN
   tunnel is up (1194/udp).
4. Confirm the §6 sync populated IPAM: onboarded VCNs/subnets appear as networks
   tagged with the correct OCID.
5. **Failover test:** stop the primary member (or its fault domain); confirm the
   anycast/LB path shifts DNS to the second member with no client reconfig.

> The same checks run by the governed flow: the ServiceNow MID Server executes these validations (`dns-validation.sh`, `discovery-sync-check.sh`, `ipam-conflict-check.sh`) as the post-apply gate in §8's ServiceNow loop — validation is identical whether an engineer runs it or the catalog flow does.

**Day-2 operations:**
- **Upgrades:** upgrade the Grid Master first, then OCI members (rolling), during
  a window; snapshot boot/block volumes beforehand.
- **Monitoring:** SNMP (161) + Infoblox Grid Manager health; forward DNS query/RPZ
  logs to OCI Logging/SIEM; alert on tunnel down and member sync lag.
- **Reconciliation:** run the OCI→IPAM discovery job on a schedule and review drift
  (CIDRs added in OCI outside pipelines); reconcile tags→extensible attributes.
- **Capacity:** track QPS and DHCP scope (on-prem) utilization; scale OCPU/memory
  or add regional members as spokes grow.
- **DR drills:** periodically promote the GMC and fail a region to validate the
  control-plane and cross-region member design.

## Sources

- [Infoblox — About vNIOS for Oracle Cloud Infrastructure](https://docs.infoblox.com/display/vniosoci/About+Infoblox+vNIOS+for+Oracle+Cloud+Infrastructure)
- [Infoblox — Deploying vNIOS for Oracle Cloud Infrastructure](https://docs.infoblox.com/display/vniosoci/Deploying+vNIOS+for+Oracle+Cloud+Infrastructure)
- [Infoblox — Uploading the vNIOS Image in Oracle Cloud Infrastructure](https://docs.infoblox.com/display/vniosoci/Uploading+the+vNIOS+Image+in+Oracle+Cloud+Infrastructure)
- [Infoblox — Supported vNIOS for OCI Appliances](https://docs.infoblox.com/space/vniosoci/1335820994/Supported+vNIOS+for+Oracle+Cloud+Infrastructure+Appliances)
- [Infoblox blog — Bringing Next-Level DDI Automation to OCI (NIOS 8.5.2 / CP-2205)](https://blogs.infoblox.com/community/bringing-next-level-ddi-automation-to-oracle-cloud-infrastructure/)
- [Infoblox — OCI (NIOS-X Servers) Deployment (Universal DDI)](https://docs.infoblox.com/space/BloxOneInfrastructure/2129920010/Oracle+Cloud+Infrastructure+%28OCI%29+Deployment)
- [Infoblox — Cloud Network Automation](https://www.infoblox.com/products/cloud-network-automation/)
- [Infoblox — Source and Destination Ports for Services (NIOS 9.0)](https://docs.infoblox.com/space/nios90/1327530037/Source+and+Destination+Ports+for+Services)
- [Oracle — Private DNS (views, zones, resolvers, endpoints)](https://docs.oracle.com/en-us/iaas/Content/DNS/Tasks/privatedns.htm)
- [Oracle — Private DNS resolvers (listening/forwarding endpoints)](https://docs.public.oneportal.content.oci.oraclecloud.com/en-us/iaas/Content/Network/Concepts/dns-topic-Private-resolver.htm)
- [Oracle A-Team — OCI Private DNS Common Scenarios](https://www.ateam-oracle.com/oci-private-dns-common-scenarios)
- [Oracle — Importing Custom Linux Images](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/importingcustomimagelinux.htm)
- [Oracle — OCI Core Landing Zone](https://docs.oracle.com/en-us/iaas/Content/cloud-adoption-framework/oci-core-landing-zone.htm)
- [Oracle — Hub-and-spoke network topology using a DRG](https://docs.oracle.com/en/solutions/hub-spoke-network-drg/index.html)
- [Oracle — IAM Policy Syntax](https://docs.oracle.com/en-us/iaas/Content/Identity/Concepts/policysyntax.htm)
- [Oracle — CIS OCI Foundations Benchmark landing zone](https://docs.oracle.com/en/solutions/cis-oci-benchmark/index.html)
- [Service Graph Connector for Infoblox — ServiceNow Store](https://store.servicenow.com/store/app/eeb927621b246a50a85b16db234bcbf1)
- [Cloud Provisioning & Governance: Terraform Connector — ServiceNow Store](https://store.servicenow.com/store/app/6ff8ef2e1be06a50a85b16db234bcbcb)
