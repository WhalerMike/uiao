// Script Include: TerraformCpgClient  (application scope: x_ssa_day2_ops)
// -----------------------------------------------------------------------------
// Server-side Cloud-Provisioning-Gateway (CPG) Terraform client for Lane D — the
// Landing Zone Front Door (Vol IX Book 02). The IaC already exists (Vol VI Book
// 01): modules stand up subscriptions, networks and subnets from reviewed source.
// What was missing is the FRONT DOOR — the governed request that turns "someone
// runs the module" into "an approved, evidenced, reconciled provisioning event."
// This client is that door. Each method maps to a NIST control in
// servicenow-day2/landingzone-control-map.json.
//
// SERVICENOW DOES NOT WRITE TO THE ESTATE. It raises, routes and evidences; the
// actuation is platform-native. Nothing here touches Azure. Every method asks the
// in-boundary MID Server to drive the CPG Terraform Connector, and the Connector
// runs the module. This client requests a run and tracks it — it does not apply
// infrastructure, and it holds no cloud credential that could.
//
// L3, NOT L4 (ADR-092). Actuation on this lane is human-approved. That is why
// the provisioning methods below start a SPECULATIVE PLAN and stop: a plan
// changes no state, and the approver reads it before anything is applied. The
// apply is a separate call (applyRun) that will not proceed without the change
// record and approver identity that prove a human authorized it. There is
// deliberately no method that plans and applies in one breath — the gap between
// those two calls is where the control lives.
//
// Boundary discipline (Vol IX Book 00 / Vol VII):
//   * All CPG calls route through the in-boundary MID Server
//     (property x_ssa_day2_ops.mid_server) — credentials/execution never leave
//     the ATO boundary.
//   * Endpoint + auth come from the Connection & Credential alias
//     (x_ssa_day2_ops.cpg) — no secrets in code.
//   * LEAST PRIVILEGE: the CPG workspace credential is scoped to the landing-zone
//     workspaces and the modules they pin — not tenant-wide Owner. A front door
//     that could deploy anything is not a front door, it is a second back door.
//
// STARTER SKELETON — pin the CPG API version and the module source refs, and
// validate the workspace credential against your subscription, before production
// use.  test_mode (x_ssa_day2_ops.test_mode = 'true') returns deterministic
// canned values so the ATF suites drive the Flow in sub-prod with NO live CPG
// connectivity.  Never enable test_mode in production.
// -----------------------------------------------------------------------------
var TerraformCpgClient = Class.create();
TerraformCpgClient.prototype = {

    initialize: function () {
        this.midServer = gs.getProperty('x_ssa_day2_ops.mid_server', '');
        this.endpoint = gs.getProperty('x_ssa_day2_ops.cpg_endpoint', '');
        this.boundary = gs.getProperty('x_ssa_day2_ops.boundary', 'gcc-moderate');
        // Workspaces are per-landing-zone, so the prefix is how a run is tied back
        // to the zone it belongs to rather than to whoever launched it.
        this.workspacePrefix = gs.getProperty('x_ssa_day2_ops.cpg_workspace_prefix', 'lz-');
        this.log = { logErr: function (m) { gs.error('[x_ssa_day2_ops.TerraformCpgClient] ' + m); } };
        this.testMode = gs.getProperty('x_ssa_day2_ops.test_mode', 'false') === 'true';
    },

    // --- Provision: landing-zone subscription (CM-2). -------------------------
    // CM-2 is "deployed state equals reviewed source", so the request may name a
    // module and a version but never carry inline configuration: anything not in
    // the pinned source is drift the moment it lands. Returns a plan run for the
    // approver to read — see applyRun for the state change.
    provisionSubscription: function (payload) {
        if (this.testMode)
            return { ok: true, runId: 'test-run-0001', status: 'planned', applied: false,
                     workspace: this.workspacePrefix + 'subscription' };
        return this._cpg('plan', {
            workspace: this.workspacePrefix + 'subscription',
            module: payload.module,
            moduleVersion: payload.moduleVersion,
            vars: {
                environment: payload.environment,
                managementGroup: payload.managementGroup,
                owner: payload.owner,
                billingScope: payload.billingScope
            }
        });
    },

    // --- Provision: virtual network (CM-3). -----------------------------------
    // CM-3 is the change-control gate itself, and the speculative plan IS the
    // artifact the gate reads — an approver cannot approve a change whose blast
    // radius they have not seen. A vnet plan that shows destroys is the case the
    // heightened approval in the control map exists for, which is only possible
    // because the plan happens before the apply and not during it.
    provisionVnet: function (payload) {
        if (this.testMode)
            return { ok: true, runId: 'test-run-0002', status: 'planned', applied: false,
                     workspace: this.workspacePrefix + 'vnet', destroyCount: 0 };
        return this._cpg('plan', {
            workspace: this.workspacePrefix + 'vnet',
            module: payload.module,
            moduleVersion: payload.moduleVersion,
            vars: {
                subscriptionId: payload.subscriptionId,
                addressSpace: payload.addressSpace,
                region: payload.region,
                environment: payload.environment
            }
        });
    },

    // --- Allocate: subnet, DDI-backed (CM-8). ---------------------------------
    // The whole point of CM-8 here is the join key: an asset inventory is only
    // real if the address an asset holds resolves to an authoritative record. A
    // free-typed CIDR has no such record — it is a number someone believed, and
    // it reconciles to nothing. So the address is NOT an input to this method.
    // The caller must present a reservation already made in the authoritative
    // IPAM/DDI (Vol VIII Book 07); the CPG run reads the block from that
    // reservation. Refusing early, here, is deliberate: by the time a plan has
    // been approved and applied, an out-of-plane allocation is already a CM-8 gap
    // that someone has to go find. No allocation outside the naming plane.
    allocateSubnet: function (payload) {
        payload = payload || {};
        if (this.testMode)
            return { ok: true, runId: 'test-run-0003', status: 'planned', applied: false,
                     workspace: this.workspacePrefix + 'subnet',
                     ddiReservationId: payload.ddiReservationId || 'test-ddi-res-0001' };
        if (!payload.ddiReservationId) {
            this.log.logErr('allocateSubnet: no ddiReservationId — refusing to plan an ' +
                            'allocation the IPAM/DDI does not know about (CM-8)');
            return { ok: false, error: 'ddiReservationId is required: the subnet must come from the ' +
                                       'authoritative IPAM/DDI, not from the request' };
        }
        return this._cpg('plan', {
            workspace: this.workspacePrefix + 'subnet',
            module: payload.module,
            moduleVersion: payload.moduleVersion,
            vars: {
                vnetId: payload.vnetId,
                // The DDI reservation is the source of the block. The CPG run
                // resolves it; nobody types a CIDR into a catalog variable.
                ddiReservationId: payload.ddiReservationId,
                environment: payload.environment
            }
        });
    },

    // --- Apply: the human-approved state change (CM-3). -----------------------
    // The L3 boundary in one method. `approval` must carry the change record and
    // the approver who signed it, and they are checked before the call goes out —
    // an apply with no provable human behind it is exactly the autonomous
    // actuation ADR-092 withholds from this lane. The MID re-verifies against the
    // run's own plan; this check is the near-side one, so an unapproved apply
    // never leaves ServiceNow at all.
    applyRun: function (runId, approval) {
        approval = approval || {};
        if (this.testMode)
            return { ok: true, runId: runId, status: 'applied', applied: true };
        if (!approval.changeSysId || !approval.approvedBy) {
            this.log.logErr('applyRun ' + runId + ': missing changeSysId/approvedBy — refusing ' +
                            'to apply without evidence a human approved it (L3, ADR-092)');
            return { ok: false, error: 'apply requires approval.changeSysId and approval.approvedBy' };
        }
        return this._cpg('apply', {
            runId: runId,
            changeSysId: approval.changeSysId,
            approvedBy: approval.approvedBy
        });
    },

    // --- Track: run state for the validation gate and close (CM-3). -----------
    // A read. The Flow polls this to move the request forward and to attach the
    // plan/apply output as evidence — the run, not a human's recollection of it,
    // is what the change record closes against.
    getRun: function (runId) {
        if (this.testMode)
            return { ok: true, runId: runId, status: 'planned', applied: false, destroyCount: 0 };
        return this._cpg('describe', { runId: runId });
    },

    // --- Internal: MID-routed CPG Terraform Connector operation. --------------
    // One transport for every op. The MID Server holds the workspace credential
    // and drives the Connector; ServiceNow only ever gets a run handle and its
    // status back. That asymmetry is the boundary: there is no code path here
    // that could reach the estate directly even if someone wanted one.
    _cpg: function (op, args) {
        try {
            var rm = new sn_ws.RESTMessageV2('x_ssa_day2_ops.cpg', 'POST');
            rm.setEndpoint(this.endpoint);
            if (this.midServer) rm.setMIDServer(this.midServer);   // in-boundary execution
            rm.setRequestBody(JSON.stringify({ op: op, args: args, boundary: this.boundary }));
            var resp = rm.execute();
            var code = resp.getStatusCode();
            return { ok: code >= 200 && code < 300, status: code, body: resp.getBody() };
        } catch (e) {
            this.log.logErr('_cpg ' + op + ' failed: ' + e);
            return { ok: false, error: '' + e };
        }
    },

    type: 'TerraformCpgClient'
};
