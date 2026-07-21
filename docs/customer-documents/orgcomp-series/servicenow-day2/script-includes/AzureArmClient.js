// Script Include: AzureArmClient  (application scope: x_fed_day2_ops)
// -----------------------------------------------------------------------------
// Server-side Azure Resource Manager (ARM) client for the Day-2 Operations app
// (Vol IX). The identity plane is actuated by EntraHelpdeskClient via Graph; this
// is the RESOURCE plane — RBAC role assignments and resource reads on the Azure
// control plane — the second half of the estate a governed task may touch.
//
// It stays a peer of the Graph client, never a superset: this class holds ARM,
// that one holds Graph, and no method spans both. A task that needs both runs
// both through the Flow, each under its own least-privilege credential.
//
// Boundary discipline (Vol IX Book 00 / Vol VII):
//   * All ARM calls route through the in-boundary MID Server
//     (x_fed_day2_ops.mid_server) — execution never leaves the ATO boundary.
//   * Endpoint + auth come from the Connection & Credential alias
//     (x_fed_day2_ops.arm) — no secrets in code. The principal behind it holds a
//     LEAST-PRIVILEGE custom RBAC role, never Owner/Contributor at subscription
//     scope (AC-6).
//   * GCC-Moderate → management.azure.com.
//
// STARTER SKELETON — pin arm_version and validate the RBAC role against your
// subscription before production. test_mode returns deterministic canned values so
// the ATF suites drive the Flow with no live ARM. Never enable in production.
// -----------------------------------------------------------------------------
var AzureArmClient = Class.create();
AzureArmClient.prototype = {

    initialize: function () {
        this.armVersion = gs.getProperty('x_fed_day2_ops.arm_version', '2022-04-01');
        this.subscription = gs.getProperty('x_fed_day2_ops.arm_subscription', '');
        this.midServer = gs.getProperty('x_fed_day2_ops.mid_server', '');
        this.boundary = gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate');
        this.log = { logErr: function (m) { gs.error('[x_fed_day2_ops.AzureArmClient] ' + m); } };
        this.testMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
    },

    // Read a resource (reconciliation / evidence read — changes nothing). --------
    getResource: function (resourceId) {
        if (this.testMode) return { ok: true, id: resourceId, properties: { provisioningState: 'Succeeded' } };
        return this._arm('GET', resourceId, null);
    },

    // Assign a least-privilege RBAC role at a scope (AC-6). The roleAssignment GUID
    // is caller-supplied and deterministic so the operation is idempotent and the
    // assignment is findable for the verify re-read.
    assignRbacRole: function (scope, roleDefinitionId, principalId, assignmentGuid) {
        if (this.testMode)
            return { ok: true, id: scope + '/providers/Microsoft.Authorization/roleAssignments/' + assignmentGuid };
        if (!scope || !roleDefinitionId || !principalId || !assignmentGuid)
            return { ok: false, reason: 'scope, roleDefinitionId, principalId and a deterministic assignment GUID are all required (AC-6)' };
        var path = scope + '/providers/Microsoft.Authorization/roleAssignments/' + assignmentGuid;
        var body = { properties: { roleDefinitionId: roleDefinitionId, principalId: principalId } };
        return this._arm('PUT', path, body, '2022-04-01');
    },

    // Remove an RBAC assignment (leaver / stale-entitlement removal). ------------
    removeRbacRole: function (scope, assignmentGuid) {
        if (this.testMode) return { ok: true, removed: assignmentGuid };
        var path = scope + '/providers/Microsoft.Authorization/roleAssignments/' + assignmentGuid;
        return this._arm('DELETE', path, null, '2022-04-01');
    },

    // Re-read an RBAC assignment for the verify gate — affirmative existence only.
    getRbacRole: function (scope, assignmentGuid) {
        if (this.testMode) return { ok: true, id: assignmentGuid, exists: true };
        var path = scope + '/providers/Microsoft.Authorization/roleAssignments/' + assignmentGuid;
        return this._arm('GET', path, null, '2022-04-01');
    },

    // --- Internal: MID-routed ARM call via the arm credential alias. -----------
    _arm: function (method, path, body, apiVersionOverride) {
        try {
            var ver = apiVersionOverride || this.armVersion;
            var rm = new sn_ws.RESTMessageV2('x_fed_day2_ops.arm', method);
            var url = 'https://management.azure.com' + path +
                      (path.indexOf('?') >= 0 ? '&' : '?') + 'api-version=' + ver;
            rm.setEndpoint(url);
            if (this.midServer) rm.setMIDServer(this.midServer);   // in-boundary execution
            if (body !== null && body !== undefined) rm.setRequestBody(JSON.stringify(body));
            var resp = rm.execute();
            var code = resp.getStatusCode();
            return { ok: code >= 200 && code < 300, status: code, body: resp.getBody() };
        } catch (e) {
            this.log.logErr('_arm ' + method + ' ' + path + ' failed: ' + e);
            return { ok: false, error: '' + e };
        }
    },

    type: 'AzureArmClient'
};
