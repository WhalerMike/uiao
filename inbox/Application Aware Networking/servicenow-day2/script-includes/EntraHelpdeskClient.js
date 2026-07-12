// Script Include: EntraHelpdeskClient  (application scope: x_ssa_day2_ops)
// -----------------------------------------------------------------------------
// Server-side Microsoft Graph client for the ServiceNow Day-2 Operations app
// (Vol IX). Wraps the common Entra / M365 helpdesk actions as scoped, audited
// operations — joiner/mover/leaver, credential resets, group & license grants,
// guest invites. Each maps to a NIST control in servicenow-day2/helpdesk-control-map.json.
//
// Boundary discipline (Vol IX Book 00 / Vol VII):
//   * All Graph calls route through the in-boundary MID Server
//     (property x_ssa_day2_ops.mid_server) — credentials/execution never leave
//     the ATO boundary.
//   * Endpoint + auth come from a Connection & Credential alias
//     (x_ssa_day2_ops.graph) — no secrets in code.
//   * The app registration behind that alias holds LEAST-PRIVILEGE, individually
//     consented Graph scopes (e.g. User.ReadWrite.All, Group.ReadWrite.All,
//     UserAuthenticationMethod.ReadWrite.All) — never Directory-wide admin.
//   * Under GCC Moderate the Graph host resolves to the commercial endpoint that
//     serves that boundary (ADR-033): graph.microsoft.com. GCC High / DoD are not
//     offered here.
//
// STARTER SKELETON — pin the Graph API version and validate scopes against your
// tenant before production use.  test_mode (x_ssa_day2_ops.test_mode = 'true')
// returns deterministic canned values so the ATF suites drive the Flow in sub-prod
// with NO live Graph connectivity.  Never enable test_mode in production.
// -----------------------------------------------------------------------------
var EntraHelpdeskClient = Class.create();
EntraHelpdeskClient.prototype = {

    initialize: function () {
        this.graphVersion = gs.getProperty('x_ssa_day2_ops.graph_version', 'v1.0');
        this.midServer = gs.getProperty('x_ssa_day2_ops.mid_server', '');
        this.boundary = gs.getProperty('x_ssa_day2_ops.boundary', 'gcc-moderate');
        this.log = new GSLog('x_ssa_day2_ops.log', 'EntraHelpdeskClient');
        this.testMode = gs.getProperty('x_ssa_day2_ops.test_mode', 'false') === 'true';
    },

    // --- Joiner: create a user from the HRIT SSOT baseline (AC-2). ------------
    createUser: function (payload) {
        if (this.testMode) return { ok: true, id: 'test-user-0001', upn: payload.upn };
        return this._graph('POST', '/users', payload);
    },

    // --- Leaver: evidenced de-provision (AC-2). Disable, revoke sessions. -----
    disableUser: function (userId) {
        if (this.testMode) return { ok: true, id: userId, accountEnabled: false };
        var r = this._graph('PATCH', '/users/' + userId, { accountEnabled: false });
        // Revoke refresh tokens / active sessions so the disable takes effect now.
        this._graph('POST', '/users/' + userId + '/revokeSignInSessions', {});
        return r;
    },

    // --- Credential: reset password / MFA method, unlock (IA-5). --------------
    resetPassword: function (userId, opts) {
        if (this.testMode) return { ok: true, id: userId, action: 'password-reset' };
        // Prefer SSPR; this admin path is the approver-gated fallback.
        return this._graph('PATCH', '/users/' + userId, {
            passwordProfile: { forceChangePasswordNextSignIn: true, password: opts.tempPassword }
        });
    },

    resetMfaMethod: function (userId, methodId) {
        if (this.testMode) return { ok: true, id: userId, action: 'mfa-reset' };
        return this._graph('DELETE', '/users/' + userId + '/authentication/methods/' + methodId, null);
    },

    // --- Access: group membership + license (AC-6 / AC-2). --------------------
    addGroupMember: function (groupId, userId) {
        if (this.testMode) return { ok: true, groupId: groupId, memberId: userId };
        return this._graph('POST', '/groups/' + groupId + '/members/$ref', {
            '@odata.id': 'https://graph.microsoft.com/' + this.graphVersion + '/directoryObjects/' + userId
        });
    },

    assignLicense: function (userId, skuId) {
        if (this.testMode) return { ok: true, id: userId, sku: skuId };
        return this._graph('POST', '/users/' + userId + '/assignLicense',
            { addLicenses: [{ skuId: skuId }], removeLicenses: [] });
    },

    // --- Guest / B2B invite (AC-2). ------------------------------------------
    inviteGuest: function (email, redirectUrl) {
        if (this.testMode) return { ok: true, invitedUser: { id: 'test-guest-0001' } };
        return this._graph('POST', '/invitations',
            { invitedUserEmailAddress: email, inviteRedirectUrl: redirectUrl, sendInvitationMessage: true });
    },

    // --- Internal: MID-routed Graph call via the credential alias. ------------
    _graph: function (method, path, body) {
        try {
            var rm = new sn_ws.RESTMessageV2('x_ssa_day2_ops.graph', method);
            rm.setStringParameterNoEscape('graph_version', this.graphVersion);
            rm.setEndpoint('https://graph.microsoft.com/' + this.graphVersion + path);
            if (this.midServer) rm.setMIDServer(this.midServer);   // in-boundary execution
            if (body !== null && body !== undefined) rm.setRequestBody(JSON.stringify(body));
            var resp = rm.execute();
            var code = resp.getStatusCode();
            return { ok: code >= 200 && code < 300, status: code, body: resp.getBody() };
        } catch (e) {
            this.log.logErr('_graph ' + method + ' ' + path + ' failed: ' + e);
            return { ok: false, error: '' + e };
        }
    },

    type: 'EntraHelpdeskClient'
};
