# Chapter 2 — Amazon Web Services

## 1. Overview — where DDI fits in the AWS landing zone

AWS ships a competent set of native name and address primitives, but they are
deliberately per-service rather than a unified DDI platform. **Route 53** provides
public DNS, **Route 53 Resolver** (the `.2` VPC resolver plus inbound/outbound
endpoints) provides recursive resolution and hybrid forwarding, and **Route 53
private hosted zones** provide split-horizon internal names scoped to VPCs.
DHCP is not a server you run — a VPC hands out addresses and options through a
**DHCP option set** attached to the VPC. For addressing, AWS now offers **Amazon
VPC IPAM**, a genuine IP-planning service, which is a real step up from the
spreadsheet era but is still AWS-scoped and account-centric.

The gaps show up at enterprise scale and, especially, at the edge of AWS. Route 53
private hosted zones do not federate cleanly across hundreds of accounts; resolver
rules must be authored and shared (via AWS RAM) per VPC; there is no single
authoritative record of every CIDR across every cloud plus on-prem; and DHCP option
sets cannot express reservations, fixed addresses, or option policies the way an
enterprise DHCP server can. The moment the landing zone spans **multiple AWS
accounts under Organizations/Control Tower, plus other clouds, plus on-prem**, you
need one authoritative IPAM and one consistent, secure resolution fabric across all
of it.

That is where Infoblox slots in — **inside** the AWS landing zone's
network/connectivity design area, not as a replacement for it. In an AWS
Landing Zone Accelerator or Control Tower topology, the connectivity account owns a
shared-services (hub) VPC attached to a **Transit Gateway**; Infoblox DNS/DHCP
members live there, workload spoke VPCs forward DNS to them, the members
conditionally forward AWS-service names to Route 53 Resolver, and a discovery
adapter keeps IPAM synchronized with the real VPCs and subnets across every onboarded
account. AWS keeps doing what it is good at (fast in-VPC resolution, service
endpoints); Infoblox provides the authoritative, cross-domain DDI and DNS-security
layer on top.

## 2. Reference architecture

