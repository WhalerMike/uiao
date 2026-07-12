# Appendix A — Sizing & cost, IPv6/dual-stack, and DHCP where it matters

Three cross-cutting topics the platform chapters deliberately keep light, gathered here so
they read consistently across clouds. These are the P1 depth items from
[`REVIEW-AND-IMPROVEMENTS.md`](./REVIEW-AND-IMPROVEMENTS.md) §3.

> **On numbers.** This appendix gives a **sizing and cost *framework* and the dimensions
> that drive it** — not fabricated prices or query-rate→SKU tables. Appliance throughput,
> VM/instance pricing, and Universal DDI subscription tiers are version-, region-, and
> contract-specific; inventing them would be worse than useless. Every table below ends in
> "estimate, then confirm with your Infoblox account team and the cloud's pricing calculator."

## A.1 Sizing & cost

### A.1.1 What actually drives DDI sizing

Size for the **peak sustained query/lease rate and the role**, not the subnet count:

| Driver | Why it matters | Where to get the number |
|---|---|---|
| Peak DNS QPS (recursive + authoritative) | The dominant sizing factor for DNS members | Existing resolver telemetry; model growth + failover concentration (a member must carry its pair's load) |
| DHCP leases/sec + active leases | Sizes DHCP members (mostly VMware/on-prem here) | Lease logs; churn of the largest scope |
| Reporting/analytics retention | Reporting members need **separate, larger disk** (DS-series / more storage) | Your retention policy (e.g. 90/180 days) |
| Threat Defense (RPZ + feeds) | RPZ zones + feed evaluation add per-query work and memory | Number/size of feeds; enable in a pilot and measure headroom |
| Grid vs Universal DDI | Grid = you size vNIOS VMs; Universal DDI = you size NIOS-X hosts + a **subscription tier** | The control-plane choice (each chapter §3) |

### A.1.2 Per-platform cost dimensions (fill from the pricing calculator)

Cost = **compute + storage + licensing + data/egress + operations**. The variable parts per
platform (map to each chapter's §4/§9):

| Platform | Compute (member VM) | Storage | Notes on cost |
|---|---|---|---|
| Azure | Esv5/Esv3 series ×N members (chapter 1) | Premium LRS SSD, ≥250 GB data (+≥250 GB reporting) | + Private Resolver endpoints (2×/28) if used |
| AWS | Compute-optimised/EBS-optimised instance ×N (chapter 2) | gp3/io2 EBS, sized as above | + Route 53 Resolver endpoints/queries if used |
| Google Cloud | `n2`/`c3` class ×N (chapter 3) | Balanced/SSD PD | + Cloud DNS inbound/outbound forwarding |
| OCI | VM.Standard shape ×N (chapter 4) | Block Volume (balanced/higher-perf) | + OCI private resolver endpoints |
| VMware | vCPU/RAM from the appliance model (chapter 5) | Datastore capacity (thin/thick per policy) | No cloud meter; cost is host capacity + support |
| **All** | **Licensing:** vNIOS BYOL/token *or* Universal DDI subscription; DNS/DHCP/Threat Defense grid licenses | | The licensing line usually dominates; get it from Infoblox |

**Cost-control levers:** right-size members to peak-with-failover (not peak×2 idle); keep
reporting on its own members; prefer anycast over oversized single members; in Universal DDI,
match the subscription tier to real query volume; scope Threat Defense feeds to what you act on.

### A.1.3 A sizing worksheet (per estate)

1. Pull peak DNS QPS and DHCP lease rate per site/cloud (with 12-month growth).
2. Add the **failover concentration** factor (a surviving member carries the pair).
3. Pick member count for HA (≥2 per hub, cross-AZ) and the VM class that clears the peak with headroom.
4. Add reporting members + disk for your retention.
5. Price compute+storage in each cloud's calculator; add the Infoblox licensing quote.
6. Re-check after a pilot with Threat Defense on — measure, don't assume.

## A.2 IPv6 / dual-stack

The volume's reference pattern is IPv4-first; here is what changes for dual-stack. Infoblox
IPAM/DNS/DHCP are natively dual-stack — the work is mostly *planning* and *platform wiring*.

### A.2.1 IPAM for IPv6
- Model the **IPv6 plan in IPAM first**, same discipline as §6.1: a ULA or GUA prefix
  (commonly a `/48` per site, `/64` per subnet) carved non-overlapping per platform/region.
- IPv6 subnets are effectively unlimited hosts — **track by allocation and purpose**, not
  utilization %. Use EAs (owner/env/app) exactly as for IPv4.
- Reverse DNS: **`ip6.arpa`** zones. Automate PTR creation (nibble-format is unwieldy by
  hand) — the same host-record automation that writes A+PTR writes AAAA+PTR.

### A.2.2 Address assignment (RA vs DHCPv6)
- Cloud VNets/VPCs assign IPv6 from the platform (SLAAC/DHCPv6 is platform-managed in cloud,
  same as IPv4 DHCP) — Infoblox **discovers and records** it; it does not hand it out.
- Where you *do* run DHCP (VMware/NSX, on-prem), decide **SLAAC vs stateful DHCPv6** per
  segment; Infoblox supports stateful DHCPv6 with option assignment. RA sets the mode
  (M/O flags); keep RA and DHCPv6 consistent or clients dual-configure.

### A.2.3 Resolution & security for v6
- Members answer **AAAA** and recurse over IPv6 transport where enabled; anycast the DNS VIP
  in both families so clients use one address per family.
- **Conditional forwarders** need the v6 targets too (Private Resolver / cloud resolver
  inbound endpoints have v6 addresses where supported).
- RPZ/threat feeds apply to AAAA answers identically — don't leave a v6 blind spot.

### A.2.4 Per-platform quick notes
| Platform | IPv6 note |
|---|---|
| Azure | Dual-stack VNets; assign a v6 space to the hub/spokes; Private Resolver v6 support is region-dependent — verify |
| AWS | Dual-stack VPCs; Route 53 Resolver supports v6; egress-only IGW for v6 outbound |
| Google Cloud | Dual-stack subnets (external/internal IPv6); Cloud DNS AAAA + inbound/outbound v6 |
| OCI | IPv6 on VCN/subnets; OCI DNS AAAA; confirm private-resolver v6 in-region |
| VMware | NSX-T dual-stack segments + DHCPv6/RA; the place you most likely run **stateful DHCPv6** |

## A.3 DHCP where it matters

The chapters correctly note that in the public clouds, **DHCP is platform-managed** — the
VNet/VPC hands out addresses and you cannot run a classic scope. So Infoblox DHCP is *not* the
common path in cloud. But there are places it is real and worth designing:

### A.3.1 VMware / NSX-T (the main one)
- NSX-T has a DHCP server/relay, but for a **single authoritative DDI** you often run
  **Infoblox DHCP** for the workload segments instead, so leases, fixed addresses, and DNS
  records live in the one IPAM (chapter 5).
- Design: **DHCP failover pairs** (two members serving the same scopes, split or hot-standby)
  so a member loss doesn't stop leasing; relay (IP helper) from NSX segments to the members.
- **Option design:** hand out the anycast DNS VIP, domain search list, NTP, PXE/next-server
  where imaging, and any vendor options. Keep the option set in IPAM, not per-segment guesswork.
- **Fingerprinting:** Infoblox DHCP fingerprinting classifies devices by their DHCP signature
  (useful for policy/reporting on a mixed VMware estate) — enable if you need device visibility.

### A.3.2 Hybrid / on-prem reached through the fabric
- On-prem and edge DHCP (where the enterprise Grid already serves it) integrates the same way;
  the point of this volume is that those leases and the cloud-discovered addresses share **one
  IPAM**, so there are no ghosts and no overlap.
- **DHCP failover across sites:** keep failover peers in the same latency domain; don't stretch
  a failover pair across a WAN you can't guarantee.

### A.3.3 Cloud (what you actually do)
- Leave DHCP to the platform; make Infoblox **discover** the assignments into IPAM (each
  chapter §6/§8) so the record of truth stays complete.
- The one cloud DHCP knob that matters: the VPC/VNet **DHCP option set / DNS servers** must
  point at the Infoblox members' anycast VIP (chapter §5/§7) — that's how cloud VMs resolve
  through the fabric even though the *address* came from the platform.

---

## Sources

- Per-platform sizing/ports/roles: [Chapter 1](./01-azure.md)–[Chapter 5](./05-vmware.md) §4 and §9.
- One-IPAM discipline and the address plan: [Chapter 6 §6.1](./06-cross-platform-operations.md).
- [Infoblox — NIOS / Grid documentation](https://docs.infoblox.com/space/nios)
- [Infoblox — Universal DDI](https://www.infoblox.com/products/universal-ddi/)
- [Infoblox — Threat Defense (RPZ / DNS security)](https://www.infoblox.com/products/threat-defense/)
