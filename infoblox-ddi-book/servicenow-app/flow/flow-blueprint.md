# Flow blueprint — "Provision DDI-backed subnet"

The Flow Designer flow that ties the app together. Flow exports are large opaque
XML; this blueprint documents the trigger, steps, and the inline Action scripts so
you can rebuild it in Flow Designer (or hand it to a partner) exactly. It implements
the closed loop from [Chapter 7](../../07-servicenow-orchestration.md).

**Scope:** `x_infoblox_ddi` · **Run as:** the app's service account · **Trigger:**
Service Catalog — item *Request a DDI-backed subnet* submitted.

## Steps

1. **Trigger — Catalog item submitted.** Inputs = the catalog variables mapped to
   the target platform's `tfvars` (see each package's `servicenow/ServiceNow-Orchestration.md`).
2. **Approval — Ask for approval** (SoD gate). Approvers = the network/DDI group.
   Reject → close request *cancelled*.
3. **Allocate CIDR (Action → Script step, `InfobloxDDIClient`):**
   ```javascript
   (function execute(inputs, outputs) {
     var c = new x_infoblox_ddi.InfobloxDDIClient();
     outputs.cidr = inputs.requested_cidr;             // or reserve a block from IPAM
     outputs.gateway_ip = c.nextAvailableIp(inputs.requested_cidr, inputs.network_view);
   })(inputs, outputs);
   ```
4. **CPG Terraform apply.** Call the **Cloud Provisioning & Governance Terraform
   Connector** catalog task for the platform's `terraform/` module, passing the
   catalog inputs as `tfvars` and `inputs.cidr` as `ddi_subnet_address_prefix`.
   Runs on the MID Server (speculative plan → the approval above → apply).
5. **Register DNS (Action → Script step, `InfobloxDDIClient`):**
   ```javascript
   (function execute(inputs, outputs) {
     var c = new x_infoblox_ddi.InfobloxDDIClient();
     outputs.record_ref = c.createHostRecord(inputs.fqdn, inputs.gateway_ip, inputs.dns_view);
   })(inputs, outputs);
   ```
6. **Validation gate (Action → Script step, `InfobloxDDIGate`):**
   ```javascript
   (function execute(inputs, outputs) {
     var g = new x_infoblox_ddi.InfobloxDDIGate();
     var v = g.runGate({
       SCRIPTS_DIR: inputs.platform,   // azure|aws|gcp|oci|vmware
       DDI_VIP: inputs.ddi_vip, TEST_FQDN: inputs.fqdn, EXPECTED_IP: inputs.gateway_ip,
       GRID_MASTER: inputs.grid_master
     });
     outputs.overall = v.overall;
     outputs.detail = JSON.stringify(v.checks);
   })(inputs, outputs);
   ```
   **If `overall != 'pass'`** → post `detail` to work-notes and route back to step 2
   (or open a task); do **not** close the change.
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
