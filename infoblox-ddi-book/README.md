# Infoblox DDI Across the Enterprise: A Multi-Cloud & VMware Implementation Volume

An implementation guide for deploying **Infoblox DDI** (DNS, DHCP, IP Address
Management) and DNS security **inside** the landing zones of every major cloud
service provider and VMware private cloud. Each platform gets its own chapter,
built on an identical section skeleton so the volume reads consistently and the
runbooks are directly comparable across platforms.

> **Framing (read this first):** Infoblox does not build the whole landing zone.
> It provides the **DDI + DNS-security layer within** a landing zone that is
> otherwise deployed by the platform's own accelerator (Azure CAF, AWS Landing Zone
> Accelerator, Google Cloud Foundation, OCI Landing Zone, VMware Cloud Foundation).
> Every chapter keeps that scope. See [Chapter 0](./00-introduction.md).

## Table of contents

| # | Chapter | Platform |
|---|---------|----------|
| 0 | [Introduction: DDI in the Multi-Cloud Landing Zone](./00-introduction.md) | Concepts, product families, shared reference architecture |
| 1 | [Microsoft Azure](./01-azure.md) | Azure CAF landing zone — Connectivity subscription / hub VNet |
| 2 | [Amazon Web Services](./02-aws.md) | AWS Control Tower / LZA — Network account / shared-services VPC |
| 3 | [Google Cloud](./03-gcp.md) | Google Cloud landing zone — Shared VPC host project |
| 4 | [Oracle Cloud Infrastructure](./04-oci.md) | OCI (CIS) Landing Zone — hub VCN |
| 5 | [VMware (VCF / vSphere / NSX-T)](./05-vmware.md) | VMware Cloud Foundation — management/edge domain |
| 6 | [Cross-Platform Operations & Multi-Cloud Governance](./06-cross-platform-operations.md) | Grid/Portal design, anycast, DR, one authoritative IPAM |
| 7 | [ServiceNow Orchestration — A Governed Front Door](./07-servicenow-orchestration.md) | Self-service catalog → approval → Terraform + Infoblox → validation → CMDB, closed loop |

## Automation packages (Terraform, per platform)

Each chapter has a companion **automation package** — a Terraform-only, `deployment_model`-driven
starter that layers Infoblox DDI onto the platform's landing-zone accelerator (Stage 1 → **DDI
module** → validation), with pipelines, validation scripts, an architecture guide, a
command-level step-by-step runbook, and fill-in variable worksheets. All share the same shared
contract, canonical variables, port table, and the GCC-Moderate SaaS-boundary guard.

| Platform | Package |
|---|---|
| Azure | [`azure-alz-automation/`](./azure-alz-automation/README.md) |
| AWS | [`aws-lz-automation/`](./aws-lz-automation/README.md) |
| Google Cloud | [`gcp-lz-automation/`](./gcp-lz-automation/README.md) |
| Oracle Cloud | [`oci-lz-automation/`](./oci-lz-automation/README.md) |
| VMware | [`vmware-lz-automation/`](./vmware-lz-automation/README.md) |

Each package also carries a **`servicenow/`** folder that fronts its Terraform module and
validation scripts with ServiceNow (self-service catalog → approval → apply → validate →
CMDB), per [Chapter 7](./07-servicenow-orchestration.md). An **importable ServiceNow app skeleton** (Script Includes, REST Message, Flow blueprint, MID gate) lives in [`servicenow-app/`](./servicenow-app/README.md).

The **ServiceNow governed front door is woven through the volume**, not siloed in one chapter:
[Chapter 0](./00-introduction.md) §0.5 introduces it as part of the target operating model,
**every platform chapter's section 8** shows the platform-specific catalog → approve → apply
→ validate → CMDB loop, [Chapter 6](./06-cross-platform-operations.md) §6.9 unifies it across
the estate, and each automation guide/runbook carries a "governed path" section.

Figures are Mermaid sources under each `figs/`, rendered to PNG by
[`figs/render-figs.sh`](./figs/render-figs.sh) with the shared
[house style](./figs/HOUSE-STYLE.md).

## How each chapter is structured

Every platform chapter follows the same 11 sections (defined in
[`_conventions.md`](./_conventions.md)):

1. Overview — where DDI fits in the platform's landing zone
2. Reference architecture
3. Infoblox product options for the platform
4. Prerequisites
5. Step-by-step deployment
6. Cloud integration adapter (discovery & automation)
7. DNS integration with native platform DNS
8. IPAM discovery & automation
9. High availability, sizing & scaling
10. Security & compliance considerations
11. Validation & Day-2 operations

## Who this is for

Cloud and network architects, platform engineers, and DDI/network-services teams
implementing a consistent, authoritative name-resolution and IP-management fabric
across a hybrid, multi-cloud estate. The reader knows their cloud platform; the volume
supplies the Infoblox side.

## How to use it

- **Deploying one platform now** → go straight to its chapter and work section 5.
- **Designing the target state** → read sections 1–2 of every chapter plus Chapter 6.
- **Standardizing** → lift the section-4 prerequisites into landing-zone guardrails and
  the section-5 runbooks into your IaC/pipelines.

## Maturity & roadmap

This volume is an honest **starter** — production-grade in structure and framing, explicitly
labeled as un-certified skeletons where the IaC and ServiceNow records are concerned. A
candid, prioritized assessment of what is strong and what to build next (test/CI gaps,
signed update set, cost/sizing tables, DHCP/IPv6 depth, GovCloud variants) is in
[`REVIEW-AND-IMPROVEMENTS.md`](./REVIEW-AND-IMPROVEMENTS.md).

---

*This volume is platform-vendor documentation, independent of the surrounding UIAO
repository's governance canon. It is intentionally self-contained under
`infoblox-ddi-book/`.*
