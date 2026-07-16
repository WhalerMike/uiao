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

> **Series membership:** this kit is also **Volume VIII — Multi-Cloud DDI
> Landing-Zone Automation** of the Federal Application-Aware Networking series.
> It is bound to the series through the compliance spine
> (`aan-compliance-spine.yml`, `vol-8`) and the volume overview at
> `docs/customer-documents/federal-aan-series/Vol_VIII_Book_00_FedAAN_DDI_Automation_Overview.qmd`,
> without relocating this kit — it remains independently distributable. The kit is
> intentionally multi-CSP (a deliberate breadth exception to the series' current
> GCC-Moderate scope); federal control closure is operated at the GCC-Moderate
> ServiceNow front door in [Chapter 7 §7.4](./07-servicenow-orchestration.md).

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
| 8 | [ServiceNow-Led Implementation](./08-servicenow-led-implementation.md) | Experience-first build order + sample catalog/approval screens, build playbook, and full user documentation |
| A | [Appendix A — Sizing & Cost, IPv6/Dual-Stack, DHCP](./appendix-A-sizing-cost-ipv6-dhcp.md) | Cross-platform sizing/cost framework, IPv6 planning, and where DHCP is real |

> Numbers are **reference order**, not the required reading order. If ServiceNow is your
> front door, read **§0.5 → Ch 8 → Ch 7** first, then your platform chapter as the fulfillment
> engine — see [Reading paths](#reading-paths-the-order-to-read-in).

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

[**Chapter 8**](./08-servicenow-led-implementation.md) flips the build order to **lead with
ServiceNow** — stand up the governed experience first, then wire the automation behind it —
and ships the human-facing deliverables: **sample ServiceNow screens** (catalog, approval,
status, flow, CMDB — [`servicenow-app/mockups/`](./servicenow-app/mockups/README.md)), a
**step-by-step [build playbook](./servicenow-app/PLAYBOOK-servicenow-led-build.md)**, and a
**full [user guide](./servicenow-app/USER-GUIDE.md)** (requester / approver / admin).

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

## Reading paths (the order to read in)

The chapters are **numbered in reference order** — platform-by-platform, so you can jump
straight to your cloud. That is deliberately *not* the only order to read them in: the
platform chapters are reference material, consulted by platform, not a front-to-back novel.
Pick the path that matches your goal — and note the first one **leads with ServiceNow**, per
the experience-first strategy in [Chapter 8](./08-servicenow-led-implementation.md).

- **⭐ ServiceNow-led** *(recommended if ServiceNow is your system of engagement)* — stand up
  the governed experience first, then the automation behind it:
  [Ch 0 §0.5](./00-introduction.md) → **[Ch 8](./08-servicenow-led-implementation.md)** →
  [Ch 7](./07-servicenow-orchestration.md) → [`servicenow-app/`](./servicenow-app/README.md)
  → your platform chapter (1–5) as the *fulfillment engine* → [Ch 6](./06-cross-platform-operations.md).
- **Platform-led** *(deploying one cloud now)* — your chapter (1–5) → its automation package
  → [Ch 7](./07-servicenow-orchestration.md)/[Ch 8](./08-servicenow-led-implementation.md) to
  add the front door → [Ch 6](./06-cross-platform-operations.md) for the estate.
- **Architecture / target-state** — [Ch 0](./00-introduction.md) → sections 1–2 of every
  platform chapter → [Ch 6](./06-cross-platform-operations.md) →
  [Ch 7](./07-servicenow-orchestration.md)/[Ch 8](./08-servicenow-led-implementation.md).
- **End users (request / approve / operate)** — go straight to the
  [user guide](./servicenow-app/USER-GUIDE.md).
- **Standardizing** — lift each chapter's section-4 prerequisites into landing-zone guardrails
  and the section-5 runbooks into your IaC/pipelines.

> **Why the chapters aren't physically renumbered ServiceNow-first:** the numeric order is
> the reference index (and the AAN volume naming), while the *reading* order above is where
> "lead with ServiceNow" lives. Renumbering would churn every cross-reference and file name
> for no reader benefit the reading paths don't already provide.

## Maturity & roadmap

This volume is an honest **starter** — production-grade in structure and framing, explicitly
labeled as un-certified skeletons where the IaC and ServiceNow records are concerned. A
candid, prioritized assessment of what is strong and what to build next (test/CI gaps,
signed update set, cost/sizing tables, DHCP/IPv6 depth, GovCloud variants) is in
[`REVIEW-AND-IMPROVEMENTS.md`](./REVIEW-AND-IMPROVEMENTS.md).

**Azure is the designated gold exemplar** — the one platform being hardened to a *tested*
reference the others pattern on. Its kit is in
[`azure-alz-automation/GOLD-EXEMPLAR.md`](./azure-alz-automation/GOLD-EXEMPLAR.md): a committed
`terraform.tfvars.example`, a `terraform validate`-clean module, and a **machine-checked
catalog↔module contract** (blocking in CI) — plus a certification checklist with evidence
slots for the live apply, validation transcript, and real screenshots you run in your
environment.

---

*This volume is platform-vendor documentation, independent of the surrounding UIAO
repository's governance canon. It is intentionally self-contained under
`infoblox-ddi-book/`.*
