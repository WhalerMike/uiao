# Chapter Conventions (shared contract)

Every platform chapter in this volume MUST follow the same 11-section skeleton so
readers can move between clouds and find the same information in the same place.
Do **not** reorder or rename these headings.

## Required section skeleton

1. **Overview — where DDI fits in the `<platform>` landing zone**
   Two-to-four paragraphs. What the platform's native DNS/DHCP/IPAM story is, its
   gaps at enterprise scale, and where Infoblox slots into the platform's landing
   zone / connectivity fabric.
2. **Reference architecture**
   Grid / appliance topology, control-plane placement (hub vs. spoke), management
   vs. data path, resolution flow. Include at least one ASCII/Mermaid topology
   diagram.
3. **Infoblox product options for `<platform>`**
   vNIOS (NIOS Grid, self-managed) vs. Universal DDI (SaaS control plane) vs. cloud
   discovery/automation adapter. State Marketplace availability and licensing model.
4. **Prerequisites**
   Accounts/tenancy, IAM roles/permissions (name the concrete role/policy), network
   (subnets, routing, firewall/security-group rules and ports), quota, licensing.
5. **Step-by-step deployment**
   Numbered, runbook-grade. Cover: (a) deploy the appliance(s) from Marketplace/
   image, (b) initial Grid setup or Universal DDI onboarding, (c) networking &
   security-group/NSG/firewall config with the actual ports, (d) HA pairing.
   Show CLI / IaC snippets where they materially help.
6. **Cloud integration adapter (discovery & automation)**
   How Infoblox discovers the platform's VPCs/VNets/VCN/subnets and syncs IPAM.
   Name the exact credential object (service principal / IAM role / service account /
   API key) and the least-privilege permissions it needs.
7. **DNS integration with native `<platform>` DNS**
   Forwarding/conditional forwarding, private zones, split-horizon, resolver
   endpoints, delegation. Show the concrete resolver/forwarder wiring.
8. **IPAM discovery & automation**
   Onboarding subscriptions/accounts/projects/compartments, tag-driven allocation,
   how leases/records/allocations stay consistent.
9. **High availability, sizing & scaling**
   Grid member roles, anycast, cross-AZ/region placement, appliance sizing guidance.
10. **Security & compliance considerations**
    Hardening, encryption, RBAC, logging/audit, DNS security (threat feeds, RPZ),
    and any sovereignty/gov-cloud notes for the platform.
11. **Validation & Day-2 operations**
    Test/validation checklist (resolve a record, confirm discovery, failover test)
    plus ongoing operational tasks, upgrades, monitoring.

## Style rules

- Audience: cloud/network architects and platform engineers implementing this in a
  real enterprise landing zone. Assume they know the cloud platform but not Infoblox.
- Be concrete: name real resource types, roles, ports, and product SKUs. Where a
  fact is version- or region-dependent, say so rather than inventing specifics.
- Prefer tables for prerequisites, ports, and permissions.
- Every chapter ends with a short **"Sources"** list of the vendor/platform docs the
  content is grounded in (markdown links).
- Do not claim Infoblox deploys the *whole* landing zone — it provides the DDI +
  DNS-security layer *within* the platform's landing zone. Keep that framing.
- Ports reference (state per platform which apply): DNS 53/tcp+udp, DHCP 67-68/udp,
  Grid comms 1194/udp (VPN) + 2114/tcp, NTP 123/udp, HTTPS mgmt 443/tcp,
  SNMP 161/udp, Universal DDI cloud sync outbound 443/tcp.
