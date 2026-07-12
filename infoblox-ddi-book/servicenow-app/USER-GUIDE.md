# User guide — the Infoblox DDI front door in ServiceNow

This guide explains how to use the ServiceNow front door for Infoblox DDI
automation: how a **requester** orders a DDI-backed subnet (with its IP space and
DNS records allocated automatically), how an **approver** reviews and signs off on
that request, and how an **admin / operator** runs the flow behind it and
troubleshoots when a step fails. It is task-oriented — read the part that matches
your role.

Behind the catalog form, an approved request runs a closed loop: Terraform applies
the platform module, Infoblox allocates the IP and registers DNS, a validation gate
confirms it, and the result reconciles into the CMDB — all recorded as audit
evidence. You do not need to understand that machinery to file or approve a request;
Part 3 covers it for operators.

> **The screens in this guide are illustrative mock-ups, not real screenshots.**
> They resemble a ServiceNow Next Experience portal to communicate the intended
> experience (see [`mockups/README.md`](./mockups/README.md)). Exact labels, field
> order, colors, and record numbers vary by instance, version, and theme. Treat the
> images as a map of *what to look for*, not a pixel-exact match to your instance.

## Who this is for

| Role | What you do | Read |
|---|---|---|
| **Requester** | Order a DDI-backed subnet (or decommission one) and track it to completion. | [Part 1](#part-1--requester-guide) |
| **Approver** | Review a submitted request, confirm separation-of-duties and pre-checks, then Approve / Reject. | [Part 2](#part-2--approver-guide) |
| **Admin / Operator** | Own the Flow, handle gate failures and stale-sync incidents, keep the CMDB honest. | [Part 3](#part-3--admin--operator-guide) |

---

## Part 1 — Requester guide

You are a network, platform, or application engineer who needs a subnet with real
IP addressing and DNS behind it. Instead of filing a ticket and waiting for someone
to run a pipeline, you fill in one catalog form and the platform does the rest.

### Opening the catalog item

In the ServiceNow **Service Catalog** (or the employee/service portal search),
open **"Request a DDI-backed subnet."** It is the front door for a single subnet on
one target platform. The form's fields map directly to the parameters the
automation needs — you are describing *what* you want, not *how* it is built.

![The 'Request a DDI-backed subnet' catalog form in ServiceNow, showing fields for target platform, region, a pre-populated hub network, requested CIDR, environment, deployment model, host FQDN, an acknowledge-SaaS-boundary checkbox, and a business justification text box, with an Order Now button](mockups/sn-01-catalog-request.png)

### Field-by-field

Fill these in top to bottom. Fields sourced from your platform's landing-zone
outputs (like the hub network) are **pre-populated** — pick from the list, don't
free-type them, so you can't invent a hub that doesn't exist.

| Field | What to enter |
|---|---|
| **Target platform** | The cloud/estate the subnet lives in — Azure, AWS, GCP, OCI, or VMware. This selects which Terraform module and validation scripts run. |
| **Region** | The provider region for the subnet (e.g. an Azure commercial region). Pick from the approved list; there is no default. |
| **Hub network** (pre-populated) | The hub VNet/VPC the subnet attaches to, sourced from your landing-zone outputs. Choose from the list — do not type a raw ID. This is what the new CIDR must fit inside. |
| **Requested CIDR** | The address range for the new subnet (e.g. `10.20.4.0/24`). It must fit inside the hub network and not overlap anything already allocated — the approval pre-checks verify this, so a bad CIDR is caught before anything is built. |
| **Environment** | `dev`, `test`, or `prod`. Drives tags and sizing **and** the approval tier — `prod` gets an extra approval step. |
| **Deployment model** | `grid` (default) or `universal_ddi`. **`grid`** keeps every DDI call in-boundary (WAPI to your Grid) — this is the boundary-clean default. **`universal_ddi`** uses Infoblox's SaaS Portal control plane, which sits **outside** the ATO boundary; pick it only when you genuinely need the SaaS path. |
| **Host FQDN** | The fully-qualified name to register in DNS for the primary/gateway address (e.g. `app-ddi-01.corp.example`). The flow creates the A record (and PTR) for this name. |
| **Acknowledge SaaS boundary** | A checkbox that only matters when **Deployment model = `universal_ddi`**. It must be checked to proceed, and checking it adds an **extra approval** because you are opting into an out-of-boundary path. Leave it unchecked for `grid`. |
| **Business justification** | A short, plain-language reason for the request. This is what the approver reads first — a clear justification speeds approval. |

**You never enter secrets here.** Passwords, grid shared secrets, join tokens, and
API credentials are not catalog fields. They live in your platform's secret store
(e.g. a Key Vault) and are resolved on the MID Server at run time. The form collects
only *references*, never secret values.

### What happens after you click Order Now

Submitting creates a request (a RITM). From then on it is hands-off — you don't run
anything. Open the request's status page to watch the closed loop advance.

![The request status page for a DDI subnet order, showing a progress timeline with stages — Submitted, Approval, Terraform apply, IPAM/DNS allocation, Validation gate, CMDB reconcile, Closed complete — and a work-notes panel with timestamped entries such as the allocated IP and the validation verdict](mockups/sn-03-request-status.png)

The timeline maps one-to-one to the automation:

1. **Submitted** — your request is filed.
2. **Approval** — an approver reviews it (Part 2). For `prod` or the SaaS path there
   is more than one approval.
3. **Terraform apply** — the platform module is planned and applied on the MID
   Server.
4. **IPAM / DNS allocation** — Infoblox allocates the next available IP in your CIDR
   and registers the host FQDN (A + PTR).
5. **Validation gate** — three checks confirm DNS resolves, discovery is in sync,
   and there's no IPAM conflict.
6. **CMDB reconcile** — the new network shows up as a configuration item.
7. **Closed complete** — done; the allocated IP and DNS name are live.

The **work notes** are your running log: the allocated IP, the DNS record
reference, the validation verdict, and — if something fails — the reason. **To find
your request** later, use *My Requests* / *My Requested Items* in the portal, or the
RITM number from your submission confirmation. **Typical timing:** the automated
steps (apply → allocate → validate → reconcile) run in minutes once approved; the
wall-clock time is dominated by how long approval takes (see the approver SLA in
Part 2).

### Decommissioning (giving a subnet back)

When a subnet is no longer needed, don't just delete resources by hand — that leaves
IPAM thinking the addresses are still in use ("ghosts"). Instead, use the
**"Decommission DDI subnet"** retirement catalog item. It runs the loop in reverse:
approval → Terraform `destroy` → Infoblox **reclaim** (delete the host/A/PTR records
and free the IP back to the pool) → retire the CMDB CI → close. **Reclaim** means
the IP space and DNS names return to the pool so they can be handed out again —
keeping IPAM an accurate inventory instead of accumulating stale entries.

---

## Part 2 — Approver guide

You are in the network/DDI approver group. Your job is the governance gate: confirm
the request is legitimate and safe before any infrastructure is built.

### Where approvals show up

Approvals land in your ServiceNow **My Approvals** list (and via notification). Open
one to see the request, the requester, the key parameters, and the automated
pre-check results.

![An approval screen for a DDI subnet request, showing the requester, target platform, requested CIDR, environment, deployment model, and business justification, alongside green pre-check results for IPAM conflict and CIDR-fits-hub, with Approve, Reject, and Request more information buttons](mockups/sn-02-approval.png)

### What you are actually gating

- **Separation of duties (SoD).** The **requester cannot be the approver.** This is
  the AC-5/AC-6 control — someone other than the person asking must authorize the
  change. If a request appears to be self-approved, reject it.
- **The extra tier for `prod`.** A `prod` request carries higher blast radius, so it
  routes through an additional (change-advisory) approval on top of the standard
  gate. Expect two sign-offs for production.
- **The pre-checks.** The screen shows automated results you should read before
  deciding:
  - **IPAM conflict** — confirms the requested CIDR does not overlap an existing
    allocation. A failure here means the address space is already in use.
  - **CIDR fits hub** — confirms the requested CIDR fits inside the chosen hub
    network. A failure means the range is outside the hub or the wrong size.
  These tell you the request is buildable *before* you approve it; a red pre-check is
  a reason to reject or ask for a corrected CIDR.
- **The SaaS-boundary approval.** If **`acknowledge_saas_boundary` is set** (the
  requester chose `universal_ddi`), there is an **extra approval** because that path
  uses the out-of-boundary Infoblox Portal control plane. Treat it as a reviewed
  exception: confirm there is a real need for the SaaS path, not the in-boundary
  `grid` default.

### Approve, Reject, or ask for more info

- **Approve** when SoD holds, the pre-checks are green, the justification is
  sound, and (for SaaS) the boundary exception is warranted.
- **Reject** when a pre-check fails, the justification is inadequate, SoD is
  violated, or the SaaS path isn't justified. Rejecting closes the request as
  *cancelled* — the requester resubmits a corrected order.
- **Request more information** when the intent is fine but a detail (CIDR size,
  FQDN, justification) needs clarification, so the requester can fix it without
  starting over.

**SLA:** act on approvals promptly — approval time is usually the longest part of
the whole request, since the automation runs in minutes once you sign off. Every
**Approve / Reject is recorded to the audit trail** (AC-5/AC-6), so your decision,
timestamp, and identity are part of the permanent change record.

---

## Part 3 — Admin / operator guide

You own the Flow and the integration. This section describes what runs, how to read
a failure, and how to keep IPAM and the CMDB honest. The importable app skeleton and
wire-up steps are in [`./README.md`](./README.md); the end-to-end build sequence is
in [`./PLAYBOOK-servicenow-led-build.md`](./PLAYBOOK-servicenow-led-build.md).

### What actually runs

The **"Provision DDI-backed subnet"** flow in Flow Designer is the engine. It is a
trigger plus a sequence of actions — the full blueprint (with the inline Action
scripts) is in [`flow/flow-blueprint.md`](./flow/flow-blueprint.md).

![The Provision DDI-backed subnet flow open in ServiceNow Flow Designer, showing a catalog-submitted trigger followed by action steps — Ask for approval, Allocate CIDR, CPG Terraform apply, Register DNS, Validation gate, CMDB reconcile, Close — with a dashed edge routing a failed validation gate back to the approval step](mockups/sn-04-flow-designer.png)

At an operator level, the steps are:

1. **Trigger — catalog item submitted.** The catalog variables are mapped to the
   target platform's `tfvars`.
2. **Approval (SoD gate).** The approvals in Part 2. Reject closes the request
   *cancelled*.
3. **Allocate CIDR** (`InfobloxDDIClient`). Reserves/confirms the subnet and asks
   Infoblox for the next available IP in the requested CIDR and network view.
4. **CPG Terraform apply.** The Cloud Provisioning & Governance Terraform Connector
   runs the platform module on the in-boundary MID Server (speculative plan →
   approval → apply). Secret references resolve on the MID Server.
5. **Register DNS** (`InfobloxDDIClient`). Creates the host record (A + PTR) for the
   FQDN against the allocated IP.
6. **Validation gate** (`InfobloxDDIGate`). Runs the three MID-Server checks and
   parses one JSON verdict (see below).
7. **CMDB reconcile.** Triggers the Service Graph Connector import so the new
   `cmdb_ci_ip_network` / `_subnet` CIs appear and attach to the request.
8. **Close.** Sets the request *closed complete*; the plan, approvals, and gate
   output are the audit trail.

### Handling a validation-gate failure

The gate (step 6) runs three checks on the MID Server — **DNS validation**,
**discovery-sync**, and **IPAM-conflict** — and emits a single JSON verdict with an
`overall` result and a per-check `detail`. **When `overall != 'pass'`:**

- The flow **posts the JSON `detail` to the request's work notes** and **routes back
  to the approval step (step 2)** — it does **not** close the change. So a failed
  request never silently completes.
- **Read the JSON verdict in the work notes** to see which of the three checks
  failed and why:
  - **DNS validation** — the registered FQDN doesn't resolve to the expected IP.
    Check the Register-DNS step and the DNS view.
  - **Discovery-sync** — Infoblox's view of the estate is stale. Check the discovery
    credential/identity and the discovery schedule.
  - **IPAM-conflict** — the allocated address collides with an existing entry. Check
    the network view and CIDR.

Fix the underlying cause, then let the request re-approve and re-run, or open a task.

### The staleness → Incident scheduled job

A **Scheduled Script Execution** runs the gate's **discovery-sync check** per
platform on an interval, independent of any request. When a sync comes back **stale
(fail)**, it **auto-creates an Incident assigned to the DDI group.** This keeps "one
authoritative IPAM" honest *between* requests — you find out discovery drifted before
the next requester hits a gate failure because of it. If these Incidents recur, the
usual root cause is an expired or misscoped discovery credential.

### The CMDB result

After a successful run, the Service Graph Connector for Infoblox reconciles the new
network into the CMDB as configuration items.

![A reconciled cmdb_ci_ip_network configuration item in ServiceNow, showing the subnet's CIDR, network view, environment and deployment-model attributes correlated from Infoblox extensible attributes, and a related-list link back to the originating catalog request](mockups/sn-05-cmdb-ci.png)

**Important: the CMDB is a reflection, not the source of truth.** Infoblox IPAM is
the system of record for IP space and DNS; the Service Graph Connector syncs *from*
IPAM *into* the CMDB. If the CMDB and IPAM disagree, IPAM wins — investigate the
sync, don't edit the CI to "fix" it.

### Troubleshooting

| Symptom | Likely cause | Where to look |
|---|---|---|
| Terraform **apply fails on the MID Server** | Secret alias/reference wrong; MID can't resolve a credential | Key Vault (or secret store) referenced by the request; the credential/connection alias `x_infoblox_ddi.infoblox`; MID Server logs |
| **Next-available-IP comes back empty** | Wrong network view, or the CIDR is full/missized | The requested CIDR and network view; whether the block has free addresses; the Allocate-CIDR step inputs |
| **Discovery-sync gate is stale / recurring staleness Incidents** | Expired or misscoped discovery credential/identity | The discovery credential (identity type, scope); the discovery schedule; the staleness scheduled job |
| **Validation gate fails but apply "worked"** | DNS didn't register as expected, or an IPAM conflict slipped in | The JSON verdict in the request work notes — which of the three checks failed |
| **CMDB CI never appears** | Service Graph Connector import didn't run or didn't correlate | The Service Graph Connector import schedule/logs; the `servicenow_sys_id` extensible attribute on the Infoblox object |
| **Request stuck at approval** | Approver hasn't acted, or SoD/SaaS extra approval pending | The approval record (Part 2); whether `environment=prod` or `acknowledge_saas_boundary` added a tier |
| **`universal_ddi` request hard-fails at plan** | `acknowledge_saas_boundary` not set to `true` | The catalog input; the SaaS-boundary approval |

---

## Governance & boundary (what every user should know)

Three rules underpin the whole front door — they're why this is a *governed* front
door and not just a form:

- **The MID Server runs in-boundary.** Terraform applies, Infoblox REST callouts,
  and the validation scripts all execute on a MID Server registered **inside the ATO
  boundary**, so the execution and credential path never leaves it.
- **Secrets are never entered in ServiceNow.** The catalog collects only references
  (e.g. a Key Vault ID); the actual passwords, grid secrets, join tokens, and API
  credentials resolve on the MID Server at run time. ServiceNow holds references, not
  secret material.
- **The Universal DDI SaaS path is a reviewed exception.** `grid` (WAPI-to-Grid) is
  the in-boundary default. `universal_ddi` uses the out-of-boundary Portal control
  plane; it is gated by `acknowledge_saas_boundary = true` and an extra approval — an
  explicit, reviewed choice, never the default.

Full control-family mapping (AC-5/AC-6 approvals, AU/CM audit trail, CM-6 validation
gates, CM-8 reclaim) is in
[Chapter 7 §7.4](../07-servicenow-orchestration.md).

---

## FAQ

**Can I pick my own IP address?**
No — you request a **CIDR** (the subnet range), and Infoblox allocates the next
available IP inside it. This keeps IPAM as the single source of truth and prevents
collisions. You *do* choose the FQDN that gets registered to that address.

**Why was my request rejected?**
Common reasons: a pre-check failed (the CIDR overlaps an existing allocation or
doesn't fit the hub), the business justification was thin, separation-of-duties was
violated, or a `universal_ddi` (SaaS) path wasn't justified. The rejection notes say
which — fix it and resubmit.

**How do I get a DNS record without provisioning a subnet?**
This catalog item is for a **DDI-backed subnet** (subnet + IP + DNS together). A
standalone DNS record is a different request — ask your DDI team; it isn't this form.

**What if I chose the wrong platform (or CIDR, region, FQDN)?**
If the request hasn't been approved yet, ask an approver to reject it and submit a
corrected one — the fields feed the automation, so they can't be swapped mid-run. If
it already provisioned, decommission it (retirement item) and re-request.

**How long does it take?**
Once approved, the automated steps run in minutes. The variable part is approval
time, so a clear justification and correct CIDR are the fastest path.

**What does "reclaim" mean when I decommission?**
The retirement flow deletes the DNS records and returns the IP space to the Infoblox
pool so it can be reassigned — leaving no stale "ghost" entries in IPAM.

**Do I need to enter any passwords or API keys?**
Never. Secrets live in your platform's secret store and resolve on the MID Server.
The form only ever collects references.

**My request completed but the CMDB CI isn't there yet — is it broken?**
Usually not. The CMDB reflects IPAM via a scheduled Service Graph Connector import,
which may lag the request slightly. If it's still missing after the next import,
raise it with the DDI/operator team (see the troubleshooting table).

**Grid vs Universal DDI — which should I pick?**
Pick **`grid`** unless you have a specific reason not to; it keeps everything
in-boundary. Choose **`universal_ddi`** only when you need the SaaS control plane,
and expect the extra boundary acknowledgement and approval.

---

## Sources

- [Service Graph Connector for Infoblox — ServiceNow Store](https://store.servicenow.com/store/app/eeb927621b246a50a85b16db234bcbf1)
- [Cloud Provisioning & Governance: Terraform Connector — ServiceNow Store](https://store.servicenow.com/store/app/6ff8ef2e1be06a50a85b16db234bcbcb)

Cross-references (in this volume):
[`./README.md`](./README.md) ·
[`./PLAYBOOK-servicenow-led-build.md`](./PLAYBOOK-servicenow-led-build.md) ·
[Chapter 7 — ServiceNow Orchestration](../07-servicenow-orchestration.md) ·
[Chapter 8 — ServiceNow-led implementation](../08-servicenow-led-implementation.md)