![AWS reference architecture: vNIOS members across two AZs in the Network account's shared-services hub VPC behind the Transit Gateway, workload-account spokes pointing DHCP option sets at the members, Route 53 Resolver inbound/outbound endpoints for split-horizon forwarding, and a cross-account IAM discovery role syncing VPCs into IPAM](figs/aws-ch-01-reference-architecture.png)

Infoblox members sit in the **Network/connectivity account's shared-services VPC**,
spread across at least two Availability Zones, behind the Transit Gateway that all
spokes attach to. The control plane is either an on-prem/in-cloud **Grid Master**
(vNIOS) or the **Infoblox Portal** SaaS (Universal DDI). Workload VPCs never talk to
the internet for DNS — they resolve against the hub members, which own recursion,
RPZ/threat feeds, and conditional forwarding.

Resolution flow: a workload instance's DHCP option set points `domain-name-servers`
at the hub members' LAN ENIs (reachable via TGW). The member answers authoritative
internal zones directly, applies RPZ, and **conditionally forwards** AWS-specific
names (e.g. `*.amazonaws.com`, `*.<region>.compute.internal`, and any Route 53
private-hosted-zone domains) to a Route 53 Resolver **inbound endpoint**. In the
reverse direction, native VPCs that must reach Infoblox-authoritative names use a
Route 53 Resolver **outbound endpoint** with forwarding **rules** targeting the hub
member IPs. Management and Grid replication ride a separate path (MGMT ENI) back to
the Grid Master.

## 3. Infoblox product options for AWS

| Option | What it is | AWS delivery | Licensing |
|---|---|---|---|
| **vNIOS for AWS (NIOS Grid)** | Self-managed virtual appliance; you run the Grid Master + members | AWS Marketplace **AMI** (BYOL v8.x/v9.x listings) or **PayGo** hourly; also deployable via AWS CLI / CloudFormation | BYOL (Infoblox license) or Marketplace PAYG; NIOS 9.0.5+ ships in-built licenses from Marketplace |
| **Universal DDI (SaaS)** | Infoblox operates the control plane (Infoblox Portal / CSP); you run lightweight managed hosts | Deployed as EC2/host under central SaaS management | Subscription; requires outbound 443 to the Portal |
| **Cloud Network Automation (adapter)** | Discovery/automation layer on top of either control plane | Runs on the Grid (license on Grid Master) or Universal Cloud | Add-on license (see §6) |

For most enterprises extending an **existing on-prem Grid** into AWS, deploy
**vNIOS members** joined to that Grid and add the **Cloud Network Automation**
license. Greenfield multi-cloud shops that prefer not to operate Grid Masters pick
**Universal DDI**. Both models use the same AWS-side integrations (IAM discovery
role, Route 53 Resolver wiring) described below.

## 4. Prerequisites

| Area | Requirement |
|---|---|
| Accounts | AWS Organizations with a **Network/connectivity account** (Control Tower or LZA); one **integration account** trusted by member-account discovery roles |
| Compute | EC2 in the hub VPC. NIOS 9.0.5+ supports **M7i / R7i** shapes; size per member role (see §9). EBS root + data volume |
| Network interfaces | Multiple **ENIs**: ENI0 = MGMT, ENI1 = LAN1 (DNS/DHCP data), optional HA ENI. Source/dest check disabled where anycast/HA requires it. Elastic IPs only if a member must be internet-reachable |
| Placement | ≥2 subnets in **≥2 Availability Zones**; same requirement for Route 53 Resolver endpoints |
| IAM | Cross-account **discovery role** with least-privilege read policy + trust to the integration account with an **ExternalId** (see §6) |
| Licensing | vNIOS grid/DNS/DHCP licenses; **Cloud Network Automation** license on the Grid Master for VPC discovery and Route 53 sync |
| Quotas | vCPU quota for the chosen shape; Elastic IP, ENI, and Route 53 Resolver endpoint limits |

**Security group ports** (apply the minimum set per member role; restrict source
CIDRs tightly):

| Service | Port / proto | Direction | Purpose |
|---|---|---|---|
| DNS | 53 tcp **and** udp | ingress | Client + zone-transfer resolution |
| DHCP | 67–68 udp | ingress | If member serves DHCP (relayed to spokes) |
| Grid VPN | **1194 udp** | ingress/egress | Encrypted Grid replication tunnel (Master ↔ member) |
| Grid comms | **2114 tcp** | ingress/egress | Grid control channel (some guides also list 2114/udp; when VPN is enabled traffic is tunneled over 1194/udp) |
| NTP | 123 udp | egress | Time sync (Grid requires tight time) |
| HTTPS (mgmt) | 443 tcp | ingress | Grid Manager UI / API |
| SSH | 22 tcp | ingress | CLI (restrict to bastion) |
| AWS API proxy | 8787 tcp | egress | Infoblox AWS API proxy (discovery/automation) |
| Universal DDI sync | 443 tcp | egress | Only for Universal DDI hosts → Infoblox Portal |

## 5. Step-by-step deployment

1. **Subscribe & launch the AMI.** In AWS Marketplace, subscribe to *Infoblox NIOS
   for AWS* (BYOL or PayGo). Launch the AMI into the **hub VPC**, choosing an M7i/R7i
   shape and a subnet in AZ-a. Attach the root EBS volume plus a data volume sized for
   the DB. For repeatable builds, deploy via **CloudFormation** or the AWS CLI instead
   of the console.
2. **Attach ENIs.** Give the instance a **MGMT ENI** (ENI0) and a **LAN1 ENI**
   (ENI1). Put DNS/DHCP service traffic on LAN1 and Grid/management on MGMT. Assign an
   Elastic IP only if the member must be publicly reachable.
3. **First-boot / initial config.** Use EC2 **user-data** to pass initial NIOS config
   (temp license, network settings, `remote_console_enabled`, admin password). The
   first appliance becomes the **Grid Master** (standalone), or you join it to an
   **existing on-prem Grid** as a cloud member.
4. **Create/extend the Grid.** On the Grid Master set the Grid name/shared secret,
   then **join** each additional member. Members synchronize with the Master over the
   VPN tunnel (**1194/udp**, control on **2114**). Confirm the SG allows those ports
   between member ENIs and the Master.
5. **Security groups.** Attach an SG implementing the port table in §4. Keep DNS
   (53 tcp/udp) open from spoke CIDRs via TGW; keep 1194/2114 open only between Grid
   members and the Master; keep 443/22 to a bastion/admin CIDR only.
6. **HA / second AZ.** Deploy the second member in **AZ-b** and pair for HA (see §9).
   For resilient client-facing resolution, front the pair with **anycast** or a
   stable service IP advertised into the TGW route tables.
7. **DHCP for spokes.** Where Infoblox serves DHCP, create a **DHCP option set** in
   each spoke VPC whose `domain-name-servers` point at the hub members' LAN IPs, and
   associate it with the VPC. (AWS VPC DHCP is option-set based; the member provides
   the lease/record intelligence.)
8. **Licensing.** Install DNS/DHCP/Grid and **Cloud Network Automation** licenses on
   the Grid Master.

## 6. Cloud integration adapter (discovery & automation)

Infoblox discovers AWS via **vDiscovery** driven by **Cloud Network Automation**
(license on the Grid Master). The exact credential object is an **AWS IAM role**.
For a single account you can attach a role to the vNIOS instance; for
**Organizations/Control Tower**, create a **least-privilege role in each member
account** and a **cross-account trust** back to the Infoblox integration account —
**always with an `ExternalId` condition** to prevent confused-deputy attacks. From
NIOS 9.0.4+, a single vDiscovery job can span **multiple accounts of an AWS
Organization across one or many regions**, including **AWS GovCloud**.

Grant a **custom** policy — not the broad AWS-managed ones. Infoblox explicitly
recommends against `AmazonVPCReadOnlyAccess` (grants the full `ec2:Describe*`
wildcard), `AmazonRoute53ReadOnlyAccess`, and `AmazonS3ReadOnlyAccess` (data-plane
`s3:GetObject`). Use only the read actions the DDI features need:

| Capability | Representative least-privilege actions |
|---|---|
| VPC / subnet / instance discovery | `ec2:DescribeVpcs`, `ec2:DescribeSubnets`, `ec2:DescribeInstances`, `ec2:DescribeNetworkInterfaces`, `ec2:DescribeAvailabilityZones`, `ec2:DescribeRegions` |
| Tags (tag-driven allocation) | `ec2:DescribeTags` |
| Route 53 DNS sync | `route53:ListHostedZones`, `route53:ListResourceRecordSets`, `route53:GetHostedZone` |
| Cross-account assume | member-account role trust policy: `sts:AssumeRole` from the integration account, `Condition` on `sts:ExternalId` |

Treat this list as a **living baseline** — Infoblox notes new asset types/features
may require additional read actions over time. The role has **zero data-plane
access** by design.

## 7. DNS integration with native AWS DNS

Two directions, wired independently:

- **AWS → Infoblox (inbound).** Create a Route 53 Resolver **inbound endpoint** in
  the hub VPC across **two AZ subnets**. Point VPC/on-prem forwarders (or a
  delegation) at its interface IPs so AWS-side queries for Infoblox-authoritative
  zones resolve at Infoblox. A **delegation inbound endpoint** can delegate a
  private-hosted-zone subdomain to the Route 53 VPC resolver where that split is
  desired.
- **Infoblox ← AWS (outbound / forwarding).** Create a Route 53 Resolver
  **outbound endpoint** plus **resolver rules**: one forwarding rule per domain
  (e.g. an internal `corp.example`) targeting the hub member IPs. Associate the rules
  with the VPCs (share across accounts via AWS RAM) so those VPCs forward matching
  queries to Infoblox. On the Infoblox side, configure **conditional forwarding** for
  AWS-owned names (`*.amazonaws.com`, `*.compute.internal`, Route 53 private-hosted-zone
  domains) toward the inbound endpoint — giving clean split-horizon in both directions.

Separately, NIOS can **synchronize Route 53 hosted zones into the Grid database** for
a unified DNS/IPAM view. This requires the **Cloud Network Automation** license and is
**one-way (Route 53 → NIOS), at the hosted-zone level**: you designate **two Grid
members** to pull the data, which relay it to the Grid Master. Records imported this
way remain **managed by Route 53** — edits made in NIOS are overwritten on the next
sync. (Route 53 integration is supported on **AWS GovCloud** from NIOS 8.6.3.)

## 8. IPAM discovery & automation

**Discovery.** vDiscovery walks each onboarded account, enumerates **VPCs, subnets,
ENIs, and EC2 instances**, and maps them into Infoblox **network views/containers**
so IPAM reflects cloud reality instead of drifting. **Tag-driven allocation** uses
`ec2:DescribeTags` to place discovered objects and drive network/host assignment by
tag (owner, environment, application). Because the same discovery role covers all DDI
capabilities for an account, one onboarding gives you IPAM + DNS visibility together.

**Relationship to AWS VPC IPAM.** Two models coexist. In the **visibility** model,
Infoblox discovers VPC CIDRs and remains the authoritative enterprise IPAM while AWS
allocates in-VPC. In the newer **authoritative** model (the 2025 *Amazon VPC IPAM ↔
Infoblox* integration), you **designate Infoblox as the management authority for a
VPC IPAM private scope**: VPC IPAM automates IP assignments *from* Infoblox, and via
**BYOIP** you pull non-overlapping CIDRs from on-prem **Infoblox Universal IPAM** into
your **top-level AWS IPAM pool**, then organize regional/sub pools. This makes
Infoblox the single source of truth while AWS-native workflows keep functioning.
Note: the integration applies to **private scopes only**, not public scopes.

Consistency is preserved because allocations, DHCP leases, and DNS records share the
one Infoblox database — an address handed out in a spoke, its record, and its IPAM
entry stay aligned rather than living in three disconnected systems.

### Governed self-service provisioning (ServiceNow)

The discovery and allocation machinery above is what an engineer drives directly. In a governed enterprise you put a **ServiceNow front door** on it so a subnet or DNS record is *requested*, *approved*, and *provisioned* through one auditable loop instead of ad-hoc API calls — the **same** Infoblox WAPI/Universal DDI operations and the **same** validation checks, now behind a catalog item and an approval gate.

![AWS ServiceNow closed loop for Infoblox DDI: a Service Catalog request carrying the AWS module tfvars is approved with a separation-of-duties gate, the CPG Terraform Connector plans and applies the aws-lz-automation/terraform module on an in-boundary MID Server, IntegrationHub REST allocates the next available IP and registers the A/PTR records over Infoblox WAPI/Universal DDI, the MID Server runs the three validation checks as a pass/fail gate, the Service Graph Connector reconciles the result into cmdb_ci_ip_network, and the request closes with a full audit trail while a failed gate routes back to approval](aws-lz-automation/figs/aws-sn-01-catalog-flow.png)

**The governed loop for AWS:** Service Catalog request (form fields mapped to this module's `tfvars`) → Flow Designer approval + separation-of-duties gate → the **CPG Terraform Connector** applies the [`aws-lz-automation/terraform`](./aws-lz-automation/terraform/README.md) module on an **in-boundary MID Server** → **IntegrationHub REST** allocates the next-available IP and registers A/PTR over Infoblox WAPI/Universal DDI → the MID Server runs the package's three validation checks (`dns-validation.sh`, `discovery-sync-check.sh`, `ipam-conflict-check.sh`) as a **pass/fail gate** → the **Service Graph Connector for Infoblox** reconciles the result into the CMDB (`cmdb_ci_ip_network`) → the request closes with a full audit trail. A failed gate routes back to approval; nothing is recorded as done until validation passes.

Boundary discipline is unchanged: the MID Server and credential path stay **inside the ATO boundary**, secrets stay in **AWS Secrets Manager**, and the Universal DDI SaaS path remains the `acknowledge_saas_boundary`-gated exception. See **[Chapter 7 — ServiceNow Orchestration](./07-servicenow-orchestration.md)** for the certified pieces and control-family mapping, **[`aws-lz-automation/servicenow/`](./aws-lz-automation/servicenow/ServiceNow-Orchestration.md)** for this platform's catalog→`tfvars` wiring and IntegrationHub payloads, and the importable **[`servicenow-app/`](./servicenow-app/README.md)** for the actual scoped-app records.

## 9. High availability, sizing & scaling

- **Grid roles.** One **Grid Master** (+ optional **Grid Master Candidate** for DR),
  and **members** doing DNS/DHCP in the hub. Keep the Master reachable over the Grid
  VPN from every member.
- **Cross-AZ.** Deploy members in **≥2 AZs** in the hub VPC; deploy Route 53 Resolver
  endpoints across the same AZ subnets. For multi-region, run members in each region's
  connectivity VPC and synchronize through the Grid.
- **Anycast / service IP.** For resilient client-facing resolution, advertise an
  **anycast** service address (disabling EC2 source/dest check as needed) so failover
  is transparent to spoke DHCP clients; alternatively use HA-pair failover.
- **Sizing.** Use **M7i/R7i** shapes (NIOS 9.0.5+); scale vCPU/RAM and the EBS data
  volume with zone count, query rate, and DHCP lease volume. Right-size the Grid
  Master separately from data members — treat concrete vCPU/RAM per role as
  **version- and workload-dependent** and confirm against the current vNIOS for AWS
  installation guide.

## 10. Security & compliance considerations

- **DNS security.** Enable **RPZ** and Infoblox **threat-intel feeds** on the hub
  members so every spoke query is filtered; add DNS tunneling/DGA detection where
  licensed. This is a primary reason to funnel spoke DNS through Infoblox rather than
  straight to Route 53.
- **Least privilege.** The discovery IAM role is read-only with **no data-plane
  access** and an **ExternalId**-gated trust (§6). Rotate/scope per account.
- **Network hardening.** Restrict SGs to the minimum ports (§4); keep 1194/2114 among
  Grid members only; terminate 443/22 at a bastion/admin CIDR; never expose the Grid
  VPN to the internet.
- **Encryption & audit.** Grid replication is encrypted over the VPN tunnel; enable
  EBS encryption (KMS). Use NIOS **RBAC**, syslog export to CloudWatch/SIEM, and Grid
  audit logging.
- **GovCloud / sovereignty.** vNIOS runs in **AWS GovCloud**; vDiscovery multi-account
  (NIOS 9.0.4+) and Route 53 integration (NIOS 8.6.3+) are GovCloud-supported. For
  fully air-gapped/sovereign estates prefer the **self-contained vNIOS Grid** over
  Universal DDI, which requires outbound 443 to the Infoblox Portal.

## 11. Validation & Day-2 operations

Validation checklist:

1. **Resolve a record** — from a spoke instance, query an Infoblox-authoritative
   internal name and an AWS name (`*.amazonaws.com`); both must answer via the hub
   member (confirming conditional forwarding + resolver rules).
2. **Reverse path** — from a native VPC, confirm the Route 53 Resolver **outbound
   rule** forwards `corp.example` to Infoblox, and the **inbound endpoint** lets AWS
   reach Infoblox zones.
3. **Confirm discovery** — run vDiscovery and verify VPCs/subnets/instances and tags
   appear in the correct network view; confirm cross-account roles assume with the
   ExternalId.
4. **IPAM authority** — if using the VPC IPAM integration, allocate a CIDR and confirm
   AWS draws it from the Infoblox-owned pool (private scope).
5. **Failover test** — stop the AZ-a member; confirm resolution continues via AZ-b
   (anycast/HA) and DHCP leases persist.

> The same checks run by the governed flow: the ServiceNow MID Server executes
> these validations (`dns-validation.sh`, `discovery-sync-check.sh`,
> `ipam-conflict-check.sh`) as the post-apply gate in §8's ServiceNow loop —
> validation is identical whether an engineer runs it or the catalog flow does.

Day-2: schedule **NIOS upgrades** Grid-wide (Master first, then members), monitor
member health/query rates via SNMP (161/udp) and CloudWatch, keep **threat feeds**
current, re-run/scheduled **vDiscovery** as accounts are added under Control Tower,
and periodically re-audit the discovery IAM policy against any newly required read
actions.

## Sources

- [Infoblox — About vNIOS for AWS (NIOS AWS Install Guide)](https://docs.infoblox.com/space/NAIG/37585115/About+Infoblox+vNIOS+for+AWS)
- [Infoblox — Provisioning vNIOS for AWS (BYOL)](https://docs.infoblox.com/space/NAIG/37650793/Provisioning+vNIOS+for+AWS+Using+the+BYOL+Model)
- [AWS Marketplace — Infoblox NIOS for AWS v9.x (BYOL)](https://aws.amazon.com/marketplace/pp/prodview-jsmupkq6ul6gm)
- [AWS Marketplace — Infoblox NIOS PayGo](https://aws.amazon.com/marketplace/pp/prodview-x5eshyamnuyc2)
- [Infoblox — AWS Least Privilege IAM Permissions (Universal DDI)](https://docs.infoblox.com/space/BloxOneDDI/2358182069/AWS+Least+Privilege+IAM+Permissions)
- [Infoblox — Cross-account access in AWS](https://docs.infoblox.com/space/BloxOneDDI/393019469/Cross+account+access+in+AWS)
- [Infoblox — vDiscovery on AWS VPCs](https://docs.infoblox.com/display/NAIG/vDiscovery+on+AWS+VPCs)
- [Infoblox — Amazon Route 53 Integration Overview](https://docs.infoblox.com/space/NAIG/37716363)
- [Infoblox — Configuring Amazon Route 53 Integration](https://docs.infoblox.com/space/NAIG/37650999/Configuring+Amazon+Route+53+Integration)
- [Infoblox — Cloud Network Automation](https://www.infoblox.com/products/cloud-network-automation/)
- [AWS — Integrate VPC IPAM with Infoblox](https://docs.aws.amazon.com/vpc/latest/ipam/integrate-infoblox-ipam.html)
- [AWS — Amazon VPC IPAM automates IP assignments from Infoblox IPAM (Nov 2025)](https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-vpc-ipam-automates-ip-from-infoblox/)
- [AWS — Route 53 Resolver endpoints and forwarding rules (Hybrid Cloud DNS whitepaper)](https://docs.aws.amazon.com/whitepapers/latest/hybrid-cloud-dns-options-for-vpc/route-53-resolver-endpoints-and-forwarding-rules.html)
- [AWS — Forwarding outbound DNS queries to your network](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-outbound-queries.html)
- [AWS — Resolving DNS queries between VPCs and your network](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-overview-DSN-queries-to-vpc.html)
- [AWS — Landing Zone Accelerator on AWS](https://aws.amazon.com/solutions/implementations/landing-zone-accelerator-on-aws/)
- [Service Graph Connector for Infoblox — ServiceNow Store](https://store.servicenow.com/store/app/eeb927621b246a50a85b16db234bcbf1)
- [Cloud Provisioning & Governance: Terraform Connector — ServiceNow Store](https://store.servicenow.com/store/app/6ff8ef2e1be06a50a85b16db234bcbcb)
