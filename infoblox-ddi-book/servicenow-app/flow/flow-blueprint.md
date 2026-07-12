# Flow blueprint — "Provision DDI-backed subnet"

The Flow Designer flow that ties the app together. Flow exports are large opaque
XML; this blueprint documents the trigger, steps, and the inline Action scripts so
you can rebuild it in Flow Designer (or hand it to a partner) exactly. It implements
the closed loop from [Chapter 7](../../07-servicenow-orchestration.md).

**Scope:** `x_infoblox_ddi` · **Run as:** the app's service account · **Trigger:**
Service Catalog — item *Request a DDI-backed subnet* submitted.

## Steps

Trigger + 7 actions. The canonical order is **pre-flight → approval → apply →
allocate/register → gate → reconcile → close** — the requested CIDR is checked
*before* approval (fail fast, and give the approver a real result to read), and the
next-available host IP is allocated *after* Terraform has created the subnet.

1. **Trigger — Catalog item submitted.** Inputs = the catalog variables mapped to
   the target platform's `tfvars` (see each package's `servicenow/ServiceNow-Orchestration.md`).
2. **Pre-flight validation (Action → Script step, `InfobloxDDIClient`).** A
   **read-only** check on the *requested* CIDR, run **before** approval so a bad
   request fails fast and the approver sees a real result (not a promise): (a) the
   CIDR fits inside the chosen hub network, and (b) it does not overlap an existing
   Infoblox network. This is advisory/pre-approval; the enforced check is the
   post-apply gate (step 6).
   ```javascript
   (function execute(inputs, outputs) {
     var c = new x_infoblox_ddi.InfobloxDDIClient();
     // read-only: fits-hub is a pure containment test; overlap is a WAPI GET.
     outputs.fits_hub    = c.cidrFitsHub(inputs.requested_cidr, inputs.hub_cidr);
     outputs.no_overlap  = c.noOverlap(inputs.requested_cidr, inputs.network_view);
     outputs.preflight_ok = outputs.fits_hub && outputs.no_overlap;
   })(inputs, outputs);
   ```
   Surface `fits_hub` / `no_overlap` to the approval screen. (`cidrFitsHub` /
   `noOverlap` are read-only helpers to add to `InfobloxDDIClient` — the client
   currently ships allocate/register/delete.)
3. **Approval — Ask for approval** (SoD gate). Approvers = the network/DDI group;
   requester ≠ approver. Route on `environment` (prod → extra change-advisory tier)
   and on `deployment_model` (`universal_ddi` requires `acknowledge_saas_boundary =
   true` + an extra approval). Reject → close request *cancelled*.
4. **CPG Terraform apply.** Call the **Cloud Provisioning & Governance Terraform
   Connector** catalog task for the platform's `terraform/` module, passing the
   catalog inputs as `tfvars` and `inputs.requested_cidr` as
   `ddi_subnet_address_prefix`. Runs on the MID Server (speculative plan → the
   approval above → apply).
5. **Allocate + register (Action → Script step, `InfobloxDDIClient`).** *After*
   apply has created the subnet, allocate the next-available **host** IP (not the
   gateway) and register the FQDN's A + PTR records:
   ```javascript
   (function execute(inputs, outputs) {
     var c = new x_infoblox_ddi.InfobloxDDIClient();
     outputs.allocated_ip = c.nextAvailableIp(inputs.requested_cidr, inputs.network_view);
     outputs.record_ref   = c.createHostRecord(inputs.fqdn, outputs.allocated_ip, inputs.dns_view);
   })(inputs, outputs);
   ```
   `network_view` / `dns_view` come from the catalog form where set, else default to
   the app property / the WAPI default view.
6. **Validation gate (Action → Script step, `InfobloxDDIGate`):**
   ```javascript
   (function execute(inputs, outputs) {
     var g = new x_infoblox_ddi.InfobloxDDIGate();
     var v = g.runGate({
       SCRIPTS_DIR: inputs.platform,   // azure|aws|gcp|oci|vmware
       DDI_VIP: inputs.ddi_vip, TEST_FQDN: inputs.fqdn, EXPECTED_IP: inputs.allocated_ip,
       GRID_MASTER: inputs.grid_master
     });
     outputs.overall = v.overall;
     outputs.detail = JSON.stringify(v.checks);
   })(inputs, outputs);
   ```
   `ddi_vip` / `grid_master` come from app properties (or the module outputs) rather
   than the requester's form. **If `overall != 'pass'`** → post `detail` to
   work-notes and route back to the **approval step** (or open a task); do **not**
   close the change.
7. **CMDB reconcile.** Trigger the **Service Graph Connector for Infoblox** import
   (or a targeted lookup) so the new `cmdb_ci_ip_network` / `_subnet` CIs appear,
   attach them to the request.
8. **Close.** Set request *closed complete*; the change record + approvals + gate
   output are the audit trail (Chapter 7 §7.4 control mapping).

## Retirement flow (companion)

Trigger = *Decommission DDI subnet*. Steps: approval → CPG `terraform destroy` →
`InfobloxDDIClient.deleteObject(record_ref)` (reclaim IP + delete records) → CMDB
retire CIs → close. This is the reclaim-on-delete half that keeps IPAM free of ghosts.

## Scheduled: discovery-sync staleness → Incident

A Scheduled Script Execution calls `InfobloxDDIGate.runGate({...only discovery-sync...})`
per platform on an interval; on `fail` (stale), create an **Incident** assigned to the
DDI group. Keeps the "one authoritative IPAM" honest between requests.
