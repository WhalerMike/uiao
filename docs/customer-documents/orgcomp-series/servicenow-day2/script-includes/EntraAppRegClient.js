// Script Include: EntraAppRegClient  (application scope: x_fed_day2_ops)
// -----------------------------------------------------------------------------
// Server-side Microsoft Graph client for Lane E — App Registration Governance
// (Vol IX Book 03). An app registration is a workload identity: a service
// principal with credentials and consented permissions. Left ungoverned it is a
// standing, unowned, un-expiring grant. Each method maps to a NIST control in
// servicenow-day2/appreg-control-map.json.
//
// Boundary discipline (Vol IX Book 00 / Vol VII):
//   * All Graph calls route through the in-boundary MID Server
//     (property x_fed_day2_ops.mid_server) — credentials/execution never leave
//     the ATO boundary.
//   * Endpoint + auth come from the Connection & Credential alias
//     (x_fed_day2_ops.graph) — no secrets in code.
//   * LEAST PRIVILEGE: the app registration behind that alias needs
//     Application.ReadWrite.OwnedBy (NOT Application.ReadWrite.All) and
//     AppRoleAssignment.ReadWrite.All. OwnedBy scopes this client to the
//     registrations the app itself owns — a governed front door must not be able
//     to rewrite every registration in the tenant.
//
// CREDENTIALS ARE NOT ISSUED HERE. Certificate issuance and rotation are the
// ACME client's job (AcmeCredentialClient, acme-via-mid). This client never adds
// a client secret: the "no long-lived secrets" rule in Vol IX Book 03 is the
// single highest-value rule in that book, and the way to keep it is to give this
// client no method that can break it.
//
// STARTER SKELETON — pin the Graph API version and validate scopes against your
// tenant before production use.  test_mode (x_fed_day2_ops.test_mode = 'true')
// returns deterministic canned values so the ATF suites drive the Flow in sub-prod
// with NO live Graph connectivity.  Never enable test_mode in production.
// -----------------------------------------------------------------------------
var EntraAppRegClient = Class.create();
EntraAppRegClient.prototype = {

    initialize: function () {
        this.graphVersion = gs.getProperty('x_fed_day2_ops.graph_version', 'v1.0');
        this.midServer = gs.getProperty('x_fed_day2_ops.mid_server', '');
        this.boundary = gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate');
        this.log = { logErr: function (m) { gs.error('[x_fed_day2_ops.EntraAppRegClient] ' + m); } };
        this.testMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
    },

    // --- Request: register the workload identity (AC-2). ----------------------
    // The governed request captures owner, purpose and the SPECIFIC scopes needed
    // BEFORE any credential exists. `owners` is required by the caller contract:
    // an ownerless registration is the orphan Vol IX Book 03 exists to prevent.
    createApplication: function (payload) {
        if (this.testMode)
            return { ok: true, id: 'test-app-0001', appId: 'test-appid-0001',
                     displayName: payload.displayName };
        var r = this._graph('POST', '/applications', {
            displayName: payload.displayName,
            signInAudience: payload.signInAudience || 'AzureADMyOrg',
            notes: payload.purpose
        });
        return r;
    },

    // --- Request: the service principal for the registration (AC-2). ----------
    createServicePrincipal: function (appId) {
        if (this.testMode) return { ok: true, id: 'test-sp-0001', appId: appId };
        return this._graph('POST', '/servicePrincipals', { appId: appId });
    },

    // --- Request: bind an accountable owner (AC-2). ---------------------------
    // Ownership is what makes attestation possible; without it a registration
    // cannot be re-attested and becomes an orphan.
    addOwner: function (applicationObjectId, ownerId) {
        if (this.testMode) return { ok: true, id: applicationObjectId, ownerId: ownerId };
        return this._graph('POST', '/applications/' + applicationObjectId + '/owners/$ref', {
            '@odata.id': 'https://graph.microsoft.com/' + this.graphVersion +
                         '/directoryObjects/' + ownerId
        });
    },

    // --- Consent: scoped, admin-consented app-role assignment (AC-6). ---------
    // Scoped consent only — one resource, the specific app roles requested. There
    // is deliberately no "grant everything" path: blanket delegation is what this
    // lane exists to refuse.
    grantAppRoleAssignment: function (servicePrincipalId, resourceId, appRoleId) {
        if (this.testMode)
            return { ok: true, id: 'test-assignment-0001', principalId: servicePrincipalId,
                     resourceId: resourceId, appRoleId: appRoleId };
        return this._graph('POST', '/servicePrincipals/' + servicePrincipalId + '/appRoleAssignedTo', {
            principalId: servicePrincipalId, resourceId: resourceId, appRoleId: appRoleId
        });
    },

    // --- Attest: read ownership + scope for the attestation cadence (AC-6). ---
    // A read, not a write: attestation asks "is this still owned, still needed,
    // still scoped?" and routes the answer to a human. It never self-remediates.
    getApplication: function (applicationObjectId) {
        if (this.testMode)
            return { ok: true, id: applicationObjectId, displayName: 'test-app',
                     owners: ['test-owner-0001'], keyCredentials: [] };
        return this._graph('GET', '/applications/' + applicationObjectId +
                                  '?$expand=owners&$select=id,displayName,keyCredentials,passwordCredentials', null);
    },

    // --- Attest: orphaned/expired sweep input (AC-6). -------------------------
    listOwnedApplications: function () {
        if (this.testMode) return { ok: true, value: [{ id: 'test-app-0001', owners: [] }] };
        return this._graph('GET', '/applications?$expand=owners&$select=id,displayName,keyCredentials', null);
    },

    // --- Internal: MID-routed Graph call via the credential alias. ------------
    _graph: function (method, path, body) {
        try {
            var rm = new sn_ws.RESTMessageV2('x_fed_day2_ops.graph', method);
            rm.setStringParameterNoEscape('graph_version', this.graphVersion);
            rm.setEndpoint('https://graph.microsoft.com/' + this.graphVersion + path);
            if (this.midServer) rm.setMIDServer(this.midServer);   // in-boundary execution
            if (body !== null && body !== undefined) rm.setRequestBody(JSON.stringify(body));
            var resp = rm.execute();
            var code = resp.getStatusCode();
            return { ok: code >= 200 && code < 300, status: code, body: resp.getBody() };
        } catch (e) {
            this.log.logErr('_graph ' + method + ' ' + path + ' failed: ' + ('' + e).replace(/[\r\n]+/g, ' ').slice(0, 500));
            return { ok: false, error: '' + e };
        }
    },

    type: 'EntraAppRegClient'
};
