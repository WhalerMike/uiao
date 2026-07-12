# Phase 5 Kickoff — RedHat on AWS (GovCloud · FedRAMP Moderate)

> Status: DRAFT kickoff for author review · Surface: `inbox/` (not canon)
> Companion to: `inbox/Federal_Compliance_Automation_Roadmap.md` (§6, Phase 5)
> Date Code: 2026-07-12 15:00 ET

## 0. Scope note — a deliberate CSP expansion, still Moderate

Phases 1–4 (DDI decision, Vol VII compliance automation, Vol IX day-2 operations,
Teams/telephony) were scoped to **FedRAMP Moderate + Microsoft GCC Moderate**. Phase 5
is the deferred workstream you set aside — *"VMs are currently RedHat in AWS, so those
are after this."* It **expands the CSP surface to AWS GovCloud** while **holding the
FedRAMP Moderate boundary**. Nothing here claims FedRAMP High; AWS GovCloud and each
RedHat/vendor product's authorization are verified on the FedRAMP Marketplace at
procurement.

The coordination doctrine makes this expansion nearly free: the AWS estate reconciles
into the **same ServiceNow queues, the same CM-8 join key, and the same attestation
pipeline** the Azure/M365 core already uses — new connectors and control-map entries,
not a new architecture.

## 1. Objective

Extend the three control planes and the coordination layer to the **AWS RedHat estate**:
patch & configuration, vulnerability & posture, and DDI/naming — coordinated by
ServiceNow and attested through the existing evidence pipeline.

## 2. What already exists to build on

| Building block | Where | Reuse for Phase 5 |
|---|---|---|
| Patch & systems mgmt (RedHat Satellite / Ansible / Insights; AWS SSM) | `Vol_III_Book_03_FedAAN_Patch_Systems_Management.qmd` | The SI-2/CM actuation stacks — worked for AWS RedHat |
| AWS DDI (Route 53, VPC IPAM, InfoBlox on AWS GovCloud) | `infoblox-ddi-book/02-aws.md` (Vol VIII Book 02) | The naming-plane realization on AWS (CM-8) |
| Coordination doctrine (Graph/native actuation → ServiceNow evidence) | Vol VII, Vol IX | Same queues, same CM-8 key, extended to AWS |
| Compliance spine | `aan-compliance-spine.yml` | New AWS closures register here |

## 3. Workstreams

### 5.1 Patch & configuration (SI-2, CM-2/6)
- **Guest-OS actuation (platform-native):** RedHat **Satellite** (content/patch) +
  **Ansible Automation Platform** (actuation) + **Insights** (advisories/drift), with
  **AWS SSM Patch Manager** for the AWS-managed layer and golden-AMI rebuilds (EC2
  Image Builder).
- **Coordination:** patch results reconcile into the **ServiceNow SI-2 queue** (the
  Vol VII Book 03 pattern, extended to AWS), SLA class keyed to KEV/exposure.
- **Boundary note:** Satellite + Ansible run **in-boundary**; **Insights is a Red Hat
  SaaS** (Hybrid Cloud Console) — treat like the InfoBlox portal (gated by an explicit
  authorization review; verify FedRAMP status at procurement).

### 5.2 Vulnerability & posture (RA-5, CM-6)
- RedHat **Insights** vulnerability + **AWS Inspector** (workload/image scanning);
  **AWS Security Hub / GuardDuty** findings ingested to the evidence lake.
- Multi-cloud posture: **Defender for Cloud** multi-cloud (Moderate default) *or*
  AWS-native, feeding **Vol III Book 07 (Evidence Fabric)**.

### 5.3 DDI / naming (SC-20/22, CM-8)
- **InfoBlox on AWS GovCloud** + Route 53 / VPC IPAM (Vol VIII Book 02); every AWS
  RedHat asset reconciled to the authoritative **CM-8 join key** — the same identity
  the Azure/M365 CMDB uses, so AWS assets join *one* compliance picture.

### 5.4 ServiceNow day-2 extension
- Extend the **Vol IX day-2 catalog + control maps** to AWS: RedHat instance
  provisioning (landing-zone front door → AWS modules), patch scheduling, and
  SSM/Ansible actuation as governed, audited catalog items.

### 5.5 Evidence & attestation
- AWS estate control state flows into the **same Vol VII Book 04 attestation** and the
  FedRAMP 20x KSI feed — no separate authorization narrative.

## 4. Compliance crosswalk (AWS RedHat estate)

| Control | Closed by | KSI |
|---|---|---|
| SI-2 / SI-2(2/3) | Satellite/Ansible + SSM, reconciled to the ServiceNow SI-2 queue | KSI-SVC, KSI-MLA |
| RA-5 | Insights + AWS Inspector → ServiceNow VR | KSI-MLA |
| CM-2 / CM-6 | Ansible/State-Manager desired-state + drift detection | KSI-CMT |
| CM-8 | AWS assets reconciled to IPAM/DDI (InfoBlox on AWS GovCloud) | KSI-PIY |
| AU-2 / AU-6 | AWS/RedHat telemetry into the evidence fabric | KSI-MLA |

## 5. Sequencing

Phase 5 runs **after** the Azure/M365 core (now built). Suggested order: 5.3 DDI/naming
first (the join key everything else reconciles to), then 5.1 patch, 5.2 posture/vuln,
5.4 day-2 extension, 5.5 attestation.

## 6. Deliverables & how it lands in the series

Two candidate shapes (author's call):
1. **Extend existing books** — a worked *RedHat-on-AWS* section in Vol III Book 03
   (patch), a cross-ref in Vol VIII Book 02 (AWS DDI), and AWS entries in the Vol IX
   day-2 control maps. Lightest; keeps the estate in its domain books.
2. **A new "Multi-CSP Extension" volume (Vol X)** — if the AWS (and later OCI/VMware)
   work is substantial enough to warrant its own coordinated volume, mirroring how
   Vol VIII carried multi-cloud DDI. Heavier; better if the scope grows past AWS.

**Recommendation:** start with option 1 (extend in place) for AWS RedHat; promote to a
Vol X only if OCI/VMware follow and the material outgrows the domain books.

## 7. Next actions

1. Confirm the landing shape (extend-in-place vs. new Vol X).
2. Author the Vol III Book 03 *RedHat-on-AWS* worked section (5.1) and register its AWS
   closures in the spine.
3. Add AWS entries to the Vol IX day-2 control maps (5.4).
4. Verify AWS GovCloud + RedHat product FedRAMP authorizations at procurement.

Tracked by the Phase 5 epic issue (filed alongside this kickoff).
