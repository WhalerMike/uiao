# Automating VMware (VCF / vSphere / NSX-T) Landing Zones with Infoblox DDI

A companion to **Vol VII / FedAAN — Infoblox Multi-Cloud DDI** (specifically the VMware
chapter, [`05-vmware.md`](../05-vmware.md)). Where the VMware chapter is the
**deploy-oriented runbook**, this package is the **automation-grade layer**: how to add
Infoblox DDI to a VMware Cloud Foundation private cloud as a modular, IaC-driven,
drift-resistant component that layers cleanly on top of an existing vSphere + NSX-T SDDC.

**This is the on-prem / private-cloud anchor of the volume.** The Grid Master often lives
right here in the VCF management domain, and — unlike the hyperscalers — **DHCP is genuinely
Infoblox's job**, so the module opens `67-68/udp` by default and wires NSX DHCP relay to the
vNIOS members.

## Why this exists

The building blocks are all vendor-supported, but **no single vendor document ties them
together**:

- **VMware / Broadcom** ships VCF, vSphere, and NSX-T — they build the SDDC, the NSX
  overlay, and the DNS forwarder / DHCP relay stubs, but ship no enterprise IPAM and know
  nothing about Infoblox.
- **Infoblox** ships the [official Terraform provider](https://github.com/infobloxopen/terraform-provider-infoblox),
  the vNIOS-for-VMware OVA, Cloud Network Automation, and the
  [IPAM plug-in for VMware Aria Automation](https://docs.infoblox.com/space/ipamvmware8x/52048987/Introduction)
  — they deploy/manage Infoblox, but know nothing about your SDDC topology.

This package is the missing seam: **Stage 1 (VCF / vSphere / NSX-T) → Stage 2 (this Infoblox
DDI module) → Stage 3 (validation)**, with the SDDC inventory of Stage 1 flowing in as the
inputs of Stage 2.

## Scope discipline (unchanged from the volume)

Infoblox does **not** build the SDDC (VCF domains, vСenter, NSX-T fabric, compute). Those
are Stage 1. This package owns the **DDI + DNS-security layer inside the management/edge
domain** and nothing else.

## Boundary & compliance posture

Built for a **FedRAMP-Moderate operating posture on a self-contained VCF private cloud** —
air-gap-friendly because the Grid runs entirely inside your SDDC. One decision follows
directly from that and is enforced in the code:

| `deployment_model` | Control plane location | FedRAMP-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** your SDDC / ATO boundary | **Boundary-clean.** The natural fit — the Grid Master usually already lives here. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443) | Requires a FedRAMP/authorization review; the module hard-fails unless `acknowledge_saas_boundary = true`. |

See [`_module-contract.md`](./_module-contract.md) for the full boundary rule.

## What's in here

| Path | What it is |
|---|---|
| [`_module-contract.md`](./_module-contract.md) | The shared contract — variables, ports, discovery scopes, naming, outputs. Read this first. |
| `VMware-LZ-Infoblox-DDI-Automation-Guide.md` | The implementation guide: 11-section skeleton mapped to VCF automation, layered architecture, sequencing, Aria plug-in, FedRAMP-Moderate control mapping. |
| [`VMware-LZ-DDI-Step-by-Step-Runbook.md`](./VMware-LZ-DDI-Step-by-Step-Runbook.md) | The **detailed step-by-step deployment runbook** — sequential phases with exact `govc`/PowerCLI/`terraform` commands, per-step verification, troubleshooting, and **Appendix A — Variable Worksheets**. Start here to actually deploy. |
| `terraform/` | Starter Terraform module (`vsphere` + `nsxt` + `infobloxopen/infoblox`), `deployment_model`-driven, with a hub-integration example. |
| `pipelines/` | GitOps example (GitHub Actions): inventory → DDI → validation, plus the Aria Automation IPAM plug-in note. |
| `validation/` | Day-0/Day-2 validation scripts (DNS resolution, discovery-sync status, IPAM conflict checks). |
| `figs/` | Mermaid sources for the reference architecture, Aria IPAM provisioning, and DNS resolution figures. |

## Status

The IaC here is a **coherent starter skeleton**, explicitly labeled as such — it encodes the
right structure, variables, resources, and guardrails, but is not a certified production
module. Pin your own provider versions, supply your own vNIOS OVA build, appliance model,
and vCPU/RAM (model/version-dependent — never hard-coded here), and test in a sandbox
vSphere cluster first. Do **not** run `terraform`/`govc`/`ovftool`/PowerCLI from this
skeleton without reviewing every value.

---

*Independent of UIAO governance canon; vendor-integration documentation, self-contained under
`infoblox-ddi-book/vmware-lz-automation/`.*
