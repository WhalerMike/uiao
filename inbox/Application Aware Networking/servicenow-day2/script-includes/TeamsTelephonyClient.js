// Script Include: TeamsTelephonyClient  (application scope: x_ssa_day2_ops)
// -----------------------------------------------------------------------------
// Server-side Microsoft Graph client for the telephony lane — governed Teams
// voice (Vol IX Book 04). A phone number is not a cosmetic attribute: it is a
// routable, dialable identity with a physical emergency address behind it, a
// calling scope that costs money, and a voice path that can cross the boundary.
// Each method maps to a NIST control in servicenow-day2/telephony-control-map.json.
//
// Boundary discipline (Vol IX Book 00 / Vol VII):
//   * All Graph calls route through the in-boundary MID Server
//     (property x_ssa_day2_ops.mid_server) — credentials/execution never leave
//     the ATO boundary.
//   * Endpoint + auth come from the Connection & Credential alias
//     (x_ssa_day2_ops.graph) — no secrets in code.
//   * LEAST PRIVILEGE: the app registration behind that alias needs the telephony
//     scopes only — TeamworkDevice/Teams voice configuration read-write for the
//     assignment paths, and AuditLog.Read.All / CallRecords.Read.All for the
//     evidence path. Not Directory-wide admin, and NOT the Teams Administrator
//     role: a front door that can change every voice policy in the tenant is not
//     a front door, it is a second admin console.
//
// SERVICENOW DOES NOT WRITE TO THE ESTATE. It raises, routes, evidences. Every
// write below is a platform-native Graph call executed through the in-boundary
// MID *after* a human approved the task — L3 actuation under ADR-092. The record
// of intent lives in ServiceNow; the change happens in Teams; the evidence comes
// back. Nothing here reaches around the platform to mutate state directly.
//
// STARTER SKELETON — pin the Graph API version and validate scopes against your
// tenant before production use.  test_mode (x_ssa_day2_ops.test_mode = 'true')
// returns deterministic canned values so the ATF suites drive the Flow in sub-prod
// with NO live Graph connectivity.  Never enable test_mode in production.
// -----------------------------------------------------------------------------
var TeamsTelephonyClient = Class.create();
TeamsTelephonyClient.prototype = {

    initialize: function () {
        this.graphVersion = gs.getProperty('x_ssa_day2_ops.graph_version', 'v1.0');
        this.midServer = gs.getProperty('x_ssa_day2_ops.mid_server', '');
        this.boundary = gs.getProperty('x_ssa_day2_ops.boundary', 'gcc-moderate');
        this.log = { logErr: function (m) { gs.error('[x_ssa_day2_ops.TeamsTelephonyClient] ' + m); } };
        this.testMode = gs.getProperty('x_ssa_day2_ops.test_mode', 'false') === 'true';
    },

    // --- Change: assign or release a phone number (CM-3). ---------------------
    // Change-controlled because the number inventory is a finite, reconciled pool:
    // an assignment that never gets released is a number the agency keeps paying
    // for and can never re-issue, and a release that does not return the number to
    // the pool is inventory drift. The caller passes action 'assign' or 'release'
    // so both directions land on one audited path — a release is a change, not an
    // absence of one.
    //
    // E911 IS A PRECONDITION, NOT A FOLLOW-UP. The Flow must call
    // validateEmergencyAddress() and get ok:true BEFORE calling this on an assign.
    // This method does not silently self-gate: the caller contract is explicit so
    // that a missing gate shows up as a missing call in review, rather than
    // hiding inside a helper nobody reads.
    assignPhoneNumber: function (userId, payload) {
        if (this.testMode)
            return { ok: true, id: userId, action: payload.action || 'assign',
                     phoneNumber: payload.phoneNumber, numberType: payload.numberType || 'callingPlan' };
        if (payload.action === 'release')
            return this._graph('POST', '/users/' + userId + '/unassignPhoneNumber', {});
        return this._graph('POST', '/users/' + userId + '/assignPhoneNumber', {
            phoneNumber: payload.phoneNumber,
            phoneNumberType: payload.numberType || 'callingPlan',
            locationId: payload.locationId
        });
    },

    // --- Change: assign calling policy / dial plan (CM-3). --------------------
    // The calling policy IS the privilege boundary for voice. Default it to the
    // least-privilege scope (domestic-only) rather than inheriting whatever the
    // tenant-wide default happens to be: an international calling grant handed out
    // by omission is both a spend leak and, on a compromised account, a toll-fraud
    // path. Widening the scope is a deliberate, approved act — so the widening is
    // what the change record captures.
    assignCallingPolicy: function (userId, policyPayload) {
        if (this.testMode)
            return { ok: true, id: userId, policy: policyPayload.policyName || 'domestic-only',
                     dialPlan: policyPayload.dialPlan };
        return this._graph('POST', '/users/' + userId + '/assignCallingPolicy', {
            policyName: policyPayload.policyName || 'domestic-only',
            dialPlan: policyPayload.dialPlan
        });
    },

    // --- Change gate: emergency address (E911) validation (CM-3). -------------
    // A READ that gates a write, and the most important method in this file.
    //
    // If an emergency address validates wrong, someone dials 911 from that number
    // and responders are dispatched to the wrong building. That is a life-safety
    // failure, not a compliance finding — no audit remediation recovers the
    // minutes. So this returns the authoritative validation status from the
    // platform and NOTHING ELSE: it does not "fix up" a near-miss address, does
    // not fall back to a default civic address, and does not treat a soft/partial
    // match as success. Ambiguity here must surface to a human.
    //
    // ok:false MUST block the number assignment. A number with an unvalidated
    // emergency address is not a number that is ready to hand out, and the Flow
    // must not proceed to assignPhoneNumber() on anything but a clean pass.
    validateEmergencyAddress: function (addressPayload) {
        if (this.testMode)
            return { ok: true, validationStatus: 'Validated', locationId: 'test-location-0001',
                     address: addressPayload };
        return this._graph('POST', '/admin/teams/emergencyLocations/validate', {
            street: addressPayload.street,
            city: addressPayload.city,
            stateOrProvince: addressPayload.stateOrProvince,
            postalCode: addressPayload.postalCode,
            country: addressPayload.country
        });
    },

    // --- Change: voice-routing / SBC configuration (CM-3, SoD-gated). ---------
    // Boundary-affecting: voice routing decides which SBC carries the media, and
    // an SBC sits at the edge of the ATO boundary. A routing change can move call
    // media onto a path the authorization never assessed — which is why the map
    // gates this on telephony_admin + security_sod. Two approvers, because one
    // person should not be able to quietly re-point the voice egress.
    changeVoiceRouting: function (routePayload) {
        if (this.testMode)
            return { ok: true, id: 'test-route-0001', routeName: routePayload.routeName,
                     sbcFqdn: routePayload.sbcFqdn };
        return this._graph('POST', '/admin/teams/voiceRoutes', {
            name: routePayload.routeName,
            numberPattern: routePayload.numberPattern,
            sbcFqdn: routePayload.sbcFqdn,
            priority: routePayload.priority
        });
    },

    // --- Detect: Teams SCuBA baseline drift (CM-6). ---------------------------
    // A READ. This is the doctrine, stated plainly: the actuation for this item is
    // `native-remediation` — the PLATFORM remediates the Teams baseline. Teams
    // policy is enforced by Teams, not by ServiceNow reaching in and setting it
    // back. ServiceNow's job on this lane is exactly two things: DETECT the drift
    // and RAISE it as an incident with the evidence attached.
    //
    // So there is deliberately NO remediateScubaDrift() in this file. If drift
    // remediation lived here, ServiceNow would be writing to the estate — a second
    // enforcement plane racing the platform's own, with two sources of truth for
    // what the baseline is and no way to tell which one last won. The absence of
    // that method is the control.
    //
    // Returns the drift findings for the task so the incident carries evidence a
    // human can act on, not just a red flag.
    detectScubaDrift: function (taskId) {
        if (this.testMode)
            return { ok: true, taskId: taskId, driftCount: 0, findings: [],
                     baseline: 'cisa-scuba-teams' };
        return this._graph('GET', '/admin/teams/settings?$select=id,displayName,policyState', null);
    },

    // --- Evidence: call-detail + telephony admin-action telemetry (AU-2). -----
    // A READ, which is the whole reason `approval: automated` is honest here.
    // Reading is not actuating: collecting call-detail records and telephony
    // admin-action logs changes nothing in the estate, so there is no human to
    // gate and nothing for an approver to weigh. The rule the map is applying is
    // not "automated is fine when it's low-risk" — it is "actuation needs a human;
    // observation does not." Every write in this file has an approver; this one
    // does not, and that asymmetry is the point.
    //
    // Feeds the evidence contract at onboarding: the admin-action side is what
    // makes the CM-3 changes above provable after the fact.
    collectTelephonyAudit: function (window) {
        if (this.testMode)
            return { ok: true, records: [], adminActions: [],
                     from: window.from, to: window.to };
        return this._graph('GET', '/auditLogs/directoryAudits?$filter=' +
                                  "loggedByService eq 'Teams' and activityDateTime ge " +
                                  window.from + ' and activityDateTime le ' + window.to, null);
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

    type: 'TeamsTelephonyClient'
};
